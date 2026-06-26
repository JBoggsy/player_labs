# Crewrift tentative lessons — session buffer

**Session started:** 2026-06-26 09:44. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`crewrift_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Crewrift-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### WITNESS-DROP-after-1st-kill (v58) HELPS in natural roles (+15pp ≥2-kill) — the masking lesson, paid off
Evidence: combined candidate v63 (Evade re-approach v53 + witness-drop v58) vs v54, NATURAL roles, 300
eps/arm, matched same-window. crewborg imposter: kills 1.12→1.38 (+0.26, t p=0.056), ≥2-kill 35→50%
(+15pp), 0-kill 24→14%, win +6pp (noise); crew unaffected (imposter-only modes). MECHANISM check
(meeting-aware @ready, cand vs base warehouses): post-kill in-view 40→42% and nearest-crew 102→104px —
UNCHANGED. So the gain is NOT from re-approach (v53 is inert — its 72t beeline washes out by the 500t-later
ready) but from the WITNESS-DROP converting in-view witnessed 2nd kills. This is the EXACT payoff of the
config lesson: v58 was helpful all along (+15pp where there's room to convert), but the pinned-config A/B
(baseline 69%, near ceiling) structurally couldn't see it — same change, same code, opposite verdict purely
from eval config. NEXT: isolate v58-ALONE in natural roles (already uploaded) to confirm it's the driver and
that v53 can be dropped; firm up the borderline p=0.056 with more episodes.

### EVAL CONFIG decides whether the gap is even visible — pinned-slot0-2-imp MASKED a 30pp imposter gap
Evidence: I A/B'd two post-kill fixes (v53 Evade re-approach, v58 witness-drop) in a PINNED config
(crewborg always imposter @ slot0 + fixed Andre co-imp + 6 crew). Baseline there: ≥2-kill 69%, post-kill
in-view 57% → looked "already good," both fixes read neutral. Then the COMPLETE v54 baseline in NATURAL
ROLES (300 eps, crewborg imposter ~25% across all seats, vs Aaron+Andre) showed the REAL numbers:
crewborg imposter ≥2-kill **52% vs Aaron/Andre 82%**, kills 1.52 vs 1.97, post-kill in-view **47% vs
76-81%**, nearest-crew @ready **95px vs 14-18px**. The ~30pp conversion gap is real and ≈ the original
v50 diagnosis (44% vs 83%) — barely moved. So the pinned config understated the gap by ~17pp (seat/
composition asymmetry — slot0 + fixed partner is easier), and the two fixes were tested against a gap
that wasn't there in that config → INCONCLUSIVE, not neutral. LESSONS: (1) **Evaluate a fix in the SAME conditions the problem was diagnosed in** — diagnosing in
config A (natural roles) then A/B-ing in config B (pinned-slot0) is a broken loop: config B muted the
gap, so a real effect had no room to show. (2) post-kill/imposter fixes must be A/B'd in NATURAL roles
(or seat-rotated imposter pinning) — pinning the SUBJECT into one favorable seat changes the measured
skill materially (seat asymmetry is large). (3) **"inconclusive" ≠ "neutral" ≠ "helpful"** — a test that
can't see an effect tells you NOTHING about whether the change helped; don't let a bad test get recorded
as "neutral" (or, conversely, assume the change must have helped). The only fix is to re-test in the
right config. (4) attribution-pinning (clean matched roster) and representative-config can conflict;
resolve by round-robining the SUBJECT's seat across arms, not by freezing it into an easy seat.

### ASSUMPTION FAILURE: I called "post-kill drift" the problem off a MEETING-CONTAMINATED distance curve
What happened: the original v50 diagnosis leaned on a "nearest-crew at kill+offset" CURVE (evade_test.py)
to argue "we drift away post-kill / Aaron snowballs, we stay flat." That curve samples raw ticks
regardless of phase, and **46-67% of its +72..+500 samples are during MEETINGS**, where all players
teleport to the Bridge and bunch up → "nearest crew" collapses artificially. I presented the dramatic
curve confidently and **built a fix (v53 Evade re-approach) on top of a conclusion that was largely an
artifact** — and the human believed it too because it looked compelling. Recomputing the SAME curve
meeting-aware (imposter Playing the whole kill..kill+offset span) the candidate-vs-baseline separation
VANISHES (base 59 / cand 79 at +500, n~40, noisy), consistent with the meeting-aware @ready table barely
moving (in-view 57→59%, convert 62→63%).
LESSONS (take these as defaults): (1) make EVERY spatial/temporal analysis meeting-aware BY DEFAULT —
exclude non-Playing ticks — it's already a written discipline ("meetings are NOT idle time") and I
ignored it. (2) When a dramatic-looking chart disagrees with a cleaner aggregate, distrust the chart
until proven, don't lead with it. (3) What actually matters is **how close we are AT KILL TIME / whether
we CONVERT**, not an abstract distance-over-time curve. (4) Re-localize on the CURRENT build+config before
building a fix — the v50 "drift" was also partly a different config (round-robin natural roles vs the
pinned 2-imp eval), and current v54 is already close at the 2nd ready (~49px, 57% in-view) → the real
lever is CONVERSION, not contact.

### In CURRENT code (v54) the post-kill gap is more CONVERSION than contact
Evidence: meeting-aware @ready on v54 (pinned imposter, 2-imp vs Andre co + Aaron/Andre crew): post-kill
crew-in-view@ready 57%, median nearest crew 49px (~2.5x KillRange), convert 62%. So we're often close-ish
and in view at the 2nd ready, but only convert ~62% — the lever looks like FINISHING the kill (witness
gate? crew leaves range? meeting interrupts?), not just getting near crew. NB this baseline is far better
than the v50 diagnosis (29% in-view) — different config (pinned 2-imp vs v50 round-robin natural roles),
so the "drift" gap is partly configuration-dependent; re-localize on the CURRENT setup before the next fix.

### Evade→"beeline to most-populated area" is NEUTRAL on kills (re-confirms the v46 crowd-seeking dead-end)
Evidence: A/B v53 (Evade beelines to densest crew area) vs v54 (old flee-Evade), 2 pairs of 100 eps,
imposter-pinned. Fully-clean episodes (full roster connected): P1 kills 1.73→1.74, RR 1.71→1.69;
no-kill 4%→4% / 1%→2%; ≥2-kill 66%→66% / 61%→61%. Dead neutral. Mechanism hypothesis: we kill
ISOLATED victims (nearest other crew ~120-170px even at the kill), so re-approaching the densest
CROWD takes us toward witnesses where Hunt's gate blocks the kill — exactly the v46 regression's
logic ("crew-densest-room is the worst place to find someone alone"). Also Evade is only 72t of the
500t cooldown and Search's random-room wander immediately undoes it. Takeaway: the lever is
re-approaching the SINGLE nearest isolated victim / the cluster it peeled from, SUSTAINED across the
cooldown (the ~428t of random Search is the bigger culprit than Evade's 72t), NOT crowd-seeking.

### A/B batches get contaminated by ASYMMETRIC platform connect-timeouts — always recompute on FULLY-clean episodes
Evidence: RR candidate looked catastrophic in compare.py (kills 1.71→1.28, win 75%→60%, every metric
"REGRESSED p<0.05") purely because that request window hit 24% of crewborg's slot with connect_timeout
AND 42% of episodes had SOME slot connect-timeout (degenerate games, fewer live crew → fewer kills).
Filtering to episodes where the FULL roster connected (no connect/disconnect_timeout on ANY slot)
flipped it to neutral (1.69 vs 1.71). compare.py's ops_fail_rate flags it but its other metrics still
INCLUDE the degenerate games. Distinguish connect_timeout (platform race, exclude) from
disconnect_timeout (mid-game crash = real bug) — here all were connect, zero disconnect, so the change
was safe. Re-probe small / re-run if a window is heavily degenerate.

### Attributable A/B baseline: build BOTH arms from the same tree, git-stash the change for the baseline
Evidence: to A/B the Evade change cleanly, baseline must be identical code/weights minus only the
change. Procedure that worked: build candidate from the working tree (with change) → `git stash` →
build baseline (`--tag` a distinct image) → `git stash pop`. Both images get the same SDK/weights/game;
only `modes/evade.py` differs. Avoids confounding against an already-uploaded version (v50/v52) whose
exact code/weights differ. `build_player.sh --tag <name>` gives distinct image tags; upload both →
v53 (cand) / v54 (base). NB stash only after the candidate build's COPY layer is done.

### crewborg's subsequent-kill gap is a POST-KILL re-approach failure, not target-selection
Evidence: localization on v50 (3 warehouses: v50_pertick + v50_warehouse + v50b). Split each
"became-ready" moment into first-cooldown vs post-kill, measured crew-in-line-of-sight at ready
and TRUE nearest-living-crew distance (per-tick x,y in `player_state`). Post-kill collapses:
crew-in-view@ready 29%/18%/35% and median nearest crew **128/201/181 px**, vs first-cd 55%/47%/68%
and 34/41/36 px. Aaron is the mirror image — post-kill in-view 81%/60%/59%, median nearest crew
**11/48/46 px** (he STAYS glued / snowballs; we drift away). When crew IS in view at ready we
convert (best-in-field execution), so this is a contact/hunting-path problem, not
selection-among-visible. Visuals (positioning_viz, past=520): cb_7 was ready a full 511 ticks
(~21s) looping Bridge/Hydroponics while all crew were across the map → meeting reset it.
Status: confirms+refines the WORKING_CONTEXT hypothesis (it's specifically POST-KILL). Analysis
script lives in scratchpad (`localize.py`); worth graduating into crewrift_lab/ alongside
`visibility_at_ready.py` if we keep using it.

### Post-kill drift is mostly SEARCH-not-re-approaching, not just Evade (falsifying query)
Evidence: traced median distance to nearest OTHER living crew from each own kill at +0/72/150/250/500t
(v50 x3 warehouses). crewborg: 169/176/162/174/109 — FLAT-HIGH the whole cooldown. Aaron:
119/73/45/50/22 — DESCENDS (he re-approaches/snowballs). At +72 (Evade ends) we're no closer than
at the kill (often farther: 169→176/181, 120→190) — so Evade does keep us away (James's hunch ✓),
but the +150→+500 stretch where Aaron closes to ~30-50px and we stay ~110-200px is SEARCH failing
to re-establish contact, not Evade. So a Evade-only fix is insufficient; the dominant lever is
re-approach through the cooldown. Also: at the kill instant (+0) our nearest other crew is already
~120-170px — we kill truly-isolated victims and then don't head back toward where crew are.
Script: `scratchpad/evade_test.py`.

### player_state events carry per-tick x,y — use them for true geometry, not just intervals
Evidence: `player_state.value` has `x`,`y` (plus vel_x/vel_y, room, kill_cooldown, phase, alive,
role). The per-tick warehouse (`--snapshot-every 1`) lets you compute exact nearest-crew distance
at any tick, which separates "far from everyone" (seeking failure) from "close but lost LoS"
(re-approach failure) — a distinction the visible-interval data alone can't make.

### duckdb: `role`/`phase` are reserved-ish — alias json_extract columns to non-reserved names
Evidence: `json_extract_string(value,'$.role') role` → ParserException "syntax error at or near
role". Renaming to `prole`/`pphase` fixed it. Minor but recurs when querying these warehouses.
### Local Gate-1 for crewborg REQUIRES `--run python -m crewrift.crewborg.coworld.policy_player`
Evidence: ran `coworld run-episode <crewrift-manifest> players-crewborg:dev` WITHOUT `--run`; the runner
applied the manifest's reference-player argv `/bin/notsus` to the crewborg image → `exec: "/bin/notsus":
no such file` (exit 127, connect_timeout on all 8 slots, scores all -100). crewborg's image CMD is
`python -m crewrift.crewborg.coworld.policy_player` but the supplied-image argv must be set explicitly via
`--run`. Matches the version-log convention (every entry passes the `--run` triple; v16: "after adding the
required --run override"). Status: re-running with `--run` added.

### Hardcoded `cow_` ids go stale; resolve crewrift by name instead
Evidence: `coworld download cow_50ee07cf` (the id recorded in WORKING_CONTEXT) → HTTP 422 Unprocessable.
`coworld download crewrift` (by name) succeeded → current `cow_52d06063-dfa8-45fc-9533-a5365a71a04d`.
Coworld ids rotate per build; the name resolves to the canonical current one. Don't trust a cow_ id pinned
in docs for local runs.

### Commander Gate-1 can exercise the LLM (unlike the meeting LLM)
Evidence: the cert/degenerate fixture has no Voting phase (so v47's meeting LLM was never hit locally), but
it DOES have a Playing phase — the gameplay commander runs during Playing, so a local run with
`--secret-env CREWBORG_LLM_COMMANDER=1 USE_BEDROCK=1` + temp Bedrock creds (`aws configure
export-credentials --profile softmax --format env`) actually fires the commander worker. Status: verifying.

### Phase-1 commander worker is observability-blind in-pod — add a trace/metric BEFORE any eval
Evidence: hosted 1-ep self-play crash test (xreq_6d62ac18, Crewrift Prime) completed clean (real game,
0 failed, 0 timeouts) but showed 0 `strategy_inferences` in-pod, vs 231–254/slot locally under
CREWBORG_TRACE=debug. Two confounders make in-pod firing UNKNOWABLE: (1) the SDK `strategy_inferences`
event isn't in crewborg trace groups `decision,action,voting`; (2) worker.py does `except Exception:
continue` with NO trace/metric, so a silent Bedrock 403 (the known XP-pod issue) is indistinguishable
from "fired fine." Lesson: a swallow-and-continue worker MUST emit a success/failure counter+trace, or
you cannot tell a working LLM from a dead one in production. First Phase-2 task: commander_decision /
commander_error trace+metric (latency, fired/fallback). Confirmed working LOCALLY (direct Bedrock via temp
softmax SSO creds); in-pod confirmation deferred to that tracing.

### `--use-bedrock` upload flag is NOT enough — also pass `--secret-env USE_BEDROCK=true`
Evidence: v55/v56 uploaded with `--use-bedrock` + `CREWBORG_LLM_COMMANDER=1` but NO `USE_BEDROCK` env →
in-pod `commander_started` traced `{enabled:false, disabled_reason:"no LLM backend configured"}` on all 8
slots. SDK `players.player_sdk.llm.bedrock_enabled(env)` only checks truthy env vars
`_BEDROCK_ENV_NAMES=("USE_BEDROCK","CLAUDE_CODE_USE_BEDROCK")`; the `--use-bedrock` CLI flag wires the
sidecar endpoint but does NOT set that env var. The working meeting LLM (v50) was uploaded with
`--use-bedrock` + `USE_BEDROCK=true` + `CREWBORG_LLM_MEETINGS=1` — the explicit env is the actual enable.
Fix: v57 adds `--secret-env USE_BEDROCK=true`. Applies to ANY crewborg LLM feature (meetings or commander).

### The commander observability paid off on its very first in-pod run
Evidence: before the trace, in-pod looked like "0 strategy_inferences, unexplained." After adding
`domain.commander_started` (+ call/applied), the first v56 episode immediately showed
`enabled:false, disabled_reason:"no LLM backend configured"` — diagnosing the USE_BEDROCK misconfig in one
shot. Lesson confirmed: instrument the async LLM worker's connect/enable BEFORE trusting any eval; a silent
client-disable is indistinguishable from "fired fine" without it.

### Commander in-pod disable is INFRA (Bedrock env absent), proven by env_seen — not eager-vs-lazy timing
Evidence: made client construction lazy (in-worker, live os.environ) + 20x retry + added env_seen diagnostic
to commander_started. Local: enabled:true, env_seen.USE_BEDROCK:true. In-pod (crewrift_prime XP, v59):
enabled:false, env_seen ALL false (USE_BEDROCK/CLAUDE_CODE_USE_BEDROCK/ANTHROPIC_API_KEY) on all 8 slots,
even after retries. So the lazy fix (candidate cause a) was RULED OUT; the Bedrock env genuinely isn't in
the player container (cause b). CREWBORG_LLM_COMMANDER (same secret-env path) DOES arrive → USE_BEDROCK is
special-cased/stripped by the platform to gate sidecar attachment, and the sidecar isn't attached for
crewrift_prime XP jobs now. Implies the meeting LLM is also currently disabled in these pods (the v50
enablement likely reverted; "TF reconciliation owed"). Lesson: an `env_seen` diagnostic on the LLM-enable
path turns an ambiguous "it's disabled" into a one-line infra-vs-code verdict — build it early. The lazy
construction is still kept (correct + matches meetings + handles genuinely-late env).

### CONFIRMED DIRECTLY: the meeting/chat LLM is ALSO disabled in-pod ("no LLM backend configured")
Evidence: v60 (both CREWBORG_LLM_COMMANDER=1 and CREWBORG_LLM_MEETINGS=1, --use-bedrock + USE_BEDROCK=true)
6-ep self-play batch on Crewrift Prime. 184 meetings -> 184/184 `domain.meeting_llm_fallback`
{reason:"llm_disabled", detail:"no LLM backend configured"}, AND commander_started enabled:false env_seen
all-false in the same pods. So the v50 "meetings working in crewrift_prime XP jobs" state has REVERTED — the
chat LLM currently never fires in these pods either. NOT a commander-specific issue: the Bedrock backend env
is simply absent for crewrift_prime experience-request player containers. Infra (re-enable + persist the
Bedrock sidecar for those jobs). The meeting LLM's existing `meeting_llm_fallback {detail}` trace already
reports this — no new code needed to check it; the commander's env_seen pins down WHY (env vars all false).

### ✅ FIX CONFIRMED: gate Bedrock on AWS_ENDPOINT_URL_BEDROCK_RUNTIME, not USE_BEDROCK (sidecar strips it)
Evidence: sidecar mode (kubernetes_runner) strips USE_BEDROCK + direct AWS identity from the player container
and injects AWS_ENDPOINT_URL_BEDROCK_RUNTIME + dummy creds. SDK bedrock_enabled() only checks
USE_BEDROCK/CLAUDE_CODE_USE_BEDROCK → wrongly "no backend" in-pod. Changed crewborg commander factory to OR-in
the sidecar endpoint as a Bedrock signal. In-pod (v62, xreq_5a87445f, Crewrift Prime): commander_started
enabled:true backend:bedrock env_seen{USE_BEDROCK:false, AWS_ENDPOINT_URL_BEDROCK_RUNTIME:true}, 672
commander_call outcome:ok, 0 errors, ~1.8s. So the sidecar IS deployed; only USE_BEDROCK was missing. The
meeting LLM still gates on USE_BEDROCK via the SDK → still dark in-pod; same one-line endpoint-gating fix
revives it. Platform/SDK fix still recommended (keep injecting USE_BEDROCK=true / SDK treat endpoint as signal)
so the documented --use-bedrock contract holds for all players.
