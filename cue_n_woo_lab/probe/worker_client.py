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


def choice_probs(style_text: str, context: str, question: str, choices: list[str], *,
                 url: str = DEFAULT_URL) -> list[float]:
    """Averaged (both-orderings) choice probabilities under the steered judge.

    Reproduces the game's per-question scoring core: builds the same option-
    selection prompt `game.py:option_selection_probs` uses, calls the worker in
    both choice orderings, and averages. Returns one probability per choice in
    the original `choices` order; they sum to ~1.
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
