---
name: cnw-bedrock-now-working
description: "Cue N Woo tournament-pod Bedrock is WORKING as of 2026-06-15 (reverses the prior 'no player pod has Bedrock' finding); LLM lift still unquantified"
metadata: 
  node_type: memory
  type: project
  originSessionId: 974bff52-7d92-49d3-b571-eddaad9f40a1
---

As of 2026-06-15 ~17:10Z, **Bedrock works on the Cue N Woo tournament pods** for
mentalist:v3 — reversing the previous session's settled conclusion that no player
pod had Bedrock access. Verified the disciplined way (success, not capability): the
5 most recent live league episodes (div_82c69031, today 17:07–17:10Z) all log
`LLM backend: bedrock, model us.anthropic.claude-haiku-4-5-20251001-v1:0` +
`bedrock ok in N.Ns (attempt 1)` on both propose and answer calls, ZERO
AccessDenied/marketplace/fallback, and emit real in-style Claude prose (not the
`"<Style> speaking…"` template). So the episode-runner IRSA role (tournament acct
583928386201) gained Anthropic marketplace access for haiku-4-5 between the v3
submit (job e942d273, which 403'd) and now.

**Why:** the entire LLM-writer half of the mentalist design is finally live in the
league for the first time; prior "no Bedrock" lesson is now stale.

**How to apply:** before re-asserting the old "no pod has Bedrock" claim, re-verify
against a FRESH episode log. Open thread: the leaderboard (mentalist v3 rank 3/3,
246.5 over 217 rounds) is a lagging average dominated by the fallback era — the LLM
lift is still unquantified. Next step: matched eval (real-LLM v3 vs fallback
baseline) or let fresh rounds wash out the old average. Related: [[cue-n-woo-lab]],
[[cnw-league-iam-hotfix]].
