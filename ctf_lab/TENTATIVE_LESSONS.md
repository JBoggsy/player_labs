# CTF tentative lessons — session buffer

**Session started:** 2026-07-27 18:44. This is THIS SESSION's lesson buffer. Write candidate
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

### Human-curated POIs beat agent-seeded ones — and areas beat points for tactical vocabulary
Evidence: James's curation pass replaced my geometric seeds with tactically-load-bearing spots I
couldn't have named from code (vees, cover triangles, sneak gaps, diamond clearings), then rev 5
converted rallies/sneaks from points to AREAS and added red_/blue_lineup strips — formalizing the
exact "line up the troops" pattern observed in h035. The agent's job is the tooling + geometric
anchors (spawns, pedestals, chokes from config); the human names what matters tactically. Editor
QoL that mattered: mirror must swap red/blue in NOTES too, and rect-resize must anchor the
opposite corner (resize-from-center felt wrong immediately).

### A background agent with an empty branch after ~2h is a yellow flag — mandate incremental commits and check mtimes
Evidence: the staged-push agent's worktree showed zero commits past the branch point + clean tree,
but source mtimes 90 min old — ambiguous between "deep in the slow A/B tail" and "stuck/reset".
The brief said "commit as you go" but nothing enforced it. Cheap progress probes: git log on the
worktree branch, file mtimes, then SendMessage for phase/blockers/ETA. Next time: make incremental
commits an explicit success criterion and consider a mid-flight check-in requirement for agents
whose tail includes long waits (batch runs).

### Editor tooling pattern: serve the LAB root, not the tool dir — relative fetches escape http.server roots
Evidence: poi_editor.html fetches ../ctf/beacon/mapdata/points_of_interest.json; served from
ctf_lab/tools/ that path 404s (server root can't see above itself), served from ctf_lab/ it works.
Same trap will hit any future single-file tool that reads lab data files. Also: CSS grid bare 1fr
columns + number inputs = intrinsic-width overflow; minmax(0,1fr) + width:100% is the fix.
