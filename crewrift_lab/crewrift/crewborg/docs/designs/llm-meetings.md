# LLM meetings — lighting up the dormant meeting brain for the hosted league

**Status:** implemented (2026-06-25). Companion to
[`../../design.md` §10.3–10.5](../../design.md), which documents the *current* meeting
machinery this builds on. Read that first. This doc records the **delta** that makes
the LLM meeting path actually run in the Crewrift league.

**The problem, in one paragraph.** crewborg already has a complete, tested LLM meeting
brain — `strategy/meeting/{llm,schema,context}.py` + `modes/attend_meeting.py`: call
cadence, a pydantic `MeetingDecision` schema (`send_chat / set_tentative_vote /
submit_vote / wait`), trust-boundary validation, deterministic fallback, full tracing,
and fake-client unit tests. But it has **never run in a league.** Its only client is
direct-Anthropic (`from anthropic import Anthropic`, gated on `ANTHROPIC_API_KEY`), and
there is **no Bedrock branch**. The hosted league runs players with `--use-bedrock`
(IRSA role, *no* API key), so as deployed the client resolves to `DisabledMeetingClient`
and the mode silently falls back to the deterministic path. No version v16–v31 ever set
`CREWBORG_LLM_MEETINGS`. The image already installs `players[bedrock]` (boto3) and the
Dockerfile *claims* Bedrock support — a doc/code mismatch this design closes. "Adding LLM
meetings" therefore means **lighting up the dormant seam**, primarily by adding a Bedrock
backend, plus per-role prompts and a deliberate latency/correctness plan.

## Decisions (recorded — James, 2026-06-25, via the ux.link decision page)

1. **LLM owns chat + vote, fully** — legal-target validation and the hard self-vote
   guard stay (correctness), but no confidence-gated vote downgrade. (§3)
2. **Both roles at once, each with its own prompts/instructions.** (§2)
3. **Bedrock backend via the SDK's `players.player_sdk.llm` helpers.** (§1)
4. **Prompts as external editable `memory/*.md` files.** (§2)
5. **Latency: keep the call synchronous; tune the timeout and the existing guards.** (§4)
6. **Process: this design doc first**, then implement on approval.

---

## 1. Bedrock backend (`strategy/meeting/llm.py`)

The single load-bearing change. Reuse the SDK seam rather than hand-rolling a second
client (matches "reuse before add"): `players.player_sdk` exposes `bedrock_enabled`,
`select_client`, `resolve_model`, `call_json`, and `extract_json_object`.

- **Client construction.** `build_meeting_llm_client_from_env` wraps SDK helper import,
  backend detection, model resolution, and `select_client(use_bedrock=..., timeout=...)`.
  Construction **must never raise** — on any failure the factory returns a
  `DisabledMeetingClient` and the mode keeps the deterministic fallback.
- **Enable logic** (`build_meeting_llm_client_from_env`). Today: `CREWBORG_LLM_MEETINGS`
  truthy **and** `ANTHROPIC_API_KEY` set. New: `CREWBORG_LLM_MEETINGS` truthy **and**
  (`bedrock_enabled(env)` **or** `ANTHROPIC_API_KEY` set). `bedrock_enabled` reads
  `USE_BEDROCK` / `CLAUDE_CODE_USE_BEDROCK`, which `--use-bedrock` sets at upload.
- **Call path.** `AnthropicMeetingClient.decide` calls SDK `call_json(...)` and parses
  the returned text with `extract_json_object(...)`; the local response/usage/JSON
  extraction helpers are gone.
- **Model.** Default to the Bedrock inference-profile id when on Bedrock, the direct id
  otherwise, via `resolve_model(use_bedrock=..., direct_model=..., bedrock_model=...,
  explicit=env.get("CREWBORG_LLM_MODEL"))`:
  - Bedrock: `us.anthropic.claude-haiku-4-5-20251001-v1:0`
  - Direct: `claude-haiku-4-5-20251001`
  - **Constraint (load-bearing):** the hosted IRSA role can invoke **haiku-4-5 but not
    opus** (opus → Marketplace 403 every episode). Do not default to or document opus.
- **Local vs hosted.** Local Gate-1 runs pass `--use-bedrock` to `coworld run-episode`
  (or set `ANTHROPIC_API_KEY` for the direct path); both now exercise a real LLM.

`MeetingLLMConfig` carries the resolved model, backend flag, timeout, trace options,
and prompt override directory.

## 2. Per-role prompts (`strategy/meeting/memory/`)

Today a single `SYSTEM_PROMPT` constant serves both roles. Split into two, stored as
**external markdown** (suspectra's pattern — tune voice/doctrine without a code edit,
clean git diffs):

- `strategy/meeting/memory/crewmate.md`
- `strategy/meeting/memory/imposter.md`

`prompts.py` loads the file for `context["self"]["role"]` at decide-time (cached after
first read; the package dir is on `PYTHONPATH` and copied into the image by the existing
`COPY crewborg ...`). Override path via `CREWBORG_LLM_PROMPT_DIR` for experiments. If a
file is missing, fall back to a baked-in minimal constant (never crash a meeting).

**Crewmate doctrine (must preserve the v25 win).** v25's crew gain came from vote
*restraint* — the fitted suspicion model votes only at P≥0.9, and the league leader wins
crew by barely voting players; loose accusing is negative-EV crew. The crewmate prompt
must encode: *default to skip; accuse/vote only on concrete, citable evidence; never
invent cues; defend yourself when wrongly accused; do not pile onto thin bandwagons.* The
serialized context already carries the suspicion ranking and the deterministic fallback
vote — the prompt instructs the model to treat a low-confidence field as skip.

**Imposter doctrine (the conversion lever).** The imposter gap is *conversion* — engineer
mis-ejections and survive meetings. The imposter prompt encodes: *never out a teammate
(`self.teammates` is in context); deflect onto a plausible non-teammate; bandwagon onto a
crewmate already taking heat with safe, in-format fabricated cues; defend a teammate
under suspicion without over-committing; skip when no deflection is safe.*

Both prompts share the hard contract (JSON-only `MeetingDecision`, legal vote targets,
ASCII ≤ `CHAT_MAX_CHARS`), factored into a small shared preamble so the two files hold
only role doctrine.

## 3. Full vote authority (`strategy/meeting/schema.py`, `attend_meeting.py`)

Per decision 1, the LLM owns the vote. The existing `validate_meeting_decision` already
enforces only legal targets (no dead/illegal color) — **no confidence-gated downgrade is
added.** Retained, non-negotiable:

- **Legal-target validation** — `vote_target` must be a live, votable color or `skip`.
- **Hard self-vote guard** — `attend_meeting._submit_vote_intent` forces `skip` if the
  resolved target is our own color, whatever the model says.
- **Deadline safety** — the 48-tick auto-submit of the tentative vote still fires so we
  never eat the −10 vote-timeout.

**Risk acknowledged:** full vote authority on the *crew* side is the main way this could
regress the v25 restraint win. The mitigation is doctrinal (§2 crewmate prompt: skip
unless near-certain), and it is **measured** (§7 splits crew vote behavior: votes-at-crew,
own-ejection rate, team crew-ejections). If the eval shows crew regression, the fallback
is a crew-only confidence gate — but we do not pre-impose it.

## 4. Latency — keep synchronous, tune and verify

The LLM call is a blocking SDK `call_json` on the meeting fast path. Meetings freeze
movement/combat, so a bounded blocking call there is acceptable (and respects the
avoid-async rule), but Bedrock in-cluster latency plus this lab's vote-timeout DQ history
make it a correctness concern. Implementation:

- Keep the existing cadence guard (`LLM_MIN_CALL_INTERVAL_TICKS=12`) and the
  `AUTO_SUBMIT_REMAINING_TICKS=48` deadline guard.
- Keep the conservative timeout default at `CREWBORG_LLM_TIMEOUT_SECONDS=3.0`.
- Convert the configured timeout to meeting ticks and refuse to start any LLM call unless
  it can return, with margin, before the auto-submit window.
- Make the deadline trigger win over `new_chat` / `chat_cooldown_ready`, and suppress
  further LLM calls after the deadline prompt fires.
- Timed-out/failed calls still degrade via `_decide_after_llm_failure`.
- **Verify, don't assume:** the `meeting_llm.latency_ms` histogram already exists; read
  it in Gate-1 and the eval. Threaded execution is a deferred fallback only if measured
  latency proves the sync path can't make the deadline.

## 5. Runtime config & enablement

- Upload with `--use-bedrock` and env `CREWBORG_LLM_MEETINGS=1` (plus the standard
  trace/metrics env). The default Bedrock model is
  `us.anthropic.claude-haiku-4-5-20251001-v1:0`; override with `CREWBORG_LLM_MODEL` if
  needed. Keep `CREWBORG_CHAT_NLP` as-is (the deterministic fallback still uses it).
- Image: no Dockerfile change needed (boto3 already present via `players[bedrock]`); fix
  the stale Dockerfile comment only if it overstates current behavior.
- New env knobs: `CREWBORG_LLM_PROMPT_DIR` (prompt override), existing `CREWBORG_LLM_*`.

## 6. Tests (`tests/test_meeting_modes.py`, `tests/test_meeting_llm.py`)

- **Backend selection** (unit, env-driven, no network): `build_meeting_llm_client_from_env`
  returns a Bedrock-backed client when `USE_BEDROCK=1`, a direct client when only
  `ANTHROPIC_API_KEY` is set, and `DisabledMeetingClient` when neither / flag off. Use a
  fake `select_client` or assert on the resolved model + `use_bedrock` flag (don't hit AWS).
- **Per-role prompt routing**: crewmate role loads `crewmate.md`, imposter loads
  `imposter.md`; missing file falls back to the baked constant; `CREWBORG_LLM_PROMPT_DIR`
  override respected.
- **Full vote authority**: an LLM `submit_vote` with a legal target casts it directly
  (no confidence downgrade); an illegal/self target is rejected/guarded to skip.
- **Latency guard**: deadline prompts win over late chat, and a late external chat inside
  the danger window does not start a blocking call that could miss auto-submit.
- Keep the existing fake-client cadence/deadline tests green.

## 7. Evaluation plan (the loop's measure step)

Upload as a new version (LLM-on, Bedrock) and A/B **role-decomposed** against the current
deterministic champion (the `crewrift-ab` skill), matched roster/roles/count, fresh window:

- **Imposter arm** (the conversion thesis): mis-ejections engineered, meeting survival,
  win rate, kills held flat. This is where the LLM should pay off.
- **Crewmate arm** (the regression guard): votes-at-crew/g, own-ejection rate, team
  crew-ejections, crew win rate — must not regress v25's restraint gains.
- **Ops/latency**: `meeting_llm.latency_ms`, fallback rate, zero vote-timeouts.

Gate-2 (league submission) only on a clean, role-decomposed win and James's go-ahead.

## 8. Open questions / risks

- **Crew vote authority** could erode the restraint win (§3) — measured, with a crew-only
  confidence gate as the named fallback.
- **Bedrock latency** in-cluster is unmeasured for this call site (§4) — Gate-1 + eval
  resolve it; threaded path is the escape hatch.
- **Prompt iteration cost**: external files make tuning cheap, but prompt changes are
  behavior changes — re-eval after non-trivial prompt edits, don't ship on vibes.
- **Cost/usage**: haiku, short max_tokens, throttled cadence — bounded, but watch the
  `usage` trace on the first hosted batch.
