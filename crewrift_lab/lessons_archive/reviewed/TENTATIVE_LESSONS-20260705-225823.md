# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-05 16:57. This is THIS SESSION's lesson buffer. Write candidate
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

### zsh does NOT word-split unquoted variables — building arg lists as strings silently breaks repeatable flags
Evidence: built `ARGS="$ARGS --episode $id"` in a loop then called `fetch_artifacts.py $ARGS
--elevated ...` (this repo's shell is zsh, not bash). argparse errored "unrecognized arguments"
with the ENTIRE `$ARGS` blob dumped verbatim — `set -x` showed zsh had passed it as ONE quoted
word, not split into separate tokens like bash would. Fix: build a real array
(`ARGS=(); ARGS+=(--episode "$id")`) and expand with `"${ARGS[@]}"`. Cost ~15 min of confused
retries assuming the (perfectly fine, actually-repeatable) `action="append"` argparse flag was
broken. Applies to ANY script here built with a loop + string-concat + unquoted expansion.

### crewborg's meeting-LLM is told the WRONG vote threshold (0.8 hardcoded vs 0.6 actually deployed)
Evidence: built a 49-episode/5-round warehouse (`/tmp/crewborg_wh`, latest 5 crewrift_prime
rounds, 2026-07-05) and compared crewborg to the batch's crew-win leaders. crewborg's crew vote
ACCURACY (64.3%, 28 votes) and chat engagement (2.51 msgs/g, 100% spoke) both beat or matched the
leaders (forgeling-focusfire 62.5%/2.11, daveey-prime-notsus 50.0%/1.89) — but crewborg's real
VOTES/game (0.72) and skip-rate (67.8%) were far worse than the leaders' (~2.0 votes/g, ~0% skip).
Root cause pinned via telemetry: 59/152 (39%) of crewborg's LLM skip-vote decisions in this batch
explicitly reasoned "No suspect above vote threshold (0.8)" (verbatim, from
`decision.reason` in the `policy_artifact` telemetry.jsonl `domain.meeting_llm_decision` events)
— several against suspects at/near the REAL bar (e.g. 0.59). `strategy/meeting/context.py`
(`_fallback_vote_reason` L103, `_suspicion_payload` L219) surfaces the legacy hardcoded
`VOTE_PROBABILITY = 0.8` (`strategy/suspicion.py:150`) to the LLM, but the actual operative bar
for the fitted-weights CREWMATE path is `WEIGHTS_VOTE_PROBABILITY` (`suspicion.py:226`,
env-tunable via `CREWBORG_VOTE_PROBABILITY`, = 0.6 per the current ship recipe) — the two are
different constants and only the second one is what `top_suspect()` (`suspicion.py:643`) actually
checks. The LLM's own prompt is therefore reasoning against a bar ~0.2 higher than the system is
tuned for.
Status: FIXED 2026-07-05 — added `active_vote_probability_bar(self_role)` to `suspicion.py` as the
single source of truth (`top_suspect()` and `context.py`'s `_fallback_vote_reason`/
`_suspicion_payload` all call it now instead of either constant directly); 610 tests pass, ruff
clean. Not yet built/uploaded/A-B'd.

### AGENTS.md's process model changed mid-session (pull) — re-read it after ANY origin/main sync, not just at session start
Evidence: this session started, did substantial work, THEN the human said "I brought us up to date
with origin/main" — the pulled `AGENTS.md` had flipped from a Gate-1-smoke-test loop to an explicit
**speed-first** model ("no smoke tests, no pre-upload gate, no test-first discipline... run a unit
test only when it's the fastest way to answer a specific question you already have, never as a
routine step"). I didn't re-read AGENTS.md after the sync and invoked the `test-driven-development`
skill (full RED/GREEN cycle) for the vote-bar bugfix immediately after — not wrong in outcome (it
happened to be the fastest way to PROVE the exact mechanism, which the new rule actually allows),
but the wrong reflex: a mid-session "brought us up to date" / "pulled" / "merged" statement is a
signal to re-read the durable process docs (AGENTS.md, WORKING_CONTEXT.md, user_preferences.md)
before continuing, the same as a fresh session start would.

### The SHARED meeting-LLM prompt actively told the LLM to cite raw ticks — a per-role prompt fix alone wouldn't have worked
Evidence: James asked to stop both meeting LLMs (crewmate + imposter) from citing exact tick values
in chat, in favor of room names + relative timing. The per-role prompt files
(`strategy/meeting/memory/{crewmate,imposter}.md`) don't mention ticks at all — the actual source was
`strategy/meeting/prompts.py`'s `_COMMON_PROMPT` (concatenated before EITHER role file), which said
"Prefer specific, game-grounded speech (names, rooms, **ticks**, who-was-where)". Editing only the
role files would have left this instruction live and fighting the new rule. Lesson: when a prompt
lives in multiple layers (common + role-specific), grep the WHOLE prompt-assembly path
(`system_prompt_for_context` → `_COMMON_PROMPT` + `_role_prompt`) for the term you're trying to
change, not just the file that seems most relevant.

### Imposter vote-rate gap (33% skip vs notsus 4%) traced to the LLM anchoring its OWN vote on the suspicion-probability bar
Evidence: warehouse query confirmed crewborg imposter skip-rate 33.3% vs notsus's 4% (n=10 games).
Telemetry `decision.reason` text showed the imposter LLM reasoning like a truth-seeking crewmate
("no one hits the 0.8 threshold, so skip") rather than a deceiver riding social pressure — the
existing deterministic bandwagon mechanism (`strategy/meeting/imposter.py:bandwagon_target`,
already correct) was never surfaced as the model the LLM should imitate. Fixed via
`memory/imposter.md`: explicit "don't accuse first → bandwagon onto the first crewmate anyone else
names → cite evidence if you have it → actually vote, not just chat" doctrine, plus an explicit note
that the suspicion/vote_probability_threshold numbers are for picking a deflection target, not a bar
the imposter's OWN vote needs to clear. Not yet built/uploaded/A-B'd — same as the crew vote-bar fix.

### Reporting "implemented and tested" to the user is NOT the same as committing — verify git status before moving on
Evidence: the vote-bar fix and the imposter-bandwagon/tick-avoidance prompt changes were both
reported to James as done, with tests passing, earlier this session — but neither was ever actually
`git commit`ed at the time. They sat as uncommitted working-tree changes through the entire
design/planning/SDD-implementation phase that followed (several hours, 7+ new commits on top),
one `git clean -fdx` or careless `git checkout .` away from silent loss, and only surfaced when an
SDD task-review subagent's `git status` incidentally showed them as "modified" alongside a
same-named file (`imposter.py`) a different task had just touched. Lesson: after implementing +
testing a change and telling the human it's done, `git commit` it in the same breath — don't let
"the tests pass" substitute for "the work is durably saved." Especially true right before starting
a different multi-step thread (like a design/planning session) that will run for a long time on top
of an assumed-clean tree.

### Swapping a feature-generating function underneath an already-fitted model is a train/serve skew risk a per-task review structurally cannot see
Evidence: the chat-evidence consolidation replaced social_evidence.py's regex chat-stance tally with
chat_evidence.py's dependency parse — same field names (`accusations_made`/`times_accused`/
`times_defended`), same PlayerRecord counters, so every per-task reviewer correctly signed off (the
counters still increment on the same triggers, tests pass). But those three fields are LIVE features
in the already-trained `suspicion_weights.json` — the weights were fitted against the regex's
statistical distribution (first-match-only, narrow DEFEND_HINT vocabulary), and are now being served
dependency-parse-generated values with a different distribution (one claim per color mention, a
wider defense vocabulary including "good"/"sure"/"with", zero on spaCy-unavailable games) — a real,
silent skew between what the model learned and what it now sees at inference time. Only the FINAL
whole-branch review caught this, because no single task's diff shows "this field feeds an
already-fitted model trained on a different generating function" — that context only exists at the
level of the whole feature. Lesson: when a plan changes what PRODUCES a value already consumed by a
trained model (not just adding new fields), flag it explicitly as a train/serve-skew risk during
design, not just correctness — a per-task reviewer verifying "does the counter still increment
correctly" will always miss it, by construction.
