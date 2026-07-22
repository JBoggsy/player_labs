# HS1 ecosystem notes — for the Honor Society spec author

Notes from the crewborg implementation (James Boggs's lab) for Alex Smith, collected
while bringing our HS1 support up to the live wire format (2026-07-21/22). Our
implementation reference: `crewrift_lab/crewrift/crewborg/strategy/honor_society.py`
and the design doc `crewrift_lab/crewrift/crewborg/docs/designs/honor-society.md`.

## 1. Same-key multi-seat collides with first-poster-wins

**Observed live:** one member key (yours) announcing as two colors in a single game —
`sasmith-crewborg-hs1` seated twice, each seat signing its own observed color
(e.g. `purple` and `cyan` in one episode).

**The mechanics of the collision.** Any receiver that implements a
*first-poster-wins* rule — "once a pubkey is bound to a color this episode, later
announcements of that key are suspected replays" — will silently distrust the second
seat. Our original implementation did exactly that (the 2026-07-02 spec text we
worked from listed first-poster-wins as the replay defense), so for weeks we would
have ignored your second seat's valid claim, logged it as a replay, and given it no
vote protection. Nothing on the wire distinguishes "the same policy in two seats"
from "a copied announcement", *except* the color-bound signature — and the color
binding already defeats copy-replay on its own (a copied line verifies against the
wrong observed color and fails).

**Recommendation — pick one and put it in the spec:**
- **(a) Bless same-key multi-seat** (what the live behavior implies): specify that
  one key MAY verify at multiple colors per episode, and that receivers MUST NOT
  apply first-poster-wins. The color-bound signature + freshness window remain the
  full replay defense. This is what we now implement.
- **(b) Distinct key per concurrent seat**: if first-poster-wins is meant to stay,
  members running multiple seats need one registered key per seat, and the registry
  format needs to say so.

Option (a) is simpler and matches deployed reality; option (b) gives per-seat
revocation granularity. Either is fine — the ambiguity is the problem, because a
conservative implementer reading "replay defense" naturally reaches for
first-poster-wins and then quietly drops your second seat.

## 2. Encoding canonicalization

The 2026-07-02 spec text says **standard (padded) base64**, but the live member
implementation emits **unpadded base64url** (verified 2026-07-02: the example
key/signature decode as valid Ed25519 only under urlsafe rules; re-confirmed
2026-07-21 against 17 captured live signatures).

**Our stance (suggested for the spec):** be liberal on receive, canonical on send.
We accept either alphabet, padded or not, on every base64 field (keys compare by raw
bytes after decode); we emit unpadded base64url, matching what the live champion
actually sends. Recommend the spec canonicalize on **unpadded base64url** (shortest,
URL/chat-safe, and what's deployed) and explicitly require receivers to accept both
during the transition.

## 3. Other findings from this implementation cycle (worth a spec note each)

- **The compact form should be published authoritatively.** We had to re-derive
  `HS1 <sig>` (Ed25519 over `HS1|<ts5>|<color>`, ts5 = unix floored to a 5-second
  grid) by brute-forcing captured live signatures against your registered key
  (17/17 verified). Until then our receiver parsed only the legacy 5-token form and
  every real announcement was invisible to us. A one-paragraph canonical write-up of
  the compact form (payload, ts5 grid, freshness window, "no pubkey on the wire —
  ledger keys only") would save every new member this archaeology.
- **Verifier cost scales O(ledger-keys × ts5-window) per candidate line.** Fine at
  2-5 members (we check 4 grid points per key); at 50 members it's ~200 Ed25519
  verifies per chat line that starts with `HS1`. If the society grows, consider an
  optional short key-hint token (e.g. first 4 bytes of the pubkey, base64url) so
  receivers can verify against one key instead of all of them. Costs 6 chars.
- **Color names are load-bearing — pin the palette.** The signature binds the
  *observed color string*, and the game changed its palette on 2026-06-24
  (`coworld-crewrift` commit `1cbd4de`). Our color table was stale for weeks; any
  member with a stale palette signs/verifies the wrong strings for slots ≥ 1 and
  every cross-verification silently fails. The spec should either pin the canonical
  color-name list (and its version) or bind something the game guarantees stable.
- **Clock-skew tolerance is asymmetric and unspecified.** We accept
  `{now5, now5−5, now5−10, now5+5}` — 10 s back plus one grid step forward for a
  slightly-fast signer. Worth specifying, otherwise implementations will disagree
  about edge-of-window announcements.
- **Registry distribution is the actual trust bottleneck.** The compact form can
  only be verified for keys already in the local ledger (fail-closed — good), which
  makes "how do members exchange registries" the real protocol surface. Ours is a
  vendored JSON (`crewborg-honor-members/v1`: `{pub, label, added, note}` entries);
  happy to converge on a shared format if you have one.
- **Liar-ledger interop — and a measured warning about Rule 4.** Rule 4 (track
  standing / punish liars) now has a working offline pipeline on our side: we
  harvest our agents' `honor_liar` telemetry (a verified claimed-crew member we
  *witnessed* kill/vent) across league games and vendor a distrust list back into
  the image, so proven liars get no trust from the first meeting of future games.
  **The warning: in-game witnessing has real false positives.** In a 199-episode
  batch our agents ledgered *your* key as a liar 6 times — and in all 6 the accused
  seat was actually crew per the episode results (kill/vent misattribution by our
  own perception under crowding). Naively federating raw in-game liar events would
  have had us permanently distrusting an honest member. Our pipeline now validates
  every liar event against post-game ground truth (results) before any key is
  distrusted; recommend the spec say explicitly that standing damage requires
  *replay/results-verified* evidence, not a live witness call. Zero **confirmed**
  lies observed so far (234 episodes scanned — everyone's honest to date). If you
  want cross-member reputation to be more than aspirational, a tiny shared format
  for "key X lied in episode Y (evidence: witnessed kill at tick T, verified
  against the replay)" would let members pool evidence rather than each
  rediscovering a liar independently.
- **Why compact exists, for the record:** the meeting chat panel is a small
  newest-first ring buffer; the 157-char legacy line was getting dropped. The
  ~90-char compact line survives. New message types should budget accordingly
  (the chat cap is 160 chars).

## Status of our implementation (so you know what to expect from `crewborg` seats)

- Sends the compact form, once per episode, first chat opportunity when crew, never
  as imposter. Key: `Gq5nOr6NdgrRPfi7Ahzm-i9fuMJdHIaNHaDDDUuRhMc` (label
  `crewborg-lab`).
- Accepts compact (ledger keys only) + legacy (self-describing), either base64
  flavor, no first-poster-wins.
- A verified claim from a ledger key ⇒ trusted crew: exempt from posterior-driven
  votes/accusations (witnessed evidence always overrides) and pinned ≈0 in our
  suspicion posterior. Live in the league since crewborg:v110 (2026-07-21).
- Challenge/response (`HS1?`/`HS1!`): not implemented, awaiting a wire spec.
