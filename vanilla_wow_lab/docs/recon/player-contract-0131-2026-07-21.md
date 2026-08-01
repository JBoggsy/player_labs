# Recon: the vanilla_wow 0.1.31 player contract (vs our pinned 0.1.19)

**Date:** 2026-07-21. **Consumer:** the wowborg migration decision — what changed in how a
Python policy observes, acts, and writes artifacts, and how our shim/bridge/policy stack
ports. Citations into `~/coding/coworlds/coworld-vanilla-wow` @ `b95d6778c` (synced to
origin/main after an upstream history rewrite — merge impossible, hard-reset required)
and **verified live inside the deployed 0.1.31 player image**
(`coworld/cow_e8eef946-…/vanilla_wow-0.1.31-1:downloaded`, pulled via
`coworld download vanilla_wow` 2026-07-21). Deployed package:
`cow_e8eef946-2010-4cca-8b18-6752c110b3dd`.

## Mission

Our wowborg v2 drives the Nim client through the 0.1.19 **file bridge**: Nim writes
`state.json`, Python writes `action.json`, Nim appends `action-results.jsonl`. Four
commits on 2026-07-16/17 (all shipping in 0.1.31) rebuilt this seam. This recon maps the
new contract end-to-end: observations, actions, launch chain, artifacts, and the
migration surface.

## The one-paragraph verdict

**`action.json` is gone; the file bridge is now read-only.** The sole mutable boundary is
a **binary framing protocol over a local TCP socket** (`vanilla_wow.nim_control.v1`,
default `127.0.0.1:41114+slot`), served by the Nim client. A Python policy either
(a) submits a **typed goal** (`leveling`/`dungeon`) and lets Nim's authored planner play
(`selection_mode="automatic"`), or (b) takes **per-step control**
(`selection_mode="external"`) by reading an immutable **EnvironmentFrame** — typed
observation + dense one-based bindings + fixed **factorized action space** + validity
masks — and submitting one mask-admitted `FactorizedAction` per frame. The container
launch chain (`KING_NIMROD_COMMAND` injection) is **unchanged**, the platform's artifact
upload URL is **unchanged** (it's injected by metta, not the game), and `state.json` /
`action-results.jsonl` still exist as evidence surfaces. Migration is a **bridge rewrite,
not an architecture change** — with one genuine loss (free-text chat) and several gains
(richer observations, masks, a 5-party dungeon goal mode, sane RFC episode budgets).

## The commit sequence (git archaeology)

| Commit | Date | What happened |
|---|---|---|
| `643bcd26e` | 07-16 | Spec first: `docs/specs/0005-nim-owned-bot-control.md` (since deleted by `6f9b29ef1`) |
| `617201df3` | 07-16 | **"Move live bot control into Nim"** — 203 files, +3.5k/−68.7k. Deleted the entire Python policy plane (`bots/llm/*`, wowee, BloogBot adapters, `docs/llm-harness.md`); gutted `runtime.py` (removed `action_file`, `write_queued_action`); grew `nim_control.py` (+700, the typed socket) |
| `cc4ad8843` | 07-16 | **"Establish canonical bot Environment Frame contract"** — created `docs/bot-environment-contract.md`; deleted `bot-tensor-contract.md` + `tensor_frame.nim` (−1.5k) |
| `4eea7d513` | 07-17 | **"Overhaul bot boundary with factorized RL contract"** — masks, `FactorizedAction`, `gymnasium_env.py` (+623) |
| `a5628838e` | 07-17 | Records the canonical **0.1.31** release |

Post-release schema-sync commits (`71509f0a2`, `12b6bc4fd`, `a4a2323c5`, …) show the
two-sided contract is actively enforced: every Nim field change lands with its Python
model change.

## Findings

### Q1 — How does a policy send actions now?

**Transport:** length-prefixed binary frames over local TCP. Python client
`src/wow_sdk/nim_control.py`: magic `0x44524E4B` ("KNRD"), header
`struct "<IHHII"` (magic, version, frame type, request id, payload length), JSON
payloads, 1 MiB cap (`nim_control.py:16-28`). Frame types: GOAL_REQUEST=1,
CONTROL_DIRECTIVE=2, ACTION_SELECTION=3, STATUS_REQUEST=4, CONTROL_STATUS=5,
ENVIRONMENT_FRAME=6, ACTION_SETTLED=7, CONTROL_ERROR=8. Host/port env:
`WOW_SDK_NIM_CONTROL_HOST` / `WOW_SDK_NIM_CONTROL_PORT` (default 41114+slot; 0 disables
— `nim_control_server.nim:357-358`). Nim server: `nim_control_server.nim:23-44` (same
constants, same frame types).

**Client API** (verified in the deployed image, `nim_control.py:722-826`):
`NimControlClient(host, port, slot).connect()` → `status(include_environment_frame=)`,
`submit_goal(GoalRequest)`, `directive(ControlDirective)` (hold/resume/cancel),
`select(ActionSelectionRequest)`, `last_settlement()`.

**Two policy modes:**

1. **Goal supervision** — `GoalRequest{goal_kind: "leveling"|"dungeon", bot_id,
   stop_level, deadline_unix_seconds, party_members/leader_name/role (dungeon),
   selection_mode: "automatic", practice_reset, rfc_launch}` — Nim's authored planner
   plays; Python watchdogs via `status()`. This is what the shipped
   `leveling_pilot.py` now is (its docstring: *"This module deliberately contains no
   observation-to-action policy"*).
2. **External selection** — submit the goal with `selection_mode="external"`, then loop:
   poll `status(include_environment_frame=True)` until `action_ready` /
   `phase ∈ {offered, executing}`, choose a mask-admitted `FactorizedAction`, submit
   `ActionSelectionRequest{action, frame_id, observed_tick, expected_slot,
   expected_revision}` — **single-use and stale-safe** (optimistic concurrency on
   revision). `src/wow_sdk/control/cli.py:215-265` is the reference loop;
   `frame.allows_action(action)` is the client-side pre-check.

**The FactorizedAction record** (`nim_control.py:385-399`): a fixed record —
`{kind, target, spell, item, equipment_slot, quest, choice, recipient, text, trigger,
dialog, destination: WorldPoint|None}` — where every discrete factor is a **one-based
index into the frame's bindings** (0 = unused). `kind` is one of ~44 semantic verbs
(same vocabulary family as 0.1.19's BotAction: move/attack/cast/interact/loot/
accept_quest/…, plus new `bind_home`, `equip_item`/`unequip_item`, `pet_attack`).
"Attack boar" = `kind=attack, target=<boar's binding index>`. Movement chooses exactly
one entity target **or** one explicit same-map `destination` (`allows_action`,
`nim_control.py:647-685`).

### Q2 — How do observations reach a policy? What is the Environment Frame?

**The EnvironmentFrame** (`vanilla_wow.bot_environment.v1`;
`docs/bot-environment-contract.md`; model `nim_control.py:628-708`) is "the only
game-client/bot-policy boundary": one immutable decision frame containing

- `observation: BotObservation` — a typed projection from PlayerStateMirror: vitals,
  XP, location, pet state (incl. happiness/feed), party, visible units/objects with
  **spline motion** (destination/speed/remaining), quest progress, cooldowns, auras,
  death/recovery counters, corpse state, indoor/outdoor, a factual
  **threat summary** (attacker count, nearest distance, level delta, elite presence,
  incoming damage rate), per-unit **line-of-sight** (`nim_control.py:262-345`;
  contract §"Observation space");
- `bindings: PolicyBindings` — dense one-based tables: entities, spells, items, quests,
  **texts** (admitted message vocabulary), triggers, dialogs (`nim_control.py:407-478`);
- `action_space` + `action_mask` — fixed factor sizes and executable eligibility (spell
  gates reuse the class-rotation logic: cooldown, resource, range, LoS…);
- `recommended_action` — the deterministic planner's choice through the same factors
  (Nim's planners are *recommenders*, not a privileged path);
- `navigation` — the fixed Detour contract (`owner: vmangos_detour`; polygons stay
  client-private; policies select semantic destinations);
- `previous_transition: ActionSettled` — the last typed settlement.

**Delivery, two identical channels:** socket frame type 6, or the atomic file
**`environment-frame.json`** in the runtime dir (`environment_frame.nim:1251-1255`;
reader `src/wow_sdk/environment_frame.py`). *"There is no Tensor Frame … or
compatibility path"* (contract §intro) — tensor frame v3 is dead.

**`state.json` survives** — still a `TelemetrySnapshot` (same module, no protocol bump),
still written every 0.5 s (`nim_sdk_runtime.nim:1137-1155`), but demoted to a
**read-only observer/evidence surface** (verified: the image's
`EmbeddedClientRuntimeClient` has only read methods). Schema diffs since 0.1.19:
`stuck` removed, `PlannerStatus` restructured (semantic action + goal identity),
`ActionExecutionResult` gained `spell_failure_reason`, `MovementSettlement` gained
`source_position/arrived_position/target_position`, `ActionClientState` gained
`observed_units`/`eligible_target_count`. `action-results.jsonl` unchanged in role.

**Settlement:** execution emits `action_settled` (frame type 7) with the exact
factorized action, success, message, settled tick; a fresh frame follows. Our
"sent is not accepted" discipline maps 1:1.

### Q3 — Container launch at 0.1.31

**The injection seam is unchanged.** Verified in the deployed manifest: both shipped
players run `["vanilla-wow-reference-player"]` and differ only in `KING_NIMROD_COMMAND`
(`/usr/local/bin/king_nimrod` vs `python3 -m wow_sdk.control.hosted_general_grinder`).
`player/Dockerfile:84-87`: same CMD, same env default. The grinder is still the
template: spawns `king_richard --scenario=nim-control` with `KING_RICHARD_AUTONOMOUS=0`
(`hosted_general_grinder.py:197,333`), then `leveling_pilot --loop` as the supervisor.

Launch-chain changes that matter to us:

- **New child env:** `KING_NIMROD_SESSION_DEADLINE_SECONDS` (= the session's
  `deadline_seconds` — our duration should derive from this instead of a hardcoded
  120 s), `WOW_SDK_NIM_RUNTIME_SLOT`, `VANILLA_WOW_NAVMESH_SERVICE_URL` (the game's
  `/player/navigation` HTTP service), `VANILLA_WOW_RFC_ASSIGNMENT` (JSON party
  assignment), `KING_NIMROD_CHARACTER_RACE/CLASS/GENDER` (`player.py:373-407`).
- **`--assets=<url>` argv appended** to the child command (`player.py:339-341`):
  **no world data ships in the player image anymore** (verified: zero mmaps, no
  navmesh-helper binary). Maps/VMaps/MMaps/DBC are fetched on demand from the *game*
  container's authenticated HTTP asset endpoint — whole-world, not Valley-of-Trials-only.
  Our `build_player.sh` sanity check (`test -d /opt/coworld-player/mmaps`) is stale for
  0.1.31 bases.
- Retry-on-exit-75, progress forwarding (`leveling-performance.jsonl` → WS `progress`
  messages), and `session_extensions=party_role,rfc_party,navigation` opt-in are new
  wrapper behaviors; none block us.
- `wow_session` schema: `realmd`/`world` direct endpoints replaced by a mandatory
  2-element `tcp_proxies`; new `character_creation`, `party_role`, `rfc_party`,
  `navigation` fields (`config.py:993-1032`).

### Q4 — Artifact writing

- **`COWORLD_PLAYER_ARTIFACT_UPLOAD_URL` is a PLATFORM contract, not a game one** — it
  appears nowhere in the game repo at any ref; it is injected by metta's job dispatcher
  ("The worker forwards each slot's URL into its player pod as
  COWORLD_PLAYER_ARTIFACT_UPLOAD_URL", `metta/app_backend/src/metta/app_backend/
  job_runner/dispatcher.py:353`). **Our `artifact.py` evidence bundle keeps working at
  0.1.31 unchanged.** (Empirically proven at 0.1.19 by the v2 smoke; the injection layer
  didn't move.)
- The 0.1.31 reference player itself uploads nothing; it streams
  `leveling-performance.jsonl` inline as WS `progress` messages. New read-only
  supervision artifacts we should bundle: `environment-frame.json`,
  `decision-audit.jsonl`, `leveling-performance.jsonl`, `decision-loop-profile.jsonl`
  (`supervision_artifacts.py:16-23`).
- Replays/results remain game-owned; the CWREPLAY pipeline and our decoder are
  unaffected.

### Q5 — Migration surface for wowborg

**The architecture ports cleanly; the bridge internals change.** Layer by layer:

| Layer | 0.1.19 (ours) | 0.1.31 | Port cost |
|---|---|---|---|
| Image/Dockerfile | `FROM` pinned base + `KING_NIMROD_COMMAND` override | identical seam | bump digest; fix sanity check (no mmaps; king_richard + wow_sdk still present) |
| `shim.py` | spawn `king_richard --scenario=nim-control`, wait for `state.json` | same spawn + pass through `--assets` argv; derive duration from `KING_NIMROD_SESSION_DEADLINE_SECONDS`; wait for control-socket connect instead of state.json | small |
| `bridge.py` observe | read `state.json` → our `Observation` | `NimControlClient.status(include_environment_frame=True)` → EnvironmentFrame (richer: bindings, masks, threat, LoS) — `state.json` also still readable | rewrite (bounded: one client class, strict models provided) |
| `bridge.py` act | write `action.json` `{kind, args}` | `submit_goal(selection_mode="external")` once, then `select(FactorizedAction)` per offered frame | rewrite; `move_to(x,y,z)` → `FactorizedAction(kind="move", destination=WorldPoint)` |
| Results | poll `action-results.jsonl` | `ActionSettled` (socket frame 7 / `last_settlement()`); results.jsonl still on disk | small |
| `policies/random_walk` | our loop drives every step | unchanged against our `types.py` seam — **this is what the swap seam was for** | ~zero |
| `trace.py` | JSONL + stdout | unchanged | zero |
| `artifact.py` | zip → `COWORLD_PLAYER_ARTIFACT_UPLOAD_URL` | unchanged (platform injects); add the new supervision files to the bundle | trivial |
| Tests | `.sdk-snapshot` from pinned image | re-extract snapshot from the 0.1.31 image; new fixture gate | small |

**New capabilities worth taking:** the `dungeon` goal kind with party roster/leader/role
handles RFC party formation *for* us (`GoalRequest` party validators;
`dungeon_pilot` in the grinder); the masks + bindings give us a legal-move list — a
policy can enumerate admissible actions instead of guessing; `FactorizedBotEnv`
(Gymnasium) exists if we ever want RL; the pre-upload **schema gate**
(`tests/test_bot_environment_frame.py`, also enforced inside `player/Dockerfile:76-81`)
makes contract drift loud at build time.

**One genuine loss — free-text chat.** The `text`/`recipient` factors index a bounded
**admitted vocabulary** binding ("currently admitted recipient/message vocabulary",
contract §bindings) — arbitrary breadcrumb strings are likely no longer expressible
as actions. Our replay-breadcrumb channel (already demoted to `minimal`) may shrink to
whatever texts the frame admits, or vanish. Evidence channels 1–2 (artifact bundle,
trace/stdout) are unaffected and confirmed retained, so this costs us redundancy, not
observability. **UNVERIFIED which texts get admitted in practice** — needs one hosted
probe or a local frame dump.

## Cross-references and surprises

- **Episode economics changed:** `rfc-five-player-clear` is now `max_ticks=300 /
  tick_rate=0.1` (≈50 min ceiling, was ~27.8 h); `orc-fresh-start` still exists but is
  re-scoped to a "Verification Fixture" (10000/10 ≈ 1000 s); the league now runs
  **three competitions** (Accelerated Leveling on `custom-fresh-start-10x`, Persistent
  Leveling on sealed 10-minute windows, RFC Speedruns) via the leveling commissioner.
  Our smoke variant of choice going forward: `custom-fresh-start` (league-shaped,
  ~1000 s single-entrant).
- **Five Nim "policy pillars"** are now first-class `bot_id`s (`king-richard`,
  `king-nimrod`, `bloogbot-datagod`, `wowee-leveling-pilot`, `grindbot-goap`) — goal
  mode can drive any of them; an A/B of pillars is nearly free.
- The strict `extra="forbid"` discipline cuts both ways: post-release commits show 0.1.x
  reference players *crashing* on wire/model lag ("The 0.1.57 reference players crashed
  with 'Extra inputs are not permitted'" — comment in `protocol.py`'s
  MovementSettlement). Pin discipline matters more, not less.
- Upstream **rewrote the repo's history** (~12k/15k divergent commits); syncing the
  read-only checkout now requires `git fetch && git reset --hard origin/main`.

## Unresolved

- **Admitted-text vocabulary in practice** — what `PolicyText` rows a real frame carries
  (breadcrumb feasibility). Resolve with a local `nim-control` run + frame dump, or the
  first 0.1.31 hosted probe.
- **Whether `selection_mode="external"` supports arbitrary exploratory movement** at the
  cadence our random-walk wants (frames are planner-paced: `action_ready` only in
  `offered`/`executing` phases; a `leveling` goal's planner may drive toward XP between
  our selections). May need a probe; worst case the T0 equivalent is a `leveling` goal
  with our supervision, and per-step control starts at T1.
- Whether wowborg:v2 (0.1.19 client) still functions against 0.1.31-hosted episodes
  (`orc-fresh-start` fixture remains, and our smoke passed on 0.1.19-era infra on
  07-15 — but the game side has since moved; a re-smoke would tell).

## Files read (full or significant section)

Game repo: `docs/bot-environment-contract.md` (full), `docs/bots.md`,
`docs/bot-author-guide.md`, `docs/bot-control-guidance.md`, `src/wow_sdk/nim_control.py`
(models + client), `src/wow_sdk/runtime.py`, `src/wow_sdk/control/{leveling_pilot,
hosted_general_grinder,cli,providers}.py`, `src/vanilla_wow_coworld/{player,config}.py`,
`player/Dockerfile`, `coworld_manifest_template.json` (players/variants),
`player/king_richard/king_richard/{nim_control_server,nim_sdk_runtime}.nim`,
`player/bots/game_interface/environment_frame.nim` (via scouts). Deployed image:
`wow_sdk` package interrogated live (runtime paths, nim_control models, grinder,
leveling_pilot CLI). Platform: metta `job_runner/dispatcher.py` (artifact URL
injection).

## Next steps (handoff)

1. **Decide the migration moment** — v2 still runs today; the forcing function is the
   base-image pin bump. Recommended: migrate now while the diff is fresh (the seam
   redesign is exactly what our swap seam anticipated).
2. Implementation order: re-extract `.sdk-snapshot` from the 0.1.31 image → rewrite
   `bridge.py` against `NimControlClient` (observe = EnvironmentFrame; act = external
   selection; results = ActionSettled) → update `shim.py` (assets argv, deadline env,
   socket-ready wait) → bump `versions.env` + fix `build_player.sh` checks → local
   container smoke with a fake control server → hosted probe on `custom-fresh-start`.
3. Probe the two Unresolved questions in the same hosted run (frame dump in the
   artifact bundle answers both).
