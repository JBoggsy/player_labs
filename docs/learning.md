# Learning and experiment records

Use [best practices](../best_practices.md) for durable method and [user preferences](../user_preferences.md) for durable choices. A historical session's permissions are not standing authorization.

## Where each record belongs

| Record | Location | Required content |
| --- | --- | --- |
| Current work | `<lab>/WORKING_CONTEXT.md` | Objective, scope, pinned identities, last observation, next decision; link detailed history |
| Candidate lesson | `<lab>/TENTATIVE_LESSONS.md` | Observation, proposed rule, scope, evidence, possible counterexample |
| Session history | `<lab>/lessons_archive/` | Preserve original evidence; copies are not independent recurrence |
| Experiment | Game's reports/experiment directory | Hypothesis, baseline/candidate IDs, cohort/config, metric, stopping rule, results, verdict, limitations |
| Uploaded artifact | Player's `version_log.md` | Immutable version UUID, source/build configuration, change and evaluation links |
| Parked work | [TODO](../TODO.md) or lab TODO | Concrete gap, reason deferred, evidence and next step |
| Promoted method | Root or lab `best_practices.md` | Narrow rule and supporting review; game-specific rules stay in the lab |

Maintain a short investigation ledger when debugging becomes circular: **hypothesis → separating check → observation → disproven/open → next check**. Keep negative and inconclusive outcomes. Update the experiment index when a result lands; a report nobody can find does not close the loop.

## Promotion rubric

1. Read actual observations and later outcomes. A polished assistant report alone does not prove the result.
2. Cluster equivalent claims; deduplicate copied buffers, inherited prompts, approval reviews and parent/child transcripts.
3. Promote recurring findings supported by separate investigations. State the narrowest scope the evidence supports.
4. Keep one-off, game-version-dependent and unverified causal explanations tentative. Record refutations explicitly.
5. Put process in shared practices; mechanics and tuning in game docs; human preferences in preferences. Do not copy whole transcripts or credentials.

The user authorized recurring supported promotions for the September 2026 modernization. Future reviews still check their current scope. The [transcript review](reports/learning-review-2026-09-14.md) records evidence and coverage, including findings we did not promote.

## Automation and portability

Claude's [settings](../.claude/settings.json) rotate active labs' buffers on a new session and run a stop reminder. Resume/compaction does not rotate. Rotation preserves archives and does **not** commit automatically; normal documentation audit and commit discipline applies. Hooks are not proof a lesson was recorded or reviewed.

Codex does not automatically run `.claude` hooks. Read context/buffers on startup and update records explicitly. Use separate worktrees for concurrent sessions: the shared buffer is not a multiwriter database. Never clear another active session's buffer. Archived labs retain history but do not collect automatic new lessons.

## Transcript research

The local `agent-transcripts` project owns ingestion and search. Refresh with its documented `pull_transcripts.py`, then use FTS and inspect actual user/assistant turns. Search globally as well as by repository: old/deleted worktrees often have no repository attribution. Track discovery separately from substantive review. Cite `source:session_id@seq`; check later correction and provenance before promotion.

Unchanged generated lesson templates are not archived on each startup. Rotation ignores only the generated timestamp when comparing the template; nonstandard or edited buffers remain preserved. Older template formats can be archived once rather than guessed to be empty.
