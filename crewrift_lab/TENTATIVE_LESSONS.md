# Crewrift tentative lessons

**What this is.** An *eager, deliberately noisy* buffer of candidate lessons from
Crewrift work — things that *might* be durably true but haven't earned a place in
[`best_practices.md`](best_practices.md) yet. Write here freely the moment something
*looks* like a reusable lesson; most entries will be noise, and that's fine — the value
is the occasional gem.

**The graduation rule.** Each lesson carries a **hit count** — bump it (and add a dated
note) every time the lesson recurs and holds up. **Once a lesson has hit enough (≈3
independent confirmations) and still holds, promote it** to the right `best_practices.md`
(Crewrift-specific → [`best_practices.md`](best_practices.md); game-agnostic → the
root [`../best_practices.md`](../best_practices.md)) and delete it here. Cull entries
that get contradicted.

**Entry format.** `### <lesson, one line>` then: `Hits:` (count + dates), `Evidence:`
(what you observed), `Status:` (`candidate` / `promote?` / `contradicted`). Keep it terse.

---

### Join league scores to a policy by `policy_version_id`, never by slot position.
- **Hits:** 1 (2026-06-10)
- **Evidence:** A daily-league round's `scores`/`participants` for crewborg v17 also
  contained a *different player's* `crewborg-v23` fork in another slot — a name- or
  position-based join would have mixed them. The episode-row `policy_version_id` is the
  authoritative handle. (Mirrors the root best-practice against position-based score
  joins; this is the concrete Crewrift instance.)
- **Status:** candidate (likely already covered by root best_practices — promote-or-cull on next hit)

### "Finished all 8 tasks" does **not** guarantee a clean crewmate score (8/108).
- **Hits:** 1 (2026-06-10)
- **Evidence:** An all-8-tasks crewmate scored **−2** (lost) and another **98** (won)
  because of a **vote-timeout (−10)**; idle penalties (−1/~20s) can also erode it. So
  the "clean success" score set means *clean play*, not *objective met*. Upside: a pure
  score-anomaly filter therefore *catches* these penalty cases for free.
- **Status:** candidate

### Daily-league *round* episodes are queryable (with scores inline) without downloading artifacts.
- **Hits:** 1 (2026-06-10)
- **Evidence:** `coworld episodes --round <round_id> --policy <name> --json` returns the
  commissioner round's episode rows — including `participants` and `scores` — so a
  cheap score-level sweep needs no artifact pull. Note this hits `/v2/episode-requests`
  by `round_id`; the episode-artifacts `endpoint-map.md` frames league episodes as a
  population *disjoint* from `/v2/episode-requests`, yet these commissioner-run league
  rounds appear there. Possibly the endpoint-map is partially stale for commissioner
  rounds, or "league episode" there means something narrower. **Verify before relying
  on the disjointness claim** — and if confirmed, fix the endpoint-map.
- **Status:** candidate (also a doc-accuracy flag)
