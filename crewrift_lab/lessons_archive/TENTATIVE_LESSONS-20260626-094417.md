# Crewrift tentative lessons — session buffer

**Session started:** 2026-06-26 09:25. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`crewrift_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Crewrift-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### Crewrift movement velocity is NOT diagonally normalized — pressing two axes is √2× faster, and crewborg already exploits it
Evidence: sim.nim `applyPlayerMovement` (d9f6b30, lines ~3020-3042) integrates velX and velY
INDEPENDENTLY — each axis accelerates by `Accel=76`/tick toward `MaxSpeed=704` with its own
friction (`144/256`). No vector normalization. So holding up+right drives both axes to 704,
giving diagonal speed √(704²+704²) ≈ 995 (~41% faster than one axis). crewborg's
`_movement_mask` (action.py:86) sets horizontal and vertical d-pad bits independently via two
`_axis_input` calls, so it presses both whenever the target is off-axis → it gets the diagonal
speed boost for free. Nav A* is 8-connected (`_FORWARD` includes diagonals, nav.py:72) and
string-pulls to arbitrary-angle waypoints, so most legs are diagonal.
Status: documented behavior, confirmed against pinned sim source; not a bug.
