# CTF tentative lessons — session buffer

**Session started:** 2026-07-13 17:13. This is THIS SESSION's lesson buffer. Write candidate
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

### CTF chat is protocol-only — the server discards it; no team channel exists
Evidence: verified in pinned game source (`.cache/ctf-src/761c098`): `server.nim:632` buffers
`SpriteClientChatMessage` text into `chatMessages`, but nothing reads it — it's cleared every
tick (`server.nim:1013`) and on reset (`:866`); never broadcast, simmed, or written to replays.
`replays.nim:211` comments "CTF has no in-game chat". Viewer-socket chat is repurposed as
replay commands (`global.nim:372`). Implication: coordination must stay emergent from shared
deterministic seat logic; returning `(mask, text)` from decide() is pure overhead; a CTF
warehouse never needs a chat table.

### The `.cache/ctf-src/<CTF_REF>/` tarball snapshot answers game-rules questions definitively
Evidence: "does CTF have chat" was answerable in minutes by grepping the cached, version-matched
game source rather than trusting docs or memory — and it matched the league-deployed ref
(761c098 from `tools/versions.env`). Prefer this over reasoning from gameplay docs alone for
any "what does the game actually do" question.

### Leaderboard rows carry per-round form via `include_recent_rounds` — cumulative score can mislead
Evidence: `/v2/divisions/{id}/leaderboard?include_recent_rounds=N` returns each entrant's recent
round ranks/scores. beacon:v5's cumulative 0.298 vs daveey's 0.434 looked like a big gap, but
last-20-round averages were ~0.34 vs ~0.38 — daveey's cumulative includes 470 rounds vs a
weaker early field. Judge form from recent rounds, not lifetime score, when round counts differ
by 10x. (Note: leaderboard `policy_label` can be None for some entrants; `player_name` is the
stable display key.)

### The CTF field grew — a close #3 (ctf-flankfire) makes rank 2 contestable from below
Evidence: division went 3 → 6 entrants since last session; Aaron's `ctf-flankfire:v1` scores
0.274 vs beacon's 0.298 with 173 rounds of history. Status-report sessions should re-check the
field composition, not just our own rank.

### Membership detail GET 404s — use the monitor script / list endpoints, not `/v2/league-policy-memberships/{id}`
Evidence: direct GET of `lpm_d5d2e3dc…` returned 404 even though the membership is live and the
lifecycle monitor renders it fine (it uses list queries + events). Reuse
`policy_lifecycle.py`'s `client()`/`get()`/`rows()` helpers for ad-hoc API pokes.
