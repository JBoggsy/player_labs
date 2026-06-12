# Tentative-lessons archive

One file per past session's lesson buffer, rotated here **automatically** by the
SessionStart hook (`crewrift_lab/tools/rotate_lessons.sh`) — the live buffer is
always `../TENTATIVE_LESSONS.md`. Reviewed buffers move to `reviewed/`.

Review cadence: ≈weekly via the **`/lessons-review`** skill — it clusters lessons
that RECUR across these independent session buffers (the graduation signal),
proposes promote/keep/cull, and graduates keepers to `best_practices.md` on the
human's call. A Stop hook (`tools/lessons_stop_nudge.sh`) nudges the agent once
per session if substantive work ends with an untouched buffer.
