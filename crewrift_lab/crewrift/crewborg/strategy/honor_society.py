"""Crewrift Honor Society (CHS) membership — design: docs/designs/honor-society.md.

Level 1: announce an Ed25519-backed crew claim at the first meeting when crew, listen
for other members' claims (signature-verified -> ``belief.society_trusted``), answer
identity challenges, and ledger liars. Everything is gated on ``CREWBORG_HONOR_SOCIETY``
(default OFF => zero behavioural change) and the whole feature failure-disables if the
``cryptography`` package is unavailable: the player must never crash over this.

Wire format (chat-only, versioned prefix, unpadded URL-safe base64):

    CHS1 iam <pub> crew <sig>     sig over "CHS1|crew|<speaker_color>"
    CHS1 chal <color> <nonce>     (we answer these; v1 never issues them)
    CHS1 resp <nonce> <sig>       sig over "CHS1|resp|<nonce>|<speaker_color>"

Society text deliberately contains no color words (the announce/response we send), so
chat-accusation parsers — ours and other policies' — cannot misread it as an accusation.
"""

from __future__ import annotations

import base64
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from crewrift.crewborg.types import Belief

ENV_FLAG = "CREWBORG_HONOR_SOCIETY"
ENV_SEED = "CREWBORG_HONOR_SEED"
PREFIX = "CHS1"

# The mode's EventEmitter (``.event(name, data)`` / ``.counter(name)``).
Emitter = Any

# Process-wide identity cache: (seed-source, signing_key, pub_b64). The key is
# stable for the process lifetime; an ephemeral key (no ENV_SEED) is generated once.
_identity: tuple[object, str] | None = None
_identity_failed = False
_ephemeral_traced = False


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(text: str) -> bytes | None:
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except Exception:
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
        seed = _b64d(seed_b64) if seed_b64 else None
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
    global _identity, _identity_failed, _ephemeral_traced
    _identity = None
    _identity_failed = False
    _ephemeral_traced = False


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


def announce_text(self_color: str) -> str:
    """`CHS1 iam <pub> crew <sig>` — our crew claim, bound to the color we claim as."""

    _key, pub = _load_identity()  # type: ignore[misc]
    return f"{PREFIX} iam {pub} crew {_sign(f'{PREFIX}|crew|{self_color}')}"


def response_text(nonce_b64: str, self_color: str) -> str:
    """`CHS1 resp <nonce> <sig>` — answer to an identity challenge naming us."""

    return f"{PREFIX} resp {nonce_b64} {_sign(f'{PREFIX}|resp|{nonce_b64}|{self_color}')}"


def parse(text: str) -> tuple[str, ...] | None:
    """A CHS line -> ("iam", pub, sig) | ("chal", color, nonce) | ("resp", nonce, sig)."""

    parts = text.strip().split()
    if len(parts) < 2 or parts[0] != PREFIX:
        return None
    kind = parts[1]
    if kind == "iam" and len(parts) == 5 and parts[3] == "crew":
        return ("iam", parts[2], parts[4])
    if kind == "chal" and len(parts) == 4:
        return ("chal", parts[2], parts[3])
    if kind == "resp" and len(parts) == 4:
        return ("resp", parts[2], parts[3])
    return None


def verify_announce(pub_b64: str, sig_b64: str, speaker_color: str) -> bool:
    return _verify(pub_b64, sig_b64, f"{PREFIX}|crew|{speaker_color}")


def verify_response(pub_b64: str, sig_b64: str, nonce_b64: str, speaker_color: str) -> bool:
    return _verify(pub_b64, sig_b64, f"{PREFIX}|resp|{nonce_b64}|{speaker_color}")


# --- belief integration ----------------------------------------------------------


def process_chats(belief: "Belief", emit: Emitter) -> None:
    """Fold new meeting-chat CHS lines into the society belief state.

    Idempotent per chat line (``society_counted_chats`` survives the per-meeting
    chat_log clear). Runs for BOTH roles — an imposter still listens and ledgers,
    it just never speaks.
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
        if msg[0] == "iam":
            _, pub, sig = msg
            if not verify_announce(pub, sig, event.speaker_color):
                emit.event("honor_invalid_sig", {"color": event.speaker_color, "text": event.text})
                continue
            belief.society_claims[event.speaker_color] = pub
            if pub not in belief.society_liar_keys:
                belief.society_trusted.add(event.speaker_color)
            emit.event("honor_claim", {"color": event.speaker_color, "pub": pub})
        elif msg[0] == "chal":
            _, color, nonce = msg
            if self_color is not None and color == self_color and nonce not in belief.society_challenges_due:
                belief.society_challenges_due.append(nonce)
        # "resp": v1 issues no challenges, so responses to others are not consumed.

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
