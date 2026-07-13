"""Read the Bedrock sidecar's per-episode LLM spend budget.

The runner enforces a league-configured **per-episode, per-player-pod** USD spend ceiling: once
the pod's running estimated spend reaches it, every further Bedrock call is rejected with a 429
(metta ``app_backend/job_runner/bedrock_sidecar.py``). crewborg's meeting LLM is token-heavy, so
firing blindly exhausts the whole episode's budget in the first meeting and 429s the rest of the
game (measured ~98% fallback). This reads the sidecar's ``GET /spend`` so the meeting loop can
budget: spend on the highest-value calls and stop before it 429s.

``GET /spend`` -> ``{"spend_usd", "spend_limit_usd", "remaining_usd"}`` (``*_limit`` /
``remaining`` are null when the league configured no limit). The sidecar base is the loopback
endpoint the runner injects as ``AWS_ENDPOINT_URL_BEDROCK_RUNTIME``.
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass

BEDROCK_SIDECAR_ENDPOINT_ENV = "AWS_ENDPOINT_URL_BEDROCK_RUNTIME"
_SPEND_TIMEOUT_SECONDS = 0.5


@dataclass(frozen=True)
class SpendStatus:
    spend_usd: float
    spend_limit_usd: float | None
    remaining_usd: float | None

    @property
    def limited(self) -> bool:
        """True when the league configured a per-episode limit (so budgeting applies)."""
        return self.remaining_usd is not None


def read_spend(env: dict[str, str] | None = None) -> SpendStatus | None:
    """Fetch the sidecar's current spend, or ``None`` if there's no sidecar / it's unreachable.

    Best-effort and fast (0.5s timeout): a failure to read must never block a meeting — the caller
    treats ``None`` as "no budget signal" and falls back to its existing call budget.
    """
    env = env if env is not None else os.environ
    base = env.get(BEDROCK_SIDECAR_ENDPOINT_ENV, "").strip()
    if not base:
        return None
    url = base.rstrip("/") + "/spend"
    try:
        with urllib.request.urlopen(url, timeout=_SPEND_TIMEOUT_SECONDS) as resp:  # noqa: S310 (loopback)
            data = json.loads(resp.read().decode())
    except Exception:
        return None
    try:
        return SpendStatus(
            spend_usd=float(data["spend_usd"]),
            spend_limit_usd=None if data.get("spend_limit_usd") is None else float(data["spend_limit_usd"]),
            remaining_usd=None if data.get("remaining_usd") is None else float(data["remaining_usd"]),
        )
    except (KeyError, TypeError, ValueError):
        return None
