# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-14 18:47. This is THIS SESSION's lesson buffer. Write candidate
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

### Importing another team's methodology: filter through the operating model, not topical overlap

Evidence: Pulled from `Metta-AI/optimizer-skills` (an *autonomous*-optimizer library) into
this *human-gated, speed-first* lab. What transferred cleanly: executable engines fitting
our shared-engine + per-lab-adapter pattern (their variance miner → `coworld-hypothesis-miner`),
durable engineering doctrine (`docs/player-engineering.md`), and dense measurement heuristics
(eval sizing from variance, opponent-field-from-goal → root `best_practices.md`). What was
deliberately rejected despite topical fit: promotion-gate / continuous-optimizer /
defend-leaderboard (their replacement for our human gate — importing would fight the lab's
model), the local-sim harness (probe deltas reverse on the live field), game-strategy
snapshots (stale vs our live labs). Where an import diverges from its source's posture,
state it in the imported doc (e.g. "uploads stay ungated here") so readers don't inherit
the source repo's caution.

### Re-verify a parked behavioral premise on CURRENT data before building — a 2-week-old "field-worst" can be field-BEST today

Evidence: Thread 9 (imposter co-location spread nudge). The TODO's premise — crewborg-imposter
near/following its co-imposter "32% of intervals (field-worst)", measured ~v101 on 2026-07-07 —
was re-measured first on 200 fresh v107/v110 eps (`/tmp/wh_anchor_base_v110`) before any code:
crewborg's co-imposter proximity share is 13.7%, the LOWEST of the 7 crewborg-family policies
(field 15.0%, z=-1.08); following share 10.2%, 2nd-lowest overall. The consequence claim also
failed: per-episode imposter-pair co-location is uncorrelated with imposter win (r=0.017 p=0.82)
and the ejection trend runs OPPOSITE the "tell" theory (high-co-location eps have FEWER imposter
ejections). Verdict REFUTED-PREMISE, zero build cost spent. Ten versions of drift (v101→v110:
self-hunt fix, palette/self-ID fix, HS) plus a different metric window fully inverted the ranking.
The premise-first gate in the thread brief saved an entire design→build→A/B cycle (~half a day +
200 paced eps). Scripts: /tmp/t9_spread/premise{,2,3,4}.py.
