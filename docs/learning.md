# Learning and current working knowledge

Use [best practices](../best_practices.md) for supported methods and
[user preferences](../user_preferences.md) for working agreements. Documentation
states what is true and useful now; it does not accumulate session history.

## Where information belongs

| Information | Location | Contents |
| --- | --- | --- |
| Active work | `<lab>/WORKING_CONTEXT.md` | Current objective, authorized scope, unresolved constraints and next decision |
| Candidate guidance | `<lab>/TENTATIVE_LESSONS.md` | Unresolved hypothesis, applicable scope and evidence needed to decide it |
| Supported method | Root or lab `best_practices.md` | Current rule, rationale, limits and verification method |
| Mechanics and tools | Owning lab's reference/how-to docs | Implemented behavior, source links, usage and constraints |
| Deferred work | Root or lab TODO | Open task, practical reason and next action |

Replace resolved questions and superseded claims in place. Remove obsolete reports,
version logs and change narratives. Do not recreate an archive or link readers to
material that has been removed. A failed hypothesis should leave a useful current
constraint only when the evidence supports that constraint.

## Experiments and evidence

Before an experiment, state one falsifiable hypothesis, the baseline/candidate,
cohort, metric, stopping rule and cost. Inspect the result against that design and
report uncertainty honestly. Raw episode artifacts and machine-readable results
remain the evidence for analysis; do not turn them into a permanent documentation
history. Resolve active policy and game identities through the platform when needed.

Promote a lesson only when independent evidence or the implementation supports it.
Copied notes do not count as independent evidence. Keep one-off associations and
unverified causal claims tentative. Put shared methods at the root and game mechanics
in the owning lab. Remove obsolete guidance instead of appending a correction below it.

## Session behavior

Claude's [settings](../.claude/settings.json) use
[lesson_context.sh](../tools/lesson_context.sh) to point at current lab knowledge.
The startup hook is read-only. It does not rotate buffers, create dated archives,
commit files or require an end-of-session history entry.

Codex reads and updates current working knowledge explicitly. Avoid overwriting
another active session's work; use separate worktrees when concurrent tasks overlap.
The current user request defines authorization for actions and strategic changes.
