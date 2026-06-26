# Crewrift tentative lessons — session buffer

**Session started:** 2026-06-26 09:04. This is THIS SESSION's lesson buffer. Write candidate
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

### Local Gate-1 for crewborg REQUIRES `--run python -m crewrift.crewborg.coworld.policy_player`
Evidence: ran `coworld run-episode <crewrift-manifest> players-crewborg:dev` WITHOUT `--run`; the runner
applied the manifest's reference-player argv `/bin/notsus` to the crewborg image → `exec: "/bin/notsus":
no such file` (exit 127, connect_timeout on all 8 slots, scores all -100). crewborg's image CMD is
`python -m crewrift.crewborg.coworld.policy_player` but the supplied-image argv must be set explicitly via
`--run`. Matches the version-log convention (every entry passes the `--run` triple; v16: "after adding the
required --run override"). Status: re-running with `--run` added.

### Hardcoded `cow_` ids go stale; resolve crewrift by name instead
Evidence: `coworld download cow_50ee07cf` (the id recorded in WORKING_CONTEXT) → HTTP 422 Unprocessable.
`coworld download crewrift` (by name) succeeded → current `cow_52d06063-dfa8-45fc-9533-a5365a71a04d`.
Coworld ids rotate per build; the name resolves to the canonical current one. Don't trust a cow_ id pinned
in docs for local runs.

### Commander Gate-1 can exercise the LLM (unlike the meeting LLM)
Evidence: the cert/degenerate fixture has no Voting phase (so v47's meeting LLM was never hit locally), but
it DOES have a Playing phase — the gameplay commander runs during Playing, so a local run with
`--secret-env CREWBORG_LLM_COMMANDER=1 USE_BEDROCK=1` + temp Bedrock creds (`aws configure
export-credentials --profile softmax --format env`) actually fires the commander worker. Status: verifying.

### Phase-1 commander worker is observability-blind in-pod — add a trace/metric BEFORE any eval
Evidence: hosted 1-ep self-play crash test (xreq_6d62ac18, Crewrift Prime) completed clean (real game,
0 failed, 0 timeouts) but showed 0 `strategy_inferences` in-pod, vs 231–254/slot locally under
CREWBORG_TRACE=debug. Two confounders make in-pod firing UNKNOWABLE: (1) the SDK `strategy_inferences`
event isn't in crewborg trace groups `decision,action,voting`; (2) worker.py does `except Exception:
continue` with NO trace/metric, so a silent Bedrock 403 (the known XP-pod issue) is indistinguishable
from "fired fine." Lesson: a swallow-and-continue worker MUST emit a success/failure counter+trace, or
you cannot tell a working LLM from a dead one in production. First Phase-2 task: commander_decision /
commander_error trace+metric (latency, fired/fallback). Confirmed working LOCALLY (direct Bedrock via temp
softmax SSO creds); in-pod confirmation deferred to that tracing.

### `--use-bedrock` upload flag is NOT enough — also pass `--secret-env USE_BEDROCK=true`
Evidence: v55/v56 uploaded with `--use-bedrock` + `CREWBORG_LLM_COMMANDER=1` but NO `USE_BEDROCK` env →
in-pod `commander_started` traced `{enabled:false, disabled_reason:"no LLM backend configured"}` on all 8
slots. SDK `players.player_sdk.llm.bedrock_enabled(env)` only checks truthy env vars
`_BEDROCK_ENV_NAMES=("USE_BEDROCK","CLAUDE_CODE_USE_BEDROCK")`; the `--use-bedrock` CLI flag wires the
sidecar endpoint but does NOT set that env var. The working meeting LLM (v50) was uploaded with
`--use-bedrock` + `USE_BEDROCK=true` + `CREWBORG_LLM_MEETINGS=1` — the explicit env is the actual enable.
Fix: v57 adds `--secret-env USE_BEDROCK=true`. Applies to ANY crewborg LLM feature (meetings or commander).

### The commander observability paid off on its very first in-pod run
Evidence: before the trace, in-pod looked like "0 strategy_inferences, unexplained." After adding
`domain.commander_started` (+ call/applied), the first v56 episode immediately showed
`enabled:false, disabled_reason:"no LLM backend configured"` — diagnosing the USE_BEDROCK misconfig in one
shot. Lesson confirmed: instrument the async LLM worker's connect/enable BEFORE trusting any eval; a silent
client-disable is indistinguishable from "fired fine" without it.
