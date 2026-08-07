# Stencil leaderless-squad retrospective

> **Historical experiment cutoff.** v52 was subsequently submitted and became
> champion on 2026-08-06. The four-entrant/old-board evaluation shape below was
> correct for those episodes; use the campaign-shaped evaluation contract for
> new work.

**Cutoff:** 2026-08-06  
**Versions:** stencil:v49-v53  
**Disposition:** safety fix retained; liveness design rejected; no squad version submitted

## Outcome

The experiment established that leaderless squads can form and follow shared
hold, watch, and move orders without a designated leader. It also established
that the current fixed-squad design is not robust to long physical separation
on tournament maps with range-limited chat.

v51 fixed the consensus safety defect: once a vote was locked, the same value
was stored, counted toward quorum, and rebroadcast. No later stressed game
showed conflicting same-squad, same-epoch commitments. The remaining failure is
liveness. A living member can leave shout range for an emergency objective,
fall back to independent behavior, and remain multiple epochs behind. Static
and continuously refreshed regroup targets did not meet the preregistered bound.

The source tree is restored to v52 behavior, the best liveness checkpoint, but
v52 is not an accepted improvement and remains unsubmitted. v53 is rejected.
v47 remains the league champion and the control for future gameplay comparisons.

## Representative evidence

Every verdict below came from full-seat hosted games on an actual campaign map,
with four entrant blocks and Daveey present. No 1v1, partial-seat, arbitrary-map,
or local episode was treated as performance evidence.

| version / gate | adoption | commits | timeouts | resyncs | conflicts | worst concurrently-live drift | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| v49, 10-game broad gate | 48/48 | 272 | 45 | — | 1 | two isolated seats ended two epochs behind | refuted: mutable votes violated safety |
| v50, 10-game matched gate | 47/47 available | 275 | 24 | 10 | 0 in broad gate | terminal 9/6/9 was a dead-member measurement confound | refuted as preregistered; metric corrected |
| v50, 3-game giant 4FFA8 stress | 23/23 available | 154 | 17 | 25 | 4 | one gap lasted 122 ticks | refuted: lock was not used by quorum counting |
| v51, 3-game giant 4FFA8 stress | 24/24 | 159 | 13 | 27 | 0 | four epochs for 1,226 ticks | safety passed; liveness refuted |
| v52, 3-game giant 4FFA8 stress | 24/24 | 164 | 13 | 33 | 0 | two epochs for 555 ticks | improved, but refuted against 90-tick bound |
| v53, 3-game giant 4FFA8 stress | 24/24 | 153 | 36 | 34 | 0 | four epochs for 967 ticks | regressed and rejected |

The directional game results were not used to override the mechanic gates.
v52 happened to win all three stress episodes; v53 won two and lost one. Those
small outcome samples do not establish a gameplay improvement.

## What worked

- The trace vocabulary made the protocol inspectable end to end:
  `squad_consensus` exposed proposals, votes, quorum, commits, timeouts, and
  resyncs; `squad_order` exposed directive changes; `squad_follow` showed the
  resulting movement and post behavior.
- A single vote lock now governs local storage, quorum counting, and rebroadcast.
  That narrow change removed the observed safety conflicts without changing the
  order model.
- Per-tick concurrent-live analysis separated real liveness failures from dead
  members that could no longer hear or respond.
- The giant 4FFA8 stress case efficiently reproduced the long-range failure
  while retaining the full tournament seating and opponent contract.

## What failed, and why

The protocol assumed that repeated communication or epoch resynchronization
would eventually reconnect a fixed squad. That assumption is false when chat is
proximity-limited and gameplay objectives can keep living members physically
partitioned. Protocol retries repair missed messages only after contact exists;
they do not create contact.

v52's timeout path sent an isolated member toward the last known teammate
position. That position could already be obsolete. v53 continuously refreshed
the target, but local sightings still did not provide a stable squad-wide
rendezvous and the extra motion increased timeouts. Further target tuning would
be moving the same failed premise around.

## Durable lessons

1. When validating distributed consensus, verify that a locked vote controls
   every downstream representation: storage, quorum counting, and rebroadcast.
2. Measure liveness only over intervals where the relevant agents are alive and
   able in principle to participate; terminal clocks from eliminated agents are
   not protocol evidence.
3. Fixed squads using range-limited communication need an explicit
   reconnection/rendezvous contract. Resync messages alone cannot repair a
   physical partition.
4. Keep preregistered mechanic gates separate from game outcomes. A few wins do
   not rescue a coordination design that missed its safety or liveness bound.

The first three are now canonical in
[`../../best_practices.md`](../../best_practices.md). The fourth is already part
of the root experimentation discipline.

## Next-session handoff

Start with the reconnection contract, not code. Decide how separated living
members discover a rendezvous point, how the choice remains leaderless, how an
emergency objective interacts with it, and what bounded concurrent-live drift
would falsify the design. Keep the order executor—generated posts, cover-aware
movement, and hold/watch/move behavior—unchanged so the next result remains
attributable.

Use v47 as the gameplay control. Use v52 only as the implementation checkpoint
for the conflict-free consensus core. Do not submit either v52 or v53, and do
not continue v53's refreshed-target tuning.

Detailed immutable verdicts:

- [`stencil-v49-squad-consensus-experiment.html`](stencil-v49-squad-consensus-experiment.html)
- [`stencil-v50-squad-consensus-experiment.html`](stencil-v50-squad-consensus-experiment.html)
- [`stencil-v50-live-consensus-experiment.html`](stencil-v50-live-consensus-experiment.html)
- [`stencil-v51-live-consensus-experiment.html`](stencil-v51-live-consensus-experiment.html)
- [`stencil-v52-timeout-rejoin-experiment.html`](stencil-v52-timeout-rejoin-experiment.html)
- [`stencil-v53-refresh-rejoin-experiment.html`](stencil-v53-refresh-rejoin-experiment.html)

Hosted request IDs for artifact recovery:

- v49 broad gate: `xreq_3abefe2c-1efc-48f5-b17b-a4cc0f7b76e1`,
  `xreq_6122f0e9-508d-40e7-9fb2-470ca3f45ab0`,
  `xreq_f71cd791-a02c-4c0e-8490-0e97a43b0c11`,
  `xreq_bd7b235f-923c-4e1a-8d93-26132def570b`,
  `xreq_19b64c44-7072-496c-8e68-a3f77c05d78d`,
  `xreq_2936d525-007f-4fba-9542-6c4e6ec1c6e9`,
  `xreq_7104e456-be3f-46fe-92c4-22f7dca77054`,
  `xreq_db21cbc5-3922-4fc0-bbfb-a25df817d7e8`,
  `xreq_79beac35-a3f2-40f6-baaf-b78eee5230db`, and
  `xreq_665fa256-8f49-4d4a-85a6-64df44d5c65e`.
- v50 broad gate: `xreq_428066d3-c453-48ef-9248-30385514e7c6`,
  `xreq_f859d5e4-7534-412e-805f-fc1a6635c8de`,
  `xreq_ba0d78db-5370-4ac2-80db-a824d18ee2e1`,
  `xreq_cae40eb8-3fdf-4e62-a73e-fff4c74e9cf1`,
  `xreq_5ef56ef9-d4f9-48ab-8331-c3531ffad394`,
  `xreq_e276300e-5165-489f-86b3-1809e9b45969`,
  `xreq_9da5c95c-dd67-4c2e-8a47-6f58e45cb888`,
  `xreq_0843187d-ed88-4471-b367-0b6eaf0a5ee8`,
  `xreq_fb9fa0f3-e7a2-4f79-af6d-317c00e35d99`, and
  `xreq_8b4d25bf-a604-412c-a03f-6da0f411b381`.
- v50-v53 stress gates: `xreq_8b8a6ea8-9c9f-4776-af09-3dea8ee52658`,
  `xreq_5c1837f1-416d-4ef0-b085-30b26caf670a`,
  `xreq_7d8078c0-6095-48db-a3b7-4311f0998234`, and
  `xreq_973298a0-a38d-487d-b75d-d07fca548d6f`.
