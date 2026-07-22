# Imposter kill→WIN survival: post-kill flee + accused-response deflection

**Status:** implemented + A/B'd as `crewborg-survive:v1` (probe upload, never
submitted). **REFUTED 2026-07-22 — do not ship either lever**; the full verdict
with the prereg table is in `2026-07-21-imposter-survival-ab-prereg.md`. Key
post-mortem: the "4px lies-in-wait" premise was a meeting-freeze measurement
artifact (conditional on still-Playing at +60t, v110 already moved 100px), the
flee costs the second kill (kills/seat 1.81→1.38, 3+-kill seats 21.5%→5.5%
p=0.01), and the meeting deflection fired decisively (spoke-first 0→23.7%) but
drew more votes than it deflected. Kept for the mechanistic analysis below.
Evidence base: Thread 2's re-derivation on v110-lineage data (2026-07-21,
`/tmp/t2_imposter/*.py` over `/tmp/wh_anchor_*` + `/tmp/wh_rot_*` +
`/tmp/wh_v110_league`; WORKING_CONTEXT Thread-2 section).

## The problem (measured)

The imposter's kill pipeline is FINE — conversion under kill-opportunity windows is
field-best (76.9% vs field 66.2%, p=0.017), victim-finding is solved, kills/seat
1.61–1.84 vs field 1.31–1.65. It dies AFTER killing:

- Kills are witnessed: isolated kills only 15% vs field 31% (p=1.7e-5); 1st kill
  witnessed 80% vs field 67% (p=0.007). (Witness-gate tuning is 3× refuted — the
  witnessing is structural; the lever is what happens NEXT.)
- **It lies in wait on the scene: median 4px moved in the 60 ticks post-kill vs
  field 23–40px.**
- Then undefended in the meeting: speaks in 31.6% of meetings-alive; speaks FIRST
  0.0% (field 40–98%).
- Net: ejected-after-witnessed-kill 62.2% vs field 31.6% (p=6e-5); overall imposter
  ejection 47.6% vs 25.5% (p=5e-6).

## Why it lies in wait (root cause, code-level)

`strategy/rule_based.py` puts the imposter in `EvadeMode` for `EVADE_TICKS=72`
after a kill. `modes/evade.py` (the 2026-06-26 rewrite) deliberately beelines to
the **densest expected-crew room** — but the imposter just killed *where the crew
are*, so the chosen destination is usually the room it is already standing in
(room-target hysteresis then pins it), and the "beeline" is a few px to the room
center next to the body. After Evade, Search holds the best-view task *in a room
with crew* — the same room. The 60-tick post-kill window is spent at the scene.

## Why it is undefended in the meeting (code-level)

`modes/attend_meeting.py:_decide_imposter` has four paths: proactive real-evidence
deflection, reactive bandwagon, parity push, deadline skip. Two gaps:

1. **No response-when-accused.** `bandwagon_target` excludes self, so when the
   only heat in the meeting is on OUR color (the common post-witnessed-kill case),
   it returns None, parity rarely gates open, and the imposter idles to a silent
   skip while the pile converges on it.
2. **Speaks-first 0.0% on the LLM path.** Thread 1's `_first_mover_accusation_intent`
   (first-tick deterministic accusation before the meeting_start LLM round-trip)
   is crew-only. The imposter always waits ~55 ticks for the LLM (or its timeout),
   forfeiting the anchoring effect Thread 1 measured (P(ejected | named first)
   28.7% vs 12.5% later, z=5.8 — and it holds for WRONG targets: 21.7% vs 9.0%,
   i.e. anchoring works independent of correctness, which is exactly what an
   imposter needs). It is also a behavioral tell once crew crewborg anchors at
   tick 0 and imposter crewborg never does.

## Hypotheses (mechanistic, pre-registered)

- **H1 (post-kill flee):** leaving the kill scene toward a plausible destination
  (a crew-dense room ≥160 px away) during the Evade window reduces post-kill
  attribution — fewer near-body sightings of us, fewer "saw them kill X" /
  "next to X's body" claims landing in the next meeting — so fewer votes against
  us and a lower ejected-after-witnessed-kill rate.
- **H2 (accused-response + imposter first-mover):** responding to accusations
  with a deflection (counter-accuse the accuser, fabricated-safe evidence, never
  "not me"), and anchoring the meeting with a first-tick accusation when we have
  a proactive/bandwagon/parity target, reduces the accusation→ejection conversion
  against our imposter seats.

## The changes (minimal, two independent code paths)

### Lever 1 — post-kill flee (`modes/evade.py`)

- Latch the kill scene (self position on the first Evade tick after a fresh
  `belief.last_kill_tick`).
- Destination preference (was: densest crew room, unconstrained):
  1. densest crew room whose center is **≥ `FLEE_SCENE_RADIUS` (160 px) from the
     scene** (`best_pretend_room_target(..., eligible_room_names=...)` — the
     existing filter seam). Room centers on croatoan are ~190–280 px apart, so
     this excludes the kill room while keeping adjacent rooms eligible — "leave
     the scene", not "cross the map". Still crew-seeking, so the second-kill
     setup (the reason for the 2026-06-26 rewrite) is preserved.
  2. no such room (occupancy cold / all crew mass at the scene): the room center
     **farthest from the scene** — plausible-destination flee.
  3. no map/rooms: the existing last-seen-crewmate fallback, unchanged.
- Walk (`navigate_to`), don't vent: a witnessed vent is citable evidence; walking
  toward a task room is the anti-tell.
- `EVADE_TICKS` stays 72 (the v65 400-tick sweep refutation was about *duration*;
  the deficit is the *destination*).
- Trace: `post_kill_flee` event (scene, destination, kind, dist) once per kill —
  the A/B mechanism check.

### Lever 2 — accused-response deflection + imposter first-mover
(`modes/attend_meeting.py`, `strategy/meeting/imposter.py`, `strategy/meeting/chat_evidence.py`)

- **Counter-accuse when accused** (deterministic `_decide_imposter`, new path 4
  before the deadline skip): when heat is on US (votes cast on our slot, or chat
  accusations of our color) and paths 1–3 found no target, counter-accuse the
  strongest accuser with `fabricate_accusation` (identical format, safe cues) and
  couple the vote. Never a self-defense ("not me" draws suspicion — chat study
  §4); deflection only. New `imposter.counter_accusation_target` +
  `chat_evidence.accusers_of` (the self-color variant of `chat_accusers`).
  Teammates/dead excluded; votes weigh over chat accusers, lowest slot breaks ties.
- **Imposter first-mover anchor** (`_imposter_first_mover_intent`, LLM path only,
  same virgin-state gates as the crew seam): at the first decide tick, before the
  meeting_start LLM call — proactive real-evidence target (`top_suspect` +
  `build_accusation`), else bandwagon (someone already accused in tick-0 chat),
  else the parity-closing target — accuse immediately with the identical
  real/fabricated format. Sets `_deterministic_chatted` and routes through
  `_send_chat_intent` exactly like the crew anchor (no double-chat, duplicate LLM
  chat suppressed). The deterministic LLM-off path already speaks at tick 0 —
  no change there.
- Trace: `meeting_imposter_first_mover` event; `meeting_decision` paths
  `counter_accuse` / `first_mover_proactive|bandwagon|parity`.

Out of scope (kept tight per the thread pin): witness-gate tuning (3× refuted),
victim-finding/search, kill volume, a mid-meeting reactive chat seam on the
LLM path (racing a pending LLM call needs its own design), HS-member-specific
accused handling.

## A/B (pre-registered separately before launch)

See `2026-07-21-imposter-survival-ab-prereg.md`. Probe `crewborg-survive:v1`
(v110's exact recipe + `CREWBORG_HS_SECRET`), ~200 cand eps vs the existing
`/tmp/wh_anchor_base_v110` baseline (same pinned roster, slot 0, natural roles).
PRIMARY: ejected-after-witnessed-kill DOWN (62.2% baseline). The two levers are
separable in the traces (`post_kill_flee` vs the meeting events) — one can ship
without the other.
