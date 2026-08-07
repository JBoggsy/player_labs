# Paintbot user preferences

Durable, Paintbot-specific preferences James has stated — layered on top of the
root [`../user_preferences.md`](../user_preferences.md), which applies in full.

- **2026-08-03 — Self-play freshness is mandatory.** Every local self-play
  batch must first resolve the live canonical Paintbot version and use its exact
  source commit. Fail closed instead of optimizing against a stale, dirty, or
  merely locally current game checkout.

- **2026-08-05, refreshed 2026-08-06 — Only campaign-shaped games count as
  tests.** Never use a partial-seat game, arbitrary map, or local micro scenario
  as evidence of Paintbot performance. A gameplay test must be full-seat and
  match the live campaign cell and battle kind. Normal two-team invasions,
  including current map ref `1v1`, use four policies in 7+7+1+1 captain/ally
  seating; `ffa4` uses four policies with one complete color each.
  Smaller scenarios may only debug a mechanism and must be labeled
  non-representative.
