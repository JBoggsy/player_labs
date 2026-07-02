"""Crewrift Honor Society (HS) membership — design: docs/designs/honor-society.md.

Level 1: announce an Ed25519-backed crew claim at the first meeting when crew, and
listen for other members' claims (signature-verified -> ``belief.society_trusted``),
ledgering liars. Everything is gated on ``CREWBORG_HONOR_SOCIETY`` (default OFF =>
zero behavioural change) and the whole feature failure-disables if the
``cryptography`` package is unavailable: the player must never crash over this.

Wire format — the society's canonical **HS1** spec (Alex Smith, 2026-07-02); one
message type, chat-only, standard (padded) base64:

    HS1 <unix_ts> <nonce> <pubkey_b64> <sig_b64>        (157 chars exactly)

- ``unix_ts``: current Unix seconds, 10 digits.
- ``nonce``: 8 base64 chars (48 random bits) — makes every announcement globally
  unique, so a byte-identical repeat is a self-evident replay.
- ``sig_b64``: Ed25519 over the UTF-8 string ``HS1|<unix_ts>|<nonce>|<my_color>``
  with the announcer's own lowercase color — a copied announcement re-broadcast by
  another seat is verifiably wrong, not merely suspicious.

A receiver accepts iff: the signature verifies with the OBSERVED speaker color,
|receipt_time - unix_ts| <= 10 s, and first-poster-wins — later announcements of an
already-bound key are suspected replays (ignored in-game, logged for audit).
Do not add fields to HS1 without re-budgeting the 160-char chat cap.

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
ENV_SEED = "CREWBORG_HONOR_SEED"
PREFIX = "HS1"
# HS1 verification window: |receipt_time - announced unix_ts| must be inside this.
ANNOUNCE_FRESHNESS_SECONDS = 10

# The mode's EventEmitter (``.event(name, data)`` / ``.counter(name)``).
Emitter = Any

# Process-wide identity cache. The key is stable for the process lifetime; an
# ephemeral key (no ENV_SEED) is generated once.
_identity: tuple[object, str] | None = None
_identity_failed = False


def _b64e(raw: bytes) -> str:
    """Standard base64 WITH padding — the HS1 encoding."""

    return base64.b64encode(raw).decode()


def _b64d(text: str) -> bytes | None:
    """Accept standard AND URL-safe base64, padded or not (receiver liberality).

    Alex's spec text says standard base64, but at least one member implementation
    emits unpadded base64url (verified 2026-07-02: their example key/sig are valid
    Ed25519 under urlsafe decoding). We SEND per the spec; we ACCEPT both.
    """

    padded = text + "=" * (-len(text) % 4)
    try:
        return base64.b64decode(padded, validate=True)
    except Exception:
        pass
    try:
        # urlsafe variant (no validate kwarg): translate then validate-decode.
        return base64.b64decode(padded.replace("-", "+").replace("_", "/"), validate=True)
    except Exception:
        return None


def _seed_b64d(text: str) -> bytes | None:
    """The seed env accepts either standard or URL-safe base64, padded or not."""

    for decoder in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            return decoder(text + "=" * (-len(text) % 4))
        except Exception:
            continue
    return None


def _flag_on() -> bool:
    return os.environ.get(ENV_FLAG, "").strip().lower() in ("1", "true", "yes", "on")


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

        seed_b64 = os.environ.get(ENV_SEED, "").strip()
        seed = _seed_b64d(seed_b64) if seed_b64 else None
        if seed is not None and len(seed) == 32:
            key = Ed25519PrivateKey.from_private_bytes(seed)
        else:
            key = Ed25519PrivateKey.generate()
        pub = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        _identity = (key, _b64e(pub))
        return _identity
    except Exception:
        _identity_failed = True
        return None


def enabled() -> bool:
    """Society active: flag on AND a working identity (crypto importable)."""

    return _flag_on() and _load_identity() is not None


def reset_identity_for_tests() -> None:
    global _identity, _identity_failed
    _identity = None
    _identity_failed = False


def public_key_b64() -> str | None:
    ident = _load_identity()
    return ident[1] if ident else None


def _sign(context: str) -> str:
    key, _pub = _load_identity()  # type: ignore[misc]
    return _b64e(key.sign(context.encode()))  # type: ignore[union-attr]


def _verify(pub_b64: str, sig_b64: str, context: str) -> bool:
    pub_raw, sig_raw = _b64d(pub_b64), _b64d(sig_b64)
    if pub_raw is None or sig_raw is None or len(pub_raw) != 32 or len(sig_raw) != 64:
        return False
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        Ed25519PublicKey.from_public_bytes(pub_raw).verify(sig_raw, context.encode())
        return True
    except Exception:
        return False


# --- wire format ---------------------------------------------------------------


def announce_text(self_color: str, *, now: float | None = None) -> str:
    """``HS1 <unix_ts> <nonce> <pub> <sig>`` — our crew claim (157 chars)."""

    _key, pub = _load_identity()  # type: ignore[misc]
    ts = int(now if now is not None else time.time())
    nonce = _b64e(os.urandom(6))  # 48 bits -> exactly 8 base64 chars, no padding
    sig = _sign(f"{PREFIX}|{ts}|{nonce}|{self_color.lower()}")
    return f"{PREFIX} {ts} {nonce} {pub} {sig}"


def parse(text: str) -> tuple[int, str, str, str] | None:
    """An HS1 line -> (unix_ts, nonce, pub_b64, sig_b64), or None."""

    parts = text.strip().split()
    if len(parts) != 5 or parts[0] != PREFIX:
        return None
    ts_text, nonce, pub, sig = parts[1:]
    if not (ts_text.isdigit() and len(ts_text) == 10):
        return None
    return (int(ts_text), nonce, pub, sig)


def verify_announce(
    unix_ts: int,
    nonce: str,
    pub_b64: str,
    sig_b64: str,
    speaker_color: str,
    *,
    receipt_time: float | None = None,
) -> str:
    """HS1 acceptance check -> "ok" | "bad_sig" | "stale".

    The payload is reconstructed with the OBSERVED speaker color (lowercase), so a
    copied announcement re-broadcast from another seat fails verification outright.
    """

    if not _verify(pub_b64, sig_b64, f"{PREFIX}|{unix_ts}|{nonce}|{speaker_color.lower()}"):
        return "bad_sig"
    receipt = receipt_time if receipt_time is not None else time.time()
    if abs(receipt - unix_ts) > ANNOUNCE_FRESHNESS_SECONDS:
        return "stale"
    return "ok"


# --- belief integration ----------------------------------------------------------


def process_chats(belief: "Belief", emit: Emitter, *, receipt_time: float | None = None) -> None:
    """Fold new meeting-chat HS1 announcements into the society belief state.

    Idempotent per chat line (``society_counted_chats`` survives the per-meeting
    chat_log clear). Runs for BOTH roles — an imposter still listens and ledgers,
    it just never speaks. First-poster-wins: once a key is bound to a color this
    episode, later announcements of that key are suspected replays (ignored, logged).
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
        unix_ts, nonce, pub, sig = msg
        if pub in belief.society_claims.values():
            # First-poster-wins: this key is already bound this episode.
            emit.event("honor_replay_suspected", {"color": event.speaker_color, "pub": pub})
            continue
        verdict = verify_announce(unix_ts, nonce, pub, sig, event.speaker_color, receipt_time=receipt_time)
        if verdict != "ok":
            emit.event("honor_invalid_announce", {"color": event.speaker_color, "why": verdict, "text": event.text})
            continue
        belief.society_claims[event.speaker_color] = pub
        if pub not in belief.society_liar_keys:
            belief.society_trusted.add(event.speaker_color)
        emit.event("honor_claim", {"color": event.speaker_color, "pub": pub})

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

    if not enabled() or belief.self_role != "crewmate":
        return False
    if target not in belief.society_trusted:
        return False
    from crewrift.crewborg.strategy.suspicion import witnessed_imposters

    return target not in witnessed_imposters(belief)
