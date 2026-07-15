# Vanilla WoW tentative lessons — session buffer

**Session started:** 2026-07-14 10:58. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`vanilla_wow_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Vanilla-WoW-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### wowborg v1 never self-terminates, so every episode runs to the FULL variant deadline — pick the variant by deadline, not by relevance
Evidence: First xreq (xreq_5d4946c2) targeted `rfc-five-player-clear`; after 40+ min still "running" I computed the deadline: max_ticks/tick_rate = 10000/0.1 = ~27.8 h per episode. v1 idles with CMSG_PING, ignores the session's `deadline_seconds`, and the game only ends on full clear or deadline lapse. Cancelled and re-issued on `orc-fresh-start` (max_ticks=100 → ~17 min), the only short variant. For integration smokes: use orc-fresh-start or pass `game_config_overrides` with a small `max_ticks`.
Status: also a wowborg v2 TODO — honor `deadline_seconds` (or self-exit) so long variants become usable.

### Experience requests CAN be cancelled: POST /v2/experience-requests/{id}/cancel
Evidence: Not in the skill's api.md; found it in the live openapi.json paths. Returned 200 and flipped xreq_5d4946c2 to status "cancelled" while all 4 episodes were mid-run. Useful escape hatch for mis-shaped or runaway requests.

### The Vanilla WoW league/division ALREADY EXISTS on Observatory — WORKING_CONTEXT's "no scored league" claim is stale
Evidence: `coworld leagues` shows "Vanilla Wow" (league_d7bf3aea…) with division "Leveling Ladder" (div_fe784707…), commissioner `vanilla-wow-leveling-commissioner`, created 2026-07-12. Live game package is v0.1.6 (WORKING_CONTEXT says 0.1.4.post8), though the game repo README badge is still "coworld verify: not ready" as of the 2026-07-14 pull. Whether the ladder actually scores/retains rounds is unverified — check before declaring the loop unblocked, then update WORKING_CONTEXT either way.

### vanilla_wow episodes have minutes of infra overhead before players even connect
Evidence: xreq_23feebad (orc-fresh-start, ~17 min deadline) episodes stayed "running" past the naive deadline estimate; each episode boots an all-in-one VMaNGOS server container on k8s first. Budget ~5+ min provisioning per episode on top of the tick deadline when estimating xreq wall-clock.

### The live coworld manifest (variants, max_ticks, schema) is fetchable via GET /v2/coworlds/{cow_id} — use it, not the checkout
Evidence: `/v2/coworlds/cow_d4b20fe9…` returns the deployed manifest (v0.1.6) with all 15 variants and their game_configs; there is no separate /variants route (404). The local game-repo checkout had matching variants this time but the deployed version is the source of truth for what an xreq will run.
