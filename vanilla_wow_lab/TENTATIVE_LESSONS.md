# Vanilla WoW tentative lessons — session buffer

**Session started:** 2026-07-24 10:55. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`vanilla_wow_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Vanilla-WoW-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### Verify the live owner contract before implementing a planned fork
Evidence: the 2026-07-27 working context correctly said the then-current owner tree had
deleted its Gym seam and proposed rebuilding one. Freshness preflight on 2026-07-29 found
accelerated-wow 0.1.122 had since shipped canonical `WS /env`, `VanillaWowEnv`, semantic
`AgentAction`, and the hosted runtime. Reverification deleted an entire client-adapter
project from scope.

### Policy images can copy a deployed Python contract without inheriting the game client
Evidence: wowborg's image copies only `/app/environment` and `/app/player` from the exact
deployed game image into a clean Python runtime. Build validation imports
`VanillaWowEnv`, hosted runtime, and navmesh SDK, then rejects historical client binaries.
This keeps policy and deployed contract aligned while preserving game ownership of the
client.

### `/player` progress must remain an observer, including time-budget ownership
Evidence: v56 proved that opening `/player` without an early `done` makes an otherwise
healthy `/env` episode fail at the player-session deadline. V57/v58 fixed teardown by
capping the policy duration, but that changed World Race station selection and produced
an avoidable zero-move course. V59 leaves the policy budget untouched and has the observer
send `done` at the handoff deadline minus the owner-standard 35-second margin. Its 2/2
hosted episodes completed with about 1,310 yards reported live and about 4,100 movement
packets retained each.

### Solo overworld replay movement comes from POV packets, not Godview
Evidence: v59 replays contain zero Godview frames by design yet retain 4,115 / 4,097 client
movement packets. The owner viewer contract says solo/overworld playback follows the
selected POV and reconstructs motion through the normal player reducer; Godview is an
optional RFC camera/boundary sidecar, not a requirement for movement.

### The game ships deterministic combat testbeds — z7-class-combat-lab and spell-lab-* variants
Evidence: `infra/coworld_manifest_template.json` (repo @ da32437e8) defines `z7-class-combat-lab`
(level-29 twink warrior+rogue on GM Island beside a cloned hostile with target_health_multiplier
200 / target_damage_multiplier 0.001 — a can't-kill-you training dummy, 10s respawn) and four
spell-lab fixtures. For rotation/combat-module development this is the route-lab equivalent:
iterate combat logic against a deterministic target before hosted grind batches.
Status: found during combat-report research 2026-07-24; not yet tried.

### The deleted 0.1.31 seam is our re-add reference — it lives in git history AND our .sdk-snapshot
Evidence: path decision (2026-07-27) is to fork the client and re-open per-step external
selection at the v2 `step()` boundary with a Gym facade. The exact prior implementation
(nim_control_server external mode, FactorizedBotEnv/gymnasium_env.py space design) is
recoverable from the game repo's git history (deleted by 51aa3869d/b27cded53 era commits)
and our pinned `.sdk-snapshot` — don't design the seam from scratch.

### Re-pull before trusting ANY report older than a day — this repo moves at contract-rewriting speed
Evidence: 327 commits in 3 days (da32437e8 → 788e22147) deleted the entire external-selection
contract (FactorizedAction/masks/ActionSettled → `step(observation)` v2), replaced the hosted
Python wrapper with a native Nim binary, split the game into three coworlds
(accelerated/persistent/speedrun-wow @ 0.1.121), and re-formatted RFC to level-19 mixed
parties scored in minutes. A 3-day-old deep-research report needed a full rewrite, not a
line-number touch-up. Audit reports against a fresh pull before acting on them.

### Deployed-package truth: `coworld list` no longer shows `vanilla_wow` — look for speedrun-wow / accelerated-wow / persistent-wow
Evidence: 2026-07-27 `coworld list` has speedrun-wow/persistent-wow/accelerated-wow 0.1.121
(canonical) and no vanilla_wow entry. The release pipeline cuts three single-variant
packages from one commit (release/build_coworld_package.py COWORLD_RELEASE_PROFILES).

### The pinned SDK snapshot is the cheap way to answer "what does OUR contract actually have"
Evidence: HEAD's nim_control.py has BotThreatObservation, combo_points, shapeshift_form,
spell_power_costs, combat_distance — none exist in `.sdk-snapshot/wow_sdk/nim_control.py`
(the 0.1.31 pin). Reading the snapshot directly resolved a conflict between two lab docs
(recon said "threat summary in frame", t1 design said "HEAD only" — t1 was right) in
minutes, no container needed. Always diff pin-vs-HEAD before designing against frame fields.

### Game repo reorganized — `player/bots/` → `player/behavior/`, manifest → `infra/`
Evidence: pull to da32437e8 (2026-07-24) moved rotations to `player/behavior/rotations/`
(per-class files: shaman.nim, warrior.nim, …, model.nim, selectors.nim), leveling to
`player/behavior/leveling/`, SDK to `player/sdk/`, manifest to `infra/coworld_manifest_template.json`.
All lab-doc citations using `player/bots/...` paths are stale.

### A clean `/env` close before the first frame can be a game startup failure
Evidence: two wowborg:v46 hosted requests on accelerated-wow 0.1.122 produced only
`ConnectionClosedOK(1000)` and `replay_missing`. The owner traced this to the hosted
environment failing to apply its per-session asset base before loading the DBC character
catalog. Accelerated-wow 0.1.124 fixes the asset initialization and now sends typed
pre-session close reasons instead of making policy and game failures indistinguishable.

### A stale `/env` rejection may be followed by more typed errors before the current frame
Evidence: v53 handled the first stale-frame rejection, then both hosted episodes exited
when another queued `EnvironmentRequestError` arrived where the adapter expected a frame.
V54 drained consecutive typed request errors until a newer `AgentFrame`; both held-out
episodes then completed with score 1.0 and replay.

### Prove navigation with novel coordinates, not only the declared station catalog
Evidence: v54 embedded a data-only course whose coordinates had never appeared in wowborg
code or docs. Two independent hosted episodes reached `novel-east-rise` in 332.9 / 341.8s
and honestly rejected a same-horizontal-position target 180 yards in the air.
