# CTF tentative lessons — session buffer

**Session started:** 2026-07-29 12:01. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`ctf_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (CTF-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### FIREFIGHT LADDER RESULT (360 eps): promising but NOT significant; claims and wider spacing both HURT

Evidence, pooled over the two decisive opponents (alphashot excluded — draw-locked, see below):
| arm | wins | rate | vs baseline |
| v35 postsonly (baseline) | 11/60 | 18.3% | — |
| v36 firefight, NO claims | 17/60 | **28.3%** | p=0.140 |
| v37 + focus claims | 13/58 | 22.4% | p=0.374 |
| v38 + wider spacing | 8/60 | 13.3% | p=0.841 |
Per-opponent: vs h050 17% -> **33%** (v36, p=0.12) -> 23% (v37) -> 13% (v38); vs focusfire 20% ->
23% -> 21% -> 13%.
Status: v36 is the best arm at +10pp but **p=0.14 at n=60 is not significant**. DO NOT SUBMIT on
this. The ordering v36 > v37 > v38 is consistent across BOTH opponents, which is weak evidence the
ordering is real even though no single cell clears significance.

### The decisive negative: MORE coordination and MORE spacing both made it WORSE

Evidence: v37 (claims) < v36 (no claims) on both opponents; v38 (wider posts) is below the v35
baseline on both. This is the opposite of the design intuition — the claim mechanism fired heavily
(2430-3182 claims sent per arm) and did converge fire, it just didn't pay.
Status: the emergent scoring alone (v36) is the useful half of the feature; the coordination layer
is not. Keep BEACON_FOCUS_CLAIMS default OFF. If firefight ever ships, ship it WITHOUT claims.

### FF suppression FELL when we tuned for it — and the win rate fell with it. It was never the bottleneck.

Evidence: friendly_fire_suppressed per agent-game vs focusfire: v35 11.8 -> v36 10.1 -> v37 8.8 ->
v38 8.5; vs h050 10.6 -> 10.9 -> 8.6 -> **7.2**. So claims + wider spacing DID reduce mutual
corridor blocking by ~30%, exactly as intended — and those same arms have the WORST win rates.
Status: the FF tension James flagged is real and measurable, but reducing it does not buy wins;
whatever spacing costs (concentration, ground held) exceeds what unblocked shots return. A
mechanism metric moving the "right" way is not evidence the change helped — check the outcome.

### THE REAL CONSTRAINT: target SELECTION moved to long range; SHOTS did not. The fire gate binds.

Evidence: with firefight on, selected-target ticks sit at 300-399px **38%** of the time and 400+px
9% — the scorer genuinely points further out. But SHOT ranges barely moved: vs h050 the 0-199px
share went 47% (v35) -> 45% (v36), and 200-299 went 38% -> 42%. We now AIM at distant enemies and
still SHOOT the near ones.
Status: this is exactly the scope limit Codex predicted before implementation ("can move selection
toward the band but cannot create a 400px+ tail; FIRE_MAX_RANGE_PX=350 and the aim/fire geometry are
unchanged"). Confirmed empirically. **The next lever is the fire gate / aim accuracy, not target
choice.** Note 38% of selection ticks are at 300-399px, partly BEYOND the 350px gate — the range
band (ideal 220-300) may be pointing at targets we cannot legally shoot, which is a live tuning bug
worth checking before any further firefight work.

### Kills are FLAT across all four arms — so the win-rate spread is probably mostly noise

Evidence: enemy lives removed per episode (24 = wipe), vs h050: v35 19.4, v36 20.2, v37 19.0, v38
19.3. vs focusfire: 19.4 / 19.2 / 19.2 / 19.4 — indistinguishable. Zero wipes in 360 episodes.
Status: a fight change that does not move kill count almost certainly did not move win rate either.
This is the strongest argument for reading v36's +10pp as noise rather than signal, and it is the
check that stopped me submitting a "winner" that wasn't one. Always pair an outcome delta with a
mechanism delta that could plausibly cause it.

### vs alphashot:v180 we are DRAW-LOCKED — a different failure mode entirely (0W/29D/1L baseline)

Evidence: every arm scores 0% vs alphashot:v180, with 25-30 of 30 games ending as draws. We remove
only **7.9 of 24** enemy lives there (vs ~19.4 against both other opponents) and they evidently
cannot finish us either. Under GV23 a draw pays -1 exactly like a loss.
Status: alphashot:v180 is not a fighting problem, it is a CAPTURE problem — neither side scores.
Fight tuning cannot help here; this needs a different lever (grab-and-run timing, or exploiting the
GV23 clock-extension rule). Do not blend alphashot into pooled fight statistics — it dilutes a real
effect with a cell where the mechanism cannot apply.
