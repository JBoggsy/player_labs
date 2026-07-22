# Chat-provided evidence → suspicion posterior, weighted by speaker trust

**Status:** designed + implemented 2026-07-22 (W3). Probe `crewborg-chatev:v1`; A/B verdict
recorded at the bottom.

James's directive (verbatim): *"we should be trusting HS member accusations and evidence
highly. I'm not sure how we currently handle chat-provided evidence, but we should have a
way of incorporating chat-provided evidence into our own beliefs, weighted based on our
suspicion level of the speaker. Given that we totally trust HS members to be crew, we
should naturally weight their evidence highly. If we don't have a high-quality, consistent,
and reliable mechanism for incorporating chat-provided evidence, this subagent should make
that happen."*

---

## Part 1 — AUDIT: what consumes other players' chat today

Every path that reads other players' chat, and where (if anywhere) it touches the
suspicion posterior:

### 1.1 `strategy/meeting/chat_evidence.py` — the unified extractor (layer 1)

The spaCy dependency-parse extractor (design `crewrift/crewborg/docs/designs/chat-evidence.md`,
shipped ~v101). `parse_claims()` turns one `ChatEvent` into `ChatClaim`s with
`claim_type ∈ {accusation, defense, location, vent, task}`; `verify_claim()` checks
location/vent/task claims against our own witnessed events
(`confirmed`/`contradicted`/`unconfirmed`). Consumers:

- `chat_accusers()` → **imposter bandwagon targeting only** (`strategy/meeting/imposter.py`).
- `accused_colors()` → **our own outgoing chat** (chat-implied fallback vote; instant-vote).
- `apply_llm_tags()` → LLM `chat_evidence` tags → `ChatClaim(source="llm")` appended to
  `PlayerRecord.claims`.

### 1.2 `strategy/social_evidence.py` — the per-tick orchestrator

`_count_chat_stances()` calls `parse_claims` per new message and banks:
`accusations_made` (speaker), `times_accused` / `times_defended` (target), plus every claim
onto `PlayerRecord.claims`. Also votes, speaking order, meeting caller, watched completions.

### 1.3 `strategy/suspicion.py` — does chat reach the posterior?

**Yes, but only barely, only on one path, and with zero speaker weighting:**

- On the **fitted-weights path** (the production path), `_fitted_features` feeds the chat
  counters into the logit: `times_accused` **+0.1288**/instance, `times_defended` −0.5075,
  `accusations_made` +0.1127 (data/suspicion_weights.json, trained 2026-07-05). So a chat
  accusation moves the posterior by ~+0.13 log-odds — near-nothing (the prior logit is
  −0.92 at 8p/2imp; the vote bar needs +3.1).
- On the **legacy hand-model path** (`CREWBORG_SUSPICION_WEIGHTS=0`), chat contributes
  **exactly zero** — `_evidence_log_lr` reads only witnessed/vent/body/follow/tail events.
- The Honor Society pin (`society_trusted` → logit floored at `prior − WITNESSED_LOG_LR`)
  is the only chat-derived signal with real posterior force — and it is **exculpatory
  only, about the speaker themselves**. An HS member's *accusation of a third party*
  carries no more weight than anyone else's.

### 1.4 `strategy/meeting/chat_nlp.py` — the spaCy lifecycle

Background-loads `en_core_web_sm` (~1.5–2 s hosted), gated by `CREWBORG_CHAT_NLP`
(default on). `parse_claims` returns `[]` while loading/failed.

### 1.5 The LLM path (`strategy/meeting/context.py`)

`_chat_payload` serializes the full meeting `chat_log` into every meeting-LLM call. The
LLM's *judgment* of that chat shows up as its chat/vote decisions — but nothing it reads
is retained as belief. Its optional `chat_evidence` tags land in `PlayerRecord.claims`
(see 1.1) and then… nothing.

### 1.6 `strategy/honor_society.py`

HS1 verified announcements → `society_trusted` → (a) the posterior pin in `_recompute`,
(b) `vote_veto` (spare trusted members from posterior votes; witnessed overrides). The
liar sweep + cross-game `honor_distrust.json` guard against trusting proven liars. T8
(2026-07-22) validated the whole channel live: veto 20/20 accurate, members verified
188/199 eps — **the trust signal is real and reliable**; it just isn't used to *weight
their testimony*.

### 1.7 What's inconsistent / unreliable / missing (the audit verdict)

1. **No speaker-trust weighting anywhere.** An imposter spamming "X sus" bumps
   `times_accused` exactly as much as an HS-verified member reporting a witnessed kill.
   This is precisely the field's fabrication pattern: the 851-game chat study found
   imposter accusations are fabricated with concrete-but-safe cues and that
   evidence-styled accusations land 64% of votes — the field *weaponizes* unweighted
   listeners.
2. **Claim severity is ignored.** "saw X kill Y" — direct hearsay testimony of the
   near-certain event class — scores the same +0.13 as a bare "X sus". There isn't even a
   kill-testimony claim type; worse, the parser mis-handles the dominant kill templates
   (measured: `"saw red kill blue"` accuses *both* red and the victim blue;
   `"red killed blue"` parses to *nothing* — both colors within 2 tokens of "killed" get
   victim-flagged).
3. **Path inconsistency.** Chat evidence exists only under the fitted weights; the legacy
   path (and any weights-load failure) silently plays chat-deaf.
4. **`PlayerRecord.claims` + `verify_claim` verification are dead weight.** Banked,
   never read by any scorer. A `contradicted` self-alibi — we *watched* them somewhere
   else — currently changes nothing.
5. **spaCy-gated with a counted-before-parsed hole.** `_count_chat_stances` marks a
   message counted *before* parsing; if the model is still loading (or failed), the
   message is dropped forever. And with `CREWBORG_CHAT_NLP=0` there is no chat evidence at
   all, even for trivially-parseable templates.
6. The layer-1 design doc itself deferred exactly this: *"Speaker credibility/trust
   scoring … the follow-on 'layer 2' design."* This is that layer.

---

## Part 2 — the mechanism (layer 2)

### 2.1 Shape

One new pure function, `chat_evidence_log_lr(belief, color, trust_of) -> float`, in
`strategy/suspicion.py`, added into the logit in `_recompute` **on both scoring paths**
(fitted and legacy) — this is a belief-layer feature, identical with the LLM on or off.
It reads the **already-banked** `PlayerRecord.claims` (spaCy-, template-, and LLM-sourced
alike): the layer-1 storage finally gets its consumer.

```
logit(target) = base_logit(target)                     # fitted or legacy, unchanged
              + clamp( Σ_speakers trust(s) · Σ_types max_claim_lr(s, type, target),
                       CHAT_EVIDENCE_LR_MIN, CHAT_EVIDENCE_LR_MAX )
```

- **Per (speaker, claim_type) dedup by max**: a speaker repeating "X sus" ten times
  counts once (anti-spam; mirrors the legacy path's max-per-type discipline and
  `chat_accusers`' distinct-speaker discipline). Independent speakers stack.
- **Trust scaling** `trust(s) ∈ [0, 1]`:
  - `1.0` — `s ∈ society_trusted` (HS-verified, not a ledgered liar): *"we totally trust
    HS members to be crew."*
  - `0.0` — `s` is a witnessed imposter, a known teammate (imposter role), unattributed
    (`speaker_color=None`), ourselves (our own chat is derived from evidence we already
    hold — counting it would double-count), or the claim's own target (self-referential
    stances are handled separately, §2.3).
  - otherwise `1 − P(imposter | s)` from the **previous tick's posterior**
    (`belief.suspicion`) — deflection-likelihood scaling: at the 8p/2imp prior a stranger's
    testimony carries ×0.71; a half-suspected player's ×0.5; a player we're near-certain
    on ~×0. Using the prior tick breaks the trust↔suspicion circularity (one-tick-lag
    fixed point; evidence persists so it converges).
  - Read-time weighting means a speaker *later* caught venting retroactively zeroes
    their past accusations — fabrication self-destructs on exposure.

### 2.2 Per-claim base log-LRs (hearsay, graded by severity)

| claim about target | base log-LR | rationale |
|---|---|---|
| `kill` (new type: "saw X kill Y", "X killed Y") | `+log(30) ≈ 3.4` | testimony of the near-certain event class, degraded to hearsay: T8 measured the honest HS liar-witness misattributing kills in 6/199 episodes — even a fully-trusted witness is ~3%/ep fallible, so this must NOT be `WITNESSED_LOG_LR` |
| `vent` ("X vented") | `+log(8) ≈ 2.1` | matches the legacy vent-dwell weight; vents are easier to misread than kills |
| `accusation` (bare "X sus", "vote X") | `+log(1.5) ≈ 0.41` | weak: the fabrication-prone class; ~3× the fitted `times_accused` weight when fully trusted |
| `defense` ("X is clear/safe") | `−log(2) ≈ −0.69` | matches the fitted `times_defended` scale |
| self-alibi with `verification == "contradicted"` | `+log(4) ≈ 1.39` **on the speaker** | we watched them somewhere else — caught-in-a-lie; the only place the (previously dead) verification output is consumed |

### 2.3 The cap — chat is hearsay, never witnessed

`CHAT_EVIDENCE_LR_MAX = log(40) ≈ 3.69`, `CHAT_EVIDENCE_LR_MIN = −log(8) ≈ −2.08`.

- At the 8-player/2-imposter prior (logit −0.92), one fully-trusted HS kill-report gives
  logit ≈ 2.5 → **P ≈ 0.92: it clears the 0.9 vote bar on its own** (James: trust HS
  evidence highly — actionable), but sits far below witnessed P ≈ 1 (log-LR 13.8) and
  **can never override** a witnessed catch, the HS pin, or the definitional floors.
- An untrusted stranger's bare accusation: 0.71 × 0.41 ≈ +0.29 → P moves 0.29 → 0.35.
  Ten strangers piling on saturate at the cap only if ~9 distinct speakers all accuse —
  and the cap still holds the ceiling at 0.94.
- A **witnessed-imposter speaker moves us 0.** The negative cap keeps coordinated
  "X is clear" chatter from clearing an actual imposter below the prior by much (the HS
  pin is the legitimate clearing mechanism, and it requires cryptographic verification).

### 2.4 Extraction upgrades (extend, don't duplicate)

In `chat_evidence.py`:

- **New `ClaimType` `"kill"`** with victim disambiguation.
- **A deterministic template pass** (`_template_claims`) that runs *before* and
  *independent of* spaCy — anchored, high-precision regexes for the field's dominant
  templates: `saw X kill Y` / `X killed Y` (kill), `saw X vent` / `X vented` (vent),
  `vote X` / `X (is) sus` / `X (is the) imposter` (accusation). This is NOT the old crude
  regex tally (which matched a color + hint anywhere in the line); each template is
  anchored to the color token. The spaCy pass still handles free-form messages, negation
  scope, defenses, and place claims; template-produced (target, type) pairs are deduped
  from its output.
- **Loading-window fix**: `_count_chat_stances` no longer marks a message counted while
  the spaCy model is still *loading* — it defers the whole message to a later tick
  (chat_log persists), so early-meeting chat is parsed once ready instead of dropped
  forever. `disabled`/`failed` states proceed template-only.

### 2.5 Consistency + flag

- Same mechanism regardless of LLM on/off: the term lives in `_recompute`, which both the
  deterministic vote (`top_suspect`) and the LLM context (`suspicion` payload, players
  prose, fallback vote) already read. LLM-sourced claims (`apply_llm_tags`) flow through
  the identical scoring.
- **`CREWBORG_CHAT_EVIDENCE`** (default **ON**, `=0` kills): the whole term is one gated
  addition; OFF reproduces today's behavior byte-for-byte.
- Known small overlap, accepted deliberately: the fitted counters `times_accused`/
  `times_defended` (±0.13/−0.51) still fire alongside the new term. Removing them means
  refitting the weights (out of scope, same posture as layer 1); the overlap is ≤4% of
  the new term's scale.

### 2.6 Tracing

`domain.chat_evidence_applied` — emitted once per meeting at vote-submit time with the
actual vote target vs the no-chat-evidence counterfactual
(`top_suspect` recomputed with the chat term zeroed), plus each live target's chat term.
This is the A/B's mechanism metric: how often chat evidence *changed the vote*.

## Pre-registered A/B (probe `crewborg-chatev:v1`, never submitted)

Candidate: this branch's code (= v111 code + this feature), v110/v111 recipe exactly
(LLM meetings, Haiku 4.5, `CREWBORG_HS_SECRET`), Thread-1 pinned roster, slot 0, natural
roles, 2×100 paced. Baseline: W1's v111 confirmatory arms (identical code minus this
feature, identical roster/recipe/slot/window) if drained — else fresh matched arms.
Ops-fail eps excluded both sides.

- **PRIMARY (both must hold):** crew vote precision (P(hit imposter | voted a player))
  not worse; imposter-ejections per crew-episode not worse AND directionally up.
- **GUARDS:** crew mis-ejections (we vote a crewmate) not up (gullibility — the field
  DOES fabricate); crew win not down; imposter side untouched (win, kills/seat);
  vote_timeouts flat.
- **MECHANISM (must fire):** `domain.chat_evidence_applied` present; >0 meetings where
  chat evidence changed the vote target vs counterfactual.

Verdict → SHIP RECOMMENDED (for W5) or REFUTED.

---

## Verdict

*(recorded after the A/B below)*
