# Optimization capability map

This is the navigation map; implementation and the linked skills define each contract. The lab combines human strategy, agent execution, hosted evaluation, game adapters, analysis/reporting and durable learning. It has no universal autonomous strategy controller.

## Shared workflow

| Decision/action | Entry point |
| --- | --- |
| Start/resume, scope and authorization | [AGENTS](../AGENTS.md), [onboarding](getting-started.md) |
| Check evaluation allowance | [XP credits](xp-credits.md) |
| Resolve roster, create/monitor evaluation | [Experience requests](../.claude/skills/coworld-experience-requests/SKILL.md) |
| Download/stream evidence | [Episode artifacts](../.claude/skills/coworld-episode-artifacts/SKILL.md) |
| Build/upload a testable version | [Build and upload](../.claude/skills/build-and-upload/SKILL.md), [artifact contract](../player-build.md) |
| Debug locally | [Local run](../.claude/skills/coworld-local-run/SKILL.md) |
| Test one mechanism | [Experiment](../.claude/skills/coworld-experiment/SKILL.md) |
| Compare baseline/candidate | [A/B](../.claude/skills/coworld-ab/SKILL.md) |
| Generate candidate hypotheses | [Miner](../.claude/skills/coworld-hypothesis-miner/SKILL.md) |
| Read community intelligence | [Community](../.claude/skills/coworld-community/SKILL.md) |
| Keep a standing, quiet presence on a forum and record what it says | [Forum agent](../tools/forum_agent/README.md) |
| Submit/monitor after permission | [Policy lifecycle](../.claude/skills/coworld-policy-lifecycle/SKILL.md) |
| Build a missing analysis tool | [Tooling guide](tooling.md) |
| Preserve/promote findings | [Learning guide](learning.md) |

## Game entry points and supported analysis

| Lab | Analysis entry points | Limits |
| --- | --- | --- |
| [Gods of the Arena](../gods_of_the_arena_lab/AGENTS.md) | [Knowledge map](../gods_of_the_arena_lab/docs/research.md), [language and starter](../gods_of_the_arena_lab/README.md), [policy and modules](../gods_of_the_arena_lab/policy/README.md), [local last-hit harness](../gods_of_the_arena_lab/tools/lasthit_eval.py), [deployed-commit check](../gods_of_the_arena_lab/tools/deployed_ref.py), [scaling tools](../gods_of_the_arena_lab/tools/scaling/README.md), [A/B adapter](../gods_of_the_arena_lab/tools/compare.py), [miner rows and features](../gods_of_the_arena_lab/tools/miner_rows.py), [replay contract](../gods_of_the_arena_lab/docs/replay-format.md#4-replay-tools-current-contract), [replay statistics](../gods_of_the_arena_lab/tools/replay_stats.py), [tape decoder](../gods_of_the_arena_lab/tools/replay_actions.py), [replay visualization](../gods_of_the_arena_lab/tools/viz_replay.py) | Version-matched, hash-verified replay rewards/events and sampled spatial/visibility data; cached Markdown/JSON tables. Ambiguous victim pairings remain null; damage attribution is unavailable. A/B and miner adapters still use their existing result/log/LH inputs and are not yet joined to replay statistics. |
| [Paintbot PW](../paintbot_pw_lab/AGENTS.md) | **Agent entry point:** `uv run python paintbot_pw_lab/tools/pw.py doctor|tools|<subcommand> --json` ([tool index + agent contract](../paintbot_pw_lab/docs/tools/README.md); skills in [paintbot_pw_lab/.claude/skills/](../paintbot_pw_lab/.claude/skills/): `paintbot-pw-loop` (autonomous loop, needs the charter in WORKING_CONTEXT), `-replay`, `-ab`, `-diagnose`, `-scout`, `-local`, `-tune`). Knowledge: [knowledge map](../paintbot_pw_lab/README.md), [scoring and rank](../paintbot_pw_lab/docs/mechanics.md), [policy surface](../paintbot_pw_lab/docs/policy-surface.md), [field](../paintbot_pw_lab/docs/field.md). Tools: hash-checked replay expansion (`pw_trace`), Parquet tables + DuckDB (`pw_episodes`), metrics, fights, flags, movement diagrams, match reports, A/B adapter with paired + SPRT tests (`compare`), local 16-seat harness at league rules (`pw_local`), public scouting, intent audit, miner adapter, win probability, SPSA tuning | Thresholds in flags/fights/metrics are uncalibrated. Hosted pairing by explicit seed and hosted seat logs are not yet exercised. Hosted h2h (self-play) is refused; screen it locally. Not the `paintbot_lab` game. |
| [webDiplomacy](../webdiplomacy_lab/AGENTS.md) | **Agent entry point:** `uv run python webdiplomacy_lab/tools/wd.py metrics|seats|local` ([lab README](../webdiplomacy_lab/README.md)). Knowledge: [game, protocol and scoring reference](../webdiplomacy_lab/docs/webdiplomacy-gameplay.md). Tools: per-seat episode loader with SC trajectories and adjudicated-order stats ([webdip_episodes.py](../webdiplomacy_lab/tools/webdip_episodes.py)), per-power metrics vs same-batch field par, [A/B adapter](../webdiplomacy_lab/tools/compare.py) (groups: all + each power), [miner adapter](../webdiplomacy_lab/tools/features.py), local all-seat runner | Country is random per episode: always read per-power rows. Field par comes from the bundled random filler only. Hosted seat logs/replays are sometimes missing; coverage is reported, not imputed. Press variants and LLM players not yet exercised. |
| [CTF](../ctf_lab/AGENTS.md) | [Tools](../ctf_lab/tools/) | Inactive lab; new gameplay work requires user direction |
| [Crewrift](../crewrift_lab/AGENTS.md) | [Survey/analysis skills](../crewrift_lab/.claude/skills/), [tools](../crewrift_lab/tools/) | Role-aware comparison; specialist belief, chat, suspicion and field studies |
| [Cue-n-Woo](../cue_n_woo_lab/AGENTS.md) | [Skills](../cue_n_woo_lab/.claude/skills/), [tools](../cue_n_woo_lab/tools/) | Game-specific reports; do not assume a shared comparison adapter |
| [Heartleaf](../heartleaf_lab/AGENTS.md) | [Event warehouse](../heartleaf_lab/.claude/skills/heartleaf-event-warehouse/SKILL.md), [tools](../heartleaf_lab/tools/) | Published aggregate and replay analysis; reporter availability must be checked per run |
| [Paintbot](../paintbot_lab/AGENTS.md) | [Tool guide](../paintbot_lab/docs/analysis-tools.md), [comparison](../paintbot_lab/tools/compare.py), [warehouse](../paintbot_lab/tools/event_warehouse.py) | Two/four-team outcomes; trace tables retain format-specific assumptions |
| [Vanilla WoW](../vanilla_wow_lab/AGENTS.md) | [Survey](../vanilla_wow_lab/tools/wow_survey.py), [tools](../vanilla_wow_lab/tools/) | Navigation, movement, profiling and route studies; no generic competitive win metric |
| [Emerg-ant](../emergant_lab/AGENTS.md) | [Tools](../emergant_lab/tools/) | Colony/economy and policy trace studies; version-specific protocols |
| [Sugarscape](../sugarscape_lab/AGENTS.md) | [policies](../sugarscape_lab/policies/) | Movement/objective evaluation; don't substitute global world welfare for a policy metric |
| [Proxywar](../proxywar_lab/AGENTS.md) | [Lab docs](../proxywar_lab/) | Recon/foundation; no claim of a complete policy evaluation stack |

The table links components rather than copying every CLI flag. Use `uv run python tools/audit_docs.py` for a discoverable file/link inventory, and each script's `--help` for its current options. A directory's existence does not prove live integration; each run records its actual validation.

Platform contracts and live-verification boundaries: [Softmax reference](platform-reference.md).
