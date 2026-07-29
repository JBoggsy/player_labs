# Server-cooldown chat swallow fix — pre-registration (2026-07-29, loop-alpha L3)

**Registered BEFORE any arm fired.** Loop 3 of the improvement-loop alpha run.
Root-caused from the orchestrator's L1 carry-forward ("settle sent-vs-visible"):
the L1 "76 sent / 2 visible" push finding decomposed into (a) the warehouse 6/meeting
extractor blindspot (measurement, resolved in L1) and (b) THIS: a real, silent
server-side chat loss eating ~30% of our accusations.

## Hypothesis

**~30% of crewborg's meeting accusations are silently swallowed by the game server's
chat cooldown — dominantly because the once-per-game HS1 announce fires 1 tick before
the accusation — and un-swallowing them recovers the persuasion that L1 showed only the
FIRST landed accusation delivers.**

Mechanism, fully pinned:
- `sim.nim:addVotingChat` (game, ref 34a97a3): a chat within `MessageCooldownTicks=100`
  of the player's previous chat is dropped with NO feedback to the client.
- `modes/attend_meeting.py:decide()`: `_society_chat_intent` (HS1 announce) runs before
  the deterministic path; `_decide_crewmate`'s accusation then fires on the next tick
  via `_send_chat_intent` with NO cooldown check → swallowed.
- `strategy/meeting/context.py:CHAT_COOLDOWN_TICKS = 60` < the server's 100 — even
  cooldown-checked chats (share_read, pushes) can be swallowed.

## Evidence (L2's 300-ep fresh v116 baseline, telemetry `chat_sent` vs replay chats)

- 203/674 (30.1%) of believed accusation sends never appear in ground truth.
- The swallow is exactly the post-HS window: accusations ≤100t after the HS announce
  are swallowed **203/207 = 98.1%** (median gap 1 tick) vs 86/467 = 18.4% otherwise.
- HS1 announces themselves land 218/222 (the announce wins the race; the accusation loses).
- **Persuasion cost measured:** votes-on-our-target after a LANDED accusation 1.45
  (1.17 for on-imposter targets) vs 0.63 (0.36) after a SWALLOWED one.
- **Links to L1's dead expire path:** retime join share 50.3% when our accusation
  landed vs 20.6% when swallowed.

## The change (one lever, two coupled edits — both serving "the accusation must land")

1. `CHAT_COOLDOWN_TICKS` 60 → **104** (the server's 100 + margin) so every
   client-gated chat clears the server cooldown.
2. `_society_chat_intent` defers to the accusation: the HS1 announce fires only once
   the deterministic chat has gone out (`_deterministic_chatted`) or the meeting is
   ≥ 240 ticks old (fallback so silent-skip meetings still announce). The accusation —
   the persuasion payload — takes the first chat slot; the once-per-game HS1 announce
   (whose in-meeting timing has no measured value) follows after the cooldown.

No vote-path changes; imposter path untouched; LLM-off deterministic ordering only.

## Design

- **Probe:** `crewborg-chatfix:v1` (probe lineage — NEVER submitted) = v117's code
  (main HEAD incl. the vendored v5 weights) + the two edits; recipe = v117's exact
  recipe (v116's flags).
- **Cand arms:** 2×100 eps, Thread-1 pinned roster, slot 0, natural roles, sequential.
- **Baseline:** loop-3's step-1 v117 batch (3×100, same day/roster/recipe:
  `xreq_302b7740` / `xreq_6f72c3dc` / `xreq_a00fd378`). Ops-profile gate as usual.
- Ops-fail episodes excluded at the game level both sides.

## Pre-registered verdict criteria

**PRIMARY (both must hold):**
1. **Accusation landed-rate up:** believed accusation sends that appear in the replay
   ground truth ≥ 90% (baseline ~70%), and post-HS-window swallows ≈ 0 (measured
   identically: telemetry `chat_sent` vs replay chats; note the warehouse 6/meeting cap
   — count against RAW replay chat records when a meeting is chat-saturated).
2. **Votes-on-our-accused-target up:** mean other-player votes on our accused imposter
   target within the meeting > baseline (one-sided p < 0.05, per-accusation).

**MECHANISM (must fire):**
3. HS1 announce still lands ≥ 90% of crew games where it fires (the deferral must not
   kill the announce; society verified-member rate comparable to baseline).

**GUARDS (any failure disqualifies):**
4. Crew WR not worse beyond noise (2-sided p < 0.05).
5. Imposter WR untouched (within noise).
6. vote_timeouts 0; self-votes 0.
7. Mis-ejections-we-voted/cep ≤ 1.5× baseline (landed accusations recruit votes — they
   must not recruit onto crew: our accusation precision is the existing top_suspect gate).
8. Hits/crew-ep not down (the v117 refit gain must persist).

**Decision rule:** all pass → build `crewborg:v118` (v117 recipe + the fix),
confirmatory A/B vs v117 per the W5 pattern (fresh prereg BEFORE firing), then STOP
AND ASK James with the full gate table. Any PRIMARY/GUARD fail → NO-SHIP, close, next
loop. MECHANISM fail (HS broken) → fix or revert the deferral, one refire allowed.

---

## VERDICT

*(pending at registration)*
