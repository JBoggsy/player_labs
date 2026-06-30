# Crewrift tentative lessons — session buffer

**Session started:** 2026-06-30 10:49. This is THIS SESSION's lesson buffer. Write candidate
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

## Crew voting investigation (direction2_voting, 2026-06-30)

**Live crew-vote path is the FITTED suspicion model at the 0.9 near-certainty bar
with NO clear-leader rule.** Confirmed: `data/suspicion_weights.json` loads (schema
matches) → `top_suspect()` for a crewmate returns a color only if `p >= 0.9`
(`CREWBORG_WEIGHTS_VOTE_P`). Crew vote = `top_suspect`; if None → silent skip.

**Warehouse (sweep_wh, trace_warning excluded) — crew vote behavior:**
- crewborg crew: 665 votes, **46% skip**, when it votes a player **vote_acc=39%**
  (hits imposter 140, hits crewmate 220).
- notsus crew: 111 votes, **4% skip**, **vote_acc=61%**.
- field ("other") crew: 29% skip, vote_acc=56%.
- Both crewborg + crewborg-base versions identical (~39% acc, ~46% skip) — NOT an
  old-version artifact; the live fitted path is doing this.

**Key contradiction:** the 0.9 fitted bar was justified by an offline held-out
decision-sim claiming ~100% imposter precision. LIVE it is 39%. The offline
calibration does NOT transfer — so the *mechanism* (suspicion ranking/calibration
under live perception), not just the gate, is the problem. A threshold sweep alone
can't fix a model that hits crewmates 61% of the time when it fires.

**Implication:** crewborg crew is BOTH passive (over-skip) AND inaccurate. Lowering
the gate adds mis-votes (the prompt's warning, quantified). Next: validate
calibration live via `suspicion_snapshot` traces; study notsus coordination.

**OUTCOME metric (ejections reconstructed from meeting-clustered vote tallies):**
- crewborg-crew: 99 meetings → 14 imposter-ejections, **31 crewmate-ejections**, 54
  no-ejection. Only **13% of crew-side episodes eject ≥1 imposter**. crewborg's
  meetings eject **2.2x more crewmates than imposters** — voting is a NET PARITY GIFT
  to imposters.
- notsus-crew: 47 meetings → 19 imp-ej, 13 crew-ej, 15 no-ej. **37% of episodes eject
  an imposter** (~3x crewborg); net-helps crew (imp-ej > crew-ej).

**The mis-vote problem dominates the skip problem.** Lowering the gate without fixing
accuracy makes it worse. Candidate root causes to validate live: (a) witnessed-kill/vent
DETECTOR misfires latching innocent crewmates at p≈1 (the WITNESSED floor forces p≈1);
(b) fitted model mis-ranks under live perception. Candidate fix with most leverage:
**CREW has ZERO coordination** — `_decide_crewmate` uses only private `top_suspect`,
never reads others' votes/chat (bandwagon logic is imposter-only). notsus's edge may be
vote concentration.

**Coordination opportunity (does field plurality help?):** In crewborg-crew
meetings, the OTHER players' single vote-leader was an imposter in 219 cases vs a
crewmate in 284 cases → **field plurality is only 44% reliable** (imposters vote too,
crew mis-vote). crewborg joins imposter-leads 12% / crew-leads 10% — its private
suspicion does NOT discriminate good field-leads from bad. **Blind bandwagon ≈ 44%
accurate, not a clean win.** Confirms: mechanism (ranking quality) and coordination
are ONE problem. The real bottleneck is the suspicion signal's live ranking (~39-44%
imposter-precision when crewborg commits, vs notsus 61%).

**Pile-reliability (the decisive coordination test):** the meeting's TOP public
player-pile is only **44-50% imposter regardless of pile size (1→6 voters) or margin**
over runner-up. The "wisdom of the crowd" is ABSENT in crewborg's field (2/8 imposters
actively frame crew + crew ~50% accurate → aggregate ≈ coin flip). **Bandwagoning the
pile would NOT beat crewborg's own 39% model.** notsus's coordination edge does NOT
transfer: notsus-crew games have multiple coordinating notsus forming a reliable
consensus; crewborg's field has none. → The fix must target the PRIVATE suspicion
mechanism (ranking/calibration), not coordination.

**notsus crew design (from source study):** vote = deterministic `chooseSocialVote`
(LLM only chats). Edge = (1) NO self-skip path — waits then force-commits to top
suspect near deadline (→4% skip); (2) player-count-scaled gate (90@8alive →60→35→
always-vote@≤4); (3) reads vote-tally as private-sus input (votes-against ×10) AND as
gated bandwagon (join pile only if own-sus clears floor); (4) reporters strongly
cleared (-150). But (3) relies on a reliable field, which crewborg lacks.

**Reframed highest-leverage outcome:** crewborg's 54 no-ejection (skip) meetings are
PROTECTIVE given the bad model; the damage is **31 crew-ejections** (parity gifts).
Reducing crew MIS-ejections (better precision / fix witnessed-detector misfires) likely
beats reducing skips. Pending: live calibration run to find WHY private model is 39-44%
(witnessed-detector false-latch vs fitted mis-rank).

**ROOT CAUSE of the 39% live vote accuracy (fitted coefficient analysis):** To hit
p≥0.9 the fitted logit must clear ~2.4. The dominant EXCULPATORY feature is
`tasks_completed_watched` = **−15.2** (clipped 5) — but it only fires when the observer
actually WITNESSED a task completion (needs LOS at the right moment). The suspicious
features penalize NORMAL crew behavior: `task_site_dwell_gt20` +0.85, `copresence_
killrange_gt20` +0.77, `near_body_bodies` +0.52, `follow_death` +1.9, `accusations_made`
+1.03. `witnessed_kills` +10.1 → p≈1 alone.

**Offline→online collapse:** offline features are computed with FULL observation (the
replay expander sees everything) → exculpation fires reliably → ~100% precision. LIVE,
crewborg sees a fraction, so `tasks_completed_watched` exculpation is usually MISSING
while the suspicious cues still fire on partial observation → innocent crew accumulate
enough to cross 0.9. **The fitted model trained on full-observation features is
mis-applied to partial-observation live belief** — that is why the offline sim's 100%
precision does not transfer. Memory's "weight refits don't move outcomes" now has a
mechanism: a refit can't fix an observation-distribution mismatch.

**LIVE calibration (6 self-play episodes, suspicion_snapshot traces, roles recovered
by ranking-subtraction):**
- Crew would_vote: 81% skip, **80% player-vote accuracy** (16 imp / 4 crew).
- Calibration OK-ish: p≥0.9 → 82% imposter, p≥0.8 → 79%, top-ranked-by-p is imposter
  52%.
- Among p≥0.9 entries: 12 imp-confirmed, 6 imp-graded, **3 crew-CONFIRMED** (witnessed-
  detector misfire ~20%), 1 crew-graded.

**THE KEY: accuracy is opponent-distribution-dependent.** Self-play (crewborg field) =
80% vote accuracy; league (warehouse, real field) = 39%. crewborg's suspicion features +
witnessed-detector work against crewborg-like opponents but mis-fire against the real
league field (different kill/movement patterns trigger the suspicious features;
exculpation `tasks_completed_watched` rarely fires on opponents it can't watch). So a
fix CANNOT be validated in self-play — needs a LEAGUE A/B. The reliable-across-fields
signal is the WITNESSED catch; the graded fitted signal is league-noise.

**Candidate fix:** env-gated crew-vote that trusts only the witnessed near-certainty
(skip graded), eliminating the graded false-positive crew-ejections (the bulk of the
parity gifts), validated by a hosted league A/B on the ejection ledger + crew win.

**FIX BUILT + verified:** `CREWBORG_CREW_VOTE_WITNESSED_ONLY` env flag (default off,
byte-identical base) in `strategy/suspicion.py:top_suspect` — crew votes only a
directly-witnessed killer/venter, else skip. 4 unit tests, full suite 465 passing.
Verified active in the rebuilt image (local self-play, flag on): 7/7 crew player-votes
were witnessed catches, 51 skips. Committed on worktree branch worktree-direction2-voting
(commit 6fd963d). A/B fired: crewborg-wvon:v1 (flag on) vs crewborg-wvoff:v1 (flag off),
same image, crewborg crew slot0 vs Prime top-7, 2 imposters, 300 eps/arm (3 interleaved
requests each). Result pending.

**TOOLING GOTCHAS this session:** (1) experience-request num_episodes caps at 100 (fire
multiple for more). (2) run-episode overrides image CMD with the manifest's player cmd —
MUST pass `--run python --run -m --run crewrift.crewborg.coworld.policy_player`. (3) traces
default to jsonl@artifact (temp file lost locally) — pass `--secret-env
CREWBORG_TRACE_OUTPUTS=jsonl@stderr` to see them in slot logs. (4) `players-crewborg:dev`
is a SHARED docker tag clobbered by parallel worktree agents — build with a UNIQUE
`--tag` and upload from it, else you silently upload another agent's image. (5) env flags
for hosted policies are baked at UPLOAD via `--secret-env`, NOT settable per experience
request — A/B an env flag by uploading the same image twice (flag on / off).


**CORRECTION (root cause):** Earlier I wrote the gap was offline FULL-observation vs
live PARTIAL-observation. That is WRONG — `suspicion_lab/tools/features.py` features are
visibility-clipped + runtime-admissible by design. The real gap is TRAIN→SERVE: the model
scores 94% imposter-precision on held-out OFFLINE rows (README) but ~39% LIVE, because the
offline features are reconstructed from the replay (`game.sees()`) and diverge from what
crewborg's live perception+`event_log` compute at the decision tick. (Plus opponent-
distribution: self-play 80% vs league 39%, same live code → opponent effect; self-play n
is small.) The witnessed-only FIX is unaffected — it rests on the robust 39% live number,
not the mechanism.
