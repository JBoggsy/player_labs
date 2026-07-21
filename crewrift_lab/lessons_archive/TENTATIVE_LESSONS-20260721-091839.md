# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-15 12:09. This is THIS SESSION's lesson buffer. Write candidate
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

### A git pull after the SessionStart rotation can conflict on TENTATIVE_LESSONS.md — resolve by archiving the remote side, never by merging lessons into the fresh buffer

Evidence: 2026-07-15 pull aborted (hook-refreshed timestamps vs remote's session buffers),
then conflicted in all 5 labs. Four were timestamp-only (keep today's stamp). Crewrift's
remote side carried an unarchived lesson (methodology-import) that auto-merge would have
planted in THIS session's fresh buffer, corrupting the recurrence signal. Correct move:
`git show <remote-sha>:<lab>/TENTATIVE_LESSONS.md > lessons_archive/TENTATIVE_LESSONS-<remote-session-stamp>.md`
and keep the live buffer fresh — i.e. do by hand exactly what rotate_lessons.sh would have
done had the remote buffer been present at session start. rotate_lessons.sh's dedup guard
already anticipates the mirror image of this (a merge restoring an already-archived buffer).

### An A/B can root-cause from telemetry alone mid-run — check the extreme metric FIRST and kill the run early

Evidence: v106-vs-v100 A/B: at 200/100 eps the interim compare showed imposter_no_kills_rate
4%→44% (the loudest, most mechanistic metric). Grepping ONE zero-kill episode's telemetry
found strikes at victim "red" = crewborg's own color (slot 0). Corpus scan confirmed
(45/53 cand eps self-strike, 0/50 base). Killed the driver + cancelled the in-flight xreq —
saved ~200 episodes of redundant data. The target metric (crew win_rate) was noise; the
regression scan metric carried the entire story.

### "Benign no-op" claims about belief-state contents are load-bearing — audit every consumer before removing an entry

Evidence: v106's reveal ingestion dropped self from teammate_colors (correct in isolation;
the comment even argued "self in teammate_colors is inert; can't kill/vote self"). But
visible_victims() filtered ONLY by teammate_colors — self's presence there was an
ACCIDENTAL protection, and removing it made the imposter hunt its own sprite (win 71%→35%).
The inertness claim was checked against the meeting path, not the hunt path. When a fix
removes a set member, grep every `in <set>` consumer first.

### The self sprite is a pathological attractor for "most isolated visible player" heuristics

Evidence: select_victim prefers most-isolated-then-nearest; the self sprite is always
visible, always in kill range (dist ~6.3px), and reads as maximally isolated when alone —
so once eligible it wins victim selection almost every tick (111,568 self-strike events in
53 episodes, each kill_attempted with target_id=null). Any entity-choice heuristic over
visible_players needs an explicit self exclusion, not an incidental one.

### Platform 500 "Coworld Manifest tags Field required" kills BOTH create and get on /v2/experience-requests — even for completed requests

Evidence: 2026-07-15 ~15:55: POST /v2/experience-requests 500'd mid-A/B (pydantic validation
error INSIDE the server: manifest missing `tags`), and GET on xreqs that completed fine hours
earlier 500'd identically — so it's a serverside manifest-(re)parse bug (likely a coworld
redeploy adding a required manifest field), not a request-shape problem. `xp-request list`
still worked (doesn't parse the manifest) and showed the created-but-unfetchable xreqs
`pending`. Response: don't mutate the request body to chase it; babysit with retrying
fetches until the platform recovers, and report the bug.
