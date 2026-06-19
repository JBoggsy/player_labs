---
name: cnw-recall-player-champion
description: "Cue N Woo — no-LLM phrase-recall player (recall_player) qualified and is competing (rank ~6/10); the league DQ was a phase-wedge bug, not strategy"
metadata: 
  node_type: memory
  type: project
  originSessionId: 974bff52-7d92-49d3-b571-eddaad9f40a1
---

**Current Cue-n-Woo direction (2026-06-19): a NO-LLM player.** James asked to
stop using our own LLM. `cue_n_woo_lab/recall_player/` is a zero-LLM,
instant-turn bot using **planted-recall**: ask the judge a probe that forces a
fixed-shape reply, then commit that reply verbatim as our secret answer — it
matches the judge's own interview transcript (which is in its scoring context),
so it reads as "the judge's own words." Policy name `mentalist-recall`. This
supersedes the LLM-based `mentalist_v4` / axis-combo direction in
[[cnw-axis-combo-rewrite]] for now.

**The league DQ was a BUG, not strategy (the key lesson).** v1/v2 kept getting
`disqualified/inactive` (timeouts) in the live league despite passing isolated
XP races. Root cause found via mirror-match logs: the in-flight "pending" guard
outlived its phase — after the 3rd probe we held `pending="ask"` waiting for
`me.judge>=3`, but the proposals-phase state arrives with `me.judge` lagging, so
the guard never cleared, the propose was blocked, the global phase stalled, and
we timed out inactive (-100). Isolated fast-judge races never reproduced it
(the lag window only opens under league load). **Fix (v4):** track
`_pending_phase`; drop the guard the instant the server's phase advances past
the action's phase. ALWAYS clear a "did my action appear in my own view" guard
on phase advance — the server's per-slot view lags across phase boundaries.

**Status after the fix:** v4 is `competing/champion` (membership/policy-slot
flag) in div_82c69031 (Competition); live leaderboard **rank ~6/10**, now ABOVE
softmaxwell (gabby's owner) at #7. Goal is division #1 (Andre Jr ~365; gap ~44).
"champion=True" is the membership flag (our active version), NOT division #1.

**Strategy evolution:** digit-recall (jordan clone) → phrase-recall (v4) →
**self-referential SIGNATURE exploit (v6), copied from the live #1 outbounds.**
Digits are character-NEUTRAL so they lose to gabby's evocative phrase. v5 (force
gabby's register + reuse one phrase) REGRESSED 0/6 (rigid template → generic
phrases that collide with gabby's and lose the crispness tiebreak; one-phrase
reuse removed v4's diversity hedge). v4 stayed champion.

**The #1 exploit (v6, the real edge):** outbounds doesn't just plant a phrase —
it plants a LABELED signature in the interview ("record your X SIGNATURE"), then
AUTHORS its proposal questions to reference it ("Earlier you recorded your X
SIGNATURE... reproduce that exact phrase = ____") and answers with it. The judge
sees its own recorded keyword in BOTH the question and the secret → picks it
~1.00 DETERMINISTICALLY (3×1.00/episode). v6 copies this verbatim (label "CORE
SIGNATURE"): live v6-vs-outbounds = [330,330]×3 dead-even tie (both rig their own
half to 1.00, halves cancel, blind half is a symmetric coin-flip); v6-vs-gabby
[440,220] win. **The top of the board is a symmetric self-reference equilibrium:**
everyone running the rig ties everyone else running it and beats everyone who
doesn't. v6 SUBMITTED (sub_76437fe2, lpm_2b2bce6b) with James's OK; qualifying.
To break the tie for SOLE #1, the only lever left is the blind half (winnable?
open question). Validator must use the game's CHARACTER token count `ceil(len/4)`,
not words. Related: [[cue-n-woo-lab]], [[cnw-axis-combo-rewrite]], [[cnw-bedrock-now-working]].
