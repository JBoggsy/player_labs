"""Per-call LLM spend attribution, shared by the meeting and commander seams.

Emits one ``domain.llm_spend`` event payload per completed LLM call attempt (success AND
failure) so telemetry can answer "when and where are we spending the most" per trigger,
meeting, and role — James's W4 directive. Design + audit:
``crewrift_lab/docs/designs/2026-07-22-bedrock-spend-telemetry-design.md``.

Why client-side token math (not a per-call ``GET /spend``): the Bedrock sidecar meters the
pod's spend from exactly the response ``usage`` token counts × a pricing snapshot (metta
``app_backend/bedrock_pricing.py``), so tokens × the vendored family rates reproduces the
sidecar's number — verified median delta $0.000000 across 335 v110-era seats. A per-call
``/spend`` read would add a blocking 20-40ms loopback HTTP GET (the 2026-07-21
vote_timeout root cause) for no extra information; the meeting mode still attaches its
CACHED sidecar reading as a cross-check.

Failed-call cost semantics (measured, 2026-07-22 W4 audit):

- A **429** (shared daily-token-pool throttle or sidecar spend cap) is rejected BEFORE
  inference and costs $0 — verified: 429-only seats' sidecar ``spend_usd`` carries no
  meeting-call residue.
- A client-side **timeout** abort leaves the request completing (and billed) upstream, so
  it wastes roughly one call's input tokens. We estimate that with the episode's running
  mean of successful input tokens (fallback: the measured corpus mean, ~2.5K).
"""

from __future__ import annotations

import threading
from typing import Any, Mapping

# (input, output, cache_read, cache_write) USD per 1M tokens — mirrors metta's
# bedrock_pricing.FAMILY_PRICING_PER_1M, which is what the sidecar meters with when the
# dispatcher's DB snapshot lacks the model. Longest matching key wins.
FAMILY_PRICING_PER_1M: dict[str, tuple[float, float, float, float]] = {
    "opus": (15.0, 75.0, 1.5, 18.75),
    "sonnet": (3.0, 15.0, 0.30, 3.75),
    "haiku": (1.0, 5.0, 0.10, 1.25),
}
DEFAULT_PRICING_PER_1M = FAMILY_PRICING_PER_1M["haiku"]  # crewborg's only production model

# Timeout-abort wasted-input fallback when no successful call has landed yet this episode:
# the measured mean input of 963 successful meeting calls across the 2026-07-21/22 corpus.
WASTED_INPUT_TOKENS_FALLBACK = 2500


def pricing_per_1m(model: str) -> tuple[float, float, float, float]:
    """The (input, output, cache_read, cache_write) USD-per-1M rates for a model id."""
    m = (model or "").lower()
    best: tuple[float, float, float, float] | None = None
    best_len = 0
    for key, rates in FAMILY_PRICING_PER_1M.items():
        if len(key) > best_len and key in m:
            best, best_len = rates, len(key)
    return best if best is not None else DEFAULT_PRICING_PER_1M


def estimate_cost_usd(
    model: str,
    *,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float:
    i, o, cr, cw = pricing_per_1m(model)
    return (input_tokens * i + output_tokens * o + cache_read_tokens * cr + cache_write_tokens * cw) / 1_000_000


def classify_error(error: str | None) -> str:
    """Bucket a call-failure repr into the classes with distinct cost semantics.

    ``throttle_429`` (free — rejected pre-inference), ``timeout`` (wasted input — the
    aborted request completes upstream), ``other``.
    """
    text = error or ""
    if "429" in text or "Too many" in text or "Throttl" in text or "RateLimit" in text:
        return "throttle_429"
    if "Timeout" in text or "timed out" in text:
        return "timeout"
    return "other"


def _tokens_from_usage(usage: Mapping[str, Any] | None) -> dict[str, int]:
    """Token counts from an Anthropic-SDK usage dict (missing/None values → 0)."""
    u = usage or {}

    def _get(*names: str) -> int:
        for name in names:
            value = u.get(name)
            if isinstance(value, (int, float)):
                return int(value)
        return 0

    return {
        "input_tokens": _get("input_tokens"),
        "output_tokens": _get("output_tokens"),
        "cache_read_tokens": _get("cache_read_input_tokens"),
        "cache_write_tokens": _get("cache_creation_input_tokens", "cache_write_input_tokens"),
    }


class SpendLedger:
    """Cumulative per-process (= per player pod = per episode) LLM spend accumulator.

    Both LLM seams (meeting mode, commander worker) record here so
    ``episode_est_cost_usd`` is one number. Thread-safe: the commander worker records
    from its daemon thread while the meeting mode records on the inner loop.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total_usd = 0.0
        self._success_calls = 0
        self._success_input_tokens = 0
        self._meeting_ordinals: dict[int, int] = {}

    def meeting_ordinal(self, meeting_id: int) -> int:
        """Stable 0-based ordinal for a meeting id (``belief.phase_start_tick``).

        Lives on the process-wide ledger because ``AttendMeetingMode`` instances are
        recreated per meeting (the strategy re-issues the directive), so any
        instance-level counter resets to 0 every meeting — measured on the spendtrace
        probe: every llm_spend event carried meeting_index 0 while seats exceeded the
        5-call per-meeting budget.
        """
        with self._lock:
            return self._meeting_ordinals.setdefault(meeting_id, len(self._meeting_ordinals))

    def success_event(
        self,
        *,
        surface: str,
        trigger: str,
        model: str,
        latency_ms: float | None,
        usage: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        """Record a delivered call and build its ``llm_spend`` payload."""
        tokens = _tokens_from_usage(usage)
        cost = estimate_cost_usd(model, **tokens)
        with self._lock:
            self._total_usd += cost
            self._success_calls += 1
            self._success_input_tokens += tokens["input_tokens"]
            total = self._total_usd
        return {
            "surface": surface,
            "trigger": trigger,
            "ok": True,
            "error_class": None,
            "model": model,
            "latency_ms": None if latency_ms is None else round(latency_ms, 1),
            "input_tokens": tokens["input_tokens"],
            "output_tokens": tokens["output_tokens"],
            "cache_read_tokens": tokens["cache_read_tokens"],
            "cache_write_tokens": tokens["cache_write_tokens"],
            "est_cost_usd": round(cost, 6),
            "episode_est_cost_usd": round(total, 6),
        }

    def failure_event(
        self,
        *,
        surface: str,
        trigger: str,
        model: str | None,
        latency_ms: float | None,
        error: str | None,
    ) -> dict[str, Any]:
        """Record a failed call attempt and build its ``llm_spend`` payload.

        429s cost $0 (pre-inference rejection); timeouts accrue an ESTIMATED wasted-input
        cost (see module docstring). Token fields are None — no usage came back.
        """
        error_class = classify_error(error)
        wasted_input = 0
        if error_class == "timeout":
            with self._lock:
                mean = self._success_input_tokens // self._success_calls if self._success_calls else 0
            wasted_input = mean or WASTED_INPUT_TOKENS_FALLBACK
        cost = estimate_cost_usd(model or "", input_tokens=wasted_input, output_tokens=0)
        with self._lock:
            self._total_usd += cost
            total = self._total_usd
        return {
            "surface": surface,
            "trigger": trigger,
            "ok": False,
            "error_class": error_class,
            "model": model,
            "latency_ms": None if latency_ms is None else round(latency_ms, 1),
            "input_tokens": None,
            "output_tokens": None,
            "cache_read_tokens": None,
            "cache_write_tokens": None,
            "est_cost_usd": round(cost, 6),
            "episode_est_cost_usd": round(total, 6),
        }


    def reset(self) -> None:
        """Zero the ledger (tests only; a hosted pod runs exactly one episode)."""
        with self._lock:
            self._total_usd = 0.0
            self._success_calls = 0
            self._success_input_tokens = 0
            self._meeting_ordinals.clear()


#: Process-wide ledger — one player pod runs one episode, so this IS the episode ledger.
EPISODE_LEDGER = SpendLedger()
