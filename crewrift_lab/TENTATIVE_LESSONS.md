# Crewrift tentative lessons — session buffer

**Session started:** 2026-06-25 13:06. This is THIS SESSION's lesson buffer. Write candidate
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

### GROUNDED: post-kill RE-APPROACH is the gap — Aaron closes onto crew (144→64px), crewborg holds ~156px (2026-06-25)
Followed the data (multiple hypotheses, each tested) instead of asserting. (a) v44-vs-v45 (self-report removed) is NOISE: kills 1.69 vs 1.63 Welch p=0.54/MWU 0.74; win 83% vs 73% chi2 p=0.12 (CIs 74-89 vs 64-81 overlap). So self-report was neutral — thread closed. (b) WHERE we kill: SAME as Aaron — ~400px from home, in task rooms (Science Bay/Storage/Med Bay), only 5-10% near home; NOT farming the re-gather point. Crew density AT the kill: crewborg DENSER (1.64 vs Aaron 1.39 other crew within 220px) — kill setup fine, refutes over-isolation. Post-kill distance to nearest living crew: both ~150px at kill+10t, but **Aaron CLOSES to 64px by kill+200t; crewborg HOLDS at 156px**. So crewborg doesn't flee (no jump) AND doesn't re-approach — it sits ~150px out (just out of clean view → the earlier 4% crew-in-view post-kill vs Aaron 18%), can't line up a 2nd kill until a MEETING re-gathers everyone. ROOT CAUSE: **post-kill RE-APPROACH** — after a kill our Search picks a RANDOM nearby room to watch instead of going to the crew right there; Aaron moves onto the nearest crew. FIX: after a kill, beeline to the nearest known crew (close the ~150px gap), i.e. extend Recon's "go to nearest crewmate" across the whole post-kill cooldown, not just the last 100t. NOT voting, NOT kill location, NOT victim isolation, NOT fleeing — re-approach.

### REVERTED v46 (crew-aware Search room-pick): significant REGRESSION, and my mechanism was BACKWARDS (2026-06-25)
v46 made _pick_room target the room with the most recently-seen crew (instead of random). A/B vs v44 (100 eps each, Prime): kills 1.69→1.11 (Welch p<0.001), win 83%→64% (chi2 p=0.004), 0-kill 3→20. SIGNIFICANT regression — reverted (git revert f78f8a4; 364 tests pass; _pick_room back to random sweep). I asserted the cause was "densest crew room = more witnesses → can't get unwitnessed kills." James made me VERIFY it — the data REFUTED it and showed the OPPOSITE: v46 room_entries/g 15.4→8.5 (moved LESS, not to crowds), crew-within-220px 2.14→1.41 (near FEWER crew), alone-when-ready 43%→59% (MORE isolated). So the change made crewborg less mobile + more isolated; the OLD random sweep's high mobility (15 room-changes/g) was what kept it near crew by covering ground. LESSONS: (1) the post-kill re-approach fix must be SURGICAL to the post-kill moment, NOT a rewrite of general room-picking (the random sweep was load-bearing via mobility). (2) METHODOLOGY (banked to game-agnostic best_practices, strengthened): I asserted a causal mechanism 3× this session and was refuted by one query each time, the last one BACKWARDS — no causal claim without the falsifying query. NEXT (verify first, don't assert): what made the random sweep keep us near crew — is mobility the lever? Test a surgical post-kill "go to nearest single crewmate" that PRESERVES the sweep otherwise.
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

### Local Gate-1 can't exercise the LLM meeting path — the cert fixture has NO Voting phase
Evidence: ran `coworld run-episode` on the crewrift cert config with `--use-bedrock --secret-env CREWBORG_LLM_MEETINGS=1`;
clean Lobby→Playing→GameOver, artifacts written, 0 errors (liveness PASS), but the trace `domain.phase_change`
events showed it NEVER entered `Voting` — the degenerate self-play cert fixture has no meeting. So the LLM
meeting call (the whole point of the change) was not exercised locally at all. How to apply: Gate-1 stays
liveness-only for meeting features; verify "the LLM actually fires" via an EXPERIENCE REQUEST (look for
`meeting_llm_decision` events + `meeting_llm.latency_ms` + zero `meeting_llm_fallback` in the artifacts). To
force a meeting locally you'd need a real game variant (`coworld play --variant` / an episode_request.json
with a real game_config), not the cert default.

### Gate-1 footguns: local↔live coworld drift, and the `/bin/notsus` default-command trap
Evidence: (1) local `coworld` 0.1.20 could not even PARSE the current crewrift 0.1.59 manifest
(`game.config_schema.properties.tokens must declare equal minItems and maxItems`) — fixed correctly by
upgrading the runner (`uv lock --upgrade-package coworld` → 0.1.26), not by working around it. (2) Supplying
your image to `run-episode` without `--run` makes the runner launch the MANIFEST's baked reference-player
command (`exec /bin/notsus` → "no such file" in a crewborg image). Must pass `--run python --run -m --run
crewrift.crewborg.coworld.policy_player` — ONE token per `--run` flag (a single space-containing `--run`
string is rejected with a message that spells out the right form). `smoke.py`'s argparse `--run` chokes on
`--run -m` (reads `-m` as a flag), so use `run-episode` directly for multi-token argv + `--use-bedrock`.

### Uncommitted worktree work is fragile — but the built Docker image is a faithful code+docs backup
Evidence: my entire LLM-meetings change was uncommitted in a git worktree (`personal_labs-wt`) when that
worktree dir was deleted out from under the session (shell cwd recovered to $HOME). No loss in the end because
(a) James had merged the work into `personal_labs` main first, and (b) the built image `players-crewborg:dev`
contains the WHOLE crewborg package — the Dockerfile `COPY crewborg /app/crewrift/crewborg` includes
`docs/`, `version_log.md`, and all source — so the image is a recoverable snapshot of code+docs. I confirmed
v47's provenance by `md5`-comparing six key files INSIDE the image against merged main (all identical). How to
apply: commit/merge before destructive worktree ops; treat the latest built image as a fallback backup for
crewborg; and when a build's source state is uncertain, hash image files vs the repo to pin down exactly what
shipped (don't assume — verify).

### LLM meetings: gating fixed (USE_BEDROCK secret-env) but BLOCKED by invalid Bedrock creds in XP-request pods (403) (2026-06-26)
First real test of the LLM meeting seam (v48/v49, round-robin natural roles vs Aaron+Andre). Verified via crewborg telemetry (policy_artifact_N.zip → telemetry.jsonl; the stdout policy_agent_N.log is ~empty, just "game over"). TWO layers found by NOT assuming Bedrock worked: (1) v48 `--use-bedrock` alone → every meeting `domain.meeting_llm_fallback reason=llm_disabled "no LLM backend configured"`. ROOT: attend_meeting.py:44 calls build_meeting_llm_client_from_env() on os.environ; llm.py:117 passed (CREWBORG_LLM_MEETINGS=1 is a --secret-env, reaches the process) but llm.py:123 fired because helpers.bedrock_enabled(os.environ) was False — **`--use-bedrock` does NOT inject USE_BEDROCK into the player PROCESS env** (it wires Bedrock at the policy/routing layer); the meeting gate reads the in-process env var. FIX (worked): also pass `--secret-env USE_BEDROCK=true` (and CLAUDE_CODE_USE_BEDROCK=true). (2) v49 with that → gate enabled, context serialized, call attempted, but `domain.meeting_llm_fallback reason=llm_call_failed error=PermissionDeniedError 403 "The security token included in the request is invalid"` (12/12). So the XP-request pod's AWS/IRSA creds are INVALID for Bedrock — infra/IAM, not crewborg code (cf. CnW league IAM hotfix; CnW Bedrock verified only from TOURNAMENT pods). IMPLICATION: LLM meetings can't be validated via Crewrift experience requests until those pods get Bedrock creds; may only work in league/tournament pods (gated submit). crewborg LLM code is complete + correctly wired. NOTE: the v48 100-ep results (imp 78%/1.53 vs Aaron 2.05/Andre 2.13) are the DETERMINISTIC version — LLM never ran.

### Bedrock 403 root cause: we hit AWS DIRECTLY, not the localhost sidecar — AnthropicBedrock ignores AWS_ENDPOINT_URL_BEDROCK_RUNTIME (2026-06-26)
James asked "are we targeting localhost for Bedrock? we should be." We are NOT. Traced via metta (read-only): the platform runs a loopback Bedrock SIDECAR and, when enabled, injects into the app container `AWS_ENDPOINT_URL_BEDROCK_RUNTIME=http://127.0.0.1:<port>` + DUMMY aws creds (sidecar re-signs with the real identity). TWO gaps, both must close: (1) CODE: players SDK `llm.select_client(use_bedrock=True)` returns `AnthropicBedrock(timeout=...)` with NO base_url; AnthropicBedrock (anthropic 0.107.1) resolves endpoint = base_url arg → `ANTHROPIC_BEDROCK_BASE_URL` → else `https://bedrock-runtime.<region>.amazonaws.com`. It IGNORES `AWS_ENDPOINT_URL_BEDROCK_RUNTIME` (that's the botocore var; the Anthropic SDK builds its own AWS URL). So even WITH the sidecar, our client bypasses localhost, signs with the DUMMY creds, hits real AWS → "403 security token invalid". FIX: pass base_url from AWS_ENDPOINT_URL_BEDROCK_RUNTIME (belongs in SDK select_client; crewborg llm.py bridge as interim). (2) INFRA: for Crewrift XP-request jobs the sidecar wasn't even attached — dispatcher.py sets USE_BEDROCK=true itself only when `COWORLD_GAME_BEDROCK_ENABLED` (resolve_game_bedrock) AND `BEDROCK_SIDECAR_ENABLED` AND coworld in `BEDROCK_COWORLD_ALLOWLIST` (empty=all). v48 platform did NOT set USE_BEDROCK → game-Bedrock is OFF for these jobs. No sidecar → no localhost endpoint. So the code fix is necessary but NOT sufficient; the sidecar must be enabled for Crewrift XP-request jobs (platform config) too. Files: metta app_backend/job_runner/{dispatcher.py:223,448-457; bedrock_sidecar_wiring.py:150-163; bedrock_enablement.py:16-37; config.py:87,108}.
