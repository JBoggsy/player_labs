# Crewrift weekly context — directions for the week of 2026-07-06

**What this is.** The week-horizon roadmap: future directions with their evidence and
readiness, distilled at the 2026-07-02 session wrap. Coarser than
[`WORKING_CONTEXT.md`](WORKING_CONTEXT.md) (the live session state); finer than
[`best_practices.md`](best_practices.md) (durable discipline). Reprioritize freely; strike
directions as they close and reseed weekly.

**Baseline going in:** champion lineage v91→v92→v93 (full stack: v4 live-fit weights,
bar 0.6+lead 0.2, ready-search + density prior, WATCH camo, Honor Society + role-reveal
trust, full tracing). Judge all form vs the window's field par, split by role.

## Direction 1 — Vote coordination (the crew conversion bottleneck) ★ top pick

Evidence: the vote-bar sweep proved precision is SOLVED live (86–100% at every bar) but
conversion is not — extra honest votes didn't become ejections (one seat rarely swings a
7-seat tally). The Honor Society trust network is the natural vehicle: members who trust
each other's claims can pile votes with confidence; accuse-then-pile chat is the non-member
version. Prereqs in place (HS live, role-reveal trust in v93). Design carefully against the
bandwagon-doesn't-transfer lesson (notsus coordination worked because MULTIPLE notsus).

## Direction 2 — Fix the caller-attribution detector, then refit suspicion v5

**STATUS 2026-07-21: the detector is ALREADY FIXED and PROVEN FIRING LIVE — no new detector
work needed; what remains is accumulating data + the v5 refit.** Investigation findings:

- The all-zero evidence was from the v90 trace batch (398 meetings, pre-2026-07-06). Root
  cause was the belief-latch self-clear bug, fixed in `0fe80c8` (shipped v96+, 2026-07-06):
  `derive_phase` has no MeetingCall state so phase stays "Playing" during the ~3 s
  interstitial, and `update_belief` cleared the just-latched caller the same tick it latched.
  The label parse itself (`perception/resolve.py` `MEETING_CALL_TEXT`) was never broken —
  "`<Color> reported|pressed|called`" is byte-identical in the current game source
  (34a97a3 = deployed 0.4.68, `global.nim meetingCallLines`); verified across all cached refs.
- **Live proof (v107 league, 2026-07-21):** `telemetry_harvest/` scan — 21 crewborg meeting
  snapshots, 10 rows `reported_bodies>0`, 19 rows `button_calls_made>0`. Replay cross-check
  (10 harvest episodes expanded with `expand_replay-34a97a3`, `vote_called_body`/`_button`
  ground truth): **17/20 attributable caller events correctly banked (85%)**. The v107-vs-v100
  A/B cand arm shows the same at scale (196 eps: 195 rb>0 + 332 bc>0 rows across 364 snapshots).
- All 3 misses share ONE signature: the caller's color == the stale `PLAYER_COLOR_NAMES[slot]`
  crewborg wrongly believed was its own (`?slot=` seed via the pre-1cbd4de palette), so
  `_bank_meeting_caller` saw "self" and the ranking excluded the color. **The palette fix
  (`2a13256`, in v109/v110) already closes this** — expect ~100% capture on v110+ telemetry.
- Added resolve-level regression tests pinned to the current game's interstitial labels
  (`tests/test_resolve.py::test_meeting_call_interstitial_*`).

Refit recipe (needs ~a week of v110+ league data via the `tools/harvest_artifacts.py` cron —
running every 10 min as of 2026-07-21, telemetry lands in `telemetry_harvest/episodes/`):
expand replays for labels (`suspicion_lab/tools/expand_corpus.py --ref 34a97a3`) →
`build_dataset_runtime.py --policy crewborg --version <N≥110>` (v107 rows carry the palette
self-ID contamination — prefer v110+) → `fit.py --features runtime --tag runtime-v5` →
`eval.py` → A/B per `suspicion_lab/README.md`. Worth adding to the feature set while refitting:
HS-derived trust flags (trusted/known member), per the original plan.

## Direction 3 — bar60-vs-bar90 confirmation (only if pursuing more solo votes)

The sweep's rule-selected bar60 showed +0.16 imp-ejections/crew-ep at p=0.09 (n=100/arm);
a dedicated 200/arm bar60-vs-bar90 would settle it. Lower priority than Direction 1 —
coordination multiplies whatever the bar yields.

## Direction 4 — Instant-vote read-out (blocked, then decide)

50v50 LLM-on episodes are on disk (`/tmp/iv_{cand,base}_eps`) missing only results.json
(the /jobs 403). When auth is fixed (or via the replay-synthesis method the camo agent
validated), read out and decide. Priors adverse (LLM-named-not-submitted 22–50% precise
historically); the knob ships OFF everywhere until this reads positive.

## Direction 5 — Imposter victim-finding tail + kill→WIN conversion

The witness-gate family is DEAD (3 refutations — never again). What remains: (a) the
victim-finding tail in emptier games (ready-search shipped as hardening, camo helps blend;
measure with `tools/imposter_movement/` per ready-window); (b) the older kill→WIN frontier —
surviving meetings after witnessed kills (deflection-when-accused has never been built;
TODO.md's social-deception entry covers the design space).

## Direction 6 — Honor Society ecosystem work (largely DONE 2026-07-22, Thread 8)

- ✅ **Alex note WRITTEN** (`docs/hs1-ecosystem-notes.md`, for James to send): same-key
  multi-seat vs first-poster-wins, encoding canonicalization (we accept both, send unpadded
  base64url per live behavior), publish-the-compact-form, palette pinning, verifier cost at
  scale, liar-evidence-needs-ground-truth warning, registry/liar-ledger interop formats.
- ✅ **Liar-ledger harvest BUILT**: `tools/harvest_liars.py` → vendored
  `data/honor_distrust.json` + the `is_distrusted` consumer seam in honor_society.py.
  Ground-truth gate is load-bearing: the in-game witness false-positived 6× on alex-smith
  (all actually crew) — raw honor_liar events must never distrust directly. 0 confirmed
  liars to date (234 eps). Add to the harvest cron cadence alongside harvest_artifacts.py.
- ✅ **HS isolated A/B DONE** (first ever): HS-NEUTRAL at episode level (crew 28% vs 28%,
  n=200/200), mechanism-positive — HS members vote against our announced crew 3× less
  (z=−7.1), vetoes 20/20 accurate. Keep ON; the payoff lever is Direction 1 (coordinated
  vote-piling with trusted members — now evidence-backed: the trust channel works).
- Challenge/response still awaits a society wire spec.
- Open anomaly: imposter-role HS-member votes against us UP with HS on (z=+3.0, small-n) —
  worth a look if imposter numbers sag.

## Platform / infra debts

- **/jobs/* 403 outage** ("not a softmax team member"; since 07-02 ~22:20Z): relogin
  `--force`, else escalate. Blocks artifact telemetry + league harvest.
- fetch_artifacts: add results.json to completeness + surface watcher deaths (bit us 3×).
- metta checkout pull blocked by local FEEDBACK.md edits (ux.ify/ux.link) — stash/commit.
- Telemetry harvest automation (league artifacts ephemeral ~1 round) — still a standing TODO.
