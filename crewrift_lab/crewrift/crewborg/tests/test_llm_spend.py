"""Per-call LLM spend attribution (W4 spend telemetry).

Design/audit: crewrift_lab/docs/designs/2026-07-22-bedrock-spend-telemetry-design.md.
"""

from __future__ import annotations

from crewrift.crewborg.strategy.llm_spend import (
    SpendLedger,
    WASTED_INPUT_TOKENS_FALLBACK,
    classify_error,
    estimate_cost_usd,
    pricing_per_1m,
)

HAIKU_BEDROCK = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def test_pricing_matches_sidecar_haiku_family_rates() -> None:
    # Must mirror metta bedrock_pricing.FAMILY_PRICING_PER_1M["haiku"] — the rates the
    # sidecar meters our pod spend with (verified median delta $0 on 335 live seats).
    assert pricing_per_1m(HAIKU_BEDROCK) == (1.0, 5.0, 0.10, 1.25)
    assert pricing_per_1m("unknown-model") == (1.0, 5.0, 0.10, 1.25)  # crewborg default
    assert pricing_per_1m("us.anthropic.claude-sonnet-4-6")[0] == 3.0


def test_cost_estimate_reproduces_a_measured_call() -> None:
    # A real v110 call: 2560 in / 135 out => 2560*1.0/1e6 + 135*5.0/1e6.
    cost = estimate_cost_usd(HAIKU_BEDROCK, input_tokens=2560, output_tokens=135)
    assert abs(cost - 0.003235) < 1e-9


def test_classify_error_buckets_the_cost_relevant_classes() -> None:
    assert classify_error("RateLimitError(\"Error code: 429 - Too many tokens per day\")") == "throttle_429"
    assert classify_error("APITimeoutError('Request timed out or interrupted')") == "timeout"
    assert classify_error("PermissionError('bedrock 403')") == "other"
    assert classify_error(None) == "other"


def test_ledger_success_accumulates_and_reports() -> None:
    ledger = SpendLedger()
    e1 = ledger.success_event(
        surface="meeting",
        trigger="meeting_start",
        model=HAIKU_BEDROCK,
        latency_ms=2500.0,
        usage={"input_tokens": 2000, "output_tokens": 100, "cache_read_input_tokens": 0},
    )
    assert e1["ok"] is True
    assert e1["surface"] == "meeting"
    assert e1["input_tokens"] == 2000 and e1["output_tokens"] == 100
    assert abs(e1["est_cost_usd"] - 0.0025) < 1e-9
    e2 = ledger.success_event(
        surface="commander",
        trigger="commander",
        model=HAIKU_BEDROCK,
        latency_ms=1000.0,
        usage={"input_tokens": 1000, "output_tokens": 0},
    )
    # One episode ledger across BOTH surfaces: cumulative spend is a single number.
    assert abs(e2["episode_est_cost_usd"] - 0.0035) < 1e-9


def test_ledger_429_failure_is_free_but_attributed() -> None:
    ledger = SpendLedger()
    event = ledger.failure_event(
        surface="meeting",
        trigger="new_chat",
        model=HAIKU_BEDROCK,
        latency_ms=80.0,
        error="RateLimitError('Error code: 429 - Too many tokens per day')",
    )
    # Measured (W4 audit): the sidecar rejects 429s pre-inference — no tokens consumed.
    assert event["ok"] is False
    assert event["error_class"] == "throttle_429"
    assert event["est_cost_usd"] == 0.0
    assert event["episode_est_cost_usd"] == 0.0
    assert event["input_tokens"] is None  # no usage came back


def test_ledger_timeout_failure_estimates_wasted_input() -> None:
    ledger = SpendLedger()
    # No successes yet: falls back to the corpus-measured mean input size.
    event = ledger.failure_event(
        surface="meeting", trigger="deadline", model=HAIKU_BEDROCK, latency_ms=6100.0, error="APITimeoutError('timed out')"
    )
    assert event["error_class"] == "timeout"
    assert abs(event["est_cost_usd"] - WASTED_INPUT_TOKENS_FALLBACK * 1.0 / 1e6) < 1e-9

    # After a success, the estimate uses the episode's own running mean input.
    ledger.success_event(
        surface="meeting", trigger="meeting_start", model=HAIKU_BEDROCK, latency_ms=2000.0,
        usage={"input_tokens": 3000, "output_tokens": 50},
    )
    event2 = ledger.failure_event(
        surface="meeting", trigger="deadline", model=HAIKU_BEDROCK, latency_ms=6100.0, error="APITimeoutError('timed out')"
    )
    assert abs(event2["est_cost_usd"] - 3000 * 1.0 / 1e6) < 1e-9
