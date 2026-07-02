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

Evidence: `reported_bodies` / `button_calls_made` are ALL-ZERO across 398 live meetings —
the runtime MeetingCall-interstitial parse never fires; these were meaningful offline
features. The refit pipeline is fully operational (every league round produces live feature
vectors now), so: fix detector → accumulate a week of league data → `fit --features runtime`
→ eval vs v4 → A/B. Also worth adding: HS-derived features (trusted/known flags) to the
feature set.

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

## Direction 6 — Honor Society ecosystem work

- Tell Alex: same-key multi-seat collides with first-poster-wins (distinct key per
  concurrent seat); encoding canonicalization (we accept both, send standard).
- Challenge/response awaits a society wire spec.
- Liar-ledger harvest: collect `domain.honor_liar` events from league telemetry weekly →
  vendored distrust list once any liar is observed.
- Watch for other members' announcements in league replays (we auto-trust + auto-verify).

## Platform / infra debts

- **/jobs/* 403 outage** ("not a softmax team member"; since 07-02 ~22:20Z): relogin
  `--force`, else escalate. Blocks artifact telemetry + league harvest.
- fetch_artifacts: add results.json to completeness + surface watcher deaths (bit us 3×).
- metta checkout pull blocked by local FEEDBACK.md edits (ux.ify/ux.link) — stash/commit.
- Telemetry harvest automation (league artifacts ephemeral ~1 round) — still a standing TODO.
