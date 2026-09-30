---
name: paintbot-pw-diagnose
description: "Use when the question is 'why are we losing', 'where is our Paintbot PW policy weakest', 'what should we change next', or 'turn this batch into hypotheses' — goes from a batch of hash-checked episodes to metrics and anomaly flags, reviews the worst losses first with match reports, and writes a few mechanistic hypotheses pinned to a BASIC module with a predicted per-group effect, then hands the chosen one to coworld-experiment. Runs the hypothesis miner when nothing specific is suspected. Agent-drivable: `pw.py episodes|metrics|flags|fights|report|intent|miner|mine ... --json`."
---

# Paintbot PW diagnose

Turn a batch of our episodes into **understanding and directions**: where our policy is weakest,
what the numbers mean in the matches, and two to four **varied, mechanistic hypotheses** for why,
each pinned to the module of our BASIC that drives it. This is the explaining step. It does not
run experiments and does not change the policy. It hands one chosen hypothesis to
`coworld-experiment`. (Pattern: crewrift-diagnose.)

**Announce:** "Diagnosing: I'll find the weakness, read the worst losses, and propose a few
mechanistic hypotheses with tests."

Run everything from the repo root (`personal_labs_paintbot_pw/`). Tool contracts:
[pw_metrics](../../../docs/tools/pw_metrics.md), [pw_flags](../../../docs/tools/pw_flags.md),
[pw_match_report](../../../docs/tools/pw_match_report.md), [pw_intent](../../../docs/tools/pw_intent.md),
[pw_fights](../../../docs/tools/pw_fights.md), [pw_winprob](../../../docs/tools/pw_winprob.md),
[miner adapter](../../../docs/tools/features.md), [tables](../../../docs/tools/tables.md), the tool
index [docs/tools/README.md](../../../docs/tools/README.md), scoring in
[mechanics.md §1](../../../docs/mechanics.md).

## 1. Assemble the batch

- Episodes of **one** policy version of ours (its `policy_version_id`; `local:<file>` for local
  runs), pulled with `coworld-episode-artifacts` into `paintbot_pw_lab/episode_data/<batch>/`.
  Ten or more for triage, thirty or more before believing a rate.
- Check the lab (`uv run python paintbot_pw_lab/tools/pw.py doctor --json`; on exit 1 with failure code `stale` run
  `deployed-ref --write` then `build`, which builds the tag in `tools/release.env`; on `rate_limited`
  wait and retry or use `doctor --offline`), then load and check the batch. **Every episode
  must be accounted for**: failures print with a code (`failures[]` in `--json`) and the command
  exits 1. Fix or explain them before reading any number.

```bash
uv run python paintbot_pw_lab/tools/pw.py episodes paintbot_pw_lab/episode_data/<batch> --json
```

## 2. Metrics and flags, worst losses first

```bash
uv run python paintbot_pw_lab/tools/pw.py metrics paintbot_pw_lab/episode_data/<batch> --policy <KEY> --csv <scratch>/metrics --json
uv run python paintbot_pw_lab/tools/pw.py flags   paintbot_pw_lab/episode_data/<batch> --policy <KEY> --top 0 --json
```

An unknown `--policy` exits 2 and lists the batch's policy keys and names (`result.valid`).
`--top 0` prints only the per-episode flag counts; `--csv FILE` keeps every row.

`pw_flags --policy` prints our losses and draws **sorted by Elo outcome, worst first**, with flag
counts per episode (`death_alone`, `long_wade`, `oscillating`, `stuck`, `friendly_fire`,
`wasted_grenade`, `heart_lost_with_allies`, `idle_alive`, `vm_disabled_suspect`,
`zero_glory_win`; `--flags a,b` picks some), and the thresholds it used. Loss rows carry
`episode_id`, not a path: find the directory with
`grep -l '"id": "<episode_id>"' paintbot_pw_lab/episode_data/<batch>/*/episode.json`.
Combat and swing, when the weakness looks like fights or timing:

```bash
uv run python paintbot_pw_lab/tools/pw.py fights paintbot_pw_lab/episode_data/<batch> --policy <KEY> --vis-every 24 --json   # engagements, first hit, opening duels
uv run python paintbot_pw_lab/tools/pw.py winprob credit paintbot_pw_lab/episode_data/<batch> --model <model.json> --out <scratch>/wp --json
```

`winprob credit` needs a model from `winprob fit` on a larger public sample (see
[pw_winprob.md](../../../docs/tools/pw_winprob.md)); `wp_policy.parquet` gives each episode's worst
minute and the events that moved P(win) most.

Name the weakness in one line with a number, split by the groups that matter here:

| Group | Why split |
| --- | --- |
| side (team 0 Ember / team 1 Azure) | a side-specific weakness is a different mechanism; the league itself shows no side advantage (odd seats 43 of 80, Wilson 43–64%), though local base-vs-base mirrors do (10 of 14) |
| opponent policy | a weakness against one leader is a different mechanism from a general one |
| match phase (opening / mid / late) | first capture, first death and first heart lost are timing features |

**Fix ops first.** A seat with `BASIC error:` in its log, a `vm_disabled_suspect` flag or
`idle_share` near 1 is a runtime failure, not gameplay. Report it and stop there. Mining
or diagnosing play on a broken seat attributes the failure to behavior.

## 3. Read the worst losses

For the three to five worst losses, render the one-page report and read it:

```bash
uv run python paintbot_pw_lab/tools/pw.py report paintbot_pw_lab/episode_data/<batch>/<episode> [...] --json
```

It shows how the match was decided, the glory composition, a timeline and the top moments
(first captures, hearts lost, kill bursts, elimination) with a movement panel each. Then say
**what the signal means in the matches**: "we lose on glory margin because X; in the games that
looks like Y; here is the tick it goes wrong."

**Intent versus truth.** When our seats print the PWI line
([reference/intent_telemetry.bas](../../../reference/intent_telemetry.bas)), the gap between what
the policy meant and what happened usually shows the mechanism:

```bash
uv run python paintbot_pw_lab/tools/pw.py intent show  paintbot_pw_lab/episode_data/<batch> --json
uv run python paintbot_pw_lab/tools/pw.py intent audit paintbot_pw_lab/episode_data/<batch>/<episode> --json
```

Read `audit --json` in two parts. `result.consistency_divergences` (target not visible, target
dead, seen-count mismatch, judged against what BASIC actually observes, disguises included) should
be **0**; a non-zero count is a policy or telemetry bug, so fix that before trusting any intent
evidence. The deception rules (`target_is_ally`: we aimed at a disguised teammate;
`seen_fooled`: the observed enemy count differs from the true enemies in view) and
`heart_not_approached` are genuine belief-versus-truth findings. To audit the baseline itself,
generate an instrumented copy with `uv run python paintbot_pw_lab/reference/wire_intent_base.py
paintbot_pw_lab OUT.bas` and record it with `pw.py intent record OUT.bas
paintbot_pw_lab/reference/base.bas --seeds 3 --json`. When the
logs are too thin, add a field to the PWI line or wire it into a module that lacks it; that is
a policy code change, so say so and let James decide.

## 4. Nothing specific suspected? Mine

```bash
uv run python paintbot_pw_lab/tools/pw.py miner paintbot_pw_lab/episode_data/<batch> --policy <KEY> --out <scratch>/mine/rows.jsonl --json
uv run python paintbot_pw_lab/tools/pw.py mine --rows <scratch>/mine/rows.jsonl --top 5 --out <scratch>/mine/hypotheses.md   # adapter preset: tools/features.py
```

One row per (episode, our policy); score = Elo outcome score in points (0-100). Needs ≥ 8 rows:
with fewer, `miner` still writes them but sets `result.warning`, and `mine` fails (exit 1,
`adapter produced N usable episodes; need >=8`). For local recordings the key is
`local:<file>` (e.g. `local:base.bas`). Read the invariant list first, then check each candidate for **reverse
causation**: engagement win share, K/D and kills are usually consequences of winning, not
causes. Prefer candidates with a timing or intent feature behind them.

## 5. Write the hypotheses (2-4, varied)

Each hypothesis uses the crewrift-diagnose schema:

| Field | Content |
| --- | --- |
| `title` | short claim |
| `evidence` | what you saw: episode ids, ticks, flag rows, PWI lines, metric values with n |
| `mechanism` | what happens and why, **pinned to a BASIC module**: targeting (Gun), footwork, dry route, territory squads (heart selection), cover seats, supplies, refuse-a-fight (retreat), grenade, stall check, comms (shout); give the section and the constant or rule |
| `change` | the one directed change it implies |
| `predicted_effect` | what moves, per group (side, opponent, phase), roughly how much, on which metric (Elo outcome first) |
| `confidence` | high / medium / low |
| `experiment` | the cheapest test: re-read existing tables, a local screen (`pw.py local`, screening only), or a hosted A/B |

Rules: a mechanism, not a tweak ("lower the threshold" is a tweak); a module location, not a
vibe; independent mechanisms, not three versions of one; include a positive outlier if one
shows up (a match we won unusually well is a behavior to make reliable). Save the JSON in
your scratchpad and present the hypotheses as options in the reply. Publish a page only if
James asks for one.

## 6. Hand off

The chosen hypothesis goes to **`coworld-experiment`** (falsify it against existing data first).
A change that ships is measured with **`coworld-ab`** through `pw.py compare` (the lab's `paintbot-pw-ab` skill). Stop after
presenting; do not implement a policy change unasked.

## Pitfalls

- **The episode is the unit.** Eight seats of one policy in one match are one sample. All the
  tools above already work that way; do not compute per-seat statistics by hand.
- **Rank moves by glory margin**, not wins: a narrow win and a big win differ. The loser's glory
  is 0 and a draw zeroes both (mechanics.md §1).
- **Local matches are not field evidence.** Diagnose on hosted episodes of our uploaded version.
  Local recordings (`pw.py intent record`) are for getting seat logs and checking mechanisms.
- Inferred columns (`aim_target*`, stuck, VM-disabled suspect, distance bands on misses) and
  flag thresholds are uncalibrated. Quote them as inferred, never as exact counts.
- Unknown is null: no seat log means intent features are missing, not zero.
- Hosted seat logs for our own xp-request episodes are not yet confirmed to come back; check
  `pw.py intent show` before planning around intent evidence.

## Autonomous use

- **Preconditions:** `uv run python paintbot_pw_lab/tools/pw.py doctor --json` exits 0; the batch is one policy version of ours, on
  disk, ten or more episodes.
- **Commands, in order:** `episodes BATCH --json` (every episode accounted for), `metrics` and
  `flags --policy KEY --top 0 --json`, `report` on the worst three to five losses from
  `flags`' `result.losses`, then `miner` + `mine` when nothing specific is suspected. All reads are
  cached; rerunning is cheap.
- **Reading the envelopes:** `result.policy` (metrics) and `result.losses` (flags, worst Elo
  outcome score first; rows are `episode_id`, `result`, `elo_outcome`, glory, `opponent` and flag
  counts) drive the triage; `failures[]` must be empty or explained before any number is
  quoted; `miner`'s `result.warning` says when there are too few rows to mine.
- **Exit codes:** 0 use it. 1 some episodes failed: list them, continue on the rest only if the
  failures are explained (a missing tape is "re-fetch", not "absent"). 2 fix the argument (an
  unknown `--policy` lists the valid ones). 3 run `next[0]` (build or login) and rerun.
- **Human gates:** diagnosing is read-only and needs no approval. The step it hands to, a new
  experiment or A/B, may create hosted experience requests: that is within the lab's
  authorization (`user_preferences.md`: create them without asking first; never for self-play)
  but it **costs XP credits**, so report the request count and credit estimate as an update.
  Changing the policy is James's direction to give; league **submission** and public community
  writes stay explicitly gated. Present the hypotheses and pause.
