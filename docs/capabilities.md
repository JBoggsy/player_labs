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
| Submit/monitor after permission | [Policy lifecycle](../.claude/skills/coworld-policy-lifecycle/SKILL.md) |
| Build a missing analysis tool | [Tooling guide](tooling.md) |
| Preserve/promote findings | [Learning guide](learning.md) |

## Game entry points and supported analysis

| Lab | Analysis entry points | Limits |
| --- | --- | --- |
| [Gods of the Arena](../gods_of_the_arena_lab/AGENTS.md) | [Knowledge map](../gods_of_the_arena_lab/docs/research.md), [language and starter](../gods_of_the_arena_lab/README.md), [deployed-commit check](../gods_of_the_arena_lab/tools/deployed_ref.py), [scaling tools](../gods_of_the_arena_lab/tools/scaling/README.md) | Source-verified mechanics; no policy uploaded yet; replay expander designed but not built, so no `compare.py`/`features.py` adapter |
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
