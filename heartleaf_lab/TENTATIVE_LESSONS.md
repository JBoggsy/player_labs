# Heartleaf tentative lessons — session buffer

**Session started:** 2026-07-06 (lab created). This is THIS SESSION's lesson buffer.
Write candidate lessons here **as you go** — eagerly and noisily; most will be noise
and that's fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you write here
is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`heartleaf_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Heartleaf-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### Heartleaf ships a full behavior engine (`talking_villager`); "build a player" ≠ raw Sprite-v1 here
Evidence: `players/talking_villager/` (~3000 lines) already does perception → pathfinding
→ 8-verb semantic action layer → Bedrock LLM → chat; the 4 league players are that same
engine + different `soul.md`. Cheapest player path is a better prompt or a deterministic
decision layer, not a crewborg-style protocol build. Unlike Crewrift where crewborg decodes
Sprite-v1 itself.

### Heartleaf scoring makes guests a rivalrous shared resource — the game is coordination, not just gathering
Evidence: `score = hosted food × guests`; only hosts score, visitors score 0. With 9
gnomes, each guest at your table is denied to a rival host and is themselves not hosting.
Efficient gathering is necessary but the differentiator is recruiting a full table over chat.

### The heartleaf game repo is `coworld-incomplete` (certify not passing) — verify game version/league before relying
Evidence: README badge "coworld verify: failed"; repo topic `coworld-incomplete`;
COWORLD-REPO-STATUS note says certification blocked. Mirrors the freshness-preflight rule.
Status: league reported to exist but not confirmed via Observatory API this session.
