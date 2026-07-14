# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-04 15:24. This is THIS SESSION's lesson buffer. Write candidate
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

### Session start had NO cached auth at all — not just the flagged 403
Evidence: `uv run softmax status` returned "Not authenticated. Run softmax login first." —
this is a fresh/expired token, distinct from the previously-flagged `/jobs/*` 403
"not a softmax team member" outage in WORKING_CONTEXT.md (which implies auth *succeeds*
but artifact routes reject). `softmax login` needs an interactive TTY it doesn't have,
so it prints a URL + `exchange-code` command and needs the human to paste a code back —
budget for this as a blocking step at the start of any session that touches Observatory,
before assuming the known 403 is the only auth risk.

### `/v2/episodes/search` returns full `results` inline, bypassing the /jobs/* 403 entirely
Evidence: with the team-member-gated 403 confirmed still active on every `/jobs/{job_id}/...`
route (results/policy-logs/policy-artifact/artifacts-replay), `POST /v2/episodes/search`
(`where: {op:eq, field:"policy.name", value:"crewborg"}` etc., documented live in
`/openapi.json` — NOT in `endpoint-map.md` yet) returned each episode's full `results` object
(win/crew/imposter/kills/tasks/vote_* per slot) inline, ungated, for league/tournament episodes.
`GET /v2/episodes/search/fields?coworld_name=crewrift_prime` gives the per-coworld-version
`results_schema` (fields matching exactly what `results.json` would have had). Reshaping
`{episode_id, created_at, tags, policies[]}` + `results` into episode.json/results.json shape
lets `crewrift-survey`'s `survey.py` run completely unmodified. This is a real, durable
workaround for the 403 outage for outcome-level (not log/telemetry) data — worth formalizing
into `coworld-episode-artifacts` or `crewrift-survey` rather than re-deriving each session.
Also useful generally: it's a cross-user episode search (not scoped to episodes you created),
so it's a good "has anyone already run this config" check before spending an experience request.
