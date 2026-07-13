# Design: `vanilla_wow_lab` — a player_labs game lab for Vanilla WoW Coworld

**Date:** 2026-07-13
**Status:** complete — scaffolding + three game docs written and verified. **Extended** (same
session, later user requests) with two more docs: a strategy/how-to-play guide and an exhaustive
interface-protocol reference — see the Addendum at the end.
**Author:** coding agent (with James)

## Problem & goal

player_labs runs one improvement loop (evaluate → report → direction → improve →
repeat → gated submit) for competitive Coworld players, with **one game lab per game**
(`crewrift_lab/`, `cue_n_woo_lab/`, `heartleaf_lab/`). We want a fourth lab for the
**Vanilla WoW Coworld** (`~/coding/coworlds/coworld-vanilla-wow`): a real World of
Warcraft 1.12.1 realm backed by VMaNGOS.

The goal of *this* task is to **create the lab in the same style and structure as the
existing labs**, with **thorough, accessible, accurate game documentation** — enough
that a newcomer (human or agent) can understand this unusually complex game without
leaving the repo. No player policy is built yet.

## Why this game is different from the other three labs

The other three labs are all **Python players on a sprite/text protocol via the
players SDK**. Vanilla WoW is fundamentally different, and that difference is the
central fact the docs must convey:

- **The game is a real WoW 1.12.1 (client build 5875) realm on VMaNGOS** — an
  open-source server emulator — not an abstract gridworld. Players do genuine WoW:
  authenticate to `realmd`, enter the world via `mangosd`, and drive a character
  through real movement/combat/questing/leveling/looting/death-recovery physics.
- **The player is a Nim packet-level WoW client**, not a Python SDK policy. The
  submittable baseline is **King Nimrod**, compiled headless (`-d:noGui -d:release`).
  It connects over a **WebSocket→TCP bridge** (`tools/wsproxy.nim`) that forwards raw
  Vanilla packet bytes to VMaNGOS TCP (`realmd` :3724, `mangosd` :8085).
- **"Sent is not accepted":** a client-honesty discipline runs through the whole
  engine — read a snapshot, queue one typed action, wait for the *settled
  authoritative* result, repeat. No fabricated state, no teleport, no packet
  injection, no disabled collision, no DB intervention.
- **Two game shapes:** a **persistent tournament realm** (continuous overworld, ranked
  by an account's highest-total-XP character) and **isolated, scored RFC episodes**
  (the certified/submitted surface). The current scored benchmark is
  **`rfc-five-player-clear`**: one policy in all five slots clears Ragefire Chasm's
  four bosses; fastest full clear wins.

Consequence for build paths: making a competitive player is heavier here than a
prompt swap — options include a new leveling profile, new/better class rotations,
forking King Nimrod, or the identity-blind "general-grinding" lane. Which path is a
human-direction call, not a default.

## Readiness gap (documented honestly)

The game repo's README badge reads **"coworld verify: not ready."** The submitted
identity is **`vanilla_wow:0.1.4.post8`** (built from a pinned Coworld commit), and
`coworld certify` has passed its executable steps, but the "ready" badge waits on
retained replay-v4 XP-request and league artifacts on Kubernetes. The lab must **not**
pretend a normal live league exists: its status is "docs + scaffolding ready; the
evaluate→improve loop is blocked until the game certifies and a league opens." Whether
a live Observatory league exists is to be **verified before** claiming the loop is
runnable. This mirrors how `heartleaf_lab` was seeded (scaffolding-only, no player).

## Decisions (from the brainstorming forks)

1. **Lab name:** `vanilla_wow_lab` (explicit; mirrors the `coworld-vanilla-wow` repo).
2. **Docs structure:** **three** game docs (the game is too complex for one):
   - `docs/vanilla-wow-gameplay.md` — the game itself, accessibly: what WoW/VMaNGOS
     is, the two game shapes, the RFC episode, dungeon/XP scoring, and the
     strategically-relevant mechanics (classes, combat, leveling, navigation,
     dungeons), written for someone who has never played WoW.
   - `docs/vanilla-wow-player-contract.md` — the wire contract: the `/player` WS
     handshake and `wow_session` message, the two network planes + `wsproxy` bridge,
     what a policy **observes** (TelemetrySnapshot + Tensor-Frame-v3), what it
     **emits** (the BotAction vocabulary + 64-byte record), "sent is not accepted",
     and the submittable image (two-stage Dockerfile).
   - `docs/vanilla-wow-rfc-roles.md` — the five RFC roles (commissioner, grader,
     diagnoser, optimizer, reporter): images, env-var contracts, outputs, auto-vs-
     on-demand, and the exact commissioner round-scoring math.
3. **Readiness:** scaffold fully **and** document the gap honestly (above).

## What gets created

Mirroring `heartleaf_lab` at its creation (scaffolding-only):

```
vanilla_wow_lab/
  README.md                    orientation + readiness gap + layout
  AGENTS.md                    the loop in Vanilla-WoW terms + build paths + docs index
  best_practices.md            near-empty placeholder (filled via lessons pipeline)
  WORKING_CONTEXT.md           seeded "just created — scaffolding only; loop BLOCKED on cert"
  TENTATIVE_LESSONS.md         session buffer (SessionStart hook regenerates)
  docs/
    vanilla-wow-gameplay.md    self-contained, accessible game reference (the anchor)
    vanilla-wow-player-contract.md  the Nim packet-level player wire contract
    vanilla-wow-rfc-roles.md   the five RFC roles + commissioner scoring
    designs/                   (empty until a policy is designed)
  tools/
    rotate_lessons.sh          SessionStart hook (paths swapped to vanilla_wow_lab)
    lessons_stop_nudge.sh      Stop hook (paths swapped)
    .gitignore                 bin/
  lessons_archive/             (empty)
  .claude/skills/lessons-review/SKILL.md   ≈weekly graduation skill (name/paths swapped)
```

Root registration:
- `.claude/settings.json` — add SessionStart + Stop hook entries for the new lab.
- `README.md` — add `vanilla_wow_lab/` to the layout tree + game-labs list.

## Explicitly NOT in scope (added when a first policy is chosen)

- No player package (`vanilla_wow_lab/<policy>/`), no Dockerfile, no tests.
- No `tools/versions.env` (only needed once a Nim policy is vendored against a pinned
  game commit — as `crewrift_lab` does).
- No game-specific analysis skills (survey/warehouse) — flagged in AGENTS.md as the
  top tooling gap to fill once real episodes exist, matching heartleaf/cue_n_woo.

## Sources

Game facts are drawn (with file:line citations preserved in the docs) from the
`coworld-vanilla-wow` repo: `docs/coworld-rfc-roles.md`,
`docs/specs/0001-isolated-rfc-episodes.md`, `docs/persistent-tournament.md`,
`docs/protocol/player_protocol_spec.md`, `docs/architecture.md`,
`docs/bot-tensor-contract.md`, `docs/bot-world-state.md`,
`docs/player-observability.md`, `docs/bot-author-guide.md`,
`docs/class-matrix-qa-plan.md`, `docs/spell-lab.md`, `docs/coworld-readiness.md`,
`src/vanilla_wow_coworld/{scoring,dungeon,dungeon_scorecard,rfc_commissioner,constants}.py`,
`player/bots/actions.nim`, `player/Dockerfile`, and `coworld_manifest_template.json`.

## Validation

The lab is documentation + scaffolding; the check is: hooks are valid and path-correct,
`settings.json` is valid JSON, the `lessons-review` skill loads, root README lists the
lab, and the three game docs are accurate against the cited source. No code to run yet.

## Addendum (2026-07-13, later same session): two more docs

After the initial three-doc scaffold was approved and built, the human asked for deeper
documentation. Two docs were added, keeping the same "reference the game repo with `file:line`
citations" discipline and blending in cited web research where the topic is real-WoW knowledge:

- **`docs/vanilla-wow-strategy-guide.md`** — a beginner's-guide-plus-pro-tips-plus-strategy doc:
  WoW-in-five-minutes for the never-played reader, leveling/solo-survival fundamentals, group
  play (holy trinity, threat/aggro, coordination failure modes), the seven playable classes, and
  an RFC-specific clear plan. Backed by a repo deep-dive (leveling policy, class rotations, RFC
  dungeon def, death/nav mechanics) + web research (Wowhead Classic, Icy Veins Classic,
  warcraft.wiki.gg), with version-sensitivity flags (1.12 vs retail/SoM).
- **`docs/vanilla-wow-protocol.md`** — the exhaustive, field-level interface-protocol reference:
  every `vanilla_wow.*` message/schema (session/done, bot_action + per-kind args + the 64-byte
  binary record, movement_settlement, navmesh_traversal, control_adapter_report), the full
  `TelemetrySnapshot`, the Tensor-Frame-v3 `CWBT` layout, the transport/ports contract + WS↔TCP
  bridge, and the `CWREPLAY` v4 format. It is the spec; `player-contract.md` is the narrative.

Final doc set (5): gameplay, player-contract, protocol, rfc-roles, strategy-guide (~1,940 lines).
No player package / `versions.env` / analysis skills yet — still deferred to first-policy time.
