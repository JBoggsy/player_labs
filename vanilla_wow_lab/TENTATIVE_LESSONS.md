# Vanilla WoW tentative lessons — session buffer

**Session started:** 2026-07-21 09:23. This is THIS SESSION's lesson buffer. Write candidate
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

### For LONG hauls, staging waypoints make the 0.1.31 executor WORSE — hand it the real destination; stage only around provably-unsolvable chokes

Evidence: 9 race batches (v5→v20). Direct 740yd Sen'jin: ~2 yd/s, ~14 yd/settlement
(completes in ~360s). Every staged variant was slower or wedged: gate-corridor via
node CAUSED a permanent oscillation jam at the gate ramp; descent stage nodes halved
chunk size to ~2.5 yd/settlement; a guessed-low z on stage nodes forced projection
recovery at 0.4 yd/s. The executor's own Detour handles long routes; our value-add is
only at genuine chokes (east-field wall — even authored approachRoute chains only
partially help there) and course design. Corollaries: stage-clear radius must be
corridor-grade (35yd not 16yd); passed stages need hysteresis or Detour jitter
re-arms them; time budgets should never cap a leg that is still displacing
(zero false DNFs after v16), with a hard 2x cap for glacial legs.

### Race-iteration method that worked: per-leg trace events + a batch scoreboard turn every hosted run into a falsifiable verdict

Evidence: race_leg/race_leg_skipped trace events (name, seconds, yards, moves, reason,
remaining_yd) + race_report.py per-waypoint difficulty table let each 4-episode batch
name its dominant failure mode in minutes (oscillation coords, budget-vs-stall split,
z-recovery crawl). 9 uploads in one session, each fixing a measured failure; endpoint
6/8 clean episodes at ~1.9 yd/s. The waypoint catalog encodes reachability knowledge
as data (tiers incl. a quarantined 'hard' benchmark tier + via chains).

### The 0.1.31 wrapper hands world data via VANILLA_WOW_ASSET_SERVICE_URL env — the KING_NIMROD_COMMAND child must convert it to --assets=<url> itself

Evidence: v3 hosted probe (2026-07-21): contract worked end-to-end but ALL 139 moves
settled "piloted movement made no goal-relative progress" — king_richard logged
"http fetch failed (No uri scheme supplied.)" for every asset and had no mmaps. The
wrapper does NOT append --assets to the child argv; hosted_general_grinder.py:293-294
reads the env var and builds the flag. v4 (env-first assets_argument) fixed it: ep2 =
102/135 legs reached, ~1,510 yd traced, replay-confirmed 1,581.8 yd. When porting a
grinder-shaped supervisor, port its ENV plumbing, not just its process tree.

### 0.1.31 admitted-text vocabulary does NOT include our breadcrumb strings — /say is now planner-vocabulary-only

Evidence: v4 probe traces show say_not_admitted for our texts; zero wowborg says in the
replay (the 135 chat packets are the Nim layer's own narration). Chat is officially a
bonus channel; trace.jsonl + artifact bundle carry all evidence. Also: ActionSettled
carries no settlement_kind/displacement (those live in action-results.jsonl) — the
trace_audit displacement check needs a v3-era update before it bites again.

### 0.1.31 rebuilt the policy seam: action.json is DEAD; the mutable boundary is a binary TCP control socket (nim_control.v1) with factorized, mask-validated actions

Evidence: player-contract recon 2026-07-21 (docs/recon/player-contract-0131-2026-07-21.md),
verified inside the deployed 0.1.31 image. Python policies now either submit typed GOALS
(leveling/dungeon; Nim's planner plays) or take per-step control via
EnvironmentFrame (observation + dense bindings + action masks) → one FactorizedAction per
offered frame, stale-safe by frame_id/revision. state.json/action-results.jsonl survive
as READ-ONLY evidence. KING_NIMROD_COMMAND injection + platform artifact upload are
unchanged → wowborg's swap seam holds: bridge rewrite, policies/tracing/artifact intact.
Watch items: free-text chat is now a bounded admitted vocabulary (breadcrumbs at risk);
player images no longer carry world data (game serves it via --assets URL; our
build_player.sh mmaps check is stale for 0.1.31 bases).

### The game repo's origin/main gets FORCE-REWRITTEN — sync the read-only checkout with `git reset --hard origin/main`, not merge

Evidence: 2026-07-21 pull: HEAD and origin/main had diverged by ~12k/~15k commits with
the SAME author/content (history rewrite upstream); `git pull` produced thousands of
add/add conflicts. Since the checkout is read-only reference, `git fetch && git reset
--hard origin/main` is the correct sync (stash untracked .recon/ first).

### wow_sdk's file-bridge contract DRIFTS at HEAD — validate bridge code against the PINNED base image's SDK, not the checkout

Evidence: HEAD (0.1.31-era) removed `action_file` from EmbeddedClientRuntimePaths
("Move live bot control into Nim", cc4ad8843) — bridge tests importing wow_sdk from the
checkout broke while our digest-pinned 0.1.19 base is unchanged and still deployed...
EXCEPT `coworld list` now shows vanilla_wow 0.1.31 deployed, so the NEXT pin bump must
re-verify the whole file-bridge contract (action.json may be gone at 0.1.31 — the
Python-policy seam may have moved). Fix applied: tests import from
vanilla_wow_lab/.sdk-snapshot/ extracted from the pinned image (recipe in conftest).

### The full evidence stack is CONFIRMED working hosted — elevated fetch returns logs+artifacts+results; all 10 slot-audits pass

Evidence: 2026-07-21 elevated re-fetch of xreq_c530da3b (both eps completed, 0 failed).
Per slot: `policy_agent_N.log` (~140 KB stdout incl. 122 WOWBORG-TRACE lines + the
"evidence bundle: [trace.jsonl, action-results.jsonl, state.json, heartbeat.json]"
confirmation), `policy_artifact_N.zip` (the bundle itself), AND `results.json` (retained
this time). `trace_audit.py` on every slot × its own episode: 10/10 agree (e.g. Freshwar
claimed 269.6 yd settled vs 273.5 yd observed). Root causes of session-3/4 gaps: 403
without `--elevated` + upstream deletion of v1 /jobs routes (fixed in 7130f40 on main).

### In same-brain self-play, identify "our" replay member by BEST breadcrumb overlap, not first match — and per-episode, artifacts only pair with their own replay

Evidence: trace_audit's first-match member detection misattributed slots (every slot
says similar "wowborg leg N" texts); fixed to max-overlap scoring, but explicit
`--member` (from trace session_start.character) is the reliable path. Also: a sloppy
audit loop cross-matched ep-1 traces against ep-2's replay → phantom findings. The
session_end "done:" say is often rate-limit-suppressed in-game but present in the trace
— a 1-say discrepancy is expected noise, not a violation.

## Nim control status_request requires ALL five fields (v25 lenient-frame silent no-op)
The 0.1.31 Nim server's `requireControlBool` raises on a MISSING key, not just a wrong
type — a hand-built raw `status_request` that omits `include_action_settled` gets a
CONTROL_ERROR, never a frame. Our v25 lenient-frame fallback silently never fired
because of this; the fake test server accepted the malformed request so tests stayed
green. Lesson: when bypassing an SDK to talk raw wire protocol, mirror the SERVER's
validation strictness in the test fake (read the Nim source, don't guess), and trace
the fallback's rejection path so "fallback never fired" is visible in episode traces.

## Bare no_path ≠ unreachable: self-probe the planner before declaring targets off-mesh
v25/v26: after two navmesh-service timeouts, EVERY plan returned bare no_path/0
waypoints — including for stations that planned fine minutes earlier — and L1 reported
reachable stations as "unreachable" (honesty metric poisoned). A here→here plan is a
free planner-health probe: it trivially succeeds on a working planner. Probe ok →
honest unreachable; probe fails → planner broken → degrade to direct moves (the
executor's server-side Detour still routes). Generic lesson: before trusting a
negative result from an external service, verify the service can still produce a
known-positive.

## Corridor tile loading returns partials on long hauls; ask for "all" once
wow_sdk route_navmesh tile_load_mode="auto" loads only corridor tiles and (helper
source fact) returns partial_poly corridors WITHOUT retrying all-tiles. Long hauls
then plan 150-300yd at a time, forcing a re-plan cycle per corridor end. First plan
per navigate_to should use tile_load_mode="all" (definitive full route or definitive
no_path); re-plans can stay cheap.

## Nav must run THROUGH trivial combat, not fight every road aggro
v26: every wolf pull paused a 2000yd haul for a full fight → 0.86 yd/s effective pace
(vs ~3 yd/s walking), 533s deadline failures. Movement in WoW is not interrupted by
being in combat; only yield to the fight when health is actually threatened (<50%) or
the executor keeps getting interrupted (stall streak). "Pause on combat" is the
correct-looking but wrong default for a navigation layer.
