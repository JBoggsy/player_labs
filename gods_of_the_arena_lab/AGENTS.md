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
| `reference/base.bas` | The official starter policy. Keep reference files distinct from candidates. |
| `docs/` | Source-verified mechanics documents, each with a Currency block naming the commit it holds at. |
| `docs/wiki/` | Our maintained copies of the public wiki pages. Public writes need James's go-ahead. |
| `docs/roles.md` | Hero role model: four jobs, per-hero mapping, farm priority; the public forum version is linked from it. |
| `forum_agent/` | Brief and state for the standing forum agent (`tools/forum_agent/` at the root) that watches the roles thread. |
| `docs/requested-game-changes.md` | Engine change requests for the polyworld maintainer, with reasons. |
| `tools/deployed_ref.py` | Prints the deployed polyworld commit and whether the docs are current. |
| `tools/scaling/` | Engine spec dump, scaling model, and figure generator for `docs/scaling.md`. |
| `../docs/reports/gota-*` | Rendered, commentable versions of the four research reports. |

## Rules specific to this lab

- **Cite the deployed commit, not `main`.** Replays only re-simulate at the recording commit,
  and `main` already differs (tower rebalance, the observation expansion in
  [docs/policy-capabilities.md §3.6](docs/policy-capabilities.md), heal buffs). Every mechanics
  doc names its commit.
- **Mechanics discoveries stay in the lab.** Do not post findings such as spell scaling to
  the forum or wiki (see `user_preferences.md`).
- **Identity.** Uploads bind to the active player session; confirm `softmax status` shows
  the James Botts player before uploading. See WORKING_CONTEXT for the current setup.
- **Team mode is a platform setting.** A seat's allies may be other players' files.
- **Never infer a binary win from XP, gold, or timeout.** A timeout scores zero for all
  ten seats; `total_xp` is diagnostic only.
- Use the shared experience-request and artifact skills for evaluation. The replay
  expander is designed ([docs/replay-format.md](docs/replay-format.md)) but not built.
- Keep documentation and wiki entries as complete current references. Replace
  superseded information directly; omit audit records, change narratives, version
  logs, obsolete measurements and references to removed information.
- League submission and public community writing remain explicitly gated.
