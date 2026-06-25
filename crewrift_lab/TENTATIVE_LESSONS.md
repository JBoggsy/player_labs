# Crewrift tentative lessons — session buffer

**Session started:** 2026-06-25 13:09. This is THIS SESSION's lesson buffer. Write candidate
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

### crewborg's LLM meeting seam is fully built but DORMANT — and its only client is direct-Anthropic, not Bedrock
Evidence: `strategy/meeting/{llm,schema,context}.py` + `modes/attend_meeting.py` implement a complete
LLM meeting brain (cadence triggers, pydantic decision schema, trust-boundary validation, deterministic
fallback, tracing, fake-client tests in `tests/test_meeting_modes.py`). BUT `llm.py:88-90` only constructs
`from anthropic import Anthropic` (direct API) and `build_meeting_llm_client_from_env` (llm.py:127-142)
returns `DisabledMeetingClient` unless `CREWBORG_LLM_MEETINGS=1` AND `ANTHROPIC_API_KEY` are set. The hosted
league runs `--use-bedrock` (IRSA, NO api key) → the client would be disabled → silent fallback to the
deterministic path. No version v16–v31 ever set `CREWBORG_LLM_MEETINGS`, so the LLM has NEVER run in a league.
Doc/code mismatch: `coworld/Dockerfile` installs `players[bedrock]` (boto3) and its comment claims the meeting
LLM "can route through AWS Bedrock when uploaded with --use-bedrock" — but llm.py has no Bedrock branch.
Status: this is the load-bearing gap to close to actually "add LLM meetings." Reuse `players.player_sdk.llm`
(`select_client`/`bedrock_enabled`/`resolve_model`/`call_json`) or copy cue_n_woo `mentalist/writer.py`'s
dual-backend `_build_client`. Model: `us.anthropic.claude-haiku-4-5-20251001-v1:0` (IRSA can call haiku, NOT opus).
Status update: IMPLEMENTED 2026-06-25 (Bedrock backend via SDK helpers, per-role `memory/*.md` prompts,
timeout-derived deadline guard). 367 tests pass, ruff clean. Not yet built/uploaded/evaluated.

### `codex exec resume` does NOT inherit the initial `-C` working dir — it edits wherever the shell cwd is
Evidence: launched a codex review with `-C <tmp worktree>` for isolation, but the `resume` (implementation)
turn ran from the real repo root (shell cwd had reset), and since `resume` rejects `-C`, codex edited the
REAL working tree, not the isolated worktree. The codex-task skill's worktree isolation was silently bypassed.
Outcome was fine here (changes landed where I wanted + validated with the real toolchain), but it could have
been a surprise. How to apply: when isolation matters, `cd` into the worktree before EVERY `codex exec resume`,
or verify file_change paths point at the worktree, not the live repo.
