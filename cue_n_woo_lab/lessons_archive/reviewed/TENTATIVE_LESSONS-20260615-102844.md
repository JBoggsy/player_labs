# Cue-n-Woo tentative lessons — session buffer

**Session started:** 2026-06-15 10:05. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`cue_n_woo_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Cue-n-Woo-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### REVERSED 2026-06-15: tournament-pod Bedrock is now WORKING for mentalist:v3 — the prior "no player pod has Bedrock" finding no longer holds.
Evidence: Pulled the 5 most recent live league episodes (today 17:07–17:10Z, div_82c69031, mentalist v3). All 10 policy_agent logs show `LLM backend: bedrock, model us.anthropic.claude-haiku-4-5-20251001-v1:0` + `bedrock ok in N.Ns (attempt 1)` on BOTH propose and answer calls. ZERO AccessDenied / marketplace-Subscribe / fallback across all logs. Answers are real in-style Claude prose ("Threshold stone worn smooth by countless passages through seasons."), not the `"<Style> speaking…"` template. So the episode-runner IRSA role (tournament acct 583928386201) gained Anthropic marketplace access for haiku-4-5 sometime between the v3 submit (job e942d273, which 403'd) and now. Verified the disciplined way — grepped for the SUCCESS log line, not capability/coherent-looking output.
Status: CONFIRMED. Caveat: leaderboard rank 3/3 (246.5 over 217 rounds) is a lagging average dominated by the fallback era; real-LLM episodes only just started. LLM lift still unquantified — next: matched eval real-v3 vs fallback baseline, or let fresh rounds wash out the old average.

### Hook commands in .claude/settings.json must use absolute paths via $CLAUDE_PROJECT_DIR, never repo-root-relative paths
Evidence: All four lesson-lifecycle hooks (SessionStart rotate_lessons.sh ×2, Stop lessons_stop_nudge.sh ×2) used bare relative paths like `crewrift_lab/tools/lessons_stop_nudge.sh`. The Stop hook fired with cwd != repo root and failed `sh: ...: No such file or directory` (exit 127). Claude Code does not guarantee hooks run from the repo root; it injects `CLAUDE_PROJECT_DIR` (absolute, available in SessionStart + Stop) for exactly this. Fix: wrap each command as `"$CLAUDE_PROJECT_DIR/<path>"`. The scripts' own `REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)` then resolves correctly because they receive an absolute argv[0].
Status: Fixed 2026-06-15. SessionStart hooks shared the same latent bug (worked only because cwd happened to be repo root at startup).
