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

### Infer authored openings from repeated trajectories, and stop before reactions dominate

Evidence: the same 10 replays per opponent produced stable, high-support opening shapes:
focusfire settled into three defensive post groups, h050 opened 2 top / 5 middle / 1 runner,
and alphashot held four seats deep in its endzone while using sparse runners. Exact simulator
positions, team-frame mirroring, 5-second windows, bounded-diameter holds, and persistent
proximity/co-motion were enough; no large clustering dependency was needed. After roughly
60 seconds, deaths, respawns, item emergencies, and contact increasingly described reactions
rather than the authored opening, so the analyzer defaults to an opening horizon and labels
low-agreement motion as `maneuver`.

### A configured battle plan and observed field behavior are different artifacts

Evidence: v39's traces show every plan phase executed, but replay trajectories also show
item-retrieval and combat rungs pulling individual bots away from their nominal rally/vee
orders. The inferred report is therefore an observation of the whole policy priority ladder,
not a source-code reconstruction. Always report confidence/support and retain `maneuver`
rather than forcing every path into a move or hold.

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

### WAREHOUSE BUG: every outcome column is dead because results.json is no longer served

Evidence: `event_warehouse.py:92-97` reads `participants.score/win/kills/deaths/captures` and
`episodes.winner/red_score/blue_score` from a per-job **results.json** artifact. On a fresh
120-episode warehouse (ctf 0.7.102): all five participants columns **null in 1920/1920 rows**, and
`episodes.winner` = **"draw" for all 120 episodes** — while episode.json ground truth shows 17 wins.
Re-fetching one episode with DEFAULT flags still reports `! results artifact unavailable`, and
results.json is absent from older batches too, so it is not a `--no-logs` mistake. The tables still
build without error, which is what makes it dangerous.
Status: derive win/draw/loss from episode.json `scores` joined via `participants` on **policy_name**
(the field is `position`, NOT `slot` — I used `slot` first and silently got zero rows), and
kills/captures from `replay_events` (kill 4876, capture 63, flag_steal 283 — all populated).
`tools/fight_ab_report.py::outcome_of` is the working reference. Handover written to
`scratch/HANDOVER-warehouse-findings.md`.

### The warehouse has shot/hit events with position + aim — undocumented and underused

Evidence: `replay_events` key='shot' (24,979 rows) and key='hit' (15,774) carry
`{x, y, aim}` re-keyed to policy/version/team/seat. The module docstring lists only
kill/steal/return/capture/respawn/score/phase/game_over, so they are easy to miss.
Status: these make shot-level questions answerable — accuracy (hit/shot) per policy, fire-range
distributions, and two-sided engagement detection. Built `tools/find_firefights.py` on them: slide a
window, require opposing-team shooters within a radius, merge contested ticks bridging short lulls.
406 firefights in v36, 407 in v37 at >=3s.

### Snapshots are a SPARSE periodic dump; the transition events carry the detail

Evidence: per bot per episode there are only ~35 `event='snapshot'` records, but 174
`firefight_target` (with the FULL score decomposition — range_px/score/wound/range_band/claim/
shootability/aim_cost/shield/shootable), 215 `focus_claim` (action + claimant_seat + release_reason),
21 `firefight` mode transitions, and 5,485 `heard_chat`.
Status: any analysis or overlay that reads only snapshots gets ~1 sample per 140 ticks and will look
like the feature barely fired. Read the transition events. Also: `firefight_target.cell` is in the
same PIXEL space as `self_xy` despite the key name — do not scale it by a grid size.

### THE REAL BOTTLENECK IS CAPTURES, NOT FIGHTING — and I falsified my own hypothesis

Evidence: replay ground truth over 60 episodes each — vs h050 **5 captures to their 31**; vs
focusfire **3 to their 24**. Yet we remove ~19-20 of 24 enemy lives per game. I hypothesised that
extended brawling was itself the losing strategy (every top-intensity firefight was in a loss) and
TESTED it: wins average MORE contested time than losses (54.7s vs 50.4s vs h050) and high-firefight
episodes have MORE captures (0.13 vs 0.03/ep). Hypothesis wrong — fighting is not hurting, it simply
is not the constraint.
Status: this explains why all four firefight arms landed within noise. The next lever is capture
conversion, not combat. Note the trap I nearly fell into: "all the big fights are losses" was an
artifact of ranking by intensity plus the dead `participants.win` column.

### 63-69% of firefight target selections are UNSHOOTABLE — the mechanism has no "no target" state

Evidence: from `firefight_target` transition events across v36/v37: **63-69%** of selections have
`shootable: false`, and **24-30%** are beyond the 350px `FIRE_MAX_RANGE_PX` gate entirely (seen
directly, e.g. range_px 424.12 with shootability -1.0). Selected range averages ~270px while actual
shots land at ~207px (barely moved from the 187px pre-firefight baseline).
Status: the `shootability` term (-1, weight 0.35) only ranks AMONG visible candidates — when every
candidate is unreachable it still picks the least-bad one and LATCHES it (min dwell 8t, switch
margin 0.10). Concrete fix for any future firefight work: add a "no acceptable target" state that
declines to latch, and re-centre the ideal range band on where shots actually connect rather than
220-300px.

### THE STEAL, NOT THE DELIVERY: our capture deficit is entirely about reaching their flag

Evidence (360 eps): steal->capture conversion is vs h050 **26%** (theirs 29%) and vs focusfire
**20%** (theirs **17%** — we are BETTER). But steals are 19 vs 106 and 15 vs 143 — 5-9x fewer
attempts. Our bots die at median depth 614-672px from our wall (midfield 617) while their flag is at
x=1049, so we expire ~380px short. Approach route in the 10s before a steal: THEY swing wide (54%
bottom, 25% top, 20% mid); WE go 85% straight mid.
Status: escort/return work would fix something that is not broken. The lever is arriving, and the
bottom is the empirically best route — which `staged_push_top` explicitly calls "deliberately naked".
Primary metric for any plan A/B should be **steals**, not win rate: steals are ~5x more frequent so
far cheaper to resolve at n=10-30.

### A LATE PLAN ENTRY TAG STALLS THE PUSH — the tag gates advancement, not just phase start

Evidence: `plan.py:142` `_TAG_RE` matches ONLY `tick|enemy_lives|own_deaths` with `<=`/`>=`, and the
next phase's entry tag must ALSO hold for a bot to advance. So `tick>=900` freezes a bot that already
reached its target at tick 200. With mean lifespan ~407 ticks vs alphashot, that is exactly how bots
never reach the steal phase — and `staged_push_top` has this flaw, gating its steal phase on
`enemy_lives<=18`. I shipped the same bug in a scaffold (tick>=300/900/1200) and caught it before it
ran.
Status: keep entry tags permissive and let MILESTONE (arrival) drive advancement; the 900-tick phase
timeout is the fallback. Un-evaluable tags (`presence(...)`, `flag(...)`) are harmless — they gate on
milestone/timeout alone.

### `via` waypoints in a battle plan are EDITOR-ONLY decoration

Evidence: `via` is parsed into the Order dataclass (`plan.py:64,109`) but nothing reads `.via`
downstream — the editor draws the polyline, the interpreter ignores it.
Status: a multi-leg route must be expressed as SEPARATE PHASES, not one order with waypoints. The
per-phase target IS the routing. This is why the bottom push is six hops.

### A plan with empty `orders` renders a blank canvas — that is the plan, not a viewer bug

Evidence: I committed a "scaffold to draw on" with `orders: []` in every phase and James reported no
markers or arrows. The renderer was fine (move -> polyline + arrowhead, hold -> filled square with
seat count). I had read "a plan to draw on" as blank canvas when a shape to ADJUST was wanted.
Status: author draft orders on named POIs so they are draggable. Verify with `poi.resolve` on every
`to`/`at`/`facing` — a typo'd POI name silently renders nothing.

### The battle-plan interpreter is ALREADY LIVE in the champion — editing a plan ships behaviour

Evidence: `BEACON_PLAN` defaults to `"staged_push_top"` (config.py:931), not empty. Traces confirm it
executes: bots advance ~2.17 phases, ~half end in phase 3, buddy-wait ~82 ticks/agent-game, and the
hold `fallback` never fired (0/60).
Status: a plan edit is not a sandbox experiment. Also worth noting the `fallback` path has never once
been exercised in measurement, so it is effectively untested behaviour.
