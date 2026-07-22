# Crewrift Honor Society (CHS) membership

**Status:** implemented; `CREWBORG_HONOR_SOCIETY` **defaults ON** (set it to a false
value for byte-identical legacy behaviour). Level 1 of the society rules.

> **Provenance / correction (2026-07-21).** The wire format below was **re-derived
> from live games**, not the original design memo. The champion `sasmith-crewborg-hs1`
> emits the **compact** `HS1 <sig>` form; our earlier code emitted only a legacy
> 5-token form and could not parse a single real announcement. We verified the real
> format by brute-forcing 17 captured signatures from live `crewrift_prime` replays
> against sasmith's registered key — 17/17 verified over `HS1|<ts5>|<color>`. We also
> found the game changed its color palette on 2026-06-24 (`coworld-crewrift` commit
> `1cbd4de`); `perception/constants.py:PLAYER_COLOR_NAMES` was stale and is now fixed,
> which matters because HS1 signs over the observed color *string*.

## The society's rules (verbatim intent)

The Crewrift Honor Society exists for the betterment of members, capitalizing on crew
wins being weighted equally to imposter wins with far more crew games. Level 1:

1. **Proof of identity** — an Ed25519 keypair; identify by public key; prove identity
   by signing an announcement bound to this episode's observed speaker color. The same
   key may be shared across policies / seats.
2. **Say when you're crew** — announce membership at the first meeting *when crew*.
3. **Never lie** — as imposter you may stay silent about membership, but never falsely
   claim to be crew.
4. **Track standing** — log liars (offline audit of replays too); punish by refusing
   future trust.
5. **Use the knowledge** — treat verified, reputation-clean claimed-crew members as
   trusted crew.

## Wire format (`HS1`, chat-only)

Meeting chat is the only channel. All base64 fields are emitted as **unpadded
base64url** and accepted as either base64url or standard base64 on parse. Two
announcement forms; verifiers accept both, we **send the compact form**.

### Compact announce (current)

```
HS1 <sig_b64>
```

Two tokens (~90 chars). `sig_b64` is Ed25519 over the UTF-8 payload
`HS1|<ts5>|<color>` where:

- `ts5` = the sender's Unix time floored to a 5-second grid: `(now // 5) * 5`.
- `color` = the sender's **observed** speaker color this episode, lowercase.

Neither the timestamp, a nonce, nor the public key is on the wire. The compact form
is short because the meeting chat panel is a small newest-first ring buffer that was
dropping the longer legacy line.

### Legacy announce (still accepted)

```
HS1 <unix_ts> <nonce> <pubkey_b64> <sig_b64>
```

Five tokens, self-describing. `sig_b64` is Ed25519 over `HS1|<ts>|<nonce>|<color>`
(observed speaker color). `nonce` = 6 random bytes → 8 base64 chars.

### Verification

- **Compact:** for each known-member key in the ledger (`data/honor_members.json`) ×
  each ts5 grid point in the freshness window, check the signature over
  `HS1|<ts5>|<observed_color>`. The window given receipt time `r` is
  `{now5, now5−5, now5−10, now5+5}` (10 s back on the 5 s grid, plus one step forward
  for a slightly-fast signer). First match returns the canonical pubkey. **Because the
  public key is not on the wire, only a key already in our ledger can be verified** —
  this *is* the fail-closed trust rule (§reputation).
- **Legacy:** verify with the on-wire pubkey over `HS1|<ts>|<nonce>|<color>`, and
  require `|receipt − ts| ≤ 10 s`.

Binding the signature to the **observed** color means a copied announcement
re-broadcast from another seat verifiably fails (it was signed for a different color).
The 10-second freshness window makes a harvested announcement stale almost
immediately. **No first-poster-wins:** one key may verify at several colors in one
episode — that is simply a member running two slots, each signing its own color
(observed live: sasmith announcing as both `purple` and `cyan` in one game).

Challenge/response (`HS1?` / `HS1!`) exists in the society spec but is not implemented
here — crewborg does announcements only.

## Key management

- `CREWBORG_HS_SECRET` (canonical) or `CREWBORG_HONOR_SEED` (our historical alias) —
  unpadded/padded base64(url) of the 32-byte Ed25519 seed, injected at upload via
  `--secret-env`. **Never commit the seed.**
- Flag on without a seed ⇒ an **ephemeral** per-process key: we still verify others
  and simply announce with a key nobody has in their ledger (harmless). This is the
  spec's **receive-always / send-optional** posture.
- **The lab's member identity** (generated 2026-07-02): public key
  `Gq5nOr6NdgrRPfi7Ahzm-i9fuMJdHIaNHaDDDUuRhMc`; the seed lives at
  `~/.crewborg/honor_seed.b64` (mode 0600, outside git). Upload recipe addition:
  `--secret-env CREWBORG_HS_SECRET=$(cat ~/.crewborg/honor_seed.b64)`
  (the flag is on by default; pass `CREWBORG_HONOR_SOCIETY=0` to disable).

## Behaviour (crew announces; imposter untouched except silence)

- **Announce** (crew, alive): at the first chat opportunity — normally the first
  meeting, before any other chat the mode would send. Exactly once per episode. Never
  as imposter (silence is permitted; claiming is not). Uses the compact form.
- **Listen** (both roles, every meeting tick): parse `HS1` lines from `belief.chat_log`
  (deduped in `society_counted_chats`, surviving the per-meeting clear). A verified
  announce from a **known** member records the claim (`society_claims[color]=pub`),
  adds the color to `society_trusted` (unless the key is on the liar ledger), and binds
  the label into `society_known`. Unverifiable lines (unknown key, stale, tampered,
  cross-seat) are ignored (traced `honor_invalid_announce`).
- **Liar ledger**: a claimed color that is (a) in `witnessed_imposters(belief)` or
  (b) in `teammate_colors` when we are the imposter is a proven liar: trust revoked,
  pubkey recorded in `society_liar_keys`, and a `domain.honor_liar` event emitted for
  offline harvest.
- **Use the knowledge** (crew only): a society-trusted color is (1) exempt from
  posterior-driven votes and accusations — `_submit_vote_intent` converts such a vote
  to skip (traced `meeting_vote_society_veto`) — and (2) pinned near P(imposter)≈0 in
  the suspicion posterior. **Witnessed evidence always overrides trust**: a trusted
  member we saw kill/vent is voted like anyone else (and ledgered as a liar).

## Reputation (the ledger)

`data/honor_members.json` (`crewborg-honor-members/v1`) vendors known member keys
(ours + `alex-smith`). A verified claim is only **trusted** when its key is in this
ledger (the compact form can't verify anything else). Keys compare by raw bytes, so
either base64 flavor matches. `CREWBORG_HONOR_MEMBERS` overrides the path; `0`
disables; missing/bad file ⇒ empty registry, never a crash.

### The cross-game distrust list (offline liar harvest — implemented 2026-07-22)

The in-game liar ledger (`society_liar_keys` + `domain.honor_liar` events) only
lasts one episode. The offline consumer closes the loop:

- **Harvest:** `crewrift_lab/tools/harvest_liars.py` scans harvested telemetry
  (`crewrift_lab/telemetry_harvest/episodes/*/` — loose `telemetry.jsonl` and
  `artifacts/policy_artifact_*.zip`) for `domain.honor_liar` events, dedupes the
  per-meeting-tick repeats to distinct (episode, color) lies, aggregates per
  pubkey, and (with `--write`) renders `data/honor_distrust.json`
  (`crewborg-honor-distrust/v1`). Run it after `harvest_artifacts.py` (same
  cadence works).
- **Ground-truth gate (load-bearing):** the in-game witness has FALSE POSITIVES —
  measured 6 ledgerings of alex-smith's key across 199 baseline episodes
  (2026-07-22), all with the accused seat actually **crew** per `results.json`
  (kill/vent misattribution by our own perception). The harvest therefore
  validates every `honor_liar` event against the episode's `results.json`
  (accused color → palette slot → real role): only confirmed lies reach the
  distrust list; witness errors are reported as `refuted`, results-less events
  as `unverified` — both excluded (fail-closed toward trusting members). As of
  2026-07-22 the corpus (675 sources / 234 episodes incl. the A/B baseline)
  contains **zero confirmed lies** (6 refuted witness errors), so the vendored
  list is empty — the normal state.
- **Consume:** `strategy/honor_society.py` (`_load_distrust`/`is_distrusted`)
  loads the vendored list (env `CREWBORG_HONOR_DISTRUST` overrides the path,
  `0` disables, missing/bad file ⇒ empty — same contract as the members
  registry). In `process_chats`, a verified announcement from a distrusted key
  is pre-ledgered into `society_liar_keys` and **never trusted** — from the
  first meeting, without re-witnessing the lie this episode (traced
  `honor_distrusted_announce`). The identity/label is still bound to
  `society_known` for telemetry.

## Safety invariants (the "don't impair the player" contract)

1. Flag off (`CREWBORG_HONOR_SOCIETY=0`) ⇒ **no code path changes**: the mode hooks
   all early-return on `honor_society.enabled()`.
2. The `cryptography` import is lazy and failure-disables the feature (trace, no
   crash) — the player must run even on an image without the wheel.
3. Society chats obey the existing chat cooldown, never pre-empt the deadline
   auto-submit or early vote submit, never fire from dead seats, and consume the same
   chat budget as any other line (one extra line per game in practice).
4. Society text contains no color words, so accusation parsers (ours and other
   policies') cannot misread it; the sender additionally bypasses `_note_own_accusation`.
5. Vote vetoes only ever convert a vote to **skip** — never produce a new vote target,
   so mis-ejection risk is strictly reduced.

## Files

- `strategy/honor_society.py` — identity, wire format (compact + legacy),
  parse/verify, `process_chats`, `vote_veto`.
- `strategy/suspicion.py` — the role-reveal posterior pin for trusted colors.
- `types.py` — `society_*` Belief fields + the per-meeting ordinal.
- `perception/constants.py` — `PLAYER_COLOR_NAMES` (must mirror the game palette;
  the observed color feeds the HS1 signature).
- `modes/attend_meeting.py` — the send hook (`_society_chat_intent`), the listen call,
  and the vote/accuse vetoes.
- `data/honor_members.json` — the known-member ledger.
- `data/honor_distrust.json` — the harvested cross-game distrust list (written by
  `crewrift_lab/tools/harvest_liars.py`).
- `crewrift_lab/tools/harvest_liars.py` — the offline liar-ledger harvest
  (tests: `crewrift_lab/tools/tests/test_harvest_liars.py`).
- `tests/test_honor_society.py` — including a real captured sasmith signature.
