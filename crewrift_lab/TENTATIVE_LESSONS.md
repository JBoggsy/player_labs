# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-29 15:41. This is THIS SESSION's lesson buffer. Write candidate
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

## loop-alpha supervision, post-interruption recovery (2026-07-29)

- **A stopped/crashed loop runner costs nothing IF state lives in commits, not context** —
  the alpha run survived ~6 transient API drops plus a deliberate stop because every
  prereg, verdict, and version row was committed at the moment it happened. Recovery =
  `git log` + the prereg doc tail + a platform xreq listing; five minutes to full state.
  Codify for beta: "commit prereg/verdict/version_log BEFORE firing the next action" is
  not just epistemic hygiene, it's the crash-recovery mechanism.
- **Check the platform for already-completed arms before deciding anything post-interrupt**
  — the L4 extension arms (xreq_ccefecb2, xreq_de8408bd) fired and completed 100/100
  during the outage window; the data was bought and sitting there. An interrupted run's
  next step is often "analyze what already landed", not "refire".
- **`GET /v2/experience-requests` (limit=N) is the fast run-state x-ray** — one call maps
  every arm of a multi-loop run to completed/pending counts and timestamps; faster than
  reading any local notes for "what was actually in flight when it died".
- **Orchestrator-as-submit-gate worked**: verifying prereg-before-firing via git commit
  timestamps (32c7b48 < probe verdict 8785358 < confirmatory 2429104) is a cheap,
  unfakeable audit of the discipline before approving a submit.

---

## loop-alpha wrap: /tmp wipe recovery + v118 ship (2026-07-29)

- **Subagent transcripts are a recovery source for lost /tmp assets** — the runner's
  `verdict.py` (the only non-re-fetchable asset after the /tmp wipe) was recovered
  VERBATIM from `~/.claude/projects/<proj>/<session>/subagents/agent-*.jsonl` by
  extracting the Write tool_use payload. Same file yields every full xreq UUID and the
  exact build/verdict command lines — replayable end to end. Check the transcript
  BEFORE reimplementing anything a dead agent built.
- **Commit analysis instruments alongside their preregs** — episodes/warehouses are
  re-fetchable from the platform (~40 min for 900 eps); the instrument that scores them
  is not. Now codified in the beta spec: verdict scripts go to
  `crewrift_lab/tools/experiments/` in the same commit as the prereg.
- **The extension-pooling pattern closed cleanly**: significance miss at n=200
  (p=0.081) with all point estimates replicating → pre-registered 2-arm extension,
  pooled 4-arm analysis → p=0.0274 with every gate green. Two rules made it honest:
  the pooled analysis set was specified BEFORE arms 3–4 fired, and the miss branch
  ("2b misses again at pooled power → NO-SHIP, close") was written down first.
- **Re-fetched data reproduced the original instrument reads almost exactly**
  (votes-on-imp-target n=458 pooled vs 247+~211 expected; base numbers identical to
  the runner's tables) — platform artifacts + committed instruments = the analysis is
  reproducible from nothing but git + the API, which is the property that made the
  wipe a 40-minute inconvenience instead of a lost run.
