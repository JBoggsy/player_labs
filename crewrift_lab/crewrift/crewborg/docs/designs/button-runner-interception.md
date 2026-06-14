# Button-runner interception (imposter)

**Status:** initial design (2026-06-12). Not yet built.
**Motivates:** deny the crew's strongest defensive play — the emergency-button
"reset our kill cooldowns" trip — by killing the runner *en route* to the button.

---

## 1. The idea, and why it's worth doing

A meeting resets **every imposter's kill cooldown** (a body report or a button
call both open a meeting). Our own league analysis already named this as the
field's best crew defense: RowDaBoat and truecrew "burn the emergency button
every game to reset imposter cool downs" (`WORKING_CONTEXT.md`). A crewmate
walking to the button to reset us is:

- heading to a **known, fixed destination** (the button anchor — baked at the
  **bridge** center, which is also `home`/spawn; `map/bake.py:131-134`);
- usually **travelling alone** (it's a deliberate solo errand); and
- about to cost us **two** things at once: our live kill window *and* a meeting
  (a vote that can eject us).

So intercepting that runner before it presses has **triple value**:

1. **+1 kill** (and one fewer crew → closer to the parity the imposter needs);
2. **no cooldown reset** — we keep the kill window the crew was trying to deny; and
3. **no meeting** — no vote against us this cycle.

This matters because it is *not* "more kills for their own sake." Our standing
read is that the kill→win link is weak and the next lever is imposter
**conversion** (survival / meetings / endgame), not kill volume
(`WORKING_CONTEXT.md`). Denying button-meetings and cooldown resets is squarely a
*conversion* lever — it lengthens our live kill windows and removes vote chances —
which is why this is more promising than the kill-tuning we've already exhausted.

### 1.1 Reframing the "500 / 900 tick" intuition

The original framing was "intercept runners around tick 500 or 900, especially
900." That intuition is correct, but the *robust* trigger is not the absolute
tick — it is **our own kill-cooldown clock** plus an **observed approach**:

- 500 ≈ the **first** kill cooldown expiry from game start; 900 ≈ the **second**
  window after an early meeting reset. Both are simply *"shortly before our kill
  becomes ready"* — i.e. exactly when a defensive crew wants to press to deny us,
  and exactly when we become able to punish them. That is `ticks_until_kill_ready`
  being small — **the window Search/Hunt are already awake for.** No new
  tick-based scheduler is needed; the behavior slots into the existing kill window.
- **"Especially 900" is right, for a sharper reason than 900 > 500.** Early
  (≈0–500) the whole crew is still clustered at the bridge/spawn (the button's
  own room), so a kill there is crowded and witnessed. By ≈900 the crew has
  dispersed to tasks, so the lone runner *returning to the front* is isolated and
  conspicuous — interceptable and killable unwitnessed. The behavior should
  therefore **prefer later windows and weight isolation**, not key on a literal 900.

Absolute ticks are fragile: every meeting resets the cooldown clock, so the next
"reset window" shifts with whatever meetings have already happened. Trigger on the
cooldown clock and the observed approach, not on wall-clock ticks.

### 1.2 Kill *en route*, not at the button

Killing the runner **at** the button is partly self-defeating: the body lands in
the bridge — the most-trafficked room — and gets reported fast, which opens a
meeting and resets our cooldown *anyway*. The value is maximized by intercepting
**early on the approach**, in a corridor before the bridge, where the body is less
likely to be seen, then **venting away** (hand off to the existing Evade). Even in
the worst case (body found) we still converted a *guaranteed* reset+meeting into a
kill plus a *maybe* reset+meeting — net positive — but the design should aim for
the clean version.

---

## 2. Phase-0 corpus findings (DONE, 2026-06-12)

Measured on **1,875 complete league games** (`suspicion_lab/expanded/`, map
`croatoan`) via `suspicion_lab/tools/button_runner_study.py`. The button call is
attributed to a caller slot (`vote_called_button`, distinct from
`vote_called_body`); the approach is reconstructed from the caller's `player_state`
position snapshots in the 250 ticks (= `SEARCH_LEAD_TICKS`) before the press.

**How common — near-universal and frequent.**
- **92.5%** of games have ≥1 button call. **Mean 2.15 button calls/game** (max 6).
- **3,740 crew** button calls vs **298 imposter** — overwhelmingly crew, i.e. the
  reset-defense premise holds. **~2.0 crew reset-calls per game.**

**Timing — the cadence is ~900 ticks, confirming "especially 900."**
- Gap from the prior meeting clusters hard at **800–1000 ticks** (median **945**,
  mean 1015). The 500-tick bucket is small. So crew re-press on a **~900-tick
  rhythm**, by which point our 500-tick kill cooldown is comfortably ready — the
  runner is vulnerable exactly as hypothesized. (First-call ticks: p25 ≈ 1020.)

**Where — runners funnel through the bridge's eastern mouth (Hydroponics
corridor), and they travel SOLO.**
- The runner is a **median 241px** from the button 250t before pressing, then
  converges — a ~240px / ~250-tick approach we can cut into.
- **Isolation: median 0 other crew within 48px for the entire approach** —
  button-runners almost always travel **alone**. Great for clean kills, and it
  means isolation doesn't discriminate *where* to intercept; pass-through and
  not-at-the-bridge do.
- **~42%** of runners are already in the Bridge 250t out (idling/tasking at the 5
  bridge tasks — little approach to cut). The **interceptable ~58%** come from
  outside, and they funnel through a clear chokepoint:

  | Approach room (pass-through %) | note |
  |---|---|
  | **Hydroponics — 57.3%** | the dominant eastern corridor into the bridge |
  | Observatory — 24.9% | northern approach |
  | Storage Deck — 21.4% | top *origin* room (20.8% start here) |
  | Science Bay — 17.8% | southern approach |
  | Shuttle Bay — 10.4% | |

- Top **chokepoint cells** (off the bridge, ~150–240px east of the button, where
  most inbound runs converge before entering the bridge): the **Bridge↔Hydroponics
  corridor mouth** at roughly **(272–368, 272)** (north) and **(272–336, 400)**
  (south), plus Hydroponics itself near **(400, 304)**. These score highest on
  pass-through × off-bridge distance, and bodies dropped there sit in the
  corridor/Hydroponics rather than the high-traffic bridge.

**Verdict: BUILD.** Reset-calls are near-universal (≈2/game), timed on a ~900-tick
rhythm our cooldown is ready for, runners are solo, and they funnel through one
identifiable off-bridge chokepoint. → The Tier-1 **front-positioning prior (§3.2)
should bias toward the Bridge↔Hydroponics corridor / Hydroponics zone** (≈x 270–410,
y 270–410, ~150–280px east of the button), **not the bridge interior** — that
catches the majority of *inbound* runners before they press, in a less-trafficked
spot, while the runner is alone. The ~42% already-at-bridge runners are not worth
camping the bridge for (the design's anti-camping guardrail stands).

*Re-run:* `uv run python crewrift_lab/suspicion_lab/tools/button_runner_study.py`
(add `--json-out <path>` to dump the cell table for tuning the bias points).

---

## 3. Architecture: layer into existing seams, don't bolt on a scheduler

The imposter already wakes for kills via the selector
(`strategy/rule_based.py:_select_imposter`): when `ticks_until_kill_ready ≤
SEARCH_LEAD_TICKS` (250) it runs **Search** (walk occupancy hotspots, follow a
visible victim); when kill-ready with a visible victim it runs **Hunt** (strike
when unwitnessed). A button-runner is just *a particularly valuable victim that
appears in a predictable place at a predictable phase of our own cooldown*. So we
do **not** add a new top-level mode or a tick scheduler. We add:

- a small pure helper module that **detects a runner** and **describes the button
  approaches**, and
- three targeted hooks into the existing Search / victim-selection / Hunt path.

This keeps the selector's priority list unchanged in shape and reuses the
leading, witness, and evade machinery already in place.

### 3.1 New module: `strategy/button_intercept.py` (pure, testable)

All functions are pure over `Belief` (mirrors `opportunity.py`'s style):

- `button_anchor(belief) -> Point | None` — `belief.nav.button_anchor` (fallback
  to `belief.map.button.center`).
- `approaching_button(belief, record) -> bool` — is this live non-teammate moving
  *toward* the button? Uses the runner's recent positions. Two cheap signals,
  AND-ed:
  - **Heading:** over its `PlayerRecord` history trail (bounded 64 entries;
    `types.py`), arc-length distance to the button along its route is *decreasing*
    — i.e. the last few samples step the runner closer to the button anchor.
  - **Locus:** it is already within the "front approach" band (below a
    nav-distance threshold to the button anchor) — not merely pointed that way
    from across the map.
- `button_runner(belief) -> PlayerRecord | None` — the highest-priority
  approaching runner among **trackable** non-teammates (seen ≤
  `TRACK_WINDOW_TICKS` = 120 ago, so we can pursue even while it's briefly out of
  view). Tie-break: closer to the button (more urgent to stop) then more isolated.
- `intercept_point(belief, record) -> Point | None` — where to cut the runner
  off: lead its motion along its button-route (reuse `strategy/trajectory`
  `predict`/`lead_ticks`) and pick the point on **our** route to it that meets its
  path earliest *before* the button. Falls back to the runner's predicted position
  if no clean intercept solves.
- `button_approach_points(belief) -> list[Point]` — front-biased loiter points for
  positioning when no runner is visible yet. **Reuse the substrate we already
  build:** `OccupancySubstrate.polylines[(anchor, "button")]` are precomputed
  routes from every anchor to the button (`agent_tracking.py:208-215`). Sample
  points along these polylines, weighted toward the **bridge-side** segment, to
  stand where approaches converge.
- `near_button(belief, point, radius) -> bool` — kill-location guard for §3.4.

No new per-tick state and no new belief fields — everything reads from the
existing `roster` trails, `agent_tracking` substrate, and `nav`.

### 3.2 Hook A — positioning prior in Search (Tier 1, ships alone)

When Search has no visible/trackable victim and is walking occupancy
(`SearchMode._next_search_point`, `modes/search.py:74`), and we are in the kill
window (already true whenever Search runs), bias the seek points toward the front:
blend `button_approach_points(belief)` with the existing
`ranked_seek_points(belief)` instead of using occupancy alone. Effect: during our
kill-ready window we *loiter near the button approaches* rather than generic
hotspots, so we are physically positioned to (a) see a runner enter the front and
(b) reach it before it presses. This is the "prioritize rooms near the front" half
of the idea, and it is what makes interception physically possible.

Guardrails:
- Only bias — never *override* a visible isolated victim elsewhere (a bird in
  hand: `_target()` / `select_victim` still win when a real victim is visible).
- Blend, don't replace, so on maps/games with no front traffic we degrade to
  normal search rather than camping a dead bridge.

### 3.3 Hook B — runner preference in victim selection (Tier 2)

`select_victim` (`strategy/opportunity.py:122`) currently returns the
**most-isolated** visible straggler. Add a documented override: **if a
`button_runner` is among the visible victims, prefer it** over the isolation
ranking — denying the press is worth more than the marginally-cleaner straggler.
Keep `select_victim` the single source of truth so Search (`_target`) and Hunt
(`_resolve_victim`) both inherit the preference for free. When the runner is
trackable-but-not-visible, Search follows it via the existing last-seen path, but
toward `intercept_point` rather than its trailing position (the one genuinely new
pursuit behavior).

### 3.4 Hook C — strike-location guard + evade handoff (Tier 2)

In Hunt's strike decision (`modes/hunt.py:42-67`), when the committed victim is a
button-runner, **prefer to strike before the bridge**: if `near_button(belief,
victim_xy, radius)` and urgency is not yet high, hold/close for one more beat to
land the kill in the approach corridor rather than in the bridge. This is a *soft*
guard — it yields to urgency (`kill_urgency_ticks`): if the runner is about to
reach the button, take the kill anyway (a kill at the button still beats a
successful press). After the kill, the existing selector already routes to
**Evade** (vent away), which is exactly what we want for a front-of-ship body.

---

## 4. What "front of the ship" means here

There is no orientation metadata on `MapData`. Operationally, **front = bridge =
button = spawn** (all colocated; `map/bake.py:131-134`). "Rooms near the front"
is therefore *proximity to the button anchor* and *the corridors on the
anchor→button routes* — and those routes are already precomputed in the tracking
substrate (`polylines[(*, "button")]`). We do not need a new spatial concept; we
need a distance-to-button band and the existing approach polylines.

---

## 5. Phasing, flags, and validation

1. **Phase 0 — corpus study (§2).** Gates everything. Output: frequency, timing,
   interceptability of naked reset-calls. Decision: build or drop.
2. **Phase 1 — Tier 1 positioning prior (§3.2)** behind an env flag
   (e.g. `CREWBORG_FRONT_BIAS`, mirroring `CREWBORG_BE_DUMB`). Cheap, low-risk,
   shippable alone. A/B vs current champion on a **2-imposter** pinned roster
   (per standing rule, never 1-imp), measuring not just kills but **crew
   button-meetings against us per game** and **imposter win conversion**.
3. **Phase 2 — Tier 2 runner preference + intercept pursuit + strike guard
   (§3.3–3.4).** Builds on Tier 1. Same A/B harness.

**Success metric is conversion, not volume.** Report: (a) naked crew button-calls
suffered per game (expect ↓), (b) mean ticks our kill stays live before a reset
(expect ↑), (c) imposter win rate / ejection rate — *not* raw kills/g, which we
already know doesn't reach wins on its own. A kills/g bump with flat wins is the
known null result; the point is the meeting/reset denial.

### 5.1 Risks / open questions

- **Detection under limited LoS:** we only see a runner in our view cone — Tier 1
  positioning is what buys the sightline; if the corpus study shows runners
  approach from directions Tier 1 doesn't cover, revisit the approach sampling.
- **Over-camping the bridge** when no one runs: mitigated by *blend not replace*
  (§3.2) and by preferring a real visible victim (§3.3). Watch idle time near the
  button in the A/B traces.
- **Body-at-front backfire:** mitigated by the en-route strike guard (§3.4) + vent
  evade, but if early kills still get reported fast, weight the strike guard harder.
- **EV may still be small** even if the mechanic works, because of the weak
  kill→win link. The corpus study (§2) is the honest go/no-go: only build if naked
  reset-calls are common and timed.

---

## 6.5 Tier-1 RESULT — REJECTED (2026-06-12)

Built behind `CREWBORG_FRONT_BIAS` and A/B'd as designed (controlled 2-imposter, 100
eps/arm: baseline v26 flag-off `xreq_fa91574b`, candidate v27 same image +secret-env
`xreq_c8abf3cb`; crewborg imposter@0, slava2 partner@7, fixed top crew@1–6, game
v0.1.54). The flag took effect (behavior changed sharply), and the result is a clear
**regression**:

- **kills 1.27 → 0.91/g** (−28%, p=0.000, d=−0.58); **no-kill games 7% → 23%**.
- Kill distribution: baseline {0:7, 1:61, 2:28, 3:3} → candidate {0:23, 1:64, 2:12,
  1:1}. The bias **tripled zero-kill games and halved 2+ kill games** — it suppresses
  kills broadly, not just marginal second kills.
- win/score: noise (49%→45% p=0.53; 62→54 p=0.27, the score drop tracks the lost kills).

**Mechanism (from the kill distribution; traces were off on v26/v27).** A *standing*
positional prior is the wrong shape. Camping the bridge↔Hydroponics corridor for the
whole kill window (a) sacrifices the general isolated-straggler hunting that
occupancy-driven Search does well, and (b) parks us in a **witness-dense** region (5
bridge tasks + spawn), so even good targets there fail the `unwitnessed` check. Runners
funnel through the corridor but only ~2×/game and briefly; the standing bias pays the
hunting cost every cooldown for a rare, often-unconvertible intercept.

**Implication for Tier 2.** Don't make interception a standing bias. Make it
**event-triggered**: hunt normally (occupancy-driven) by default, and divert toward the
button **only when an actual approaching runner is detected** *and* our kill is
ready/near — `button_intercept.button_runner()` / `intercept_point()` (§3.1, §3.3),
never the `button_approach_points()` positional prior. The Phase-0 finding stands (the
opportunity is real); the lesson is that capturing it must not cost general hunting.
`strategy/button_intercept.py` and the Phase-0 study remain as the substrate for a
future event-triggered Tier 2; the `SearchMode` positional-prior hook is the part that
should not ship.

## 6.6 Isolation-off follow-up — NO EFFECT on kills (2026-06-12)

After Tier-1 failed partly on witnessed-kill vetoes near the bridge, we tested
dropping the witness gate entirely (`CREWBORG_NO_ISOLATION` →
`opportunity.unwitnessed()` always True). Traced 2×2, 100 eps/arm (v28 control, v29
no-iso, v30 no-iso+front; xreqs in the version log):

| cell | front | iso-gate | kills/g | score/g | win | ejected |
|---|---|---|---|---|---|---|
| v28 control | off | on | **1.27** | 54.9 | 43% | 7% |
| v29 | off | **off** | 1.24 | 51.8 | 39% | 9% |
| v30 | on | off | 1.07 | 56.7 | 47% | 10% |
| (v26 prior) | off | on | 1.27 | 62.2 | 49% | — |
| (v27 prior) | on | on | 0.91 | 54.1 | 45% | — |

**Removing the witness gate is a no-op on kills** (1.27 → 1.24, p=0.80; no-kill rate
13%→12%). **Trace mechanism:** Hunt spends ~96% of its ticks in *every* arm (incl.
iso-off) **closing distance to a victim, not waiting out witnesses** — the gate is
almost never the thing blocking a kill. Median first-kill tick is unchanged (~4500)
regardless of the gate. Dropping caution just makes it strike marginally more eagerly
(more kill *intents*, +2pp ejection from 7%→9%) for **zero net kill gain** — the cap is
the 500-tick cooldown + getting a victim into range during the ready window, exactly as
the v22/v23 (BE_DUMB) and v24 (kill-sooner) analyses concluded.

**Front-bias is trace-confirmed active and still bad:** v30's Search points sit ~100px
closer to the button (302px vs ~400px control) — the flag works — yet kills still
regress (1.27→1.07). The corridor is simply the wrong place to hunt.

**Conclusion (CORRECTED 2026-06-13 — see §6.7): against the pinned top-7 the kill rate
looks ceilinged at ~1.27/g, but that ceiling is OPPONENT-RELATIVE, not structural.**

## 6.7 Opponent-relative kills + iso-off RESCUED vs weak crew (2026-06-13)

James flagged that every A/B above used the **pinned top-7** — the strongest, least-
isolable crew. A random-field run (1,200 eps, natural roles, pooled to be field-mix-
invariant) showed imposter kills scale steeply with opponent weakness: **strong(≥55)
1.12 / mid(50–55) 1.61 / weak(<50) 1.90 k/g**, corr(opp_strength, kills) = **−0.35**. The
"~1.27 ceiling" was an artifact of the opponent choice. (The cross-subject three-way in
that run was confounded — `random:true` resolves once-per-request so subjects drew
different lineups — but the strength-bucketed pooled correlation is draw-invariant.)

**So we re-ran the iso-off A/B with a PINNED WEAK-crew roster** (ranks 11–16:
yatharth/shivvy/Lively/sussybuster/kyle/suspectra-richard, mean ~47; crewborg imposter@0,
slava2 partner@7, 100 eps/arm, traced; v28 `xreq_dbb61f51`, v29 `xreq_2568cea0`). Result —
**iso-off WINS here** (the opposite of vs top-7):

| metric (imposter) | v28 control | v29 no-iso | verdict |
|---|---|---|---|
| kills/g | 1.69 | **1.92** | ▲ p=0.016 |
| win | 59% | **73%** | ▲ p=0.05 |
| score/g | 75.7 | **92.4** | ▲ p≈0.06 |
| ejected | 14% | **3%** | ▼ (fewer!) |
| kill_attempts/ep (trace) | 1.65 | 1.89 | more strikes |
| median game len (trace) | 3935 | 3802 | shorter |

**Mechanism (traces):** iso-off lifts kill *attempts* (1.65→1.89) — vs beatable crew the
witness gate WAS occasionally the thing blocking a strike (unlike vs top-7, where victims
are never isolated enough to matter). The ejection rate *drops* 14%→3% because more/faster
kills win by parity **before** crew can organize a meeting (kill-dist shifts to 2–3 kills:
3-kill games 6→15; median game ~130 ticks shorter). So against weak crew it's more kills
*and* fewer ejections — not the kills-for-ejections trade we feared.

**Revised conclusion:** the imposter kill lever is NOT exhausted — it's **opponent-
conditional**. `CREWBORG_NO_ISOLATION` is neutral vs elite crew (top-7 A/B: 1.27→1.24,
p=0.80) and a clear win vs the weaker majority of the field (weak A/B: +0.23 k/g, +14pp
win). That asymmetric profile (neutral-or-better, never worse observed) makes it a
**plausible ship** — pending James. Front-bias (`CREWBORG_FRONT_BIAS`) remains rejected
(regressed in both regimes).

## 6. Why this is clean

- **No new top-level mode, no tick scheduler.** It reuses the existing
  kill-window activation (`ticks_until_kill_ready ≤ SEARCH_LEAD_TICKS`), the
  leading/witness/evade machinery, and the precomputed button-route polylines.
- **One new pure module** (`button_intercept.py`) plus three small, named hooks in
  Search / `select_victim` / Hunt — each independently testable, each a *bias or
  preference*, never a hard override of "kill the visible isolated victim."
- **Tier 1 ships and proves value alone**; Tier 2 sharpens it. The corpus study
  gates the whole thing so we don't build a niche behavior on a hunch.
</content>
</invoke>
