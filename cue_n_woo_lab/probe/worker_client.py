"""Minimal unsigned client for the Cue-n-Woo FLAS/Gemma judge worker.

Research-spike utility (not player code). Mirrors the wire format the game
referee uses (`v2/coworld/game.py:WorkerClient`) but sends unsigned requests,
which the worker serves at normal priority. The worker steers Gemma-2-9b-it
toward a text "concept" (writing style) and exposes:

  POST /generate        -> judge answers a prompt in the steered style
  POST /choice-logprobs -> scores which of N candidate answers the steered
                           model prefers, at the first divergent token

Both endpoints batch: one POST may carry many `requests`.
"""
from __future__ import annotations

import json
import math
import urllib.request
from typing import Any

DEFAULT_URL = "https://cue-n-woo-worker.softmax-research.net"

# Tournament-fixed steering knobs (manifest `default` variant).
FLAS = {"flowtime": 2.0, "steps": 3}
TEMPERATURE = 0.7
JUDGE_MAX_TOKENS = 128


def _post(path: str, payload: dict[str, Any], url: str = DEFAULT_URL, timeout: int = 600) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url + path, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def health(url: str = DEFAULT_URL) -> dict[str, Any]:
    with urllib.request.urlopen(url + "/health", timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _concept(style_text: str) -> dict[str, Any]:
    return {"type": "text", "text": style_text}


def generate(style_text: str, question: str, *, url: str = DEFAULT_URL,
             max_tokens: int = JUDGE_MAX_TOKENS, temperature: float = TEMPERATURE) -> str:
    """Single steered judge answer, exactly as `game.py:ask_judge` builds it."""
    return generate_batch([(style_text, question)], url=url, max_tokens=max_tokens, temperature=temperature)[0]


def generate_batch(pairs: list[tuple[str, str]], *, url: str = DEFAULT_URL,
                   max_tokens: int = JUDGE_MAX_TOKENS, temperature: float = TEMPERATURE,
                   chunk_size: int = 6, timeout: int = 300) -> list[str]:
    """Batch of (style_text, question) -> list of judge answers, order preserved.

    The shared worker is slow (~1 gen / 10s at 128 tokens), so a large single POST
    can exceed the read timeout. We chunk into small POSTs; each returns when its
    chunk is done, giving partial progress and bounded per-request time.
    """
    answers: list[str] = [""] * len(pairs)
    for start in range(0, len(pairs), chunk_size):
        chunk = pairs[start:start + chunk_size]
        requests = [
            {
                "id": str(j),
                "prompt": f"Answer the question directly and helpfully.\n\nQuestion: {question}",
                "concept": _concept(style),
                "flas": FLAS,
                "sampling": {"max_tokens": max_tokens, "max_prompt_tokens": 1024, "temperature": temperature},
            }
            for j, (style, question) in enumerate(chunk)
        ]
        out = _post("/generate", {"requests": requests}, url=url, timeout=timeout)
        by_id = {r.get("id"): r["text"] for r in out["results"]}
        for j in range(len(chunk)):
            answers[start + j] = by_id[str(j)]
        print(f"  generated {min(start + chunk_size, len(pairs))}/{len(pairs)}", flush=True)
    return answers


# The game's scoring context is now a FIXED generic string (cue-n-woo@95a4af2,
# scoring_context()) — the judge sees only the challenge question + the two answers,
# no transcripts. Use this as `context` to reproduce the live game.
SCORING_CONTEXT = ("You will be presented with a question/challenge and two possible "
                   "answers. Please select one of the two answers.")
UNSTEERED_FLAS = {"flowtime": 0.0, "steps": 3}  # base-model leg of delta scoring


def delta_choice_probs(style_text: str, question: str, secret: str, opponent: str, *,
                       url: str = DEFAULT_URL) -> dict[str, float]:
    """The game's CURRENT delta-of-delta scoring (cue-n-woo PR #19, game.py
    delta_option_selection_probs): query the judge STEERED and UNSTEERED, and score by
    how much the steering AMPLIFIES preference for each answer vs the base model:
        delta = log_odds(steered_secret, steered_opp) - log_odds(unsteered_secret, unsteered_opp)
        secret_prob = sigmoid(delta)
    Averaged over both orderings (context-free, the fixed SCORING_CONTEXT). Returns
    {secret, opponent} probs summing to 1 + the raw steered/unsteered legs for diagnosis.

    KEY: an answer the BASE model already prefers scores ~0.5 (no credit). You win by
    picking the answer the steering most amplifies — "who best exploits the steering."
    """
    prompt = (f"{SCORING_CONTEXT}\n\n"
              "Choose the answer that best answers the question based on the available evidence.\n"
              f"Question: {question}\n"
              "Valid answers are listed one per line. Select one line exactly.")

    def one_order(choices):
        out = _post("/choice-logprobs", {"requests": [
            {"id": "steered", "prompt": prompt, "concept": _concept(style_text),
             "flas": FLAS, "choices": choices, "ordering": {"mode": "given_order"}},
            {"id": "unsteered", "prompt": prompt, "concept": _concept(style_text),
             "flas": UNSTEERED_FLAS, "choices": choices, "ordering": {"mode": "given_order"}},
        ]}, url=url)
        by = {r["id"]: r["probabilities"] for r in out["results"]}
        return by["steered"], by["unsteered"]

    eps = 1e-12

    def lo(a, b):
        return math.log(max(eps, a)) - math.log(max(eps, b))

    def sig(v):
        return 1.0 / (1.0 + math.exp(-v)) if v >= 0 else math.exp(v) / (1.0 + math.exp(v))

    secret_ps = []
    legs = {}
    for choices in ([secret, opponent], [opponent, secret]):
        st, un = one_order(choices)
        si = choices.index(secret)
        oi = 1 - si
        delta = lo(st[si], st[oi]) - lo(un[si], un[oi])
        secret_ps.append(sig(delta))
        legs.setdefault("steered_secret", []).append(st[si])
        legs.setdefault("unsteered_secret", []).append(un[si])
    sp = sum(secret_ps) / len(secret_ps)
    return {"secret": sp, "opponent": 1 - sp,
            "steered_secret": sum(legs["steered_secret"]) / 2,
            "unsteered_secret": sum(legs["unsteered_secret"]) / 2}


def choice_probs(style_text: str, context: str, question: str, choices: list[str], *,
                 url: str = DEFAULT_URL) -> list[float]:
    """DEPRECATED for scoring — single-leg STEERED-only probs (pre-PR#19 method).

    The live game now scores by delta-of-delta (steered vs unsteered): use
    `delta_choice_probs`. This remains only for non-scoring style-similarity probes.
    Averaged over both orderings; returns one prob per choice, summing to ~1.
    """
    prompt = (
        f"{context}\n\n"
        "Choose the answer that best answers the question based on the available evidence.\n"
        f"Question: {question}\n"
        "Valid answers are listed one per line. Select one line exactly."
    )
    forward = _choice_one_order(style_text, prompt, choices, url=url)
    reverse = _choice_one_order(style_text, prompt, list(reversed(choices)), url=url)
    reverse = list(reversed(reverse))
    return [(f + r) / 2 for f, r in zip(forward, reverse)]


def choice_probs_n(style_text: str, context: str, question: str, choices: list[str], *,
                   orderings: list[list[int]] | None = None, url: str = DEFAULT_URL) -> list[float]:
    """Like choice_probs but for N>=2 choices. Averages over the given index
    orderings (default: forward + reverse) to reduce position bias. Returns one
    probability per choice in the original order; they sum to ~1."""
    prompt = (
        f"{context}\n\n"
        "Choose the answer that best answers the question based on the available evidence.\n"
        f"Question: {question}\n"
        "Valid answers are listed one per line. Select one line exactly."
    )
    n = len(choices)
    if orderings is None:
        orderings = [list(range(n)), list(reversed(range(n)))]
    acc = [0.0] * n
    for order in orderings:
        ordered = [choices[i] for i in order]
        probs = _choice_one_order(style_text, prompt, ordered, url=url)
        for local_i, orig_i in enumerate(order):
            acc[orig_i] += probs[local_i]
    return [v / len(orderings) for v in acc]


def _choice_one_order(style_text: str, prompt: str, choices: list[str], *, url: str = DEFAULT_URL) -> list[float]:
    out = _post("/choice-logprobs", {"requests": [{
        "id": "0",
        "prompt": prompt,
        "concept": _concept(style_text),
        "flas": FLAS,
        "choices": choices,
        "ordering": {"mode": "given_order"},
    }]}, url=url)
    return out["results"][0]["probabilities"]
