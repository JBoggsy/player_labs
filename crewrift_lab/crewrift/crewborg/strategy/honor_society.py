"""Crewrift Honor Society (HS) membership — design: docs/designs/honor-society.md.

Members prove — cryptographically, inside ordinary meeting chat — that they are
honestly claiming to be crew this episode, then trust each other's claims (spare
a verified clean member from suspicion-driven ejection, and pin their posterior
near zero). Everything is gated on ``CREWBORG_HONOR_SOCIETY`` and the whole
feature failure-disables if ``cryptography`` is unavailable: the player must never
crash over this.

Wire format — the society's canonical **HS1** protocol (verified against the live
sasmith-crewborg-hs1 champion, 2026-07-21; see docs/designs/honor-society.md). All
messages are space-delimited ASCII tokens; every base64 field is emitted as
**unpadded base64url** and accepted as either base64url or standard on parse.

    Compact announce (current):  HS1 <sig>
    Legacy announce (accepted):  HS1 <ts> <nonce> <pubkey> <sig>

The compact signature is Ed25519 over the payload ``HS1|<ts5>|<color>`` where
``ts5 = (unix_seconds // 5) * 5`` (a 5-second grid) and ``<color>`` is the
announcer's OBSERVED speaker color this episode. Neither the timestamp, a nonce,
nor the public key rides the wire — the verifier recovers them by brute-forcing
each known-member key × a small ts5 window (``{now5, now5-5, now5-10, now5+5}``)
over ``HS1|<ts5>|<observed_color>``. Because the public key is not on the wire, a
compact announcement is only verifiable from a member already in our ledger
(``data/honor_members.json``) — which is exactly the spec's fail-closed rule:
trust requires a known key. The legacy form is self-describing (pubkey on wire),
verified over ``HS1|<ts>|<nonce>|<color>`` within ±10 s of receipt.

Binding the signature to the observed color means a copied announcement
re-broadcast from another seat verifiably fails (it was signed for a different
color); the 10-second freshness window makes a harvested announcement stale
almost immediately. There is no first-poster-wins rule — one key may verify at
several colors in one episode, which is simply a member running two slots.

The announcement contains no color words, so chat-accusation parsers — ours and
other policies' — cannot misread it as an accusation.
"""

from __future__ import annotations

import base64
import os
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from crewrift.crewborg.types import Belief

ENV_FLAG = "CREWBORG_HONOR_SOCIETY"
# The 32-byte Ed25519 seed. ``CREWBORG_HS_SECRET`` is the society's canonical env
# name; ``CREWBORG_HONOR_SEED`` is our historical one — accept either (canonical
# first) so the lab identity works whichever the deploy sets.
ENV_SECRET = "CREWBORG_HS_SECRET"
ENV_SEED = "CREWBORG_HONOR_SEED"
PREFIX = "HS1"

# Freshness: an announcement is only accepted close to when it was signed.
MAX_AGE_SECONDS = 10       # legacy: |receipt - wire ts| bound
QUANTUM_SECONDS = 5        # compact: the ts5 signing grid
NONCE_BYTES = 6            # legacy nonce (-> 8 base64 chars)

# The society flag defaults ON: HS is receive-always / send-optional, so with no
# seed we still verify others and simply never announce. Set the flag to a false
# value ("0"/"false"/"no"/"off") to fully disable (zero behavioural change).
_FLAG_DEFAULT = "1"

# The mode's EventEmitter (``.event(name, data)`` / ``.counter(name)``).
Emitter = Any

# Process-wide identity cache. The key is stable for the process lifetime; an
# ephemeral key (no seed) is generated once.
_identity: tuple[object, str] | None = None
_identity_failed = False

# Known-members registry (data/honor_members.json): raw-key-bytes -> label. This
# is our ledger's key list — a verified claim is only trusted if its key is here.
# Lazy + failure-tolerant like the identity; None until loaded, {} if unavailable.
ENV_MEMBERS = "CREWBORG_HONOR_MEMBERS"
MEMBERS_SCHEMA = "crewborg-honor-members/v1"
_members: dict[bytes, str] | None = None


def _b64e(raw: bytes) -> str:
    """Unpadded base64url — the HS1 emission encoding."""

    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(text: str) -> bytes | None:
    """Accept standard AND URL-safe base64, padded or not (receiver liberality)."""

    padded = text + "=" * (-len(text) % 4)
    try:
        return base64.urlsafe_b64decode(padded)
    except Exception:
        pass
    try:
        return base64.b64decode(padded, validate=True)
    except Exception:
        return None


def _canonical_pub(raw: bytes) -> str:
    """A raw 32-byte key -> its canonical unpadded-base64url identity string."""

    return _b64e(raw)


def _flag_on() -> bool:
    return os.environ.get(ENV_FLAG, _FLAG_DEFAULT).strip().lower() in ("1", "true", "yes", "on")


def _load_identity():
    """The (signing_key, pub_b64) pair, or None if crypto/key setup fails.

    Lazy so the ``cryptography`` import never runs (and can never fail) unless the
    society flag is on; a failed import disables the feature for the process.
    """

    global _identity, _identity_failed
    if _identity is not None:
        return _identity
    if _identity_failed:
        return None
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import (
            Encoding, PublicFormat,
        )

        seed_b64 = (os.environ.get(ENV_SECRET) or os.environ.get(ENV_SEED) or "").strip()
        seed = _b64d(seed_b64) if seed_b64 else None
        if seed is not None and len(seed) == 32:
            key = Ed25519PrivateKey.from_private_bytes(seed)
        else:
            key = Ed25519PrivateKey.generate()
        pub = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        _identity = (key, _canonical_pub(pub))
        return _identity
    except Exception:
        _identity_failed = True
        return None


def enabled() -> bool:
    """Society active: flag on AND a working identity (crypto importable).

    Note: this gates SENDING and the vote veto. Verification of others only needs
    crypto + the registry, but we tie the whole feature to one predicate for a
    clean on/off contract; with the flag on and no seed we still receive (an
    ephemeral identity always loads), matching receive-always / send-optional.
    """

    return _flag_on() and _load_identity() is not None


def have_secret() -> bool:
    """True when a real (non-ephemeral) seed is configured — i.e. we can announce
    as our persisted lab identity, not a throwaway key."""

    seed_b64 = (os.environ.get(ENV_SECRET) or os.environ.get(ENV_SEED) or "").strip()
    seed = _b64d(seed_b64) if seed_b64 else None
    return seed is not None and len(seed) == 32


def reset_identity_for_tests() -> None:
    global _identity, _identity_failed
    _identity = None
    _identity_failed = False


def public_key_b64() -> str | None:
    ident = _load_identity()
    return ident[1] if ident else None


def _load_members() -> dict[bytes, str]:
    """The known-members registry: raw key bytes -> label. Never raises.

    Vendored at data/honor_members.json; `CREWBORG_HONOR_MEMBERS` overrides the
    path ("0" disables). Keys compare by raw bytes so either base64 flavor matches.
    """

    global _members
    if _members is not None:
        return _members
    _members = {}
    override = os.environ.get(ENV_MEMBERS, "").strip()
    if override == "0":
        return _members
    try:
        import importlib.resources
        import json

        if override:
            from pathlib import Path

            data = json.loads(Path(override).read_text())
        else:
            resource = importlib.resources.files("crewrift.crewborg.data").joinpath("honor_members.json")
            data = json.loads(resource.read_text())
        if data.get("schema") != MEMBERS_SCHEMA:
            return _members
        for entry in data.get("members", []):
            raw = _b64d(str(entry.get("pub", "")))
            if raw is not None and len(raw) == 32:
                _members[raw] = str(entry.get("label", "member"))
    except Exception:
        pass  # missing/bad registry => empty; the society still works without it
    return _members


def known_member_label(pub_b64: str) -> str | None:
    """The registry label for a key (either base64 flavor), or None if unknown."""

    raw = _b64d(pub_b64)
    if raw is None:
        return None
    return _load_members().get(raw)


def reset_members_for_tests() -> None:
    global _members
    _members = None


def _sign(context: str) -> str:
    key, _pub = _load_identity()  # type: ignore[misc]
    return _b64e(key.sign(context.encode()))  # type: ignore[union-attr]


def _verify_raw(pub_raw: bytes, sig_raw: bytes, context: str) -> bool:
    if len(pub_raw) != 32 or len(sig_raw) != 64:
        return False
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        Ed25519PublicKey.from_public_bytes(pub_raw).verify(sig_raw, context.encode())
        return True
    except Exception:
        return False


# --- wire format ---------------------------------------------------------------


def _quantize_ts(now: float) -> int:
    """Floor to the QUANTUM_SECONDS grid — the compact signing timestamp (ts5)."""

    return (int(now) // QUANTUM_SECONDS) * QUANTUM_SECONDS


def _ts5_candidates(receipt: float) -> tuple[int, ...]:
    """The bounded ts5 grid points a fresh compact signature could carry, given a
    receipt time: {now5, now5-5, now5-10, now5+5} — the MAX_AGE window backwards
    plus one step forward to tolerate a signer whose clock runs slightly fast."""

    now5 = _quantize_ts(receipt)
    back = MAX_AGE_SECONDS // QUANTUM_SECONDS
    return tuple(now5 - k * QUANTUM_SECONDS for k in range(back + 1)) + (now5 + QUANTUM_SECONDS,)


def announce_text(self_color: str, *, now: float | None = None) -> str:
    """``HS1 <sig>`` — our compact crew claim (~90 chars).

    Signs ``HS1|<ts5>|<color>`` with our persisted key; the receiver recovers ts5
    and our key by brute force (we are in their ledger)."""

    ts5 = _quantize_ts(now if now is not None else time.time())
    sig = _sign(f"{PREFIX}|{ts5}|{self_color.lower()}")
    return f"{PREFIX} {sig}"


def announce_text_legacy(self_color: str, *, now: float | None = None) -> str:
    """``HS1 <ts> <nonce> <pub> <sig>`` — the self-describing legacy form.

    Retained for interop tests / fallback; the mode sends the compact form."""

    _key, pub = _load_identity()  # type: ignore[misc]
    ts = int(now if now is not None else time.time())
    nonce = _b64e(os.urandom(NONCE_BYTES))  # 48 bits -> 8 base64 chars
    sig = _sign(f"{PREFIX}|{ts}|{nonce}|{self_color.lower()}")
    return f"{PREFIX} {ts} {nonce} {pub} {sig}"


class ParsedAnnounce:
    """A parsed HS1 announcement — compact (``sig`` only) or legacy (self-describing)."""

    __slots__ = ("form", "sig_b64", "ts", "nonce", "pub_b64")

    def __init__(self, form: str, sig_b64: str, *, ts: int = 0, nonce: str = "", pub_b64: str = "") -> None:
        self.form = form              # "compact" | "legacy"
        self.sig_b64 = sig_b64
        self.ts = ts
        self.nonce = nonce
        self.pub_b64 = pub_b64


def parse(text: str) -> ParsedAnnounce | None:
    """An HS1 line -> ParsedAnnounce, or None if it is not a well-formed announce.

    Compact: ``HS1 <sig>`` (2 tokens). Legacy: ``HS1 <ts> <nonce> <pub> <sig>``
    (5 tokens, 10-digit ts)."""

    parts = text.strip().split()
    if len(parts) < 2 or parts[0] != PREFIX:
        return None
    if len(parts) == 2:
        return ParsedAnnounce("compact", parts[1])
    if len(parts) == 5:
        ts_text, nonce, pub, sig = parts[1:]
        if not (ts_text.isdigit() and len(ts_text) == 10):
            return None
        return ParsedAnnounce("legacy", sig, ts=int(ts_text), nonce=nonce, pub_b64=pub)
    return None


def verify(
    parsed: ParsedAnnounce,
    speaker_color: str,
    *,
    receipt_time: float | None = None,
) -> tuple[str, str | None]:
    """HS1 acceptance check -> (verdict, canonical_pub_b64|None).

    verdict is "ok" | "bad_sig" | "stale". The payload is reconstructed with the
    OBSERVED speaker color (lowercase), so a copied announcement re-broadcast from
    another seat fails outright. On "ok", the returned pubkey is the canonical
    unpadded-base64url identity (for compact: the matched known-member key)."""

    receipt = receipt_time if receipt_time is not None else time.time()
    color = speaker_color.lower()
    sig_raw = _b64d(parsed.sig_b64)
    if sig_raw is None or len(sig_raw) != 64:
        return ("bad_sig", None)

    if parsed.form == "legacy":
        pub_raw = _b64d(parsed.pub_b64)
        if pub_raw is None or len(pub_raw) != 32:
            return ("bad_sig", None)
        if not _verify_raw(pub_raw, sig_raw, f"{PREFIX}|{parsed.ts}|{parsed.nonce}|{color}"):
            return ("bad_sig", None)
        if abs(receipt - parsed.ts) > MAX_AGE_SECONDS:
            return ("stale", None)
        return ("ok", _canonical_pub(pub_raw))

    # compact: brute-force known-member keys × the ts5 freshness window. The
    # bounded candidate set IS the freshness check (a harvested sig goes stale
    # once receipt drifts past the window), so compact has no separate "stale".
    candidates = _ts5_candidates(receipt)
    for raw, _label in _load_members().items():
        for ts5 in candidates:
            if _verify_raw(raw, sig_raw, f"{PREFIX}|{ts5}|{color}"):
                return ("ok", _canonical_pub(raw))
    return ("bad_sig", None)


# --- belief integration ----------------------------------------------------------


def process_chats(belief: "Belief", emit: Emitter, *, receipt_time: float | None = None) -> None:
    """Fold new meeting-chat HS1 announcements into the society belief state.

    Idempotent per chat line (``society_counted_chats`` survives the per-meeting
    chat_log clear). Runs for BOTH roles — an imposter still listens and ledgers,
    it just never speaks. A verified claim from a KNOWN member (the only keys the
    compact form can verify) binds this episode's color to the key and, unless the
    key is a known liar, trusts that color. Unknown/legacy keys that verify are
    recorded as claims but are NOT trusted (fail-closed: trust needs a ledger key).
    """

    from crewrift.crewborg.strategy.suspicion import witnessed_imposters

    self_color = belief.self_color or belief.voting.self_marker_color
    for event in belief.chat_log:
        key = (event.tick, event.speaker_color, event.text)
        if key in belief.society_counted_chats:
            continue
        belief.society_counted_chats.add(key)
        if event.speaker_color is None or event.speaker_color == self_color:
            continue
        msg = parse(event.text)
        if msg is None:
            continue
        verdict, pub = verify(msg, event.speaker_color, receipt_time=receipt_time)
        if verdict != "ok" or pub is None:
            emit.event("honor_invalid_announce", {"color": event.speaker_color, "why": verdict, "text": event.text})
            continue
        belief.society_claims[event.speaker_color] = pub
        label = known_member_label(pub)
        if label is not None:
            # A KNOWN member's verified claim: reputation-backed. Trust it (unless
            # ledgered a liar) and bind the label so the meeting/vote layers and
            # telemetry can distinguish it from a bare verified signature.
            if pub not in belief.society_liar_keys:
                belief.society_trusted.add(event.speaker_color)
            belief.society_known[event.speaker_color] = label
            emit.event("honor_known_member", {"color": event.speaker_color, "label": label})
        emit.event("honor_claim", {"color": event.speaker_color, "pub": pub, "known": label})

    # Liar sweep — claims contradicted by definitional knowledge. Witnessed
    # kills/vents work for either of our roles; teammate knowledge only exists
    # when we are the imposter.
    proven = witnessed_imposters(belief) | (belief.teammate_colors if belief.self_role == "imposter" else set())
    for color, pub in belief.society_claims.items():
        if color in proven and pub not in belief.society_liar_keys:
            belief.society_liar_keys.add(pub)
            belief.society_trusted.discard(color)
            emit.event("honor_liar", {"color": color, "pub": pub})
            emit.counter("honor_liar")


def vote_veto(belief: "Belief", target: str) -> bool:
    """True when a crew posterior-driven vote/accusation should spare ``target``.

    Trust never outranks witnessed evidence, and never affects imposter play.
    """

    if not enabled() or belief.self_role == "imposter":
        # Applies to crew AND role-limbo (self_role None): the veto is skip-only,
        # so it is safe when the role is unknown — and a role-limbo seat plays the
        # crew paths anyway. Only a known imposter is exempt (deflection untouched).
        return False
    if target not in belief.society_trusted:
        return False
    from crewrift.crewborg.strategy.suspicion import witnessed_imposters

    return target not in witnessed_imposters(belief)
