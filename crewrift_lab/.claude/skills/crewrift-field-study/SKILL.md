---
name: crewrift-field-study
description: "Use to run a fresh, field-wide cross-policy study on Crewrift — every policy, not just crewborg — that pulls a multi-hundred-episode batch (split across the 100-episode-per-request cap), optionally cross-checks against the existing suspicion_lab historical corpus, and validates any cheap/regex detector against the event-warehouse's LLM-based suss job. Triggers: 'run a field study', 'compare all policies not just crewborg', 'field-wide chat/vote/outcome analysis', 'historical cross-check', 'validate a detector against the LLM labeler', 'pull N00+ fresh episodes for a study'. Packages the process (and the gotchas that cost real time) from the 2026-07-02 chat-accuracy-effectiveness study."
---

# Crewrift Field Study

The recipe for a **field-wide** (all-policies, not crewborg-specific) empirical study built on a
fresh Coworld data pull plus this lab's existing infra — as opposed to `crewrift-survey`/
`crewrift-event-warehouse` (crewborg-vs-field diagnosis) or `crewrift-experiment` (one hypothesis
about crewborg's own behaviour). Worked example, with all tools live:
`crewrift_lab/chat_effectiveness/` (design: `crewrift_lab/docs/designs/2026-07-02-chat-accuracy-effectiveness-design.md`;
findings: `crewrift_lab/crewrift/crewborg/docs/reports/2026-07-02-chat-accuracy-effectiveness.html`).

**Announce at start:** "Running a field study — resolving the roster, pulling episodes, then building/validating the analysis."

## Workflow

1. **Resolve the roster by pinning champions, not `top_n`/`random`.** As of 2026-07-02 those
   selectors hit a real server-side 500 (a query timeout on the champion-ranking join).
   `uv run python crewrift_lab/chat_effectiveness/tools/resolve_champion_roster.py --division <div_id> --top-n <seats> --num-episodes 100 --out /tmp/req.json`
   resolves the top-N players' current champion `policy_ref` labels via `coworld results`/
   `coworld memberships --active-only` and writes a ready-to-POST pinned-roster body. `--top-n`
   must equal the game's seat count (Crewrift = 8) — the API requires one roster entry per seat.
2. **Split anything over 100 episodes into sequential requests.** `num_episodes` caps at 100/request
   (undocumented until this study). Create N requests via `coworld-experience-requests`' `experience_request.py create`, one per 100-episode chunk.
3. **Stream artifacts with `--no-artifacts --no-logs`** unless the study genuinely needs per-agent
   telemetry zips or policy logs. Those are large and are the actual failure point — two live
   `fetch_artifacts.py --watch` processes crashed on `ReadTimeout` fetching them before this flag
   combo was added. `--watch` is crash-safe/resumable either way (relaunch the same command).
4. **Verify the expander against ONE fresh replay before the full pull.** Check for
   `"complete":true` in the `trace_complete` event and a sane event-key inventory (chat, vote_cast,
   vote_called_body/button, died, kill present) — cheap insurance against silent version/button
   skew. `crewrift_lab/chat_effectiveness/tools/expand_episodes.py --episodes <dir> --expand-replay <bin> --out <dir>`
   expands a whole downloaded batch and reports a failure count; a nonzero count on a fresh pull
   means re-check the expander before trusting any of it.
5. **The event-warehouse's `chat_suss` (LLM-labeled chat) keys episodes by `episode.json`'s
   internal `id`, NOT the directory-stem join key this lab's tools (`replay_parse.py`,
   `suspicion_lab`, this skill's own tools) use everywhere else.** Any join against `chat_suss` needs
   an id→stem remap first (`crewrift_lab/chat_effectiveness/tools/validate_detector.py`'s
   `build_episode_id_map` is the reference implementation) — without it you get a silent 0-row
   join, not an error.
6. **For a historical cross-check, audit the corpus before trusting it's uniform.** Not every
   scraped batch has the full 4-file set (`episode.json`+`replay.json`+`replay.json.z`+`results.json`)
   — the most recent batch in a corpus is often an interrupted/partial scrape.
   `crewrift_lab/chat_effectiveness/tools/build_historical_subset.py --corpus <corpus dir> --expanded <expanded dir> --out-corpus <dir> --out-expanded <dir> --limit <N>`
   builds a bounded, verified (symlinked) subset instead of assuming the whole corpus works.
7. **Spot-check a suspiciously uniform aggregate before reporting it.** A flat 0.0% (or 100%)
   across every row is this lab's standing tell for a tooling artifact, not a real finding — it
   caught a real bug this way (`replay_parse.py`'s per-meeting `ejected_slot` silently never set,
   because the meeting-closing `phase` event and the `died` event land on the same tick and process
   in the wrong order for the `is None` guard). When it happens in shared, read-only code, fix it
   locally in your own analysis code (derive from the raw event list instead) rather than patching
   the shared file, and record the bug as a lesson so the next consumer doesn't repeat it.
8. **Report both datasets, never blended.** Fresh pull = current meta; historical corpus = larger n
   but older policy versions. State both n's and let the reader see whether they agree.

## Integration

**Uses:** `coworld-experience-requests` (roster/xreq creation), `coworld-episode-artifacts`
(streaming download), `crewrift-event-warehouse` (the `suss` LLM-labeling job for detector
validation). **Pairs with:** `crewrift-survey` for a fast crewborg-vs-field pass first, to decide
whether a full field study is warranted. **Not for:** a single-hypothesis test about crewborg's own
behaviour — that's `crewrift-experiment`.
