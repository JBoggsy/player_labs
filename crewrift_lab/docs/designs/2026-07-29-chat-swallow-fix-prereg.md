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

## VERDICT (2026-07-29): **NO-SHIP per the pre-registered rule — GUARD-7 exceeded its bar.** Mechanism decisively fixed; the guard failure is marginal and carries to a NEW, powered prereg (L4).

Cand = `crewborg-chatfix:v1` (`714cbd59…`, identity 200/200), arms `xreq_7c2ba7bd` +
`xreq_5ca6fda7` (200 eps, 0 ops; 155 crew / 45 imp). Baseline = loop-3's fresh v117
batch (300 eps, 0 ops; 215 crew / 85 imp). Analysis `/tmp/loop3/verdict.py` + the
sim-acceptance instrument below.

**Instrument correction (pre-verdict, applies to PRIMARY-1's wording):** raw replay
bytes contain even server-DROPPED chats — `server.nim` `writeChat`s every client
message *before* `addVotingChat` applies the cooldown filter — so "appears in the
replay file" is not visibility. The honest instrument is re-applying `addVotingChat`'s
acceptance rule (≥100t since our last *accepted* chat) to the believed send stream;
the warehouse `chat` partition stays capped at 6/meeting (L1 finding) and undercounts
both arms.

| criterion | cand (chatfix) | base (v117) | verdict |
|---|---|---|---|
| PRIMARY-1 accusations accepted by the server | **413/413 = 100%** | 554/680 = 81.5% | ✅ (bar ≥90%) |
| PRIMARY-2 votes-on-our-imposter-target per landed accusation | **1.12** (n=228) | 0.94 (n=343) | ✅ MW 1-sided p=0.025 |
| MECH-3 HS1 announce accepted / member verification | 100%; known_member 194/200 eps | 100%; 283/300 | ✅ |
| GUARD-4 crew WR | **34.2%** | 30.2% | ✅ (directionally up, p=0.42) |
| GUARD-5 imposter WR | 64.4% | 70.6% | ✅ within noise (p=0.47) |
| GUARD-6 vote_timeouts / self-votes | 0 / 0 | 0 / 0 | ✅ |
| GUARD-7 mis-ej-we-voted/cep | **0.181** | 0.116 | ❌ **FAIL — bar was ≤0.174 (1.5×)**; fisher p=0.098 NS |
| GUARD-8 hits/cep | 1.406 | 1.377 | ✅ not down |

**Honest read.** The fix does exactly what it claims — zero swallowed accusations, +19%
votes recruited onto our true-imposter targets, crew WR +4pp directional, and the L3
baseline independently confirms v117's refit gains persist (hits/cep 1.377 vs v116's
1.030). But louder accusations recruit onto our *wrong* targets too (~20% of our
accusations hit crew), and the mis-ejection guard tripped its point-estimate bar
(0.181 > 0.174; 28/155 vs 25/215 eps, p=0.098 — underpowered). Per the registered
decision rule — any guard failure disqualifies — **NO-SHIP**. No post-hoc gate
adjustment.

**Disposition:** the L3 verdict stands. The guard failure is a noisy point estimate on
a mechanism that measurably works; a NEW pre-registered, powered test (L4) is the
correct next step — registered separately BEFORE its arms fire, pooling pre-specified.
