# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-14 10:58. This is THIS SESSION's lesson buffer. Write candidate
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

### Discord multipart file uploads: em-dashes/section-signs in an inline `-F payload_json={...}` break the form encoding — pass `payload_json` from a file
Evidence: Sending the experimentation guide to Michael Smith, `curl -F 'payload_json={"content":"… — … §7 …"}'` returned 50035 PAYLOAD_JSON_INVALID; ASCII-only payload written to a file and sent as `-F 'payload_json=</tmp/payload.json;type=application/json'` (note `<`, not `@`) succeeded. Also: the first retry silently produced no output because `payload_json=<ifs/tmp/...` (typo'd redirect) is accepted by curl as a literal.

### The lab's experiment doctrine ports as a document: method (loop/diagnose/experiment/ab) + delivery system (layered AGENTS/best_practices, method-vs-binding skills, lessons pipeline) — the delivery system is the half outsiders miss
Evidence: Distilling player_labs for an external agent, all methodology content was reconstructible from 9 files (root AGENTS/best_practices + 4 skills + crewrift bindings); persona review's high-severity gaps were all "how does the agent RECEIVE this" (skill file format, session-state file shapes, jargon translation), not method gaps. Written up in docs/reports/experimentation-guide-2026-07-14.md.
