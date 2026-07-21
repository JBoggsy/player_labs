# Pre-registered A/B: crewborg-anchor:v1 (first-mover accusation) — written BEFORE launch

**Candidate:** `crewborg-anchor:v1` — main (`e0c2fcb`, = v110's code) + commit `0c303fa`
(first-mover anchoring accusation). Upload recipe identical to v110 (LLM meetings recipe +
`CREWBORG_HS_SECRET`), so vs the v110 arm the ONLY delta is the anchor change.

**Arms (matched pinned roster, crewborg slot 0, natural roles, div_acbde92a):**
- Candidate: 2×100 eps, fresh (fired by this thread).
- Baseline A (exact-code control): Thread 1's v110 arms `xreq_136dd84f` + `xreq_edd0f75e`
  (2×100 eps, completed 2026-07-21T23:02Z, same roster/slot/division/recipe).
- Baseline B (champion reference, per instructions since v110 was unvalidated at launch):
  Thread 1's v107 arm `xreq_774a384d` (100 eps, same roster/slot).

**Criteria (decided before any candidate episode is seen):**
1. PRIMARY: crewborg crew-accusation → same-meeting ejection-of-target conversion rate
   UP vs baseline A (and not worse than baseline B). Measured with the premise-check
   method (warehouse chat + died events; accusation = first substantive chat naming
   another player's color; ejection = died event attributed to the meeting).
2. Crew win rate not worse than baseline (allowing normal noise; a significant drop fails).
3. No new vote_timeouts (candidate ~0, matching baseline).
4. Imposter win rate / kills per seat unchanged (crew-only change).
5. Ops-fail (score <= -100 / dead games) ~0 both arms; if the candidate arm's ops-fail
   is materially higher, the run is invalid — re-run, don't interpret.
6. Mechanism check: `meeting_first_mover_accusation` fires in the candidate telemetry
   (else the A/B tested nothing and the verdict is "no-fire", not "refuted").

**Ship rule:** all pass → SHIP RECOMMENDED (lever ships inside the next crewborg version;
the probe name is never submitted). Any fail → refutation recorded in TENTATIVE_LESSONS +
version_log; no ship.
