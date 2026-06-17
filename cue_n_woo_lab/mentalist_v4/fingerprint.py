"""Fingerprinting — recover the judge's steered axis values from its probe answers (v6).

The judge, asked our 3 free-response probe questions, names/evokes its steering far better
than prose reveals it. v6 uses 3 DIFFERENT questions (labels6, nouns_adj, object) chosen
for complementary axis coverage (probe_question_selection: union 14/15 axes).

Reference matrix (data/axis_reference_embeddings.npz, built by probe/build_v6_references.py):
  N = 326 values x 3 questions rows, each a Titan-v2 embedding of that value's single-axis
  answer to that question. We match QUESTION-TO-QUESTION: our labels6 answer is compared to
  each value's labels6 reference, etc., and the per-question similarities are averaged per
  value. This is more faithful than pooling all text together.

Pipeline per question: embed our judge answer (Titan; char-TFIDF fallback), cosine vs that
question's reference rows. Average across questions we actually asked -> one score per value
-> per-axis top guess + within-axis margin.

TRACING: emits per-call the backend, each probe answer, the top-K ranked (value, axis,
score), per-axis winners + margins, and the recovery decision — so weak fingerprints can be
mined from traces (which axes rank low, backend failures vs genuine low similarity).
"""
from __future__ import annotations

import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

_REF_PATH = os.path.join(os.path.dirname(__file__), "data", "axis_reference_embeddings.npz")
_TITAN_MODEL = "amazon.titan-embed-text-v2:0"


def _noop_emit(name: str, data: dict | None = None, *, step=None) -> None:
    pass


# Margin -> P(this axis guess is actually one of the planted axes). Calibrated on the
# eval combos (Titan): empirical precision by margin band was <0.05->~5%, 0.05-0.12->~10%,
# 0.12-0.16->~47%, 0.16-0.22->~55%, >0.22->~very high. We expose this so the writer can
# weight each hint, and so a high-confidence top guess can be prepended directly.
def margin_to_likelihood(margin: float) -> float:
    if margin >= 0.22:
        return 0.90
    if margin >= 0.16:
        return 0.55
    if margin >= 0.12:
        return 0.45
    if margin >= 0.08:
        return 0.12
    if margin >= 0.05:
        return 0.10
    return 0.05


@dataclass(frozen=True)
class AxisGuess:
    axis: str
    value: str
    score: float
    margin: float  # gap to the 2nd-best value of the SAME axis (axis confidence)

    @property
    def likelihood(self) -> float:
        return margin_to_likelihood(self.margin)


@dataclass
class Fingerprint:
    backend: str
    guesses: list[AxisGuess]
    top_value: str | None
    confident: list[AxisGuess] = field(default_factory=list)

    def lead_token(self) -> str | None:
        if not self.confident:
            return None
        return self.confident[0].value

    def confident_lead(self, min_margin: float) -> str | None:
        """A single concept WORD to prepend, only if the top guess clears min_margin."""
        if not self.guesses or self.guesses[0].margin < min_margin:
            return None
        words = [w for w in re.findall(r"[A-Za-z]+", self.guesses[0].value) if len(w) > 3]
        return words[0].lower() if words else None

    def guess_values(self, k: int = 4) -> list[str]:
        """Top-k guessed axis VALUES (for centering the writer). Always available."""
        return [g.value for g in self.guesses[:k]]

    def ranked_guesses(self, k: int = 5) -> list[AxisGuess]:
        """Top-k guesses (with axis/score/margin/likelihood) for the writer prompt."""
        return self.guesses[:k]


class Fingerprinter:
    """Loads the multi-question reference matrix once; scores probe answers at runtime.

    Construction never raises: missing matrix/numpy -> a no-op that returns
    Fingerprint(backend="none").
    """

    # Within-axis margin to call an axis "confident". Calibrated on the eval combos
    # (Titan): gate 0.04 -> 5.3 guesses/combo at 18% precision (mostly noise); 0.12 ->
    # ~1 guess/combo at 55% precision. We want few, trustworthy hints for the writer.
    MARGIN_GATE = 0.12
    TOP_K_TRACE = 12

    def __init__(self, emit: Callable[..., None] | None = None,
                 timeout: float = 8.0, region: str | None = None) -> None:
        self.emit = emit or _noop_emit
        self.timeout = timeout
        self.region = region or os.environ.get("AWS_REGION") or "us-east-1"
        self._vectors = None      # [N,1024] L2-normed
        self._axes: list[str] = []
        self._values: list[str] = []
        self._questions: list[str] = []   # per-row question id
        self._texts: list[str] = []
        self._titan = None
        self._titan_tried = False
        self._char_cache: dict[str, tuple] = {}  # qid -> (vectorizer, matrix, row_idx)
        self._load_refs()

    def _load_refs(self) -> None:
        try:
            data = np.load(_REF_PATH, allow_pickle=True)
            self._vectors = data["vectors"].astype(np.float32)
            self._axes = [str(a) for a in data["axes"]]
            self._values = [str(v) for v in data["values"]]
            self._texts = [str(t) for t in data["texts"]]
            # questions column is v6-only; tolerate older single-question matrices
            self._questions = ([str(q) for q in data["questions"]]
                               if "questions" in data.files else ["_" for _ in self._values])
        except Exception as exc:
            self.emit("fingerprint_refs_unavailable", {"error": repr(exc)[:200]})

    @property
    def ready(self) -> bool:
        return self._vectors is not None

    # -- main entry: dict {qid: judge_answer} ----------------------------------
    def identify(self, answers_by_question: dict[str, str]) -> Fingerprint:
        answers = {q: a for q, a in (answers_by_question or {}).items() if a and a.strip()}
        if not self.ready or not answers:
            self.emit("fingerprint", {"backend": "none", "reason": "no refs or empty answers"})
            return Fingerprint(backend="none", guesses=[], top_value=None)

        # per-value accumulated score across the questions we asked
        value_scores: dict[str, list[float]] = defaultdict(list)
        value_axis: dict[str, str] = {}
        backend_used = "none"
        for qid, ans in answers.items():
            sims, backend = self._score_one(qid, ans)
            if sims is None:
                continue
            backend_used = backend
            rows = self._rows_for_question(qid)
            for ridx, sim in zip(rows, sims):
                value_scores[self._values[ridx]].append(float(sim))
                value_axis[self._values[ridx]] = self._axes[ridx]
        if not value_scores:
            self.emit("fingerprint", {"backend": "none", "reason": "all backends failed"})
            return Fingerprint(backend="none", guesses=[], top_value=None)

        agg = {v: sum(ss) / len(ss) for v, ss in value_scores.items()}
        fp = self._assemble(agg, value_axis, backend_used)
        self._trace(answers, backend_used, agg, value_axis, fp)
        return fp

    def _rows_for_question(self, qid: str) -> list[int]:
        return [i for i, q in enumerate(self._questions) if q == qid] or list(range(len(self._values)))

    # -- scoring per question (titan primary, char-tfidf fallback) -------------
    def _score_one(self, qid: str, text: str) -> tuple[np.ndarray | None, str]:
        rows = self._rows_for_question(qid)
        vec = self._titan_embed(text)
        if vec is not None:
            q = vec / (np.linalg.norm(vec) + 1e-9)
            return self._vectors[rows] @ q, "titan"
        try:
            return self._char_tfidf_sims(qid, rows, text), "char_tfidf"
        except Exception as exc:
            self.emit("fingerprint_fallback_failed", {"qid": qid, "error": repr(exc)[:200]})
            return None, "none"

    def _titan_embed(self, text: str) -> np.ndarray | None:
        try:
            if self._titan is None and not self._titan_tried:
                self._titan_tried = True
                import boto3
                self._titan = boto3.client("bedrock-runtime", region_name=self.region)
            if self._titan is None:
                return None
            import json
            r = self._titan.invoke_model(modelId=_TITAN_MODEL, body=json.dumps({"inputText": text}))
            return np.asarray(json.loads(r["body"].read())["embedding"], dtype=np.float32)
        except Exception as exc:
            self.emit("fingerprint_titan_failed", {"error": repr(exc)[:200], "falling_back_to": "char_tfidf"})
            return None

    def _char_tfidf_sims(self, qid: str, rows: list[int], text: str) -> np.ndarray:
        if qid not in self._char_cache:
            from sklearn.feature_extraction.text import TfidfVectorizer
            vec = TfidfVectorizer(lowercase=True, analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
            mat = vec.fit_transform([self._texts[i] for i in rows])
            self._char_cache[qid] = (vec, mat, rows)
        from sklearn.metrics.pairwise import cosine_similarity
        vec, mat, _ = self._char_cache[qid]
        return cosine_similarity(vec.transform([text]), mat)[0]

    # -- assemble per-axis guesses --------------------------------------------
    def _assemble(self, agg: dict[str, float], value_axis: dict[str, str], backend: str) -> Fingerprint:
        by_axis: dict[str, list[tuple[float, str]]] = defaultdict(list)
        for v, s in agg.items():
            by_axis[value_axis[v]].append((s, v))
        guesses = []
        for axis, lst in by_axis.items():
            lst.sort(reverse=True)
            top_s, top_v = lst[0]
            margin = top_s - (lst[1][0] if len(lst) > 1 else 0.0)
            guesses.append(AxisGuess(axis=axis, value=top_v, score=top_s, margin=margin))
        guesses.sort(key=lambda g: g.score, reverse=True)
        confident = [g for g in guesses if g.margin >= self.MARGIN_GATE]
        return Fingerprint(backend=backend, guesses=guesses,
                           top_value=guesses[0].value if guesses else None, confident=confident)

    def _trace(self, answers, backend, agg, value_axis, fp: Fingerprint) -> None:
        ranked = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)[: self.TOP_K_TRACE]
        self.emit("fingerprint", {
            "backend": backend,
            "answers": {q: (a or "")[:140] for q, a in answers.items()},
            "top_k": [{"value": v, "axis": value_axis[v], "score": round(s, 4)} for v, s in ranked],
            "axis_guesses": [{"axis": g.axis, "value": g.value, "score": round(g.score, 4),
                              "margin": round(g.margin, 4)} for g in fp.guesses[:8]],
            "confident": [{"axis": g.axis, "value": g.value, "margin": round(g.margin, 4)}
                          for g in fp.confident],
            "top_value": fp.top_value,
        }, step="fingerprint")
