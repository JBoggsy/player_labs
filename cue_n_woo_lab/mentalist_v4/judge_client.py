"""Runtime delta-scorer — rank candidate answers by how much the steering favors them.

The game scores delta-of-delta (cue-n-woo PR #19): an answer's value is how much the
STEERED judge prefers it over the UNSTEERED base model. We reproduce that at TEST time by
calling the public, unsigned judge worker directly: for each candidate word, score it vs a
neutral baseline under both steered (flas_flowtime=2) and unsteered (flowtime=0) judges,
in both orderings, and take sigmoid(steered_log_odds - unsteered_log_odds). The candidate
with the highest delta is the one the steering most amplifies -> the one that wins.

The judge worker is the same fleet the game uses. /choice-logprobs BATCHES, so all K
candidates for a question score in ONE POST (measured ~3-4s for 8 candidates). We keep a
hard per-call timeout and total-call budget so we never blow the 600s episode timer; on any
failure the caller falls back to the LLM's own first pick (graceful, never blocks).
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
import urllib.request

DEFAULT_WORKER = os.environ.get("CUE_N_WOO_WORKER_URL", "https://cue-n-woo-fleet.softmax-research.net")
SCORING_PROMPT_CTX = ("You will be presented with a question/challenge and two possible answers. "
                      "Please select one of the two answers.")
NEUTRAL = "A thing"
STEERED_FLAS = {"flowtime": float(os.environ.get("CUE_N_WOO_FLAS_FLOWTIME", "2.0")),
                "steps": int(os.environ.get("CUE_N_WOO_FLAS_STEPS", "3"))}
UNSTEERED_FLAS = {"flowtime": 0.0, "steps": int(os.environ.get("CUE_N_WOO_FLAS_STEPS", "3"))}


def _log(msg: str) -> None:
    print(f"[mentalist_v4.judge] {msg}", file=sys.stderr, flush=True)


def _sigmoid(v: float) -> float:
    return 1.0 / (1.0 + math.exp(-v)) if v >= 0 else math.exp(v) / (1.0 + math.exp(v))


def _log_odds(a: float, b: float) -> float:
    eps = 1e-12
    return math.log(max(eps, a)) - math.log(max(eps, b))


class JudgeClient:
    """Scores candidate words by steered-vs-base delta. Construction never raises."""

    def __init__(self, concept_text: str, *, worker_url: str = DEFAULT_WORKER,
                 timeout: float = 12.0, max_calls: int = 12) -> None:
        self.concept = {"type": "text", "text": concept_text or ""}
        self.worker_url = worker_url
        self.timeout = timeout
        self.max_calls = max_calls          # hard budget on POSTs per episode (timer safety)
        self.calls = 0

    def _post(self, payload: dict) -> dict | None:
        if self.calls >= self.max_calls:
            return None
        self.calls += 1
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(self.worker_url + "/choice-logprobs", data=data,
                                         headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            _log(f"worker call failed ({exc!r})")
            return None

    def best_word(self, question: str, candidates: list[str], baseline: str | None = None
                  ) -> tuple[str | None, list[tuple[str, float]]]:
        """Return (max-delta candidate, [(cand, delta)...]) or (None, []) if scoring failed.

        Scores every candidate vs a BASELINE answer, both orderings, steered+unsteered, in ONE
        POST. baseline defaults to NEUTRAL ("A thing") — the v9 "is this word steered-favored?"
        objective. Pass the opponent's flood word as baseline for HEAD-TO-HEAD scoring (v11):
        then a candidate's delta is "how much more the steering favors my word over THEIRS".
        """
        base = (baseline or NEUTRAL).strip() or NEUTRAL
        cands = [c for c in candidates if c and c.strip() and c.strip().lower() != base.lower()]
        if not cands:
            return None, []
        prompt = (f"{SCORING_PROMPT_CTX}\n\n"
                  "Choose the answer that best answers the question based on the available evidence.\n"
                  f"Question: {question}\n"
                  "Valid answers are listed one per line. Select one line exactly.")
        # build batched requests: per candidate, 2 orderings x {steered, unsteered}
        reqs = []
        for ci, c in enumerate(cands):
            for oi, choices in enumerate(([c, base], [base, c])):
                for leg, flas in (("s", STEERED_FLAS), ("u", UNSTEERED_FLAS)):
                    reqs.append({"id": f"{ci}|{oi}|{leg}", "prompt": prompt, "concept": self.concept,
                                 "flas": flas, "choices": choices, "ordering": {"mode": "given_order"}})
        out = self._post({"requests": reqs})
        if not out:
            return None, []
        by = {r.get("id"): r["probabilities"] for r in out.get("results", [])}
        scored = []
        for ci, c in enumerate(cands):
            deltas = []
            for oi, choices in enumerate(([c, base], [base, c])):
                s = by.get(f"{ci}|{oi}|s")
                u = by.get(f"{ci}|{oi}|u")
                if not s or not u:
                    continue
                ci_idx = choices.index(c)
                oi_idx = 1 - ci_idx
                deltas.append(_sigmoid(_log_odds(s[ci_idx], s[oi_idx]) - _log_odds(u[ci_idx], u[oi_idx])))
            if deltas:
                scored.append((c, sum(deltas) / len(deltas)))
        if not scored:
            return None, []
        scored.sort(key=lambda x: -x[1])
        return scored[0][0], scored

    def best_word_multi(self, question: str, candidates: list[str], baselines: list[str]
                        ) -> tuple[str | None, list[tuple[str, float, dict]]]:
        """Pick the candidate that best beats ALL baselines at once (max of the MIN delta across
        baselines). baselines = [NEUTRAL, "goblin", "phlogiston", ...] — neutral asks "is this
        steered-favored?", the flood words ask "does this beat the floppers' word under our
        steering?". Requiring a high min-delta yields a word that is both distinctively steered
        AND beats the generic flood words on our own questions (the v12 fix). One POST per
        baseline (each batches all candidates); total calls = len(baselines), within budget.

        Returns (best_candidate, [(cand, min_delta, {baseline: delta}) ...]) sorted by min_delta.
        """
        per_base: dict[str, dict[str, float]] = {}
        for b in baselines:
            _, scored = self.best_word(question, candidates, baseline=b)
            per_base[b] = {c: d for c, d in scored}
        # candidates present in every baseline's scoring
        cands = [c for c in candidates if all(c in per_base[b] for b in baselines)]
        rows = []
        for c in cands:
            deltas = {b: per_base[b][c] for b in baselines}
            rows.append((c, min(deltas.values()), deltas))
        if not rows:
            return None, []
        rows.sort(key=lambda x: -x[1])
        return rows[0][0], rows
