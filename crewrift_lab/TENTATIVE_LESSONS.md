# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-01 15:16. This is THIS SESSION's lesson buffer. Write candidate
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

### An arrival deadband that can straddle an interaction rect edge is a permanent freeze
Evidence: H4 warehouse forensics (v82 league, 227 clean eps): 107/145 crewborg crew
standing-still penalties sat EXACTLY one pixel outside a 14x14 task-station rect —
`ARRIVE_RADIUS=4` lets the agent settle outside while `inside` (exclusive at x+w) stays
false, so the A-hold never starts and no d-pad ever fires again. Recurring at specific
croatoan stations (4, 7, 28, 34, 37) whose baked anchors sit near a rect edge. Fix =
nudge at the rect center (always > ARRIVE_RADIUS inside) when the navigate mask goes
dead within 24px of the station.

### "A stall the mode can react to" is a freeze unless some mode actually reacts
Evidence: action.py:179 returns hold-still on an empty route and the comment says the
mode can react — no crew mode ever did; 38/145 H4 penalties were exactly this park.
Same class as the recon-stall and WATCH-idle lessons: every idle path needs an owner
with a timeout escape (NormalMode now blocks the target after 100 stationary ticks).

### Verify an idle hypothesis' TIMING before designing a posture fix
Evidence: H4 was posed as "post-8th-task idling doctrine gap" — but 0/145 penalties
were post-8th-task (89 all-tasks-done seats took zero penalties; `_return_to_start`
walking works), 79/145 were ghosts, and all sat mid-assignment at a wedged station.
The cheap warehouse timing/position query redirected the fix from "post-task posture"
to "execution wedge + stall escape" before any build was spent.

### A frozen crew seat blocks the crew task-win and drags the game
Evidence: 12/173 v82 crew games had a >=2-penalty frozen crewborg seat: crew win 8.3%
vs 29.8% in clean games, mean length 12181 vs 6928 ticks — the unfinished tasks (alive
or ghost) make the task-completion win unreachable, so the game grinds until the
imposters kill out. Standing-still score (-1 each) is the SMALL part of the cost.

### H4 A/B result: stall escape + wedge nudge eliminates the crew freeze (44 penalties -> 1)
Evidence: matched crew-pinned A/B, crewborg:v82 (xreq_78d75331) vs crewborg-h4:v1
(xreq_038f4eef), 100 eps/arm, identical pinned Prime top-7 field, 2 imposters.
ss-penalties/g 0.454->0.010 (p=6.8e-13), frozen games 4->0, voted-out-as-crew
11.3%->2.0% (p=.0094, unpredicted bonus — likely the witness posture/no-freeze
reads less suspicious), tasks/g 6.62->6.43 (p=.53 noise), crew win 30.9%->25.0%
(p=.43 noise), survival 29.9%->34.0% (noise). Mechanism confirmed; win-rate lift
(expected ~1.5pp) unresolvable at this n. Report: crewrift_lab/docs/h4_experiment.html
(worktree); design + verdict pre-committed.
