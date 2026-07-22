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
- **`CREWBORG_CHAT_EVIDENCE`**: the whole term is one gated addition; OFF reproduces
  today's behavior byte-for-byte. (Designed default-ON; the probe ran with `=1`;
  **flipped to default OFF post-verdict** — see the verdict section.)
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

## Verdict (2026-07-22): REFUTED as-shipped — mechanism works exactly as designed, but no crew gain and a borderline gullibility signal. DO NOT ship default-ON without re-tuning.

**Arms.** Cand `crewborg-chatev:v1` (`0873f708…`) — `xreq_a63252e9` + `xreq_d38011ed`
(200 eps, 3 ops-fail) vs baseline v111 — `xreq_fab85490` + `xreq_2f42f740` (200 eps,
0 ops-fail), identical roster/recipe/slot-0, same day, only delta = the chat-evidence
term. Metrics scripts `/tmp/w3_metrics.py`, `/tmp/w3_ejections.py`; episode dirs
`/tmp/w3_cand_eps`, `/tmp/w3_base_eps`.

| pre-registered criterion | cand | base | delta / p | pass? |
|---|---|---|---|---|
| PRIMARY: crew vote precision not worse | 100/146 = 68.5% | 91/126 = 72.2% | −3.7pp, p=0.51 | ✅ (noise) |
| PRIMARY: imp-ejections/crew-ep not worse AND directionally up | 0.490 | 0.517 | z=−0.33, p=0.74 | ❌ **directionally DOWN** |
| GUARD: crew mis-ejections not up | 0.848/ep (all voters) | 0.662/ep | z=+1.84, **p=0.066** | ⚠️ borderline (our own mis-votes/ep 0.317 vs 0.232, p=0.16) |
| GUARD: crew win not down | 27.6% | 25.2% | +2.4pp, p=0.69 | ✅ |
| GUARD: imposter untouched | win 55.8% / kills 1.44 | 63.3% / 1.59 | −7.5pp, p=0.54 | ✅ (noise) |
| GUARD: vote_timeouts flat | 0 | 0 | — | ✅ |
| MECHANISM: chat_evidence_applied fires; changes votes | 384 events; **47 changed-vote** instances | 0 | — | ✅ decisive |

**The decisive mechanism read:** chat-CHANGED votes hit imposters at **67.4%** (31/46)
— statistically indistinguishable from suspicion-alone votes (69.0%, 69/100). The
field's templated chat is exactly as informative as our own posterior, no more. So the
term adds vote *volume* (crew player-votes 146 vs 126) at unchanged precision: correct
votes/crew-ep +0.087 (NS) **and** mis-votes/crew-ep +0.085 (NS) — symmetric, netting
zero imposter-ejection gain, while total crew ejections rose (each extra vote of ours
seeds piles other players complete, both ways).

**Interpretation.** The infrastructure is sound and validated live (extraction,
trust-scaling, dedup, cap, tracing, counterfactual). What failed is the *calibration
for untrusted speakers*: at the prior, a stranger's kill-report carries ×0.71 of
log 30 ≈ +2.4 — enough to cross the vote bar alone, and the 851-game study says
exactly this class (evidence-styled accusations) is what imposters fabricate.
**Follow-up worth probing (not run):** keep the mechanism but floor the trust gate —
testimony counts only from speakers with trust ≥ ~0.9 (in practice: HS-verified
members + near-cleared players), zeroing the stranger path. That is the literal core
of James's directive with the gullibility surface removed. The
`CREWBORG_CHAT_EVIDENCE` flag ships in the code default-ON but the probe verdict says
**run crewborg with it only after that re-tuning**; W5 should NOT fold
`crewborg-chatev:v1` into the next ship.

---

## W3b — the trust-FLOOR variant (`crewborg-chatev:v2`)

**Status:** implemented + probe pre-registered 2026-07-22 (W3b).

### Implementation

`CREWBORG_CHAT_EVIDENCE_TRUST_FLOOR` (default **0.9** whenever
`CREWBORG_CHAT_EVIDENCE=1`): in `chat_evidence_log_lr`, a speaker whose trust is
below the floor contributes **zero** testimony. HS-verified members (trust 1.0)
pass in full; near-cleared players (1 − P(imposter) ≥ floor, i.e. suspicion
≤ 0.1 at the default) pass at their trust value; everyone else — the entire
intermediate-trust stranger band that sank v1 — contributes nothing. Floor `0`
reproduces chatev:v1 exactly. The contradicted-self-alibi weight stays
**un-floored** (it is our own observation, not testimony). Everything else
(caps, per-(speaker,type) dedup, LR table, tracing) unchanged.

### Offline fire-rate + precision estimate (BEFORE the probe)

Replayed the retained W3 cand-arm telemetry (`/tmp/w3_cand_eps`, 145 clean crew
eps; scripts `crewrift_lab/tmp_probe/fire_rate.py`, `claim_precision.py` —
template-parse extraction, HS state from `honor_known_member`/`honor_liar`,
near-cleared from the preceding `suspicion_snapshot`):

- **Would-fire rate 0.57/crew-ep** (83/145 eps with ≥1 floor-passing claim;
  114/384 traced meetings) — 10× above the ~0.05/ep structurally-unpowered bar.
  An HS-verified member is visible in 93.8% of crew eps.
- Floor-passing claims: **HS 127** (kill/vent 22, accusations 105), near-cleared
  27 (all accusations). The un-floored v1 fuel was 823 any-speaker claims — the
  floor removes ~81% of the volume.
- **Ground-truth precision (does the claim's target turn out to be an actual
  imposter):** HS **kill/vent 22/22 = 100%**; HS bare accusations 63.8%;
  near-cleared accusations 59.3%; strangers (the removed band) 64.4% overall;
  **imposter-speakers 0/158 = 0%** — pure fabrication, all floor-removed.
  The floor keeps exactly the evidence class that is both bar-clearing
  (log 30) and empirically perfect, and removes everything at-or-below our own
  posterior's precision.
- Powered-or-not: a 200-ep probe is **powered for the pre-registered
  criteria** (not-worse + mechanism-diagnostic) but NOT for a statistically
  significant imp-ejection gain: ~22 HS kill/vent events → expected extra
  correct ejections ≈ +0.03–0.05/crew-ep, below 200-ep noise (±0.09). The
  decisive read is the mechanism diagnostic (changed-vote hit rate), as in W3.

### Pre-registered A/B (probe `crewborg-chatev:v2`, BEFORE firing)

Candidate: v111 recipe exactly + `CREWBORG_CHAT_EVIDENCE=1` +
`CREWBORG_CHAT_EVIDENCE_TRUST_FLOOR=0.9` (explicit for self-documentation),
Thread-1 pinned roster, slot 0, natural roles, 2×100. Baseline: W1's v111
confirmatory arms (`xreq_fab85490` + `xreq_2f42f740`, retained at
`/tmp/w3_base_eps`). Ops-fail eps excluded both sides.

- **PRIMARY (both must hold):** imp-ejections/crew-ep (measured as our
  correct-imposter votes/crew-ep, same as W3) not worse; crew mis-ejections
  NOT up (the W3 failure mode — v1 showed +0.186/ep total crew ejections,
  p=0.066).
- **MECHANISM (must fire + must pass):** `domain.chat_evidence_applied`
  events present with **HS-member sources predominating** among floor-passing
  contributions (offline source-class recount); chat-CHANGED votes hit
  imposters at **≥ the suspicion-alone rate** (the W3 killer diagnostic:
  67.4% vs 69.0% — now expected to pass because only 100%-precision-class
  sources contribute at bar-clearing weight).
- **GUARDS:** crew win not down; imposter side untouched (win, kills/seat);
  vote_timeouts flat.

Verdict → **SHIP RECOMMENDED** (default ON with floor) / **SHIP OFF** (keep
code, off by default) / **REFUTED**.
