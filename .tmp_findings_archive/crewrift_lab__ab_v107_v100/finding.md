## Finding: the self-hunt is GONE; v107 plays at (or slightly above) v100's imposter level

**Mechanism check (the point of this A/B).** Across all 36 v107 imposter episodes:
**zero self-strikes** (504/504 strikes at real victims). v106 had self-strikes in 45/53
episodes (111,568 events). The bug is dead.

**Recovery check.** Every v106 regression metric is restored to v100 level or better:
kills/imposter-game 1.67 vs v100's 1.28 (v106: 0.58); zero-kill games 3% vs 11%
(v106: 44%); imposter win 64% vs 61% (v106: 35%). All formally "noise" vs v100 —
which is exactly the desired outcome for a pure bug-fix: no regression anywhere,
with a mild (n.s., d=+0.44) kills uptick.

**Context.** Both arms fired same-day against the same pinned top-7 champion roster,
natural roles. The base arm ran post-outage (~1h later than cand r1) — acceptable
same-window drift. LLM decision rate was low in both arms (~19-27%, shared-pool
contention), so as with the v106 A/B this compares the deterministic path — fine,
since the fix is deterministic-path only.

**Conclusion.** v107 = v106's fixes (self-ID, dead-mute) + restored imposter play.
Strictly dominates the damaged v106 champion currently competing. Recommend submit.
