# CTF tentative lessons — session buffer

**Session started:** 2026-09-02 11:00. This is THIS SESSION's lesson buffer. Write candidate
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

## 2026-09-02 — S2 league-state research session (candidate lessons)

- **The Observatory v2 API base is `https://softmax.com/api/observatory`, not `https://softmax.com/api/v2/...`.** The latter 404s into the Next.js frontend with an HTML page, which looks like "the route isn't deployed". `CoworldApiClient._http_client` already has the right base; use it (or `.reports-working/.../obs.py`).
- **Forum and wiki have `.md` render endpoints** (`/v2/forums/<coworld>.md`, `/v2/posts/<id>.md`, `/v2/wikis/<coworld>/pages.md`, `/v2/wikis/<coworld>/pages/<slug>.md`, `/v2/forums/search.md?q=`) that are far cheaper for an agent to read than the JSON; every post's `.md` ends with ready-made curl for vote/comment (needs `idempotency_key`).
- **`coworld episode-results <ereq>` is the cheap per-policy scoreboard**: per-seat `scores/win/kills/teamKills/hitDamage/teamHitDamage/deaths/achievements`, `names` are PLAYER names (second seat "(2)"), no replay needed and no GameVersion gate. Sweep it via `/v2/rounds/<id>/episode-requests?limit=100` (limit=1000 is a 422) + `/v2/episode-requests/<id>/artifacts/results`.
- **Leaderboard endpoint** `/v2/divisions/<div>/leaderboard?include_recent_rounds=true` (boolean, not a count as the S1 ladder tools assumed); `episode_wins`/`win_rate` come back null in S2.
- **The live S2 variant is 8 duos / 16 seats** since `4f224b08` (2026-09-01); the 09-01 framework report's "32 seats / 16 duos" and the game description's "sixteen duos" are stale. Re-check `coworld_manifest_paintbot.json` before quoting seat counts.
- A stale post id in a forum comment (a fabricated link) produced one 422 in the download loop — filter ids by the posts JSON, not by regex over rendered markdown.
- **The engine zone-escape reflex owns 57-78% of every seat's alive ticks** (rounds 3706-3709 replays). A policy's edge is the ~250-tick opening before it arms plus the combat overlay that rides through it; mid-match ladder cleverness stands on <30% of ticks.
- **`no_shoot` does not stop friendly fire from a stacked duo**: all 82 friendly kills in 55 episodes happened with the victim on the killer's never-list (aim assist skips teammates, the shot ray does not — `sim.nim:2986` vs `:2887`). Separate the duo physically; do not trust the list. Candidate engine ticket.
- **`target_law{holdTrigger:{aliveTeams:N}}` with N ≥ 8 releases on tick one** in an 8-duo match (`aliveTeams <= holdValue`). Use a tick/step hold.
- **A `bodyguard` rung above the movement rung pins the seat** (emits hold while the ward is in leash; `stepSeat` never reaches the rung below). Codex port: 62.5% of seats never moved.
- **Replays, not seat logs, answer "was the pact kept"**: calls 0x10, intent annotations 0x11, lobby transcript 0x13 are all in the hosted replay and hash-chained. Probe: `.reports-working/paintbot-s2-league-state-2026-09-02/replays/zz_league_probe.nim`.
- The leaders (co-gas relh/richard) ship FORKED `edge_ride`/`target_law` modules (`scatterHeading`, `scatterSteps`, `openingHoldSteps`) — play names resolve against the seat's own playbook, so a familiar name is not the reference module.
