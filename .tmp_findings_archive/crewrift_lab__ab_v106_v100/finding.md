## Finding: v106's imposter hunts ITSELF — the reveal self-exclusion removed an accidental protection

**The numbers.** Imposter win 71%→35% (p=0.005), kills_mean 1.58→0.58, zero-kill
imposter games 4%→44%. Crew unchanged (noise). This is not a social-rework effect —
the LLM fired only ~27%/19% (cand/base), well under the 60% gate; the regression is
in the deterministic hunt path.

**The mechanism (telemetry-confirmed across 53 cand / 50 base imposter episodes).**
crewborg is pinned slot 0 ⇒ its own color is **red** (`PlayerColors[slot mod 16]`).
In the candidate arm, 45/53 imposter episodes show hunt strikes at victim **"red"**
— crewborg's own sprite, at victim_dist ≈ 6.3 (its own body), `in_range=True`,
`unwitnessed=True` — 111,568 self-strike events vs 24 real-victim strikes, each
emitting `kill_attempted {target_id: null}` (the engine can't resolve a self-kill).
The baseline arm has **zero** self-strikes (517 real ones).

**Why v106 and not v100.** `visible_victims()` (strategy/opportunity.py:147) filters
only `color not in teammate_colors` — it has never excluded `self_color`. In v100,
imposter reveal ingestion did `teammate_colors |= reveal_player_colors`, and the
reveal icons include SELF — so self sat in teammate_colors and was *accidentally*
excluded from the victim pool. v106's fix for the v102 kill regression
(types.py:868-871) now correctly drops self from teammate_colors at ingest — which
silently un-protected the hunt path. The most-isolated victim heuristic then loves
the self sprite (always visible, always in range).

**Why the league hasn't collapsed [caveat].** In league play crewborg isn't always
slot 0; whether the self-sprite wins victim selection may vary by seat/color. Rank
14/16 with score 1464 suggests real damage is likely already occurring in imposter
rounds.

**The lever.** One-line fix: exclude `belief.self_color` in `visible_victims()`.
