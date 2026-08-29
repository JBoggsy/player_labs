# Stencil v55 early-defense evaluation — campaign round 399

Date: 2026-08-06

Candidate: `stencil:v55` (`bc7c1079-5684-47b0-82b2-7d2f69e75089`)

Control: `stencil:v54` (`cf88a169-2f85-403e-bb54-6b8bdc751ea5`)

Game: Paintbot 0.7.206, source `ec244e6b01485e8c7acd7a7929a9268354d50957`, GameVersion 40

## Verdict

Reject v55 as the general replacement for v54. The opening behavior activated
for all 278 v55 seats and substantially improved immediate survival, but it did
not improve two-team outcomes and regressed FFA combat output. V55 went **39-0-11**
against v54's **42-0-8** in the 50-pair matched field.

The aggregate outcome difference is not statistically decisive: v55 improved
four matched scenarios, tied 39, and regressed seven (two-sided sign test
`p=0.55`). The mechanism is nevertheless clear enough to reject the exact
policy: v55 produced 70 fewer kills overall, entirely from an 80-kill FFA
shortfall. The paired FFA kill delta was -3.33 per episode with a paired
bootstrap 95% interval of -5.25 to -1.54.

The narrow idea remains promising in two-team play. The next candidate should
retain v54's FFA opening and apply the covered lead gate only to two-team modes,
or give FFA a short bounded release rather than waiting for every enemy team.

## Design

- 100 one-episode, full-seat requests: 50 v55 and 50 v54.
- 28 `1v1`, 24 `2v2`, and 48 `4ffa` episodes overall, matching the live
  round-399 board's 52% two-team / 48% FFA mode mix.
- Each candidate episode had a same-window control with the same map seed,
  exact opponent versions, allies, subject color, and all 16 seats pinned.
- Two-team cells used both captain seatings. FFA used six episodes per subject
  color in each arm.
- The set included both captain seatings on round-399 cell `(3,2)` against Max
  Yankov's current `golergka-paintbot-beliefscan:v8`.
- All 100 requests completed without an episode or artifact-fetch failure.
  Every bundle contained episode metadata, results, replay, logs, and Stencil's
  native trace artifacts.

## Results

| mode | v55 record | v54 record | v55 score | v54 score | v55 kills/deaths | v54 kills/deaths |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `1v1` | 10-0-4 | 11-0-3 | +15 | +16 | 315/135 | 303/155 |
| `2v2` | 12-0-0 | 11-0-1 | +24 | +20 | 266/115 | 268/94 |
| `4ffa` | 17-0-7 | 20-0-4 | +61 | +76 | 385/140 | 465/146 |
| **total** | **39-0-11** | **42-0-8** | **+100** | **+112** | **966/390** | **1,036/395** |

The combined two-team result was exactly tied at 22 wins and four losses per
arm. V55 improved two paired games and regressed two; its +0.38 kills and +0.04
deaths per episode are noise. The `1v1`/`2v2` row difference should not be read
as a mode-specific causal effect at these counts.

FFA was directionally worse: 70.8% wins for v55 versus 83.3% for v54. V55
improved two paired games and regressed five (`p=0.45`), so the win-rate gap
alone is not conclusive. The combat-output regression is stronger: 16.04 versus
19.38 kills per episode, while deaths barely changed (5.83 versus 6.08).

Across all pairs, the mean candidate-control deltas were -0.24 score, -1.40
kills, and -0.10 deaths per episode. Paired bootstrap 95% intervals were
[-0.82, +0.36], [-2.54, -0.32], and [-1.06, +0.82], respectively.

## Did the requested behavior happen?

Yes. Every one of v55's 278 subject seats entered `early_defense`. In the 48
episodes where the gate released before game end, the team-wide release tick
had median 659 and range 233–5,098. The median was 519 in two-team games and
870 in FFA.

Using each candidate episode's release tick as the matched early-game cutoff,
v55 seats suffered **32 deaths versus v54's 75**. The reductions held in both
groups: 25 versus 46 in two-team and seven versus 29 across the 22 releasing
FFA episodes. Paired bootstrap intervals for the per-episode death deltas were
[-1.50, -0.23] in two-team and [-1.64, -0.45] in FFA.

The trace explains how. Through those matched cutoffs, v55 snapshots were in
an active firefight 17.5% of the time versus 23.3% for v54 and marked
`under_fire` 3.5% versus 4.4%. V55 actually observed enemies more often (42.3%
versus 35.1%), so the evidence supports covered observation and reduced
engagement—not invisibility to enemies, which the trace cannot directly
measure.

The survival benefit was temporary rather than a full-game life advantage:
total deaths were 390 for v55 and 395 for v54. V55 spent the saved opening
lives later while producing fewer kills.

## Why FFA failed

The exact all-opponents gate is too strict for FFA. Two v55 FFA games never
released before the match ended. Both were yellow against the same Richard +
Daveey + Rohit field on distinct cells; both ended in capture losses, with
v55 recording 9 and 15 fewer kills than its matched v54 control. Both v54
controls won.

This is the structural failure mode: in FFA, one opponent can capture another
opponent's heart while v55 waits for all three enemy teams to trail in lives.
The policy preserves early lives but gives up initiative in a match that can
end through third-party interaction.

## Max Yankov focus cell

V55 did not solve the round-385/399 `(3,2)` matchup:

| seating | v55 | v54 | v55 kills/deaths | v54 kills/deaths |
| --- | ---: | ---: | ---: | ---: |
| red captain | wipe loss | capture loss | 22/8 | 22/9 |
| blue captain | wipe loss | wipe win | 21/5 | 23/6 |

No v55 seat died before the defense gate released in either seating, so the
opening worked locally. The team still lost both games after release. Turning
one capture loss into a later wipe loss is not an outcome improvement, and the
blue seating regressed from a v54 win. The underlying Max failure therefore is
not just initial exposure around spawn.

## Statistical and provenance notes

The bootstrap intervals resample the 50 matched scenario deltas with a fixed
seed and 20,000 draws. Outcome discordance uses a two-sided exact sign test.
These episodes are matched by configuration but remain stochastic game runs;
the evidence supports rejecting v55, not a precise estimate of its true win
rate. No operationally failed episodes were removed.

The request manifest, exact created-request ledger, raw artifacts, and analysis
output are retained under `.tmp/paintbot-v55-r399/`. The first matched pair is
`xreq_747ee3b5-1e7e-453f-8b86-b97b420d7fdc` /
`xreq_6f095eae-476e-41c4-8f74-8748b028c57a`; the final matched pair is
`xreq_7fab6953-e302-4ab0-be0f-cae35e797094` /
`xreq_9d9718f6-0d17-4018-8cfe-09c3c6cea898`. The ledger contains all 100 IDs
in preregistered request order.
