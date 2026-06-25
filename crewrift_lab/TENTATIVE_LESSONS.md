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
