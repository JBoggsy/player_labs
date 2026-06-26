# Crewrift tentative lessons — session buffer

**Session started:** 2026-06-26 09:44. This is THIS SESSION's lesson buffer. Write candidate
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

### Commander in-pod disable is INFRA (Bedrock env absent), proven by env_seen — not eager-vs-lazy timing
Evidence: made client construction lazy (in-worker, live os.environ) + 20x retry + added env_seen diagnostic
to commander_started. Local: enabled:true, env_seen.USE_BEDROCK:true. In-pod (crewrift_prime XP, v59):
enabled:false, env_seen ALL false (USE_BEDROCK/CLAUDE_CODE_USE_BEDROCK/ANTHROPIC_API_KEY) on all 8 slots,
even after retries. So the lazy fix (candidate cause a) was RULED OUT; the Bedrock env genuinely isn't in
the player container (cause b). CREWBORG_LLM_COMMANDER (same secret-env path) DOES arrive → USE_BEDROCK is
special-cased/stripped by the platform to gate sidecar attachment, and the sidecar isn't attached for
crewrift_prime XP jobs now. Implies the meeting LLM is also currently disabled in these pods (the v50
enablement likely reverted; "TF reconciliation owed"). Lesson: an `env_seen` diagnostic on the LLM-enable
path turns an ambiguous "it's disabled" into a one-line infra-vs-code verdict — build it early. The lazy
construction is still kept (correct + matches meetings + handles genuinely-late env).

### CONFIRMED DIRECTLY: the meeting/chat LLM is ALSO disabled in-pod ("no LLM backend configured")
Evidence: v60 (both CREWBORG_LLM_COMMANDER=1 and CREWBORG_LLM_MEETINGS=1, --use-bedrock + USE_BEDROCK=true)
6-ep self-play batch on Crewrift Prime. 184 meetings -> 184/184 `domain.meeting_llm_fallback`
{reason:"llm_disabled", detail:"no LLM backend configured"}, AND commander_started enabled:false env_seen
all-false in the same pods. So the v50 "meetings working in crewrift_prime XP jobs" state has REVERTED — the
chat LLM currently never fires in these pods either. NOT a commander-specific issue: the Bedrock backend env
is simply absent for crewrift_prime experience-request player containers. Infra (re-enable + persist the
Bedrock sidecar for those jobs). The meeting LLM's existing `meeting_llm_fallback {detail}` trace already
reports this — no new code needed to check it; the commander's env_seen pins down WHY (env vars all false).

### ✅ FIX CONFIRMED: gate Bedrock on AWS_ENDPOINT_URL_BEDROCK_RUNTIME, not USE_BEDROCK (sidecar strips it)
Evidence: sidecar mode (kubernetes_runner) strips USE_BEDROCK + direct AWS identity from the player container
and injects AWS_ENDPOINT_URL_BEDROCK_RUNTIME + dummy creds. SDK bedrock_enabled() only checks
USE_BEDROCK/CLAUDE_CODE_USE_BEDROCK → wrongly "no backend" in-pod. Changed crewborg commander factory to OR-in
the sidecar endpoint as a Bedrock signal. In-pod (v62, xreq_5a87445f, Crewrift Prime): commander_started
enabled:true backend:bedrock env_seen{USE_BEDROCK:false, AWS_ENDPOINT_URL_BEDROCK_RUNTIME:true}, 672
commander_call outcome:ok, 0 errors, ~1.8s. So the sidecar IS deployed; only USE_BEDROCK was missing. The
meeting LLM still gates on USE_BEDROCK via the SDK → still dark in-pod; same one-line endpoint-gating fix
revives it. Platform/SDK fix still recommended (keep injecting USE_BEDROCK=true / SDK treat endpoint as signal)
so the documented --use-bedrock contract holds for all players.
