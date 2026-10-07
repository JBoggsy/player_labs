# Paintbot PW lab

A lab for building and improving a BASIC policy for **paintbot-pw**, Paintbot rebuilt on
the Polyworld Nim engine. Sixteen cogs (Red = even seats, Blue = odd) fight for ten
heart towers on Heartwick island; every seat is a BASIC script the game hosts itself, so
there is no player container. Agree the policy and strategic objective with James before
implementing behavior.

**This is not [`paintbot_lab/`](../paintbot_lab/AGENTS.md).** That lab covers the older
Paintbot coworlds (Season 1 capture-the-heart shooter, Season 2 battle royale with WASM
plays and the Stencil Nim player). Different engine, rules, player format, replay format
and tools. Do not reuse its code, mechanics claims or lessons here without re-verifying
them against paintbot-pw source. The closest sibling is
[`gods_of_the_arena_lab/`](../gods_of_the_arena_lab/AGENTS.md): same engine family and
BASIC dialect, different game and host API.

## Agents: start here

Every tool is one command away and drivable without a human. From the repo root:

```bash
uv run python paintbot_pw_lab/tools/pw.py doctor --json   # release pin vs league, builds, env; prints fix commands
uv run python paintbot_pw_lab/tools/pw.py tools --json    # the tool catalog: what each answers, inputs, outputs
```

- **Tool index and the agent CLI contract:** [docs/tools/README.md](docs/tools/README.md)
  (generated from `tools/pw.py`; [contract](docs/tools/README.md#agent-contract)). Every Python
  tool takes `--json` (one object: `ok`, `outputs`, `counts`, `failures`, `result`, `next`) and
  exits 0 ok / 1 some inputs failed / 2 usage (valid values listed) / 3 build or environment
  missing (`next` holds the fix). The shell and Nim wrappers (`build`, `build-native`, `trace`,
  `map-raw`) and the shared `mine`/`test` passthroughs do not print the JSON envelope.
- **Opponent refs:** `pw.py leaders --json` lists today's champions as exact `name:vN` refs
  (it handles champions whose leaderboard label is null).
- **Deferred game-specific work:** [TODO.md](TODO.md).
- **Release pin:** `tools/release.env` is the single source of the engine tag every tool uses;
  `pw.py deployed-ref --write --json` moves it when the league moves.
- **Skills** (in [.claude/skills/](.claude/skills/); read the SKILL.md directly when working from
  the repo root, since lab skills only auto-load for files under this directory):

| Skill | Use when |
| --- | --- |
| [paintbot-pw-compile](.claude/skills/paintbot-pw-compile/SKILL.md) | compiling committed strategy source with Claude or Codex through local gates |
| [paintbot-pw-loop](.claude/skills/paintbot-pw-loop/SKILL.md) | running the improvement loop unattended (needs the loop charter in WORKING_CONTEXT) |
| [paintbot-pw-replay](.claude/skills/paintbot-pw-replay/SKILL.md) | unpacking or looking at a replay/episode: events, metrics, movement diagrams, match report |
| [paintbot-pw-ab](.claude/skills/paintbot-pw-ab/SKILL.md) | deciding whether a change helped (A/B on an explicit score outcome and ranking margin) |
| [paintbot-pw-diagnose](.claude/skills/paintbot-pw-diagnose/SKILL.md) | "why are we losing / what should we change": flags, worst losses, hypotheses, miner |
| [paintbot-pw-scout](.claude/skills/paintbot-pw-scout/SKILL.md) | what the leaders do, from public episodes: matrix, profiles, shout protocols |
| [paintbot-pw-local](.claude/skills/paintbot-pw-local/SKILL.md) | compile checks and fast local screening (never field evidence) |
| [paintbot-pw-tune](.claude/skills/paintbot-pw-tune/SKILL.md) | SPSA search over `' @tune` constants, then a hosted A/B |

## Read in this order

1. [WORKING_CONTEXT.md](WORKING_CONTEXT.md) — current objective, identity, next decision.
2. [README.md](README.md) — the knowledge map: what we know, where it is, how to check it
   is still current. Run `tools/deployed_ref.py` first.
3. [docs/mechanics.md](docs/mechanics.md) — the rules as deployed; section 1 (winning
   versus glory) sets the whole strategy.
4. [docs/policy-surface.md](docs/policy-surface.md) — the BASIC dialect, budgets, failure
   modes and every host call. Read before writing any BASIC.
5. [docs/field.md](docs/field.md) — leagues, match configuration, standings, experience
   request options and credit budget.
6. [docs/evidence-pipeline.md](docs/evidence-pipeline.md) — artifacts, the replay format and
   hash-checked re-simulation; [docs/tools/README.md](docs/tools/README.md) — the tools built on it.
7. [TENTATIVE_LESSONS.md](TENTATIVE_LESSONS.md) — untested hypotheses to turn into A/Bs.

## Files

| Path | Contents |
| --- | --- |
| `docs/mechanics.md` | Rules at the deployed commit: heart meter vs glory, awards, hearts, lives, combat, pickups, vision, modes, result fields, guide-vs-code mismatches. |
| `docs/policy-surface.md` | Upload formats (raw `.bas`, neural ZIP), dialect, per-tick execution, budgets, failure modes, host API, advisor oracle, starter summaries. |
| `docs/field.md` | Both leagues' configuration and ranking rule, dated standings, entrants, our account's presence, experience-request fields and credit costs. |
| `docs/community.md` | Forum/wiki digest (the forum is empty; the wiki is a stale README copy), maintainer measurements, gotchas, release cadence. |
| `docs/evidence-pipeline.md` | Artifact inventory, replay format, re-simulation constraints, local runs. |
| `docs/reports/` | Dated evidence reports (not maintained as current truth): [2026-09-29-league-field-analysis.md](docs/reports/2026-09-29-league-field-analysis.md) (80 league episodes: endings, sides, seeds, champion styles, shout protocols, friendly fire). The readable game overview is the repo-level [onboarding report](../docs/reports/paintbot-pw-onboarding-2026-09-28.html). |
| `docs/tools/` | One reference per tool (agent contract, commands, outputs, limits); `README.md` is the generated index, `tables.md` the Parquet table contract. |
| `strategy/` | The policy source (layout: strategy-file-format design §4.1). **Load-bearing: `STRATEGY.md` is the source of truth; compiled BASIC is never edited by hand.** [`compiler/`](strategy/compiler/) contains the M0 runtime and agent instructions; [`pw.py strategy`](docs/tools/pw_strategy.md) compiles committed sources. `STRATEGY.md` and `skills/motor/skill.bas` now specify M3 communications and receiver effects; [`compiled/b41ef1fc-1/report.md`](strategy/compiled/b41ef1fc-1/report.md) records passing gates and identical baseline play. [`comms.md`](strategy/comms.md) defines comms v1 and its acceptance status. |
| `docs/designs/` | Design documents. [`2026-09-29-tooling-plan.html`](docs/designs/2026-09-29-tooling-plan.html) is the tools-and-skills plan, now implemented (brief: `.tooling-plan-brief.md`). [`2026-09-30-strategy-file-format.md`](docs/designs/2026-09-30-strategy-file-format.md) (rendered: `.html`) is the **accepted** format for the load-bearing strategy file (2026-09-30). [`2026-09-30-strategy-compilation.md`](docs/designs/2026-09-30-strategy-compilation.md) (rendered: `.html`) is the **accepted** compile process: deterministic Python around one LLM step, unit files, versioning, report, gates. |
| `tools/` | The instruments: `pw.py` (dispatcher, catalog, doctor), `pw_cli.py` (shared CLI contract), `release.env` / `pw_release.py` (engine pin), Nim `pw_trace` / `pw_map`, Python readers, metrics, visuals, A/B, local harness, scouting, miner, win probability, tuning; `tests/`. Build products go to gitignored `tools/bin/` and `tools/.cache/`. |
| `.claude/skills/` | The seven lab skills listed above. |
| `reference/base.bas`, `reference/jev.bas` | Frozen official teams starters at 0.3.89 (preserved across engine-pin migration), from `coworld/paintbot/players/` (the files the manifest's `player[]` hashes name). The repo's `examples/paintbot/players/base.bas` is an older engine-test copy; do not use it. Keep reference files distinct from candidates. |
| `reference/intent_telemetry.bas`, `reference/wire_intent_base.py` | The intent-line module for our policies, and a script that wires it into `base.bas` for audits. |
| `reference/heartland/` | FFA-kin starters for the separate Heartland coworld; they do not compile in the teams game. |
| `reference/manifest-0.3.80.json` | The deployed coworld manifest (config schema, variants, readme). |
| `episode_data/`, `analysis/` | Downloaded episodes and tool outputs (gitignored). |

## Rules specific to this lab

- **Every policy change goes through `strategy/STRATEGY.md` and the compiler.** Never hand-edit
  `.bas` files outside skills: edit `STRATEGY.md` (or a skill's authored `skill.bas`), then build
  with `pw.py strategy compile`. This applies to optimizer loops, local experiments and tuning
  candidates alike; the paintbot-pw-loop skill's `policy_file` means the strategy source.
  (James, 2026-10-06.)
- **Cite the deployed commit, not `main`.** The source is `Metta-AI/paintbot-pw` (local
  clone `~/coding/coworlds/paintbot-pw`), a standalone copy of Polyworld. The manifest's
  `source_url` carries no commit; the `coworld-v<version>` tag is the only link from a
  release to source, which `tools/deployed_ref.py` resolves. Releases ship several times a
  day (40 in the first 10 days), so re-run it before trusting any mechanics claim.
- **Maintainer docs are leads, not truth.** The game's guide, `DEPLOYMENT.md`, `neural_basic.md`,
  the manifest readme and the wiki have all disagreed with the deployed code (budgets, glory
  values, size limits). Verify every mechanical claim against source at the deployed commit before
  relying on it; record mismatches in `docs/mechanics.md` §8 / `docs/community.md` and move on.
- **Resolve the current ranking rule before performance comparisons.** On 2026-10-05 the
  current league reports OpenSkill, `margin_scale: 600`, and mean round scoring. The earlier
  Elo outcome formula is historical; backend semantics were verified at metta `dcdfc19a`. Use the additive
  `score_outcome` metric with explicit `--margin-scale 600` after rechecking the live value;
  `elo_outcome` remains the historical default. Result scores remain winning glory, with loser/draw scores zero. Read
  [docs/mechanics.md §1](docs/mechanics.md) and never infer a win from anything but the result.
- **A BASIC compile error fails the whole episode** (no results, no data from that
  eval slot); it shows up as failed hosted episodes, which is the signal to read. Using a host
  function name as a variable is a compile error too: `rnd` became one in 0.3.89. A file the host
  rejects at staging also shows up as a failed episode on the platform (live, 2026-09-30). When
  the platform attributes a failure to one policy, Elo scores that side as a forfeit loss
  (`elo.py:174-179`) and 3 consecutive failures disqualify a league entry, so only submit
  a version with completed hosted episodes. A runtime error or budget overrun disables
  only that seat for the rest of the episode.
- **Budgets are 50,000 instructions and 125,000 work units per decision**
  (`bots.nim:41-42` at `118e1619`; scaled up by seats/16 above 16 seats); the guide and starter headers still say 20,000.
- **Teams-only vs FFA-only names.** Calling an FFA-kin function (`kin()`, `gene()`, …) in
  the teams game is a compile error. Keep Heartland code paths separate.
- **Replays re-simulate across versions and Nim builds.** The newest build replays older rules
  versions hash-exactly (rules-44 replays under 0.3.65-0.3.89 builds), and hosted tapes built with
  Nim 2.2.10 replay exactly under local Nim 2.2.6 (80 of 80 hosted 0.3.79 episodes and 12 of 12
  hosted 0.3.89 episodes under a 0.3.89 build, 2026-09-30). Always hash-check:
  `pw_trace` does; the repo's `replay_stats.nim` does not.
- **Experience-request rosters:** pin all 8 opponent seats to one explicit policy to match
  league conditions; `top_n`/`random` draw per seat and mix opponents. Never put our policy on
  both teams in a hosted request (self-play; `pw_ab_requests.py` refuses `h2h`): screen
  candidate-vs-baseline locally with `pw.py local screen`.
- **Identity.** Uploads bind to the active player session; confirm `uv run coworld player list` marks
  the intended player before uploading (see WORKING_CONTEXT).
- Use the shared experience-request, artifact, A/B and miner skills; this lab supplies
  the game adapters. Keep documentation as complete current references; replace
  superseded information in place.
- League submission and public community writing remain explicitly gated.

## Strategy compiler for Codex and Claude

Use `pw.py strategy compile --agent codex|claude --json`. Both agents read
[`strategy/compiler/AGENT.md`](strategy/compiler/AGENT.md); the driver owns the
compile loop. See [the command reference](docs/tools/pw_strategy.md). Never edit
finalized BASIC builds. Source and compiler inputs must be committed first.

`pw.py strategy audit ROOT... --build ID --json` audits existing recordings against a
verified build. Read the [audit contract](docs/tools/pw_strategy.md#five-level-audit-m2):
exit 0 means analysis completed, not that checks passed. Unmeasurable checks and missing
level declarations never pass. M2 is qualified locally and in a hosted episode on 0.3.115; see WORKING_CONTEXT.

For compiler architecture, Python interfaces, artifact contracts and cross-game adaptation,
read [the maintainer guide](docs/strategy-compiler-maintainers.md). The compiler is currently
Paintbot-specific; `--source` does not select a different game. Coordinate compiler/runtime
edits with concurrent policy work, and never change inputs underneath an active build.
