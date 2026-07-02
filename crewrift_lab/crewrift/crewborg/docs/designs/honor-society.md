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

## Wire format (`CHS1`, chat-only)

Meeting chat is the only channel. crewborg's own chat cap is 160 chars
(`CHAT_MAX_CHARS`); the sim renders at least ~170. All binary values are
**unpadded URL-safe base64**; the version prefix `CHS1` makes the format evolvable and
cheap to parse. Since the society publishes no canonical encoding, this file is the
reference — other members interop by adopting it.

| message | text | signature is over |
|---|---|---|
| announce | `CHS1 iam <pub> crew <sig>` | `CHS1\|crew\|<speaker_color>` |
| challenge | `CHS1 chal <color> <nonce>` | — (nonce: 12 random bytes) |
| response | `CHS1 resp <nonce> <sig>` | `CHS1\|resp\|<nonce>\|<speaker_color>` |

- `<pub>` = 32-byte Ed25519 public key (43 chars); `<sig>` = 64-byte signature
  (86 chars). Announce ≈ 148 chars — inside the cap.
- The announce signature binds the key to the **claimed color and the crew claim**, so
  a bystander cannot splice a seen pubkey into their own claim. It does **not** prevent
  verbatim replay of a whole announce line in another game by whoever holds the same
  color there — that is what challenges are for. Trust from a bare announce is
  therefore *provisional* by design; Level 1 accepts it (the liar ledger is the
  backstop, per the rules).
- crewborg **answers** challenges (rule: prove identity when challenged) but does not
  issue them in v1 — issuing spends scarce chat turns and mentions a color word, which
  other policies' chat parsers may read as an accusation.

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

## Files

- `strategy/honor_society.py` — identity, wire format, parsing/verification,
  `process_chats`, `vote_veto`.
- `types.py` — `society_*` Belief fields + the per-meeting ordinal.
- `modes/attend_meeting.py` — the send hook (`_society_chat_intent`), the listen call,
  and the vote/accuse vetoes.
- `tests/test_honor_society.py`.
