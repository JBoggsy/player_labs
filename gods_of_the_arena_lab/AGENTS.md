# Gods of the Arena lab

A lab for building and improving a BASIC policy for Gods of the Arena, a 5v5 lane battler
run by polyworld. Ten seats each control one hero; the game hosts the BASIC file itself,
so there is no player container. Agree the policy and strategic objective with James
before implementing behavior.

## Read in this order

1. [WORKING_CONTEXT.md](WORKING_CONTEXT.md) — current objective, identity, next decision.
2. [docs/research.md](docs/research.md) — the knowledge map: what we know, where it is,
   and how to check it is still current. Run `tools/deployed_ref.py` first.
3. [README.md](README.md) — the language, the execution model, limits, and the starter.
4. [docs/policy-capabilities.md](docs/policy-capabilities.md) — every observation and
   action a policy has, with acceptance rules. Read before writing any BASIC.
5. [docs/leveling-economy.md](docs/leveling-economy.md) and [docs/scaling.md](docs/scaling.md)
   — how income works and how the numbers change with level; these set the strategy.
6. [TENTATIVE_LESSONS.md](TENTATIVE_LESSONS.md) — untested hypotheses to turn into A/Bs.

## Files

| Path | Contents |
| --- | --- |
| `policy/` | The James Botts policy: modules, `build.py`, the assembled `dist/james_botts.bas`, and its [README](policy/README.md) (module interface, telemetry, PRINT budget). |
| `tools/lasthit_eval.py` | Local evaluation harness: mirror or versus-reference matches, per-class last hits, XP cross-check, rates per 1,000 ticks. Initial R&D only; a local result is not evidence against the live field. |
| `tools/expand_replay.nim`, `tools/build_expand_replay.sh` | Version-matched replay expansion, exact rewards, action acceptance and sampled state; [output contract](docs/replay-format.md#4-replay-tools-current-contract). Ambiguous victim identities remain null without losing verified episodes. |
| `tools/replay_actions.py` | Pure-stdlib tape/CPU decoder when the recording engine cannot build; acceptance and hash verification are unavailable. |
| `tools/replay_stats.py` | Cached episode/batch replay tables (Markdown/JSON), policy names, team shares/ranks and explicit coverage failures; fast reward-only mode by default. |
| `tools/viz_replay.py` | Pillow paths/heatmaps on the tile grid from expanded objective-state samples. |
| `tools/test_replays.py` | Focused decoder parity, reward statistics and cache checks; see the replay contract for the command. |
| `tools/gota_episodes.py` | Reader for downloaded hosted episodes (`episode.json`, `results.json`, the game log summary, our seats' `LH` telemetry): per-episode and per-seat records, seat-to-class map, role tiers. |
| `tools/compare.py` | `coworld-ab` adapter: matched fresh A/B of two policy versions, one observation per episode per group (`--group class|role|team|all`), XP, level, last hits, kills, deaths, VM errors, draws. |
| `tools/miner_rows.py`, `tools/features.py` | `coworld-hypothesis-miner` row builder and feature adapter: one row per own seat, score = XP, XP rate, last hits, or win; score components excluded from the features. |
| `episode_data/` | Downloaded hosted batches (gitignored), one directory per experience request. |
| `docs/designs/` | Design documents; the last-hit policy design carries the engine evidence it rests on. |
| `reference/base.bas` | The official starter policy. Keep reference files distinct from candidates. |
| `docs/` | Source-verified mechanics documents, each with a Currency block naming the commit it holds at. |
| `docs/wiki/` | Our maintained copies of the public wiki pages. Public writes need James's go-ahead. |
| `docs/roles.md` | Hero role model: four jobs, per-hero mapping, farm priority; the public forum version is linked from it. |
| `forum_agent/` | Brief and state for the standing forum agent (`tools/forum_agent/` at the root) that watches the roles thread. |
| `docs/requested-game-changes.md` | Engine change requests for the polyworld maintainer, with reasons. |
| `tools/deployed_ref.py` | Resolves the league's current coworld release to its polyworld commit and says whether the docs are current. |
| `tools/scaling/` | Engine spec dump, scaling model, and figure generator for `docs/scaling.md`. |
| `../docs/reports/gota-*` | Rendered, commentable versions of the four research reports. |

## Rules specific to this lab

- **Cite the deployed commit, not `main`.** Replays only re-simulate at the recording commit,
  and `main` moves ahead of the league (three releases shipped on 2026-09-16 alone). The
  league moved to polyworld `f2ab9598` (coworld 2026.9.16.5) on 2026-09-17; the mechanics
  documents still cite `7365e4e9` and the differences are listed in WORKING_CONTEXT. Every
  mechanics doc names its commit; `tools/deployed_ref.py` resolves the live one through the
  league's game record, because each release is a separate coworld record.
- **Mechanics discoveries stay in the lab.** Do not post findings such as spell scaling to
  the forum or wiki (see `user_preferences.md`).
- **Identity.** Uploads bind to the active player session; confirm `softmax status` shows
  the James Botts player before uploading. See WORKING_CONTEXT for the current setup.
- **Team mode is a platform setting.** A seat's allies may be other players' files.
- **PRINT budget is two events per item, 128 per decision.** About 63 printed items per
  decision in total; more disables the hero for the match. Keep telemetry sparse.
- **Never infer a binary win from XP, gold, or timeout.** A timeout scores zero for all
  ten seats; `total_xp` is diagnostic only.
- Use the shared experience-request and artifact skills for evaluation. The replay
  tools are implemented; use the [current contract](docs/replay-format.md#4-replay-tools-current-contract)
  and the recording commit. Damage attribution remains blocked on engine change request 14.
- Keep documentation and wiki entries as complete current references. Replace
  superseded information directly; omit audit records, change narratives, version
  logs, obsolete measurements and references to removed information.
- League submission and public community writing remain explicitly gated.
