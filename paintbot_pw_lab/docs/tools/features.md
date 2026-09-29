# features.py + miner_rows.py: the hypothesis-miner adapter

The lab's adapter for the shared [`coworld-hypothesis-miner`](../../../.claude/skills/coworld-hypothesis-miner/SKILL.md)
engine. `miner_rows.py` turns a batch of hash-checked episodes into one JSONL row per
(episode, our policy); `features.py` exports `adapter` and `METAS` that map a row to the
engine's `Episode(score, features)`. Use it when nothing specific is suspected and you want a
ranked list of behaviors that separate our policy's good matches from its bad ones.

Files: [`tools/miner_rows.py`](../../tools/miner_rows.py), [`tools/features.py`](../../tools/features.py),
tests in [`tools/tests/test_features.py`](../../tools/tests/test_features.py).

## Commands

```bash
# Rows: one per (episode, our policy). Without --policy it lists the batch's policies and exits 2.
uv run python paintbot_pw_lab/tools/miner_rows.py ROOT [ROOT ...] --policy KEY_OR_NAME \
    [--score elo|win] [--out /tmp/mine/rows.jsonl] [--refresh]

# Mine.
MINER=.claude/skills/coworld-hypothesis-miner/scripts
uv run python $MINER/mine_hypotheses.py --rows /tmp/mine/rows.jsonl \
    --adapter paintbot_pw_lab/tools/features.py --top 5 --out /tmp/mine/hypotheses.md [--json assoc.json]
```

`miner_rows.py` prints how every episode was used: `used`, `policy_absent`,
`mirror_both_teams` (our policy on both teams has no own-vs-other score), `no_score`,
`load_failed`. It exits 1 if any episode failed to load, and warns under 8 rows (the engine
refuses fewer).

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py miner ROOT... --policy KEY --out FILE --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | `miner`: roots, `--policy` (required), `--score elo\|win`, `--out FILE` (required with `--json`), `--refresh`. `mine`: the shared engine's flags (`--rows`, `--top`, `--out`, `--json FILE`); `pw.py mine` presets `--adapter tools/features.py` |
| Outputs | `miner`: the JSONL rows file (stdout without `--out`); `mine`: a Markdown ranking |
| `--json` result | `miner`: `{rows, tally, out, warning}` (`warning` when fewer than 8 rows). `mine` does not print the lab envelope: its `--json FILE` writes the association table |
| Exit codes | `miner`: 0 ok; 1 some episodes failed to load; 2 no or unknown `--policy` (`result.valid` lists the batch's keys and names), `--json` without `--out`; 3 `pw_trace` not built. `mine`: the shared engine's own codes |
| Idempotence / cache | reads the trace caches; the rows file is rewritten |
| Typical next step | `uv run python paintbot_pw_lab/tools/pw.py mine --rows FILE --top 5` (the envelope's `next[]`), then `coworld-experiment` |

## Unit and score

- **Unit:** one row per (episode, policy_key). The policy's 8 seats in a match are one
  sample. `policy_key` is the exact `policy_version_id` for hosted episodes and
  `local:<file name>` for local ones.
- **Score** (`--score`, stored in the row): `elo` (default) is the ladder's Elo outcome,
  `clamp(0.5 + (our − their glory)/2000, 0, 1)`, which is what league rank moves by
  ([mechanics.md §1](../mechanics.md)). `win` is 1 / 0.5 / 0. The adapter reports both as
  **outcome points, 0-100** (`SCORE_SCALE`), because the engine emits no hypothesis whose
  swing is under 0.3 score units, which a 0-1 score could never reach.

## Row schema (JSONL)

`episode_id, policy_key, policy_name, team, opponents[], source, rules, ticks, result,
score_kind, score`, plus blocks (unknown = null, never 0):

| Block | Source | Contents |
| --- | --- | --- |
| `metrics` | `pw_metrics.policy_metrics` | every policy-level metric (counts, ratios, `elo_outcome`, …) |
| `team_metrics` | `pw_metrics.team_metrics` | first capture tick, capture starts/resets, contests, lead changes, hearts held, longest supply gap, glory-heart glory, cogs out, lives left |
| `timing` | tables | `first_kill_tick`, `first_death_tick`, `enemy_first_death_tick`, `first_heart_lost_tick`, `first_friendly_hit_tick` (null = never) |
| `fights` | `pw_fights.fight_policy_metrics` | engagements, won, first hit, outnumbered, opening duels, trades |
| `flags` | `pw_flags.episode_flags` | count per flag for our seats and our team (`zero_glory_win` left out: it is an outcome) |
| `intent` | `pw_intent.intent_summary` | our seats' PWI summary: seats logged, lines, bad lines, VM errors, heart switches, line-weighted mode shares; null without seat logs |

## Features

54 in `METAS` (up to 47 reach the miner once score components are dropped), each with a kind, a one-line definition and a `change_hint` naming the module
of our policy that owns the behavior (base.bas lineage): **targeting** (Gun), **footwork**,
**dry route**, **territory squads** (heart selection), **cover seats**, **supplies**,
**refuse-a-fight** (retreat), **grenade**, **stall check**, **comms** (shout), **runtime**.

- **Timing:** first capture, first death, first kill, first heart lost. Never = match
  ticks + 1.
- **Presence:** first blood, lost a heart at all, friendly fire at all, grenade used,
  VM-disabled suspect (inferred), `BASIC error:` logged (our logs only).
- **Rates and shares:** accuracy, long-range shot share (inferred band), shots, kills and
  deaths per minute, K/D, trade share, friendly HP per minute, alive share, heart-reach,
  contested, water, trench, stuck (sampled) and idle shares, pickups per minute, grenade
  effectiveness, shouts per minute, capture-reset share, contests per minute; engagement
  win share, first-hit share, outnumbered share and win share, opening-duel win share;
  flag rates (stuck, oscillating, idle, death alone, heart lost with allies, long wade) and
  wasted-grenade share; PWI heart switches per minute and mode shares (retreat, supply,
  fight, heart).
- A feature whose denominator is 0 (no deaths, no grenades, no logs) is **left out** of that
  row, not set to 0. The engine then computes it on the rows that have it (`coverage`).

**Excluded as score or win arithmetic** (`SCORE_COMPONENTS`): glory is the match-length
countdown plus quiet-supplies, behind-in-lives, behind-in-cogs and glory-heart awards, and
the win is the heart meter or elimination. So for `elo`: match minutes, glory hearts per
minute, longest supply gap, plus the win conditions; for `win`: hearts held, captures
completed per minute, cogs out and lives left. Deaths stay in (they are the main combat
signal) but also pay behind-in-lives glory to the side that is behind, and their blurb says so.

## Verified (2026-09-29)

- 22 local matches recorded with seat logs (`pw_intent.py record`: an instrumented copy of
  base.bas vs base.bas seeds 1-7 and vs a one-constant variant seeds 1-4, both sides):
  `miner_rows.py` used all 22 (0 failures), and the miner ran on them with `--score elo`
  (47 features) and `--score win`. Top candidates: engagement win share, K/D, opening-duel win
  share. On this corpus that is a smoke test, not a finding: the instrumented policy plays
  exactly like base.bas, so most of the variance is the side (odd seats win most local
  matches) and the opponent variant. Fight outcomes are also the textbook reverse-causation
  case the miner warns about.
- Tests: `uv run python -m pytest paintbot_pw_lab/tools/tests/test_features.py` (never = last
  tick + 1, score scaling, zero denominators absent, score components excluded per kind,
  unscored rows dropped, every emittable feature has a meta).

## Not verified / limits

- Not yet run on a hosted corpus of one policy version: the public samples hold at most 5
  episodes per policy. A real run needs ≥ 8 (better 30+) episodes of **our** uploaded
  version against the field.
- Mix of opponents and sides confounds the corpus. Mine one opponent set at a time when the
  corpus is large enough, and read `notes` (team, opponents) on surprising rows.
- `vm_error_logged` and the intent features exist only where our seat logs exist; hosted
  retrieval of our own logs is not yet exercised.
- Depends on `pw_fights.py` and `pw_flags.py` APIs as of 2026-09-29
  (`fight_policy_metrics`, `episode_flags`, `FLAG_NAMES`).
