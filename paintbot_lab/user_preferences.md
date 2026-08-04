# Paintbot user preferences

Durable, Paintbot-specific preferences James has stated — layered on top of the
root [`../user_preferences.md`](../user_preferences.md), which applies in full.

- **2026-08-03 — Self-play freshness is mandatory.** Every local self-play
  batch must first resolve the live canonical Paintbot version and use its exact
  source commit. Fail closed instead of optimizing against a stale, dirty, or
  merely locally current game checkout.
