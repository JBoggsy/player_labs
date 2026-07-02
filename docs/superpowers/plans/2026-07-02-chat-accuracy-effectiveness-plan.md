# Chat Accuracy & Effectiveness Study Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a field-wide dataset + report answering (1) how accurate crew
chat accusations are vs. ground-truth imposter identity, and (2) how
effective accusations (crew + imposter) are at moving votes/ejections and
correlating with win rate — broken down per player/policy across Crewrift
Prime.

**Architecture:** A small `crewrift_lab/chat_effectiveness/tools/` package
with four pure-function modules (outcomes join, accusation extraction,
metrics, detector validation) plus a report renderer, each independently
testable on synthetic data. The final task wires them to real data: a fresh
~20-round Prime pull, the existing historical suspicion_lab corpus as a
cross-check, and the event-warehouse's `suss` job for detector validation.

**Tech Stack:** Python 3, pandas + pyarrow (parquet, already a repo
dependency via suspicion_lab), pytest. Reuses
`crewrift_lab/suspicion_lab/tools/{replay_parse,features}.py` read-only.

## Global Constraints

- Spec: `crewrift_lab/docs/designs/2026-07-02-chat-accuracy-effectiveness-design.md`.
- No changes to crewborg runtime code or committed suspicion model weights.
- No changes to `suspicion_lab/tools/{replay_parse,features}.py` (read-only
  imports only).
- All results are observational/associational — every report artifact must
  say so explicitly, never implying causation.
- All work happens in the worktree created in Task 0
  (`.claude/worktrees/chat-accuracy-effectiveness`,
  branch `worktree-chat-accuracy-effectiveness`) — do not touch `main`
  directly.
- The join key across every table in this plan is **`episode`** = the
  corpus/expanded-replay directory-or-file stem (e.g.
  `20260623T200341_ereq_d695988a-02`) — confirmed by
  `expand_corpus.py:85` (`out_path = args.out / f"{ep_dir.name}.jsonl.gz"`)
  and matched by `replay_parse.parse_game`'s default `episode` (path stem).
  Never use `episode.json`'s internal `episode_id`/`id` fields as the join
  key — they don't correspond to the corpus directory name.

---

### Task 0: Create the isolated worktree

**Files:** none (git operation only).

- [ ] **Step 1: Create the worktree and branch**

```bash
cd /Users/jamesboggs/coding/personal_labs
git worktree add .claude/worktrees/chat-accuracy-effectiveness -b worktree-chat-accuracy-effectiveness
```

Expected: `Preparing worktree (new branch 'worktree-chat-accuracy-effectiveness')` and a new directory at `.claude/worktrees/chat-accuracy-effectiveness`.

- [ ] **Step 2: Verify the worktree is on the right commit and clean**

```bash
cd .claude/worktrees/chat-accuracy-effectiveness && git status && git log -1 --oneline
```

Expected: `nothing to commit, working tree clean` and the log line matching the current `main` tip (the design-doc commit, `948393c` or later).

All subsequent tasks run inside `.claude/worktrees/chat-accuracy-effectiveness`, not the primary checkout.

---

### Task 1: Per-slot ground-truth outcomes (`episode_outcomes.py`)

**Files:**
- Create: `crewrift_lab/chat_effectiveness/tools/episode_outcomes.py`
- Test: `crewrift_lab/chat_effectiveness/tests/test_episode_outcomes.py`

**Interfaces:**
- Produces: `parse_episode_outcome(episode_dir: Path) -> list[dict]`, each
  dict with keys `episode, slot, policy_name, policy_version, role, win,
  score` (`role` is `"imposter"` or `"crew"`; `episode` is `episode_dir.name`).
  Also `build_outcomes_table(episodes_root: Path) -> pandas.DataFrame` with
  the same columns, one row per (episode, slot) across every subdirectory of
  `episodes_root` that has both `episode.json` and `results.json`.

- [ ] **Step 1: Write the failing test**

```python
# crewrift_lab/chat_effectiveness/tests/test_episode_outcomes.py
import json
import sys
from pathlib import Path

import pandas as pd

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from episode_outcomes import build_outcomes_table, parse_episode_outcome  # noqa: E402

EPISODE_JSON = {
    "id": "ep_opaque_internal_id",
    "episode_id": "also_opaque",
    "participants": [
        {"position": 0, "policy_name": "crewborg", "version": 89, "player_name": "James"},
        {"position": 1, "policy_name": "notsus", "version": 168, "player_name": "Andre"},
    ],
}

RESULTS_JSON = {
    "names": ["James", "Andre"],
    "scores": [108, 20],
    "win": [True, False],
    "tasks": [8, 0],
    "kills": [0, 2],
    "imposter": [0, 1],
    "crew": [1, 0],
}


def _write_episode_dir(root: Path, name: str) -> Path:
    d = root / name
    d.mkdir()
    (d / "episode.json").write_text(json.dumps(EPISODE_JSON))
    (d / "results.json").write_text(json.dumps(RESULTS_JSON))
    return d


def test_parse_episode_outcome_uses_dir_name_as_episode_key(tmp_path):
    d = _write_episode_dir(tmp_path, "20260702T000000_ereq_abc123-01")

    rows = parse_episode_outcome(d)

    assert len(rows) == 2
    assert rows[0]["episode"] == "20260702T000000_ereq_abc123-01"
    assert rows[0]["slot"] == 0
    assert rows[0]["policy_name"] == "crewborg"
    assert rows[0]["policy_version"] == 89
    assert rows[0]["role"] == "crew"
    assert rows[0]["win"] is True
    assert rows[0]["score"] == 108
    assert rows[1]["role"] == "imposter"
    assert rows[1]["win"] is False


def test_build_outcomes_table_across_multiple_episode_dirs(tmp_path):
    _write_episode_dir(tmp_path, "ep_one")
    _write_episode_dir(tmp_path, "ep_two")
    (tmp_path / "not_an_episode").mkdir()  # no episode.json/results.json — must be skipped

    df = build_outcomes_table(tmp_path)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 4
    assert set(df["episode"]) == {"ep_one", "ep_two"}
    assert list(df.columns) == [
        "episode", "slot", "policy_name", "policy_version", "role", "win", "score",
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/worktrees/chat-accuracy-effectiveness && uv run pytest crewrift_lab/chat_effectiveness/tests/test_episode_outcomes.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'episode_outcomes'` (file doesn't exist yet).

- [ ] **Step 3: Write the implementation**

```python
# crewrift_lab/chat_effectiveness/tools/episode_outcomes.py
"""Per-(episode, slot) ground-truth outcomes: policy identity, role, win.

Reads a downloaded episode directory's episode.json (policy identity per
seat) and results.json (per-slot win/role arrays) into one row per seat.
The join key is the episode directory's own name (matches
expand_corpus.py's `<ep_dir.name>.jsonl.gz` output and
replay_parse.parse_game's default episode-from-path-stem) — NOT
episode.json's internal id/episode_id fields, which don't correspond to it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

OUTCOME_COLUMNS = ["episode", "slot", "policy_name", "policy_version", "role", "win", "score"]


def _policy_by_position(episode: dict) -> dict[int, dict]:
    """slot/position -> {policy_name, policy_version, player_name}."""
    by_position: dict[int, dict] = {}
    for pt in episode.get("participants", []):
        by_position[pt["position"]] = {
            "policy_name": pt["policy_name"],
            "policy_version": pt["version"],
            "player_name": pt.get("player_name", ""),
        }
    if by_position:
        return by_position
    # League-shaped episode.json fallback (policy_results[] instead of
    # participants[]) — unverified against real local data as of this plan;
    # confirm against a real league-scraped episode.json before trusting it.
    for pr in episode.get("policy_results", []):
        by_position[pr["position"]] = {
            "policy_name": pr["policy"]["name"],
            "policy_version": pr["policy"]["version"],
            "player_name": pr.get("policy", {}).get("player_name", ""),
        }
    return by_position


def parse_episode_outcome(episode_dir: Path) -> list[dict]:
    episode = json.loads((episode_dir / "episode.json").read_text())
    results = json.loads((episode_dir / "results.json").read_text())
    episode_key = episode_dir.name
    policies = _policy_by_position(episode)

    rows: list[dict] = []
    for slot in range(len(results["win"])):
        policy = policies.get(slot, {"policy_name": "", "policy_version": None, "player_name": ""})
        rows.append(
            {
                "episode": episode_key,
                "slot": slot,
                "policy_name": policy["policy_name"],
                "policy_version": policy["policy_version"],
                "role": "imposter" if results["imposter"][slot] else "crew",
                "win": bool(results["win"][slot]),
                "score": results["scores"][slot],
            }
        )
    return rows


def build_outcomes_table(episodes_root: Path) -> pd.DataFrame:
    rows: list[dict] = []
    for d in sorted(episodes_root.iterdir()):
        if not d.is_dir():
            continue
        if not (d / "episode.json").exists() or not (d / "results.json").exists():
            continue
        rows.extend(parse_episode_outcome(d))
    return pd.DataFrame(rows, columns=OUTCOME_COLUMNS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the per-slot outcomes table.")
    parser.add_argument("--episodes", type=Path, required=True, help="Dir of episode subdirs (episode.json + results.json each).")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    df = build_outcomes_table(args.episodes)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False)
    print(f"Wrote {len(df)} outcome rows -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/worktrees/chat-accuracy-effectiveness && uv run pytest crewrift_lab/chat_effectiveness/tests/test_episode_outcomes.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
cd .claude/worktrees/chat-accuracy-effectiveness
git add crewrift_lab/chat_effectiveness/tools/episode_outcomes.py crewrift_lab/chat_effectiveness/tests/test_episode_outcomes.py
git commit -m "feat(chat-effectiveness): per-slot ground-truth outcomes from episode.json + results.json"
```

---

### Task 2: Accusation extraction (`extract_accusations.py`)

**Files:**
- Create: `crewrift_lab/chat_effectiveness/tools/extract_accusations.py`
- Test: `crewrift_lab/chat_effectiveness/tests/test_extract_accusations.py`

**Interfaces:**
- Consumes: `replay_parse.Game/Meeting/Vote/ChatLine/PlayerInfo` (from
  `suspicion_lab/tools/replay_parse.py`, imported read-only) and
  `features.chat_stances(game) -> list[StanceTriple]` (from
  `suspicion_lab/tools/features.py`, imported read-only).
- Produces: `extract_accusation_rows(game: Game) -> list[dict]`, one row per
  accusation/defense `StanceTriple`, columns: `episode, meeting_idx,
  call_tick, speaker_slot, speaker_role, stance, target_slot, target_role,
  target_is_imposter, target_voted_same_meeting, target_ejected_same_meeting,
  num_candidates`. Every speaker/role is included (crew AND imposter) — unlike
  suspicion_lab's `build_dataset.py`, which restricts to crew observers.

- [ ] **Step 1: Write the failing test**

```python
# crewrift_lab/chat_effectiveness/tests/test_extract_accusations.py
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
SUSPICION_TOOLS = Path(__file__).resolve().parents[3] / "suspicion_lab" / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(SUSPICION_TOOLS))

from extract_accusations import extract_accusation_rows  # noqa: E402
from replay_parse import ChatLine, Game, Meeting, PlayerInfo, StateSample, Vote  # noqa: E402


def _game_with_one_meeting() -> Game:
    players = {
        0: PlayerInfo(slot=0, name="P0", color="red", role="crew"),
        1: PlayerInfo(slot=1, name="P1", color="blue", role="imposter"),
        2: PlayerInfo(slot=2, name="P2", color="green", role="crew"),
    }
    states = {
        slot: [StateSample(tick=0, x=0, y=0, room="hall", alive=True, connected=True)]
        for slot in players
    }
    meeting = Meeting(
        call_tick=100,
        caller_slot=0,
        kind="body",
        votes=[
            Vote(tick=110, voter_slot=0, target_slot=1),
            Vote(tick=111, voter_slot=2, target_slot=1),
        ],
        chats=[
            # "blue sus, saw them vent" -> P0 accuses P1 (the actual imposter)
            ChatLine(tick=101, slot=0, text="blue sus, saw them vent"),
        ],
        ejected_slot=1,
        end_tick=120,
    )
    return Game(
        episode="test_ep",
        config={},
        players=players,
        states=states,
        visibility={},
        body_visibility={},
        kills=[],
        bodies=[],
        ejections=[(120, 1)],
        meetings=[meeting],
        task_completions=[],
        vents=[],
        task_sites=[],
        tick_count=120,
        complete=True,
    )


def test_extract_accusation_rows_joins_ground_truth_and_meeting_outcome():
    game = _game_with_one_meeting()

    rows = extract_accusation_rows(game)

    assert len(rows) == 1
    row = rows[0]
    assert row["episode"] == "test_ep"
    assert row["speaker_slot"] == 0
    assert row["speaker_role"] == "crew"
    assert row["stance"] == "accuses"
    assert row["target_slot"] == 1
    assert row["target_role"] == "imposter"
    assert row["target_is_imposter"] is True
    assert row["target_voted_same_meeting"] is True
    assert row["target_ejected_same_meeting"] is True
    assert row["num_candidates"] == 2  # P1 and P2, excluding the speaker P0


def test_extract_accusation_rows_returns_empty_for_no_meetings():
    game = _game_with_one_meeting()
    game.meetings = []

    assert extract_accusation_rows(game) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/worktrees/chat-accuracy-effectiveness && uv run pytest crewrift_lab/chat_effectiveness/tests/test_extract_accusations.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'extract_accusations'`.

- [ ] **Step 3: Write the implementation**

```python
# crewrift_lab/chat_effectiveness/tools/extract_accusations.py
"""Extract (speaker, stance, target) accusation events per meeting, joined to
same-meeting vote/ejection outcomes and ground-truth roles — for ALL
speakers (crew and imposter), unlike suspicion_lab's build_dataset.py, which
aggregates crew-observer-only, prior-meetings-only cumulative features for
training crewborg's own suspicion model.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

SUSPICION_LAB_TOOLS = Path(__file__).resolve().parents[2] / "suspicion_lab" / "tools"
sys.path.insert(0, str(SUSPICION_LAB_TOOLS))
from features import chat_stances  # noqa: E402
from replay_parse import Game, parse_game  # noqa: E402

ACCUSATION_COLUMNS = [
    "episode", "meeting_idx", "call_tick", "speaker_slot", "speaker_role",
    "stance", "target_slot", "target_role", "target_is_imposter",
    "target_voted_same_meeting", "target_ejected_same_meeting", "num_candidates",
]


def _alive_at(game: Game, slot: int, tick: int) -> bool:
    state = game.state_at(slot, tick)
    return bool(state and state.alive and state.connected)


def extract_accusation_rows(game: Game) -> list[dict]:
    if not game.players or not game.meetings:
        return []
    stances = chat_stances(game)
    rows: list[dict] = []
    for triple in stances:
        meeting = game.meetings[triple.meeting_idx]
        speaker = game.players.get(triple.speaker_slot)
        target = game.players.get(triple.target_slot)
        if speaker is None or target is None:
            continue
        candidates = [
            slot for slot in game.players
            if slot != triple.speaker_slot and _alive_at(game, slot, meeting.call_tick)
        ]
        rows.append(
            {
                "episode": game.episode,
                "meeting_idx": triple.meeting_idx,
                "call_tick": meeting.call_tick,
                "speaker_slot": triple.speaker_slot,
                "speaker_role": speaker.role,
                "stance": triple.stance,
                "target_slot": triple.target_slot,
                "target_role": target.role,
                "target_is_imposter": target.role == "imposter",
                "target_voted_same_meeting": any(v.target_slot == triple.target_slot for v in meeting.votes),
                "target_ejected_same_meeting": meeting.ejected_slot == triple.target_slot,
                "num_candidates": len(candidates),
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract accusation events from expanded replays.")
    parser.add_argument("--expanded", type=Path, required=True, help="Dir of *.jsonl(.gz) expanded replays.")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)

    paths = sorted(list(args.expanded.glob("*.jsonl.gz")) + list(args.expanded.glob("*.jsonl")))
    if args.limit:
        paths = paths[: args.limit]
    if not paths:
        sys.exit(f"No expanded episodes in {args.expanded}")

    all_rows: list[dict] = []
    skipped = 0
    for i, path in enumerate(paths):
        try:
            game = parse_game(path)
            if not game.complete:
                skipped += 1
                continue
            all_rows.extend(extract_accusation_rows(game))
        except Exception as exc:  # noqa: BLE001 - skip corrupt games, keep building
            print(f"  skip {path.name}: {exc}", file=sys.stderr)
            skipped += 1
        if (i + 1) % 100 == 0:
            print(f"  …{i + 1}/{len(paths)} episodes, {len(all_rows)} rows", file=sys.stderr)

    df = pd.DataFrame(all_rows, columns=ACCUSATION_COLUMNS)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False)
    print(f"Wrote {len(df)} accusation rows from {len(paths) - skipped} games ({skipped} skipped) -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/worktrees/chat-accuracy-effectiveness && uv run pytest crewrift_lab/chat_effectiveness/tests/test_extract_accusations.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
cd .claude/worktrees/chat-accuracy-effectiveness
git add crewrift_lab/chat_effectiveness/tools/extract_accusations.py crewrift_lab/chat_effectiveness/tests/test_extract_accusations.py
git commit -m "feat(chat-effectiveness): extract same-meeting accusation/vote/eject rows for all speakers"
```

---

### Task 3: Metrics (`metrics.py`)

**Files:**
- Create: `crewrift_lab/chat_effectiveness/tools/metrics.py`
- Test: `crewrift_lab/chat_effectiveness/tests/test_metrics.py`

**Interfaces:**
- Consumes: the `episode, slot, policy_name, policy_version, role, win,
  score` DataFrame from Task 1, and the `episode, meeting_idx, call_tick,
  speaker_slot, speaker_role, stance, target_slot, target_role,
  target_is_imposter, target_voted_same_meeting, target_ejected_same_meeting,
  num_candidates` DataFrame from Task 2.
- Produces: `enrich_accusations(accusations, outcomes) -> DataFrame` (adds
  `speaker_policy, speaker_win, target_policy`);
  `crew_accuracy_table(enriched) -> DataFrame` (`speaker_policy, n,
  accuracy`); `effectiveness_table(enriched) -> DataFrame`
  (`speaker_policy, speaker_role, n, p_target_voted, p_target_ejected,
  mean_baseline_rate`); `winrate_association_table(enriched, outcomes) ->
  DataFrame` (`policy_name, role, seat_games, seat_win_rate,
  accusations_made, accuracy`).

- [ ] **Step 1: Write the failing test**

```python
# crewrift_lab/chat_effectiveness/tests/test_metrics.py
import sys
from pathlib import Path

import pandas as pd

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from metrics import (  # noqa: E402
    crew_accuracy_table,
    effectiveness_table,
    enrich_accusations,
    winrate_association_table,
)

OUTCOMES = pd.DataFrame(
    [
        {"episode": "ep1", "slot": 0, "policy_name": "crewborg", "policy_version": 89, "role": "crew", "win": True, "score": 108},
        {"episode": "ep1", "slot": 1, "policy_name": "notsus", "policy_version": 168, "role": "imposter", "win": False, "score": 20},
        {"episode": "ep2", "slot": 0, "policy_name": "crewborg", "policy_version": 89, "role": "crew", "win": False, "score": 10},
        {"episode": "ep2", "slot": 1, "policy_name": "notsus", "policy_version": 168, "role": "imposter", "win": True, "score": 108},
    ]
)

ACCUSATIONS = pd.DataFrame(
    [
        {
            "episode": "ep1", "meeting_idx": 0, "call_tick": 100, "speaker_slot": 0,
            "speaker_role": "crew", "stance": "accuses", "target_slot": 1,
            "target_role": "imposter", "target_is_imposter": True,
            "target_voted_same_meeting": True, "target_ejected_same_meeting": True,
            "num_candidates": 1,
        },
        {
            "episode": "ep2", "meeting_idx": 0, "call_tick": 100, "speaker_slot": 0,
            "speaker_role": "crew", "stance": "accuses", "target_slot": 1,
            "target_role": "imposter", "target_is_imposter": True,
            "target_voted_same_meeting": False, "target_ejected_same_meeting": False,
            "num_candidates": 1,
        },
    ]
)


def test_enrich_accusations_adds_policy_identity_and_win():
    enriched = enrich_accusations(ACCUSATIONS, OUTCOMES)

    assert list(enriched["speaker_policy"]) == ["crewborg", "crewborg"]
    assert list(enriched["target_policy"]) == ["notsus", "notsus"]
    assert list(enriched["speaker_win"]) == [True, False]


def test_crew_accuracy_table_is_perfect_for_this_fixture():
    enriched = enrich_accusations(ACCUSATIONS, OUTCOMES)

    table = crew_accuracy_table(enriched)

    row = table[table.speaker_policy == "crewborg"].iloc[0]
    assert row["n"] == 2
    assert row["accuracy"] == 1.0


def test_effectiveness_table_reports_half_voted_half_ejected():
    enriched = enrich_accusations(ACCUSATIONS, OUTCOMES)

    table = effectiveness_table(enriched)

    row = table[(table.speaker_policy == "crewborg") & (table.speaker_role == "crew")].iloc[0]
    assert row["n"] == 2
    assert row["p_target_voted"] == 0.5
    assert row["p_target_ejected"] == 0.5


def test_winrate_association_table_includes_zero_accusation_policies():
    enriched = enrich_accusations(ACCUSATIONS, OUTCOMES)

    table = winrate_association_table(enriched, OUTCOMES)

    crewborg_row = table[(table.policy_name == "crewborg") & (table.role == "crew")].iloc[0]
    assert crewborg_row["seat_games"] == 2
    assert crewborg_row["seat_win_rate"] == 0.5
    assert crewborg_row["accusations_made"] == 2
    notsus_row = table[(table.policy_name == "notsus") & (table.role == "imposter")].iloc[0]
    assert notsus_row["accusations_made"] == 0  # notsus never accused anyone in this fixture
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/worktrees/chat-accuracy-effectiveness && uv run pytest crewrift_lab/chat_effectiveness/tests/test_metrics.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'metrics'`.

- [ ] **Step 3: Write the implementation**

```python
# crewrift_lab/chat_effectiveness/tools/metrics.py
"""Join accusation events to ground-truth outcomes and compute the three
study metrics: crew accusation accuracy, same-meeting effectiveness, and
seat-normalized win-rate association — all per player/policy.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def enrich_accusations(accusations: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    """Add speaker/target policy identity + speaker's win, by (episode, slot)."""
    speaker_cols = outcomes.rename(
        columns={"slot": "speaker_slot", "policy_name": "speaker_policy", "win": "speaker_win"}
    )[["episode", "speaker_slot", "speaker_policy", "speaker_win"]]
    target_cols = outcomes.rename(
        columns={"slot": "target_slot", "policy_name": "target_policy"}
    )[["episode", "target_slot", "target_policy"]]
    enriched = accusations.merge(speaker_cols, on=["episode", "speaker_slot"], how="left")
    enriched = enriched.merge(target_cols, on=["episode", "target_slot"], how="left")
    return enriched


def crew_accuracy_table(enriched: pd.DataFrame) -> pd.DataFrame:
    """Per crew speaker policy: accusation accuracy vs. actual imposter identity."""
    crew_accusations = enriched[(enriched.speaker_role == "crew") & (enriched.stance == "accuses")]
    grouped = crew_accusations.groupby("speaker_policy").agg(
        n=("target_is_imposter", "size"),
        accuracy=("target_is_imposter", "mean"),
    )
    return grouped.reset_index().sort_values("accuracy", ascending=False)


def effectiveness_table(enriched: pd.DataFrame) -> pd.DataFrame:
    """Per (speaker_policy, speaker_role): does an accusation move the room?"""
    accusations = enriched[enriched.stance == "accuses"]
    grouped = accusations.groupby(["speaker_policy", "speaker_role"]).agg(
        n=("target_voted_same_meeting", "size"),
        p_target_voted=("target_voted_same_meeting", "mean"),
        p_target_ejected=("target_ejected_same_meeting", "mean"),
        mean_baseline_rate=("num_candidates", lambda s: (1 / s).mean() if len(s) else float("nan")),
    )
    return grouped.reset_index()


def winrate_association_table(enriched: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    """Per (policy_name, role): seat-normalized win rate vs. accusation volume/accuracy.

    Uses `outcomes` (every seat-game, not just those with an accusation) so a
    policy that never accuses gets an explicit accusations_made=0 row instead
    of being silently absent.
    """
    seat_games = outcomes.groupby(["policy_name", "role"]).agg(
        seat_games=("win", "size"),
        seat_win_rate=("win", "mean"),
    )
    accusations = enriched[enriched.stance == "accuses"]
    accusation_stats = accusations.groupby(["speaker_policy", "speaker_role"]).agg(
        accusations_made=("target_is_imposter", "size"),
        accuracy=("target_is_imposter", "mean"),
    )
    accusation_stats.index = accusation_stats.index.set_names(["policy_name", "role"])
    joined = seat_games.join(accusation_stats, how="left")
    joined["accusations_made"] = joined["accusations_made"].fillna(0).astype(int)
    return joined.reset_index()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute chat-effectiveness metric tables.")
    parser.add_argument("--accusations", type=Path, required=True)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    accusations = pd.read_parquet(args.accusations)
    outcomes = pd.read_parquet(args.outcomes)
    enriched = enrich_accusations(accusations, outcomes)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    crew_accuracy_table(enriched).to_parquet(args.out_dir / "crew_accuracy.parquet", index=False)
    effectiveness_table(enriched).to_parquet(args.out_dir / "effectiveness.parquet", index=False)
    winrate_association_table(enriched, outcomes).to_parquet(args.out_dir / "winrate_association.parquet", index=False)
    print(f"Wrote metric tables -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/worktrees/chat-accuracy-effectiveness && uv run pytest crewrift_lab/chat_effectiveness/tests/test_metrics.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
cd .claude/worktrees/chat-accuracy-effectiveness
git add crewrift_lab/chat_effectiveness/tools/metrics.py crewrift_lab/chat_effectiveness/tests/test_metrics.py
git commit -m "feat(chat-effectiveness): crew accuracy, same-meeting effectiveness, seat-normalized win-rate tables"
```

---

### Task 4: Detector validation (`validate_detector.py`)

**Files:**
- Create: `crewrift_lab/chat_effectiveness/tools/validate_detector.py`
- Test: `crewrift_lab/chat_effectiveness/tests/test_validate_detector.py`

**Interfaces:**
- Consumes: `features.ACCUSE_HINT`, `features.DEFEND_HINT` (public module
  constants from `suspicion_lab/tools/features.py`, imported read-only —
  the color-matching helper is re-derived locally since `_color_pattern` is
  private to that module).
- Produces: `regex_lines(game: Game) -> list[dict]` (every classifiable chat
  line: `episode, meeting_idx, tick, speaker_slot, text, regex_stance,
  regex_target_slot`); `compute_agreement(sample: DataFrame, chat_suss:
  DataFrame) -> dict` (`n_matched, n_sampled, stance_agreement,
  target_agreement`) — this is the pure, unit-testable function; the live
  Bedrock-backed `chat_suss` table itself comes from the event-warehouse's
  existing `suss` job (Task 6, not mocked here).

- [ ] **Step 1: Write the failing test**

```python
# crewrift_lab/chat_effectiveness/tests/test_validate_detector.py
import sys
from pathlib import Path

import pandas as pd

TOOLS = Path(__file__).resolve().parents[1] / "tools"
SUSPICION_TOOLS = Path(__file__).resolve().parents[3] / "suspicion_lab" / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(SUSPICION_TOOLS))

from replay_parse import ChatLine, Game, Meeting, PlayerInfo  # noqa: E402
from validate_detector import compute_agreement, regex_lines  # noqa: E402


def _game_with_chat() -> Game:
    players = {
        0: PlayerInfo(slot=0, name="P0", color="red", role="crew"),
        1: PlayerInfo(slot=1, name="P1", color="blue", role="imposter"),
    }
    meeting = Meeting(
        call_tick=100,
        caller_slot=0,
        kind="body",
        chats=[ChatLine(tick=101, slot=0, text="blue sus, saw them vent")],
    )
    return Game(
        episode="test_ep", config={}, players=players, states={}, visibility={},
        body_visibility={}, kills=[], bodies=[], ejections=[], meetings=[meeting],
        task_completions=[], vents=[], task_sites=[], tick_count=120, complete=True,
    )


def test_regex_lines_extracts_classifiable_chat():
    rows = regex_lines(_game_with_chat())

    assert len(rows) == 1
    assert rows[0]["episode"] == "test_ep"
    assert rows[0]["speaker_slot"] == 0
    assert rows[0]["tick"] == 101
    assert rows[0]["regex_stance"] == "accuses"
    assert rows[0]["regex_target_slot"] == 1


def test_compute_agreement_matches_on_episode_speaker_tick():
    sample = pd.DataFrame(
        [{"episode": "test_ep", "speaker_slot": 0, "tick": 101, "regex_stance": "accuses", "regex_target_slot": 1}]
    )
    chat_suss = pd.DataFrame(
        [{
            "episode_id": "test_ep", "slot": 0, "ts": 101,
            "is_suss": True, "suss_target_slot": 1,
        }]
    )

    agreement = compute_agreement(sample, chat_suss)

    assert agreement["n_matched"] == 1
    assert agreement["n_sampled"] == 1
    assert agreement["stance_agreement"] == 1.0
    assert agreement["target_agreement"] == 1.0


def test_compute_agreement_handles_no_matches():
    sample = pd.DataFrame(
        [{"episode": "test_ep", "speaker_slot": 0, "tick": 101, "regex_stance": "accuses", "regex_target_slot": 1}]
    )
    chat_suss = pd.DataFrame(columns=["episode_id", "slot", "ts", "is_suss", "suss_target_slot"])

    agreement = compute_agreement(sample, chat_suss)

    assert agreement == {"n_matched": 0, "stance_agreement": None, "target_agreement": None}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/worktrees/chat-accuracy-effectiveness && uv run pytest crewrift_lab/chat_effectiveness/tests/test_validate_detector.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'validate_detector'`.

- [ ] **Step 3: Write the implementation**

```python
# crewrift_lab/chat_effectiveness/tools/validate_detector.py
"""Sample chat lines and compare the regex detector's (stance, target) call
against the event-warehouse's LLM-based `suss` labels, to bound confidence in
the regex-derived accuracy/effectiveness numbers computed elsewhere in this
package. The live LLM labels come from the existing
`crewrift-event-warehouse suss` job (Bedrock-backed) — this module only
consumes its output parquet, it does not call Bedrock itself.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

import pandas as pd

SUSPICION_LAB_TOOLS = Path(__file__).resolve().parents[2] / "suspicion_lab" / "tools"
sys.path.insert(0, str(SUSPICION_LAB_TOOLS))
from features import ACCUSE_HINT, DEFEND_HINT  # noqa: E402
from replay_parse import Game, parse_game  # noqa: E402


def _color_lookup(game: Game) -> tuple[re.Pattern, dict[str, int]]:
    by_color = {p.color.lower(): p.slot for p in game.players.values() if p.color}
    alternation = "|".join(sorted((re.escape(c) for c in by_color), key=len, reverse=True))
    return re.compile(rf"\b({alternation})\b", re.IGNORECASE), by_color


def regex_lines(game: Game) -> list[dict]:
    """Every classifiable chat line with tick + raw text, for sampling."""
    if not game.players or not game.meetings:
        return []
    pattern, by_color = _color_lookup(game)
    rows: list[dict] = []
    for mi, meeting in enumerate(game.meetings):
        for chat in meeting.chats:
            text = chat.text or ""
            named = [by_color[m.group(1).lower()] for m in pattern.finditer(text)]
            named = [s for s in named if s != chat.slot]
            if not named:
                continue
            if DEFEND_HINT.search(text):
                stance = "defends"
            elif ACCUSE_HINT.search(text):
                stance = "accuses"
            else:
                continue
            rows.append(
                {
                    "episode": game.episode,
                    "meeting_idx": mi,
                    "tick": chat.tick,
                    "speaker_slot": chat.slot,
                    "text": text,
                    "regex_stance": stance,
                    "regex_target_slot": named[0],
                }
            )
    return rows


def sample_lines(expanded: Path, n: int, seed: int) -> pd.DataFrame:
    paths = sorted(list(expanded.glob("*.jsonl.gz")) + list(expanded.glob("*.jsonl")))
    all_rows: list[dict] = []
    for path in paths:
        try:
            game = parse_game(path)
        except Exception:  # noqa: BLE001 - skip corrupt games
            continue
        if game.complete:
            all_rows.extend(regex_lines(game))
    rng = random.Random(seed)
    if len(all_rows) > n:
        all_rows = rng.sample(all_rows, n)
    return pd.DataFrame(all_rows)


def compute_agreement(sample: pd.DataFrame, chat_suss: pd.DataFrame) -> dict:
    """Join the regex sample to warehouse chat_suss rows on (episode, speaker
    slot, tick) and compute stance/target agreement rates.
    """
    if chat_suss.empty:
        return {"n_matched": 0, "stance_agreement": None, "target_agreement": None}
    suss = chat_suss.rename(columns={"episode_id": "episode", "slot": "speaker_slot", "ts": "tick"})
    joined = sample.merge(suss, on=["episode", "speaker_slot", "tick"], how="inner")
    if joined.empty:
        return {"n_matched": 0, "stance_agreement": None, "target_agreement": None}
    stance_agree = (joined["regex_stance"] == "accuses") == joined["is_suss"]
    accused_rows = joined[joined["is_suss"]]
    target_agree = (
        (accused_rows["regex_target_slot"] == accused_rows["suss_target_slot"]).mean()
        if len(accused_rows)
        else None
    )
    return {
        "n_matched": int(len(joined)),
        "n_sampled": int(len(sample)),
        "stance_agreement": float(stance_agree.mean()),
        "target_agreement": None if target_agree is None else float(target_agree),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the regex accusation detector against LLM suss labels.")
    parser.add_argument("--expanded", type=Path, required=True)
    parser.add_argument("--chat-suss", type=Path, required=True, help="events/key=chat_suss/*.parquet from the warehouse.")
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    sample = sample_lines(args.expanded, args.n, args.seed)
    chat_suss_raw = pd.read_parquet(args.chat_suss)
    value_df = pd.json_normalize(chat_suss_raw["value"].apply(json.loads))
    chat_suss = pd.concat([chat_suss_raw.drop(columns=["value"]), value_df], axis=1)

    agreement = compute_agreement(sample, chat_suss)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(agreement, indent=2))
    print(json.dumps(agreement, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/worktrees/chat-accuracy-effectiveness && uv run pytest crewrift_lab/chat_effectiveness/tests/test_validate_detector.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
cd .claude/worktrees/chat-accuracy-effectiveness
git add crewrift_lab/chat_effectiveness/tools/validate_detector.py crewrift_lab/chat_effectiveness/tests/test_validate_detector.py
git commit -m "feat(chat-effectiveness): regex-vs-LLM detector validation against the warehouse's suss job"
```

---

### Task 5: Report renderer (`build_report.py`)

**Files:**
- Create: `crewrift_lab/chat_effectiveness/tools/build_report.py`
- Test: `crewrift_lab/chat_effectiveness/tests/test_build_report.py`

**Interfaces:**
- Consumes: the three metric `DataFrame`s from Task 3
  (`crew_accuracy_table`, `effectiveness_table`, `winrate_association_table`
  outputs) and the `dict` from Task 4 (`compute_agreement` output), plus a
  small `meta` dict (`field_snapshot_date, round_ids, n_episodes, entrants`).
- Produces: `render_html(meta, detector_validation, crew_accuracy,
  effectiveness, winrate) -> str` — plain f-string HTML, following
  `crewrift-survey`'s `scripts/survey.py:render_html` pattern (no Jinja2, no
  external template files — confirmed as this lab's existing convention).

- [ ] **Step 1: Write the failing test**

```python
# crewrift_lab/chat_effectiveness/tests/test_build_report.py
import sys
from pathlib import Path

import pandas as pd

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from build_report import render_html  # noqa: E402

META = {"field_snapshot_date": "2026-07-02", "round_ids": "391-394", "n_episodes": 240, "entrants": "11"}
VALIDATION = {"n_matched": 150, "n_sampled": 200, "stance_agreement": 0.82, "target_agreement": 0.77}
CREW_ACCURACY = pd.DataFrame([{"speaker_policy": "crewborg", "n": 40, "accuracy": 0.55}])
EFFECTIVENESS = pd.DataFrame(
    [{"speaker_policy": "crewborg", "speaker_role": "crew", "n": 40, "p_target_voted": 0.6, "p_target_ejected": 0.4, "mean_baseline_rate": 0.2}]
)
WINRATE = pd.DataFrame(
    [{"policy_name": "crewborg", "role": "crew", "seat_games": 100, "seat_win_rate": 0.24, "accusations_made": 40, "accuracy": 0.55}]
)


def test_render_html_includes_all_sections_and_caveats():
    html = render_html(META, VALIDATION, CREW_ACCURACY, EFFECTIVENESS, WINRATE)

    assert "Crew accusation accuracy" in html
    assert "Same-meeting effectiveness" in html
    assert "Win-rate association" in html
    assert "Observational, not causal" in html
    assert "crewborg" in html
    assert "2026-07-02" in html


def test_render_html_flags_missing_validation():
    html = render_html(META, {"n_matched": 0, "stance_agreement": None, "target_agreement": None}, CREW_ACCURACY, EFFECTIVENESS, WINRATE)

    assert "not yet run" in html or "unverified" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/worktrees/chat-accuracy-effectiveness && uv run pytest crewrift_lab/chat_effectiveness/tests/test_build_report.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'build_report'`.

- [ ] **Step 3: Write the implementation**

```python
# crewrift_lab/chat_effectiveness/tools/build_report.py
"""Render the chat-effectiveness study into a static HTML report.

Follows crewrift-survey's plain f-string HTML pattern
(crewrift_lab/.claude/skills/crewrift-survey/scripts/survey.py:render_html)
— no templating engine, no external template files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def _table(df: pd.DataFrame) -> str:
    return df.to_html(index=False, float_format=lambda x: f"{x:.3f}", border=0, classes="tbl")


def render_html(
    meta: dict,
    detector_validation: dict,
    crew_accuracy: pd.DataFrame,
    effectiveness: pd.DataFrame,
    winrate: pd.DataFrame,
) -> str:
    if detector_validation.get("n_matched"):
        validation_note = (
            f"Regex-vs-LLM agreement on {detector_validation['n_matched']} sampled chat lines: "
            f"stance agreement {detector_validation['stance_agreement']:.2f}, "
            f"target agreement {detector_validation['target_agreement']}. "
            "Treat the tables below with this precision in mind — they are not ground truth "
            "on the detector's own accuracy."
        )
    else:
        validation_note = "Detector validation not yet run — regex accusation-target detection is unverified."

    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><title>Chat accuracy &amp; effectiveness — {meta.get('field_snapshot_date', '')}</title>
<style>
body {{ font-family: -apple-system, sans-serif; margin: 2rem; color: #1a1a2e; }}
h1, h2 {{ border-bottom: 1px solid #ddd; padding-bottom: .3rem; }}
table.tbl {{ border-collapse: collapse; margin: 1rem 0; }}
table.tbl th, table.tbl td {{ padding: .4rem .8rem; border: 1px solid #ddd; text-align: right; }}
table.tbl th:first-child, table.tbl td:first-child {{ text-align: left; }}
.note {{ background: #fff8e1; padding: .8rem 1rem; border-left: 4px solid #f9a825; margin: 1rem 0; }}
.caveat {{ color: #555; font-style: italic; }}
</style></head><body>
<h1>Chat accuracy &amp; effectiveness — Crewrift Prime</h1>
<p class="caveat">Field snapshot: {meta.get('field_snapshot_date', '')} &middot; rounds {meta.get('round_ids', '')} &middot;
episodes {meta.get('n_episodes', '')} &middot; entrants {meta.get('entrants', '')}</p>
<p class="caveat">Observational, not causal: no randomized intervention on who accuses whom.</p>
<div class="note">{validation_note}</div>

<h2>1. Crew accusation accuracy (vs. ground-truth imposter)</h2>
{_table(crew_accuracy)}

<h2>2. Same-meeting effectiveness (crew + imposter)</h2>
{_table(effectiveness)}

<h2>3. Win-rate association (seat-normalized)</h2>
{_table(winrate)}
</body></html>"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the chat-effectiveness HTML report.")
    parser.add_argument("--meta", type=Path, required=True, help="JSON: field_snapshot_date, round_ids, n_episodes, entrants.")
    parser.add_argument("--validation", type=Path, required=True, help="JSON from validate_detector.py.")
    parser.add_argument("--metrics-dir", type=Path, required=True, help="Dir with crew_accuracy/effectiveness/winrate_association parquet.")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    meta = json.loads(args.meta.read_text())
    validation = json.loads(args.validation.read_text())
    crew_accuracy = pd.read_parquet(args.metrics_dir / "crew_accuracy.parquet")
    effectiveness = pd.read_parquet(args.metrics_dir / "effectiveness.parquet")
    winrate = pd.read_parquet(args.metrics_dir / "winrate_association.parquet")

    html = render_html(meta, validation, crew_accuracy, effectiveness, winrate)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html)
    print(f"Wrote report -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/worktrees/chat-accuracy-effectiveness && uv run pytest crewrift_lab/chat_effectiveness/tests/test_build_report.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
cd .claude/worktrees/chat-accuracy-effectiveness
git add crewrift_lab/chat_effectiveness/tools/build_report.py crewrift_lab/chat_effectiveness/tests/test_build_report.py
git commit -m "feat(chat-effectiveness): static HTML report renderer"
```

---

### Task 6: Run the full pipeline on real data and ship the report

**Files:**
- Create: `crewrift_lab/chat_effectiveness/README.md`
- Create (data, gitignored): `crewrift_lab/chat_effectiveness/data/` (fresh
  pull outcomes/accusations/metrics parquet + validation.json + report.html)
- Create (data, gitignored): historical cross-check outputs under the same
  `data/` directory with a `historical_` prefix.
- Modify: `crewrift_lab/chat_effectiveness/.gitignore` (new file: ignore
  `data/`, matching suspicion_lab's `corpus/`/`expanded/`/`dataset/`
  gitignore pattern).

This task is operational (real API calls, real cost), not unit-testable —
run every step for real and inspect the output at each stage before moving
to the next.

- [ ] **Step 1: Confirm the current Prime field + division id**

```bash
cd .claude/worktrees/chat-accuracy-effectiveness
uv run softmax status
uv run coworld divisions --league league_a12f5172-0907-4d04-8bcb-ca02f5360e3a --json | tee /tmp/prime_divisions.json
```

Expected: authenticated status, and a JSON array containing the Prime
division with a full `division_id` (WORKING_CONTEXT.md's `div_acbde92a-…`
is truncated — resolve the full id here; do not hardcode the truncated
form). Record the full id as `$DIVISION_ID` for the next step.

- [ ] **Step 2: Verify the expander still matches the live Prime build**

```bash
uv run coworld download cow_50ee07cf-44d5-41a8-aeab-29c1b73f388d --json | python3 -c "import json,sys; print(json.load(sys.stdin)['runnable']['source_url'])"
ls -la /tmp/expand-043
```

Expected: the source commit matches what `/tmp/expand-043` was built from
(per `WORKING_CONTEXT.md`, `26ee08c`, valid for `crewrift_prime 0.4.3–0.4.7`).
If the version has moved past 0.4.7, rebuild via
`crewrift_lab/tools/build_expand_replay.sh --ref <new-commit>` and verify
`trace_complete` on one fresh replay before proceeding — do not trust a
stale expander (a recurring gotcha in this lab: silent hash-fails on
divergent builds).

- [ ] **Step 3: Create the fresh ~20-round experience request**

```bash
cat > /tmp/chat_eff_req.json <<'EOF'
{
  "target": {"division_id": "REPLACE_WITH_$DIVISION_ID"},
  "roster": [
    {"player": {"top_n": 8}}, {"player": {"top_n": 8}}, {"player": {"top_n": 8}},
    {"player": {"top_n": 8}}, {"player": {"top_n": 8}}, {"player": {"top_n": 8}},
    {"player": {"top_n": 8}}, {"player": {"top_n": 8}}
  ],
  "num_episodes": 240,
  "notes": "chat-accuracy-effectiveness study: ~20 rounds, natural roster, no role override"
}
EOF
S=.claude/skills/coworld-experience-requests/scripts/experience_request.py
uv run python "$S" create /tmp/chat_eff_req.json --check-schema
uv run python "$S" create /tmp/chat_eff_req.json | tee /tmp/chat_eff_xreq.json
```

Expected: schema check passes, then a created request with an `xreq_...`
id. Record it as `$XREQ_ID`.

- [ ] **Step 4: Stream episode artifacts as they complete**

```bash
F=.claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py
uv run python "$F" --xreq $XREQ_ID --watch --out /tmp/chat_eff_eps
```

Expected: each episode downloads (`episode.json`, `results.json`,
`replay.json(.z)`) into `/tmp/chat_eff_eps/<episode_dir>/` as it finishes;
completes when the batch is fully terminal (~240 episodes at Prime's
~10-min/12-eps cadence).

- [ ] **Step 5: Expand replays for chat/vote/meeting parsing**

```bash
mkdir -p /tmp/chat_eff_expanded
for d in /tmp/chat_eff_eps/*/; do
  name=$(basename "$d")
  /tmp/expand-043 --format jsonl --snapshot-every 24 "$d/replay.json" > /tmp/chat_eff_expanded/"$name".jsonl 2>/tmp/chat_eff_expanded/"$name".err \
    || echo "FAILED: $name" >> /tmp/chat_eff_expand_failures.log
done
wc -l /tmp/chat_eff_expand_failures.log 2>/dev/null || echo "0 failures"
```

Expected: a `.jsonl` per episode in `/tmp/chat_eff_expanded/`, filename
stem == the episode directory name (matches this plan's join-key
convention). A nonzero failure count is a signal to re-check Step 2, not to
proceed silently — per this lab's recurring "hash-fail = version/button
divergence" lesson.

- [ ] **Step 6: Build the event warehouse (for the detector-validation `suss` job only)**

```bash
B=crewrift_lab/.claude/skills/crewrift-event-warehouse/scripts/build_warehouse.py
uv run python "$B" --xreq $XREQ_ID --out /tmp/chat_eff_wh --expand-replay /tmp/expand-043
uv run crewrift-event-warehouse suss --out /tmp/chat_eff_wh
```

Expected: `/tmp/chat_eff_wh/manifest.json` with `episodes_ok` close to 240,
then `/tmp/chat_eff_wh/events/key=chat_suss/chat_suss.parquet` written by
the LLM-labeling job (requires real AWS/Bedrock credentials — confirm
`uv run softmax status`-equivalent AWS auth is live before this step, since
`suss.py` has no dry-run path).

- [ ] **Step 7: Run the extraction → join → validation → report pipeline**

```bash
mkdir -p crewrift_lab/chat_effectiveness/data
uv run python crewrift_lab/chat_effectiveness/tools/episode_outcomes.py \
  --episodes /tmp/chat_eff_eps --out crewrift_lab/chat_effectiveness/data/outcomes.parquet

uv run python crewrift_lab/chat_effectiveness/tools/extract_accusations.py \
  --expanded /tmp/chat_eff_expanded --out crewrift_lab/chat_effectiveness/data/accusations.parquet

uv run python crewrift_lab/chat_effectiveness/tools/metrics.py \
  --accusations crewrift_lab/chat_effectiveness/data/accusations.parquet \
  --outcomes crewrift_lab/chat_effectiveness/data/outcomes.parquet \
  --out-dir crewrift_lab/chat_effectiveness/data/metrics

uv run python crewrift_lab/chat_effectiveness/tools/validate_detector.py \
  --expanded /tmp/chat_eff_expanded \
  --chat-suss /tmp/chat_eff_wh/events/key=chat_suss/chat_suss.parquet \
  --n 200 --out crewrift_lab/chat_effectiveness/data/validation.json

cat > crewrift_lab/chat_effectiveness/data/meta.json <<EOF
{"field_snapshot_date": "$(date -u +%Y-%m-%d)", "round_ids": "<fill in from xreq round metadata>", "n_episodes": <fill in from manifest.json episodes_ok>, "entrants": "<fill in from manifest.json distinct_policies>"}
EOF

uv run python crewrift_lab/chat_effectiveness/tools/build_report.py \
  --meta crewrift_lab/chat_effectiveness/data/meta.json \
  --validation crewrift_lab/chat_effectiveness/data/validation.json \
  --metrics-dir crewrift_lab/chat_effectiveness/data/metrics \
  --out crewrift_lab/chat_effectiveness/data/report.html
```

Expected: each command prints a row/episode count and writes its output
file; `report.html` opens in a browser showing all three metric tables and
a non-empty detector-validation note (or the explicit "not yet run" note if
Step 6 was skipped — do not present validation numbers if that step
failed).

- [ ] **Step 8: Cross-check against the historical suspicion_lab corpus**

```bash
uv run python crewrift_lab/chat_effectiveness/tools/episode_outcomes.py \
  --episodes crewrift_lab/suspicion_lab/corpus --out crewrift_lab/chat_effectiveness/data/historical_outcomes.parquet

uv run python crewrift_lab/chat_effectiveness/tools/extract_accusations.py \
  --expanded crewrift_lab/suspicion_lab/expanded --out crewrift_lab/chat_effectiveness/data/historical_accusations.parquet

uv run python crewrift_lab/chat_effectiveness/tools/metrics.py \
  --accusations crewrift_lab/chat_effectiveness/data/historical_accusations.parquet \
  --outcomes crewrift_lab/chat_effectiveness/data/historical_outcomes.parquet \
  --out-dir crewrift_lab/chat_effectiveness/data/historical_metrics
```

Expected: three more parquet files. Compare
`historical_metrics/crew_accuracy.parquet` and
`historical_metrics/winrate_association.parquet` against the fresh-pull
versions for the policies present in both — note any large divergence in
the report as a stability caveat rather than silently trusting whichever
number is more convenient.

- [ ] **Step 9: Manual spot-check (required before trusting aggregates)**

Pick 10 rows at random from `data/accusations.parquet`, look up the
corresponding chat text in the matching `/tmp/chat_eff_expanded/<episode>.jsonl`
(the `chat` events), and confirm by eye that the regex-derived
`speaker_slot`/`stance`/`target_slot` match what the line actually says, and
that `target_voted_same_meeting`/`target_ejected_same_meeting` match the
same episode's `vote_cast`/`died` events. Note any mismatches found; if
more than 1-2 of 10 are wrong, treat the headline numbers as unreliable and
say so rather than shipping the report as-is.

- [ ] **Step 10: Write the README and commit**

```markdown
# crewrift_lab/chat_effectiveness/README.md
# chat_effectiveness — field-wide chat accuracy & effectiveness study

Answers two questions about Crewrift Prime chat, field-wide (every
player/policy, not just crewborg): (1) how accurate are crew accusations
vs. ground-truth imposter identity, and (2) how effective are accusations
(crew + imposter) at moving votes/ejections and correlating with
seat-normalized win rate. Design:
[`../docs/designs/2026-07-02-chat-accuracy-effectiveness-design.md`](../docs/designs/2026-07-02-chat-accuracy-effectiveness-design.md).

Observational, not causal — no randomized intervention on who accuses whom.

## Pipeline

    uv run python tools/episode_outcomes.py --episodes <dir of episode dirs> --out data/outcomes.parquet
    uv run python tools/extract_accusations.py --expanded <dir of expanded jsonl> --out data/accusations.parquet
    uv run python tools/metrics.py --accusations data/accusations.parquet --outcomes data/outcomes.parquet --out-dir data/metrics
    uv run python tools/validate_detector.py --expanded <expanded dir> --chat-suss <warehouse>/events/key=chat_suss/chat_suss.parquet --out data/validation.json
    uv run python tools/build_report.py --meta data/meta.json --validation data/validation.json --metrics-dir data/metrics --out data/report.html

`data/` is gitignored (rebuildable from a fresh pull + the historical
suspicion_lab corpus); the report and any durable findings get written up
in `crewrift_lab/TENTATIVE_LESSONS.md` per this lab's living-docs
discipline.

## Files

- `tools/episode_outcomes.py` — per-slot policy identity/role/win from
  `episode.json` + `results.json`.
- `tools/extract_accusations.py` — same-meeting accusation/vote/eject rows
  for every speaker (crew and imposter), via `suspicion_lab`'s
  `chat_stances()`/`replay_parse.py` (read-only reuse).
- `tools/metrics.py` — crew accuracy, same-meeting effectiveness,
  seat-normalized win-rate association tables.
- `tools/validate_detector.py` — regex-vs-LLM agreement, using the
  event-warehouse's existing `suss` job as the LLM ground truth.
- `tools/build_report.py` — static HTML report (plain f-strings, matching
  `crewrift-survey`'s pattern).
```

```bash
cat > crewrift_lab/chat_effectiveness/.gitignore <<'EOF'
data/
EOF
git add crewrift_lab/chat_effectiveness/README.md crewrift_lab/chat_effectiveness/.gitignore
git commit -m "docs(chat-effectiveness): pipeline README + gitignore data dir

Ran the full study: ~240-episode fresh Prime pull (rounds <fill in>) +
historical suspicion_lab cross-check. See data/report.html (not committed,
rebuildable) for the per-player accuracy/effectiveness/win-rate tables and
the regex-vs-LLM detector validation number."
```

- [ ] **Step 11: Record the findings in the lab's living docs**

Per this lab's standing discipline (`crewrift-living-docs-discipline`),
append a dated entry to `crewrift_lab/TENTATIVE_LESSONS.md` summarizing the
headline numbers from `data/report.html` (crew accuracy by policy,
effectiveness by policy/role, win-rate association, and the detector
validation agreement rate) — write the actual numbers observed in Step 7,
not placeholder values. Commit that update separately.

```bash
git add crewrift_lab/TENTATIVE_LESSONS.md
git commit -m "docs: chat-accuracy-effectiveness study findings"
```

---

## Self-review notes

- **Spec coverage:** Task 1 covers the outcomes/win join; Task 2 covers
  accusation extraction + same-meeting vote/eject join (both roles); Task 3
  covers all three named metrics (crew accuracy, effectiveness, seat-normalized
  win-rate association); Task 4 covers detector validation; Task 5 covers the
  HTML report + observational-not-causal framing; Task 6 covers the fresh
  pull, the historical cross-check, the manual spot-check, and living-docs
  recording. All spec sections have a task.
- **Type consistency:** `episode` is the join key everywhere (Task 1's
  `episode_outcomes` output, Task 2's `extract_accusations` output, both
  consumed identically in Task 3's `enrich_accusations`). `speaker_policy`/
  `target_policy`/`speaker_win` names introduced in Task 3 are only consumed
  within Task 3 and Task 5 (via the parquet files, not direct import), so no
  cross-task signature drift.
- **No placeholders:** Task 6's dynamic values (`$DIVISION_ID`, `$XREQ_ID`,
  round ids, episode counts) are runtime-captured from prior command output,
  not unresolved design gaps — every one has an exact command that produces
  it.
