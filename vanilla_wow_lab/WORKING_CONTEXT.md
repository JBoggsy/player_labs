# Vanilla WoW working context

**What this is.** The live, high-signal state of *what we're working on right now* in the
Vanilla WoW lab — the minimal cross-session facts to carry into the next session. Read it on
startup to resume; **update it as you learn** (keep it tight). This is *not* a log: the full
game reference lives in [`docs/vanilla-wow-gameplay.md`](docs/vanilla-wow-gameplay.md); this
file is the one-screen "where are we and why."

> Read order for a newcomer: this file → [`README.md`](README.md) →
> [`docs/vanilla-wow-gameplay.md`](docs/vanilla-wow-gameplay.md) →
> [`docs/vanilla-wow-player-contract.md`](docs/vanilla-wow-player-contract.md). And the
> lab-wide [`../AGENTS.md`](../AGENTS.md) for the operating model.

---

## Status (2026-07-29): OWNER-PROVIDED `/env` REPLACES THE CLIENT-ADAPTER PLAN

The current accelerated-wow release now ships the convenient Gymnasium interface the
lab previously expected to own. `wowborg` has been rewritten against that canonical
surface:

- `VanillaWowEnv.reset()` yields `AgentFrame`; policies submit canonical
  `AgentAction` values with synchronous `step()`.
- The game owns the WoW client, projection, action admission/execution, settlement,
  reconnects, and transport. Wowborg contains no client binary, mask adapter, or
  compatibility path.
- The deployed accelerated-wow 0.1.122 image
  (`sha256:608ac6685...e5e4`) and its source commit
  (`5bde7b590533ef8b87b2586c69156a029e450574`) are pinned in
  `tools/versions.env` and the root lockfile.
- Navigation uses the owner SDK's authenticated `/player/navigation` query while the
  policy loop uses `/env`. The full wowborg test suite is the current focused gate;
  real-navmesh catalog and held-out course results belong in `wowborg/VERSION_LOG.md`.

The older status sections below are historical context. In particular, the 2026-07-27
decision to fork/re-open a Gym seam has been superseded by the owner's shipped `/env`.

---

## Status (2026-07-27, session 5j): UPSTREAM CONTRACT REWRITTEN — combat report re-audited and rewritten; wowborg path decision is the gate

**A line-by-line audit of the combat report against the freshly-pulled game repo
(788e22147, +327 commits in 3 days) found the seam wowborg v4 is built on was DELETED
upstream.** The report is rewritten in place
(`../docs/reports/coworld-wow-combat-2026-07-24.md`, "revised 2026-07-27") around the new
v2 contract. What changed upstream (all verified in code, key commits f68817e35 /
b27cded53 / fa050a369 / 51aa3869d / 81d3aaf7b):

- **Contract v2:** no FactorizedActions, no masks, no external selection, no
  recommended_action, no ActionSettled. Bot boundary = in-process Nim
  `actions = step(observation)` at 1s sim cadence; actions are semantic verbs with REAL
  arguments (GUIDs/spell ids/world points); server is the only validity oracle; policy
  never consumes action results. Python = goal supervision only (nim_control.v2:
  submit_goal/hold/resume/cancel + observer frames).
- **Hosted player is a native Nim binary** (`vanilla-wow-reference-player
  --scenario=coworld-session`); the Python wrapper + KING_NIMROD_COMMAND seam are gone.
  Our 0.1.31 pinned image still runs (v1 session payload explicitly preserved for
  immutable players) but is a FROZEN ISLAND.
- **Three separate hosted coworlds now:** accelerated-wow (720s @ 10x, score
  level+xp/next), persistent-wow (10-min windows), speedrun-wow (RFC). Deployed at
  0.1.121; the old vanilla_wow package is gone from `coworld list`.
- **RFC format rfc-19-v1:** level-19 normalized chars (was 30), submitted role profiles
  (2 tank / 3 healer / 8 dps ids; druid now playable incl. RFC), all-role self-play
  qualifier then MIXED-POLICY scored parties, tank-invoked `.rfcreset` launch (4-attempt
  budget), godview timing, score = rfc_elapsed_minutes lower-is-better (failed run = 60.0).
  Old 1e6−seconds formula deleted. Per-slot deaths now actually count (−10k, wired).
- **Observation got richer** (threat, combo, shapeshift, spell costs, combat_distance,
  visible action bar, local_world Detour geometry in-frame); interrupt_watch verb and
  interrupt_reflex/action_bar reconciler deleted; ~1s reflex floor is real.
- **The 25-capability catalog SURVIVES** (decision-level, seam-agnostic; +P9 local_scene,
  −the mask/oracle leverage). Report §3.5 lays out the fork — with the boundary stated
  precisely: the PLATFORM contract is unchanged (any image speaking 1.12.1 over the byte
  pipes; our repo, our language). The in-process-Nim `step()` rule binds only reuse of
  THEIR client. Paths: (a) stay on the 0.1.31 island, (b) goal-supervision player on
  current packages, (c) fork their client with decisions in Nim (our pinned fork, our
  image), (d) fork their client and re-open a Python per-step seam (we own the seam they
  deleted), (e) own client from scratch (legal; still the ~20-45k-line session-4 price).
  Step 0 was the human path decision — made below.

**DECIDED (2026-07-27, James): path (d) — fork their client, RE-OPEN the per-step seam,
wrap it in a Gym-like Python interface.** Key facts feeding the decision: (i) the v2 body
ships NO gym env — the 0.1.31 `gymnasium_env.py` + external selection were deleted; we
restore and own that seam in our fork (bounded: one `nim_control` server mode + one
Python client; the v2 single-decision `step()` boundary makes the re-add simpler than the
0.1.31 original); (ii) today we maintain NO translation layer — their pinned client does
all wire work, our ~700-line bridge/shim just speaks its socket; (iii) (d) is the only
path where the proven Python nav/policy stack (v5-v45) carries over nearly intact.
Gym facade: obs space from HEAD `BotObservation` (threat/combo/costs/action-bar/
local_world), action space from `SemanticAction` (real GUIDs/ids/points; NO masks —
selector-style legality checks on our side, server rejection as ground truth; deleted
`gymnasium_env.py` in git history is the space-design reference). Revised build order in
the report §9: fork+toolchain spike → re-open seam + Gym facade → port nav brain →
combat capabilities (shaman first) → RFC. Costs accepted: seam ownership + fork rebase
burden; mitigate with a minimal mechanical seam patch and per-iteration fork pins.

**Also:** upstream ships two RFC pace identities (richard-rfc 50% vs relh-rfc 65% party-
mana advance gate) — a free A/B on the knob they think is binding. Lab docs
(player-contract recon, gameplay, rfc-roles, strategy-guide engine citations) are now
stale on contract/scoring — the revised report supersedes them where they conflict.

---

## Status (2026-07-24, session 5i): combat capability report published — T1 combat is fully scoped

**The combat research is done:** `../docs/reports/coworld-wow-combat-2026-07-24.md` — deep
research (game repo @ da32437e8 + pinned 0.1.31 SDK snapshot + web) into WoW 1.12 combat,
the nim-control obs/action contract, and the authored combat stack, distilled into a
**25-capability atomic catalog** (8 perception / 12 decision / 5 group) + arbiter spine,
dependency graph, build order (shaman first), and measurement plan. Load-bearing findings:
(1) the **pin-vs-HEAD observation diff** — our 0.1.31 pin lacks threat summary, combo
points, shapeshift form, spell costs, combat_distance (all at HEAD); perception capabilities
derive them behind HEAD-shaped interfaces so a pin bump deletes code; (2) the game ships
**deterministic combat testbeds** we haven't used (`z7-class-combat-lab` training dummy,
`five-geared-party` RFC party sans clock) — the combat route-lab equivalents; (3) the game
repo REORGANIZED (`player/bots/` → `player/behavior/`, manifest → `infra/`; King Richard
policy gone, binary name remains) — old lab-doc citations are stale; (4) RFC budget is now
300/0.1 ≈ 50 min (gameplay doc's 10000/0.1 is stale). **Next:** the combat design doc
(per-capability dataclass contracts, shaman profile, arbiter loop), then build step 1
(P1+P4+D1+D3-minimal+D11 = "kill safe things, loot them" → first nonzero XP).

---

## Status (2026-07-24, session 5h): nav v2 audited, remediated, and RE-validated — planning generalizes; survivability is the residual

**The codex audit invalidated the 5g one-shot claim** (`docs/recon/nav-v2-audit-codex-2026-07-23.md`,
18 findings): the benchmark's skip logic censored exactly the long-range/cross-map
cases the claim needed, v37 wasn't held-out (code changed for its course), reachability
could exceed 100%, and the "validated" world coordinates were guesses (Cleft z wrong
by 56yd). All mechanical findings fixed (v39-v45, commits 841b071→ee360c7): un-censored
scoring (skips fail reachability; coverage/surprise_arrivals surfaced), off-mesh
projection terminal, arc-length staging ladder, spatial portal fakes, typed recovery,
authoritative coordinates + the south-road chain from the game repo's decision graph
(`bots/decision/graph_data.py`, `fast_travel.py`).

**The route lab** (`tools/route_lab.sh`) is the new fast loop: real planner + full
1,783-tile world navmesh + spatial area triggers inside the pinned game image, actual
L1/L2 code, idealized executor — full 13-station catalog in ~15min vs ~1h hosted.
**Re-validation through it: 13/13 catalog (incl. Orgrimmar 376s, RFC-entrance via
portal 2230 527s, deep-RFC cavern 606s sim), plus TWO held-out courses with zero code
changes: Barrens gate / Crossroads / Bloodhoof Village (Mulgore, 3000+yd) / Bazzalan's
ledge (deep RFC) 5/5, and Camp Narache / Scytheclaw plateau / Jergosh's rostrum /
razor-north-field 5/5.** Cross-continent probes fail fast+typed (unknown_region).

**Hosted long-session truth (persistent-leveling, 3470s, v41-v45):** roads walked
correctly, flee-through-combat works (deaths 7→1 on the razor leg), corridor
ghost-runs recover properly — and Orgrimmar/RFC still deadline because a LEVEL-1
character dies every ~500yd crossing level-10 territory. Route lab passes the same
journeys: the residual is **survivability, not navigation** — exactly the T1 combat
capability queued next. Nav planning is done; hosted long-range proof needs either
leveled variants (five-geared-party, rfc-five-player-clear) or T1 combat.

---

## Status (2026-07-23, session 5g): NAV V2 ONE-SHOT BAR MET — World Race generalizes to fresh courses

**The /goal is closed (v21→v38, 14 hosted batches):** add stations as pure DATA and the
agent one-shots them. Two consecutive fresh courses (never-raced coordinates baked via the
new `--stations` build seam, zero code changes) validated it:

- **v37** (canyon-mouth / trial-road / sarkoth-approach + adversarial): **4/4 episodes,
  100% reachability, 100% honesty**, adversarial probes failed-fast in ~8.5s.
- **v38** (valley-crossroads / canyon-interior / west-rise / senjin-coast + under-canyon):
  100/67/67/100 — the only misses were senjin-coast **deadline** losses (~800yd at the
  seam's ~1.5yd/s effective pace vs a 533s share: session-length physics, not navigation;
  the one senjin attempt with enough runway ARRIVED at 540.7s).

**Architecture that got there** (`wowborg/nav/`: local.py L0 / route.py L1 / journey.py L2,
`policies/world_race.py`, design: `docs/designs/wowborg-nav-v2.md`):
- **One direct semantic move per plan** — never micro-hop service waypoints; the executor's
  server-side Detour owns locomotion (v28: waypoint-feeding marched it into "no admissible
  source projection" traps). `/player/navigation` supplies reachability verdicts,
  true-distance budgets, partial progression targets.
- **Honesty machinery**: off-mesh projection / zero-waypoint no_path → fail fast (~8-13s);
  planner self-probe (here→here) distinguishes broken planner from unreachable target;
  empty partials (corridor end inside stage radius) are STALLS counted by the same-spot
  replan limit (4), never "unreachable".
- **Staging ladder** on stalls/oscillation: direct → corridor 1/2 → 1/4 → … (v37 fixed
  canyon-mouth 1/4 → 4/4); ladder resets when a leg lands. Stuck spell 7355 in L0's
  unstick (sanctioned relocation). Oscillation = revisit WITHOUT goal progress
  (switchback ramps are legal).
- **Run through trivial combat** (yield only <50% health or combat-stall); resume the same
  walk after combat (no re-plan). Lenient frames + state.json fallback survive the 0.1.31
  validation storms ("recommended action must be admitted" upstream bug — raw status_request
  needs ALL 5 fields or the Nim server errors).
- **Race policy**: nearest-first ordering, physically-honest skip (world-graph travel
  estimate vs fair-share deadline → `skipped_insufficient_time`, excluded from
  reachability), last station gets the whole remaining session.

**Known limits:** seam pace is ~2.2yd/s moving / ~1.5yd/s effective (executor advances ≤8
corridor waypoints ≈ 17yd per ~7.6s settle cycle — `ControlMoveMaxWaypoints=8` server-side),
so ~800yd is the practical single-station radius on a 970s `custom-fresh-start` session;
Orgrimmar/RFC stations need longer variants (rfc-five-player-clear: ~50min). RFC portal edge
(area_trigger 2230) still unproven hosted. **Next:** T1 combat modules per
`docs/designs/wowborg-t1-combat-modules.md` (start: combat_state + target_selector +
minimal rotation_engine; shaman first).

---

## Status (2026-07-21, session 5b): 0.1.31 player contract mapped — migration is a bridge rewrite

**The deployed game moved to 0.1.31 and rebuilt the policy seam** (recon:
[`docs/recon/player-contract-0131-2026-07-21.md`](docs/recon/player-contract-0131-2026-07-21.md),
verified inside the deployed image):

- `action.json` is gone. The mutable boundary is a **binary TCP control socket**
  (`vanilla_wow.nim_control.v1`, 127.0.0.1:41114+slot): submit a typed **goal**
  (leveling/dungeon → Nim's planner plays) or take per-step **external selection** —
  read an **EnvironmentFrame** (typed observation + dense bindings + action masks +
  recommended action), submit one mask-admitted **FactorizedAction** per offered frame.
- `state.json`/`action-results.jsonl` survive as read-only evidence;
  `environment-frame.json` is a new atomic file mirror of the frame.
- **Unchanged**: `KING_NIMROD_COMMAND` injection, the WS wrapper CMD, platform-side
  `COWORLD_PLAYER_ARTIFACT_UPLOAD_URL` injection (metta dispatcher) → our
  policies/types/trace/artifact layers port as-is; **bridge.py + shim.py rewrite** is
  the migration (the swap seam did its job).
- Notables: player images no longer carry world data (game serves assets via
  `--assets` URL — our build sanity check is stale for 0.1.31 bases);
  `rfc-five-player-clear` is now a ~50 min ceiling (300/0.1); league split into three
  competitions (smoke variant of choice: `custom-fresh-start`, ~1000 s);
  `dungeon` goal mode handles RFC party formation natively; free-text chat is now a
  bounded admitted vocabulary (breadcrumbs at risk — probe needed).
- Open probes: admitted-text vocabulary in a real frame; whether external selection
  paces well for pure exploration; whether v2 (0.1.19) still runs on 0.1.31 infra.

**HOSTED VERIFICATION DONE (session 5d) — wowborg v4 works against the real 0.1.31 controller:**

- **v3 probe** (xreq_bafc50aa, custom-fresh-start): contract PROVEN (socket connect,
  goal armed, 139 frames offered/selected/settled, evidence bundle retained incl.
  environment-frame.json) but **all moves failed "no goal-relative progress"** —
  king_richard had no world data. Root cause: the wrapper exports
  `VANILLA_WOW_ASSET_SERVICE_URL` and expects the KING_NIMROD_COMMAND child to convert
  it to `--assets=<url>` (as hosted_general_grinder does); our shim only checked argv.
- **v4 = the fix** (env-first assets_argument). Probe xreq_34150d19: ep1 26 legs /
  15 reached / ~259 yd; **ep2 135 legs / 102 reached / ~1,510 yd traced — replay
  independently shows 1,581.8 yd**. External per-step selection paces FINE for pure
  exploration (102 settled moves in ~16 min; zero mask fallbacks). Failures are honest
  Detour outcomes ("no goal-relative progress" on unreachable random points).
- **Admitted-text probe answered:** our `/say` breadcrumbs did NOT appear in the replay
  (say_not_admitted) — the vocabulary is planner-supplied; chat channel now truly
  bonus-only. The 135 chat packets in the replay are the Nim layer's own narration.
- trace_audit caveat vs 0.1.31: settlement_kind/displacement aren't in ActionSettled
  (they live in action-results.jsonl) — audit's displacement check no-ops on v4 traces;
  breadcrumb check correctly flags the unsendable says. Tool update queued.

**READY FOR THE WAYPOINT RACE** — `policies/waypoint_race.py` shipped + container-smoked:
ordered course via `WOWBORG_WAYPOINTS` (or default Valley of Trials loop), 8 yd arrival
tolerance, 3-attempt DNF skip, per-leg `race_leg` trace events, lap counting,
yards/second summary. Run = upload with `WOWBORG_POLICY=waypoint_race` (+ course env)
and fire an xreq on custom-fresh-start.

**WAYPOINT RACES CONSISTENT (session 5e, v5→v20, 9 hosted batches):** the
`waypoint_race` policy races randomized tier-balanced courses (2 near + 1 mid + 1 far
from an 11-landmark Durotar catalog, all authored-profile coordinates; seedable via
`WOWBORG_RACE_SEED`; `WOWBORG_COURSE_TIERS` overrides). **Final state (v19+v20):
6/8 episodes fully clean, ~1.9 yd/s (executor ceiling ~2.0), far legs (740 yd
Sen'jin) completing in 356-391 s.** The iteration ladder (each verdict from
race_report.py over trace bundles): v6 progress-based legs (chunked settlements) →
v7/v8 authored staging → v9 positional staging → v10 socket-timeout resilience →
v13 stage hysteresis (oscillation) → v16 moving-legs-keep-budget (zero false DNFs) →
v17 course sizing → v18 true-z on nodes → **v19 far-legs-DIRECT (staging made long
hauls WORSE — halved Detour chunk size; the executor solves the south descent alone)**
→ v20 south-rim replaces the executor-hostile shelf pocket. Residuals: (1) rare
permanent wedge in the Sen'jin coastal rocks (~1/8 episodes; unstick can't recover —
next idea: rescue-point recovery, move to nearest proven waypoint when
stalls>2×MAX); (2) hard tier (east field/mesa/NW ridge) quarantined as the
benchmark for future nav work (`{"hard": N}` course for stress tests).
`tools/race_report.py` scores batches (per-episode + per-waypoint difficulty).

**MIGRATION DONE (session 5c) — wowborg v3 built + fake-server smoked, not yet uploaded:**
bridge rewritten against `NimControlClient` (external selection over EnvironmentFrames,
mask-checked FactorizedActions, ActionSettled results); shim updated (assets passthrough,
deadline-derived budget, socket-ready wait, expanded evidence bundle); pin bumped to the
0.1.31 digest; `.sdk-snapshot` re-extracted; build sanity checks fixed (no mmaps at
0.1.31). 57 tests green — bridge tests exercise the REAL wow_sdk client against a
scripted control server (`tests/fake_control_server.py`); container smoke: goal armed,
legs selected/settled, positions tracked, clean teardown.

**Next steps:** (1) upload v3 + hosted probe on `custom-fresh-start` — validates the
contract against the real Nim controller AND answers the two open probes (admitted-text
vocabulary; external-selection pacing for exploration — watch legs_fallback in the
summary); (2) then T1 (combat/loot/quests via FactorizedAction composition — the masks
make legal-move enumeration trivial now); (3) party formation via the native `dungeon`
goal mode when RFC work starts.

---

## Status (2026-07-21, session 5): FULL evidence stack verified hosted — all 10 slot-audits pass

Elevated re-fetch of the v2 smoke (xreq_c530da3b, both eps completed / 0 failed) closed
every open evidence question:

- **All three artifact families returned** per slot: `policy_agent_N.log` (~140 KB
  stdout: 122 `WOWBORG-TRACE` JSONL lines, 40 `WOWBORG-POLICY leg` lines, the
  `evidence bundle: ['trace.jsonl','action-results.jsonl','state.json','heartbeat.json']`
  confirmation, clean exit-0), `policy_artifact_N.zip` (the bundle — trace parses,
  ~122 events/slot), and **`results.json`** (retained now; scoring =
  `highest_character_total_xp`, session metric `top_character_xp_gained`; all 0 for the
  random-walker, as expected).
- **`trace_audit.py`: 10/10 slot×own-episode audits agree** (e.g. Freshwar: 269.6 yd
  claimed vs 273.5 yd observed in the replay). Two slots show the known 1-say noise
  (the final "done:" say suppressed by our own rate limit). "Sent is not accepted" is
  now an automated, passing check.
- Root causes of the session-3/4 artifact gaps: (a) 403 without `--elevated`;
  (b) upstream deleted the v1 `/jobs` policy-artifact routes — main's `7130f40` already
  repointed the fetcher to v2 episode-request routes.
- Episode 2 totals: 5/5 members walked 244–290 yd, 18–23 legs. Survey re-rendered over
  all 6 episodes (v1 retro + both v2).
- trace_audit member auto-detection fixed for same-brain self-play (max breadcrumb
  overlap, not first match); explicit `--member` from the trace's
  `session_start.character` is the reliable path.

**Next steps:** (1) T1 bridge growth — combat/loot/quests per the obs/action design doc,
now measurable leg-by-leg and XP-by-XP (results.json gives per-slot xp_gained);
(2) party formation (invite/accept via slot-0 convention) toward the RFC benchmark;
(3) consider `wow-survey` skill packaging once T1 lands.

---

## Status (2026-07-15, session 4c): wowborg v2 HOSTED SMOKE PASSED — the loop is LIVE

**wowborg:v2 uploaded** (`eb6aa13e-…`, tag `purpose=v2-shim-random-walk`) and smoked on
`orc-fresh-start` (xreq_c530da3b-…, 2 eps; ep 1 completed, ep 2 queued behind large
crewrift batches at session end — retry-watcher running). **Episode 1 = full pass:**

- All 5 members logged in AND PLAYED: ~120 s in-world each (duration budget honored —
  the 27.8 h failure mode is dead), ~400 movement packets each.
- **Random-walk worked**: e.g. Freshwar walked **273.5 yd** over 20 legs (17 reached);
  all five members: 18–21 legs, 9–17 reached, mix of reached_target /
  advanced_corridor / no_progress settlements — real Detour-settled navigation.
- **All evidence channels proved out in the replay**: `/say` breadcrumbs
  (`wowborg leg N: <kind> (M reached)`) extracted via
  `tools/cwreplay.py packets --say-only`; trajectory via `trajectory` subcommand.
  ALSO discovered: the shim layer narrates `Policy action: <kind>` says — that's the
  NIM side echoing our queued actions (bonus channel, slightly noisy).
- **Artifact-route reality check** (job 29fcfad4-…): `policy-logs` → 403 "not a softmax
  team member" (SO: session-3's "no logs retained" was likely just the 403 — retry with
  `--elevated`); `policy-artifact` → 404 (either no upload URL injected for this game's
  players or bundle upload failed — check WOWBORG-SHIM "evidence bundle:" line via
  elevated logs next session). results.json still absent for vanilla_wow episodes.
- **Reporting tools live**: `tools/wow_survey.py` (batch HTML survey; validated on both
  smokes) and `tools/trace_audit.py` (trace↔replay "sent is not accepted" cross-check;
  needs the trace file from the artifact bundle or elevated logs to run on hosted eps).
- Known platform irritant: the xreq detail endpoint (`GET /v2/experience-requests/{id}`)
  intermittently 500s, killing `--watch`; workaround = retry wrapper (/tmp/watch_retry.sh
  pattern). The list endpoint stays healthy.

**Next steps:** (1) fetch ep 2 + rerun the survey over both; (2) retry `policy-logs`
with `--elevated` to confirm the artifact-upload question and read our trace; (3) T1
bridge growth (combat/loot/quests) per the obs/action design doc — leveling policies can
now be measured leg-by-leg.

---

## Status (2026-07-15, session 4): wowborg v2 = shim adoption; built + smoke-tested locally, NOT yet uploaded

Session 4 made the strategic pivot and built it:

- **Decision (human): drive the game's bundled Nim client (the "shim") instead of
  reimplementing the WoW protocol in Python.** Sizing recon showed a faithful Python
  client is a 20–45k-line port, while the deployed reference player image's *default
  path already is* "Python policy drives `king_richard --scenario=nim-control`
  (`KING_RICHARD_AUTONOMOUS=0`) over the file bridge" — a versioned, documented seam
  (`state.json` / `action.json` / `action-results.jsonl`,
  `vanilla_wow.llm_sdk_state.v1`). Design: `docs/designs/wowborg-v2-shim-adoption.md`.
- **Typed obs/action target spaces designed first** (session 4a):
  `docs/designs/wowborg-observation-action-spaces.html` — full observation + action
  vocabulary with wire citations and T0/T1/T2 tiers; v2 implements the T0 slice over
  the shim.
- **wowborg v2 exists and passes local validation**: `shim.py` (supervisor, the swap
  point) + `bridge.py` (only module importing `wow_sdk`) + `types.py` +
  `policies/random_walk.py` (random 10–20 yd legs, typed settlements). 45 tests green;
  image `players-wowborg:dev` builds (amd64) FROM the deployed player image pinned by
  digest in `tools/versions.env` (vanilla_wow **0.1.19**, fetched via
  `coworld download vanilla_wow` 2026-07-15); container smoke with a scripted fake
  king_richard ran 12 legs, all `reached_target`. Deadline discipline is structural now
  (`WOWBORG_DURATION_SECONDS`, default 120 s).
- **Reporting stack exists (session 4b)** — recon:
  `docs/recon/replay-tooling-2026-07-15.md`. Highlights:
  - **`tools/cwreplay.py`** — standalone CWREPLAY decoder (summary / packets-JSONL /
    trajectory / members / header; chat-text extraction). Validated against the 4 smoke
    replays. **Knowability boundary (important):** stateless decode covers
    self-describing packets — chat, login, XP events, and our OWN trajectory (outbound
    MovementInfo is plaintext) — but derived world state (other units' positions/health,
    update-field values, auras) requires the stateful client reducer; the supported
    tier-2 path is extending the game repo's `inspect_party_wire_replay.nim`
    (replay → PlayerStateMirror → snapshot JSONL), planned for when combat analysis
    needs it. Full roadmap (survey → tier-2 decode → warehouse → wow-ab):
    `docs/recon/replay-tooling-2026-07-15.md` §Build plan.
  - **v1 login RETROACTIVELY CONFIRMED**: the decoder shows `SMSG_LOGIN_VERIFY_WORLD`
    for **all 5 members in all 4 episodes** (durations ~999 s, moves=0, as expected for
    the idle skeleton). Session 3's "login success unconfirmed" is now resolved ✔.
  - **wowborg v2 tracing**: `trace.py` (JSONL + `WOWBORG-TRACE` stdout mirror of every
    observation/intent/typed-outcome), `artifact.py` (session-end evidence zip PUT to
    `COWORLD_PLAYER_ARTIFACT_UPLOAD_URL` — the retention-proof channel), and
    replay-visible `/say` breadcrumbs (`ShimBridge.say`, rate-limited) so the replay
    itself carries our leg narrative even if logs vanish again.
  - Human replay viewing: `uv run coworld replay-open <episode> --hosted` (the WASM
    viewer route was fixed upstream after our session-2 notes).
- **Next steps:** (1) upload v2 (`build-and-upload`) and run a hosted
  `orc-fresh-start` smoke — evidence now comes from THREE channels (policy-artifact
  zip, stdout/trace if retained, `/say` breadcrumbs in the replay via
  `tools/cwreplay.py packets --say-only`); (2) confirm the runner injects
  `COWORLD_PLAYER_ARTIFACT_UPLOAD_URL` (the shim logs `evidence bundle: …`);
  (3) build the `wow-survey` skill (tier-2 report over episode.json + cwreplay
  summaries); (4) grow the bridge toward the T1 slice per the obs/action design doc.

---

## Status (2026-07-14, session 3): first hosted smoke PASSED-ish; league exists; partly UNBLOCKED

Session 3 ran `wowborg` v1's first hosted experience requests. What changed since session 2:

- **The Observatory league EXISTS now** (the session-2 "no scored league" claim below is
  stale): league **"Vanilla Wow"** (`league_d7bf3aea-…`), division **"Leveling Ladder"**
  (`div_fe784707-…`), commissioner `vanilla-wow-leveling-commissioner`, weekly rounds
  (`schedule_interval_minutes: 10080`), created 2026-07-12. **Not yet verified**: whether
  the ladder actually scores/retains rounds (the game repo README badge is still
  "coworld verify: not ready" as of the 2026-07-14 pull — the badge and the league's
  existence currently disagree; treat the league's scoring as unconfirmed).
- **Deployed game package is `vanilla_wow` v0.1.6** (session 2 said 0.1.4.post8). The live
  manifest (15 variants, game configs) is fetchable via `GET /v2/coworlds/cow_d4b20fe9-…`;
  trust it over the local checkout.
- **First smoke (xreq_23feebad-…, 4 episodes, `orc-fresh-start`, wowborg:v1 in all 5 seats):
  all 4 episodes completed, score 0.0 each** — the artifact runs hosted episodes end-to-end
  without crashing. Caveats: no per-agent policy logs were retained and no results artifact
  was available (replay only, a custom `CWREPLAY` binary format), so the intended success
  signal (`SMSG_LOGIN_VERIFY_WORLD` in WOWBORG logs + nonzero realmd/world audit bytes)
  **could not be confirmed**. Completion without failure is the only evidence so far.
- **Two operational hard lessons** (also in the lessons buffer): (1) wowborg v1 never
  self-terminates and ignores `deadline_seconds`, so every episode runs to the FULL variant
  deadline — `rfc-five-player-clear` is 10000/0.1 ≈ **27.8 h per episode**; a first attempt
  (xreq_5d4946c2-…) had to be cancelled via `POST /v2/experience-requests/{id}/cancel`
  (route exists; not in the skill docs). Use `orc-fresh-start` (max_ticks=100, ~17 min) or a
  `game_config_overrides` with small `max_ticks` for smokes. (2) Each episode boots an
  all-in-one VMaNGOS container on k8s first — budget ~5+ min infra overhead per episode.

**Next steps:** figure out why policy logs weren't retained (elevated fetch? platform gap?);
decode the `CWREPLAY` replay format to extract the login-success signal; make wowborg v2
honor `deadline_seconds`; verify whether the Leveling Ladder actually scores rounds before
calling the loop unblocked.

---

## Status (2026-07-13, session 2): `wowborg` v1 implemented; loop still BLOCKED

`vanilla_wow_lab` was created from the `heartleaf_lab` template, and the first Python policy
skeleton now exists. What exists:

- **Five docs**, from a deep read of the game repo + web research (with citations):
  [`docs/vanilla-wow-gameplay.md`](docs/vanilla-wow-gameplay.md) (the game, accessibly),
  [`docs/vanilla-wow-player-contract.md`](docs/vanilla-wow-player-contract.md) (the Nim wire
  contract, narrative), [`docs/vanilla-wow-protocol.md`](docs/vanilla-wow-protocol.md) (the
  **exhaustive** interface-protocol reference — every message/schema/binary format, field-level),
  [`docs/vanilla-wow-rfc-roles.md`](docs/vanilla-wow-rfc-roles.md) (the 5 RFC roles + round
  scoring), and [`docs/vanilla-wow-strategy-guide.md`](docs/vanilla-wow-strategy-guide.md)
  (how to *play* WoW well: beginner's guide + leveling/group/RFC strategy + pro tips, blending
  cited real-Vanilla-WoW knowledge with engine-grounded facts).
- **Standard lab scaffolding**: README, AGENTS, near-empty best_practices, this file, the
  lessons buffer + hooks (`tools/rotate_lessons.sh`, `tools/lessons_stop_nudge.sh`, registered
  in the root `.claude/settings.json`), and the `/lessons-review` skill.
- **`wowborg` v1**: a pure-Python policy under [`wowborg/`](wowborg/) that connects to the
  Coworld `/player` session, authenticates to realmd over `/tcp/realmd`, opens `/tcp/world`,
  logs the seeded `character_name` into mangosd through `SMSG_LOGIN_VERIFY_WORLD`, sends the
  worldport ACK / active mover packets, then idles with periodic `CMSG_PING`. It does not decode
  world state or play yet. Focused validation: `uv run pytest vanilla_wow_lab/wowborg/tests -q`
  passes (14 tests).

**The loop is BLOCKED** and cannot run yet — this is the single most important fact:

- The game package is **`vanilla_wow:0.1.4.post8`** (policy id `cow_0466d25f-…`, built from
  pinned Coworld commit `754ff27c…`). It **passed all ten executable certification steps** and
  a local isolated-RFC snapshot smoke (176 live RFC frames, clean all-left, no identity leak),
  **but** the README badge is **"coworld verify: not ready"**.
- The badge is gated on **one retained hosted commissioner round + one retained XP-request
  episode on Kubernetes** proving snapshot import / results / replay upload+load — **neither
  has been authorized or created** (`docs/coworld-readiness.md`).
- There is a **live persistent *practice* realm** (Tailscale), but its runs are unscored
  (`scope=persistent_realm_session`). There is **no live scored Observatory league** for this
  game, and the persistent-tournament commissioner / account-mapping / hosted leaderboard are
  **designed but not implemented** (`docs/persistent-tournament.md:273-284`).

So uploading `wowborg` may produce a runnable score-0 artifact, but there is still nothing live
to compete in yet, and an experience request may have no scored field to run against. **Do not**
treat this like the crewrift/heartleaf loop until the game is live.

## Key facts (the hard-won ones — full detail in the docs)

- **Two game shapes** (docs/vanilla-wow-gameplay.md "Two game shapes"): a **persistent realm**
  (ranked by an account's highest-XP character, `highest_character_total_xp`) and **isolated
  scored episodes** (disposable servers from a signed `CWROSTER` 5-character snapshot; nothing
  writes back). Keep them distinct.
- **The scored benchmark is `rfc-five-player-clear`**: one policy fills **all five slots**
  (`self_play=True`), a level-30 Horde party (warrior tank / priest healer / shaman / rogue /
  mage) clears Ragefire Chasm (map 389), four bosses (Oggleflint 11517, Taragaman 11520,
  Jergosh 11518, Bazzalan 11519).
- **Round score = clear-then-speed:** full clear → `max(1.0, 1_000_000 − clear_seconds)`;
  partial → `bosses_defeated / bosses_total` (< 1.0). Every clear beats every partial; among
  clears, fastest wins. **Cross the full-clear threshold before optimizing time.**
- **7200 is NOT the episode deadline** — it's `DUNGEON_LAB_RESPAWN_SECONDS`, the boss-respawn
  timer that keeps a killed boss readable as dead. The episode budget is `max_ticks/tick_rate`
  (RFC: 10000/0.1). Be precise when writing about time.
- **The player is Nim, packet-level** (King Nimrod, headless `-d:noGui`), connects via a
  WebSocket→TCP bridge (`wsproxy`), and must obey **"sent is not accepted"** (confirm every
  action from `action-results.jsonl` / typed state transition; no teleport / injection /
  synthetic state / DB repair after login).
- **Only 7 of 9 classes are seedable** (Horde-only seeding; **paladin** Alliance-unreachable,
  **druid** unseeded). Class rotations exist for those same 7 (`player/bots/rotations.nim`).
- **No `-100` failure sentinel** (that's Crewrift). Detect player failure via episode status;
  read a low completed-episode score as a gameplay signal.

## Open threads (next steps — all human-gated)

1. **Verify the game's live state** before anything else: has a scored league / XP-request path
   opened since 2026-07-13? Is `vanilla_wow` submittable to a real competition yet? This
   determines whether the loop can even start. (`git -C ~/coding/coworlds/coworld-vanilla-wow
   pull` and re-read `docs/coworld-readiness.md` + the README badge.)
2. **If live:** build/upload `wowborg` and run the first hosted integration eval. Expected score
   is 0; success is `SMSG_LOGIN_VERIFY_WORLD` in `WOWBORG` logs plus nonzero `/tcp/realmd` and
   `/tcp/world` audit bytes.
3. **Tooling gap:** a Vanilla-WoW survey/report skill (on the reporter's recap/events/stats +
   diagnoser findings) is the top investment once real episodes exist — analogous to
   `crewrift-survey`.

## Reference

- Game repo (reference only): `~/coding/coworlds/coworld-vanilla-wow` — Python adapter
  `src/vanilla_wow_coworld/`, Nim player `player/`, dungeons `dungeons/`, manifest
  `coworld_manifest_template.json`. **Read-only for us; pull before relying on it.**
- Design doc for this lab's creation: `../docs/superpowers/specs/2026-07-13-vanilla-wow-lab-design.md`.

## Discipline (from [`../AGENTS.md`](../AGENTS.md))

Human sets strategic direction; you build observability, measure, hold the correctness gate.
**Propose-and-pause.** Change one component per iteration. Uploading is routine/ungated;
**league submission is the human's gate** (public, champion-making, hard to roll back) — and
here, doubly gated behind the game even being live.
