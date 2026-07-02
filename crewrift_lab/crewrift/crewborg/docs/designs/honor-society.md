# Crewrift Honor Society (CHS) membership

**Status:** implemented behind `CREWBORG_HONOR_SOCIETY` (default OFF — zero behavioural
change when unset). Level 1 of the society rules only.

## The society's rules (verbatim intent)

The Crewrift Honor Society exists for the betterment of members, capitalizing on crew
wins being weighted equally to imposter wins with far more crew games. Level 1:

1. **Proof of identity** — an Ed25519 keypair; identify by public key; prove identity
   by signing challenge text other players provide. The same key may be shared across
   policies.
2. **Say when you're crew** — announce membership at the first meeting *when crew*.
3. **Never lie** — as imposter you may stay silent about membership, but never falsely
   claim to be crew.
4. **Track standing** — log liars (watch replays too); punish by refusing future trust.
5. **Use the knowledge** — treat verified claimed-crew members as trusted crew.

## Wire format (`HS1`, chat-only — the society's canonical spec, Alex Smith 2026-07-02)

Meeting chat is the only channel. crewborg's own chat cap is 160 chars
(`CHAT_MAX_CHARS`); the sim renders at least ~170. One message type:

```
HS1 <unix_ts> <nonce> <pubkey_b64> <sig_b64>
```

- `unix_ts` — current Unix time in seconds (10 digits).
- `nonce` — 8 chars of base64 (48 random bits): every announcement is globally
  unique, so a byte-identical repeat is a self-evident replay.
- `pubkey_b64` — the member's Ed25519 public key, **standard base64** (44 chars).
- `sig_b64` — Ed25519 signature, standard base64 (88 chars), over the UTF-8 string
  `HS1|<unix_ts>|<nonce>|<my_color>` where `<my_color>` is the announcer's own player
  color, lowercase. Binding the color means a copied announcement re-broadcast by
  another seat is **verifiably wrong**, not merely suspicious.
- Length: 4+10+1+8+1+44+1+88 = **157 chars** — 3 to spare under the 160 budget.
  **Do not add fields to HS1 without re-budgeting.**

**Verification.** A receiver accepts an announcement iff all of:

1. The signature verifies for `pubkey_b64` over the payload reconstructed with the
   **observed** speaker color.
2. `|receipt_time − unix_ts| ≤ 10 s` (receipt = when the verifier observes it).
3. **First-poster-wins**: no earlier valid announcement of the same key was seen this
   episode. Later announcements of an already-bound key are suspected replays —
   ignored in-game (`honor_replay_suspected`), logged for post-hoc audit.

An accepted announcement binds this episode's color to the key; how much to trust the
key is the verifier's own business (crewborg trusts it unless the key is on its liar
ledger). The rules' challenge/response clause has no wire spec yet — crewborg
implements announcements only until the society specs challenges.

## Key management

- `CREWBORG_HONOR_SEED` — unpadded/padded base64 of the 32-byte Ed25519 seed, injected
  at upload via `--secret-env`. **Never commit the seed.** The lab keeps it outside git;
  the public key may be published freely.
- Flag on without a seed ⇒ an **ephemeral** per-process key is generated (fine for
  smoke tests; useless for reputation).
- **The lab's member identity** (generated 2026-07-02): public key
  `Gq5nOr6NdgrRPfi7Ahzm-i9fuMJdHIaNHaDDDUuRhMc`; the seed lives at
  `~/.crewborg/honor_seed.b64` (mode 0600, outside git). Upload recipe addition:
  `--secret-env CREWBORG_HONOR_SOCIETY=1 --secret-env CREWBORG_HONOR_SEED=$(cat ~/.crewborg/honor_seed.b64)`.

## Behaviour (all gated on the flag; imposter behaviour untouched except silence)

- **Announce** (crew, alive): at the first chat opportunity — normally the first
  meeting, before any other chat the mode would send; if the first meeting gives no
  chat slot, the next meeting. Exactly once per episode. Never as imposter (silence is
  permitted; claiming is not).
- **Listen** (both roles, every meeting tick): parse `CHS1` lines from
  `belief.chat_log` (deduped in `society_counted_chats`, surviving the per-meeting
  clear). A valid-signature announce from another color records the claim
  (`society_claims[color]=pub`) and adds the color to `society_trusted`. Invalid
  signatures are ignored (traced `honor_invalid_sig`). Challenges naming our color
  queue a response (sent only when crew — an imposter stays entirely silent, which the
  rules allow).
- **Liar ledger**: a claimed color that is (a) in `witnessed_imposters(belief)` or
  (b) in `teammate_colors` when we are the imposter (we *know* our teammates) is a
  proven liar: trust revoked, pubkey recorded in `society_liar_keys`, and a
  `domain.honor_liar` event emitted so the lab can harvest liars across games (rule 4's
  "we'll also watch for them in replays" is the offline half; a vendored distrust list
  can be added once any liar is ever observed).
- **Use the knowledge** (crew only): a society-trusted color is exempt from
  posterior-driven votes and accusations — `_submit_vote_intent` converts such a vote
  to skip (traced `meeting_vote_society_veto`) and the deterministic crew chat picks a
  different (or no) accusation target. **Witnessed evidence always overrides trust**:
  a trusted member we saw kill/vent is voted like anyone else (and ledgered as a liar
  if they claimed crew).

## Safety invariants (the "don't impair the player" contract)

1. Flag off ⇒ **no code path changes**: the mode hooks all early-return on
   `honor_society.enabled()`.
2. The `cryptography` import is lazy and failure-disables the feature (trace, no
   crash) — the player must run even on an image without the wheel.
3. Society chats obey the existing chat cooldown, never pre-empt the deadline
   auto-submit or early vote submit, never fire from dead seats, and consume the same
   chat budget as any other line (one extra line per game in practice).
4. Society text contains no color words (announce/response), so
   `_note_own_accusation` and other policies' accusation parsers cannot misread it;
   the sender additionally bypasses `_note_own_accusation` explicitly.
5. Vote vetoes only ever convert a vote to **skip** — they can never produce a new
   vote target, so the mis-ejection risk is strictly reduced.

## Known-members registry

`data/honor_members.json` (`crewborg-honor-members/v1`) vendors known member keys
(ours + Alex Smith's, added 2026-07-02). Keys compare by raw bytes, so either base64
flavor matches. A verified claim from a known key additionally lands in
`belief.society_known` (color → label) and emits `honor_known_member` — reputation-
backed trust, distinct from fresh unknown keys (provisionally trusted only).
`CREWBORG_HONOR_MEMBERS` overrides the path; `0` disables; missing/bad file ⇒ empty
registry, never a crash.

## Files

- `strategy/honor_society.py` — identity, wire format, parsing/verification,
  `process_chats`, `vote_veto`.
- `types.py` — `society_*` Belief fields + the per-meeting ordinal.
- `modes/attend_meeting.py` — the send hook (`_society_chat_intent`), the listen call,
  and the vote/accuse vetoes.
- `tests/test_honor_society.py`.
