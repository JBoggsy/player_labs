"""StyleClassifier — cheap local TF-IDF nearest-neighbor over a shipped
reference library (player-design §5; validated at ~96% top-1 by probe finding 4).

The library (data/library.json) holds, for each of the 61 known styles, the
judge's answers to our fixed private questions across multiple independent
temp-0.7 draws. At runtime the judge's 3 answers are fingerprinted the same way
and matched by max cosine over each style's draws. No LLM, no network.
"""
from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass

DEFAULT_LIBRARY_PATH = os.path.join(os.path.dirname(__file__), "data", "library.json")


def feat_word_raw(text: str) -> list[str]:
    # Keep case, short function words, and standalone punctuation: style lives there.
    return re.findall(r"[A-Za-z0-9']+|[^\sA-Za-z0-9]", text)


def feat_char_3_5(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text)
    grams: list[str] = []
    for n in range(3, 6):
        grams += [text[i:i + n] for i in range(len(text) - n + 1)]
    return grams


FEATURIZERS = {"word_raw": feat_word_raw, "char_3_5": feat_char_3_5}


@dataclass
class StyleMatch:
    index: int
    style: str  # the full concept descriptor text
    score: float  # cosine similarity of the best-matching draw


class StyleClassifier:
    def __init__(self, library_path: str = DEFAULT_LIBRARY_PATH, featurizer: str = "word_raw") -> None:
        lib = json.load(open(library_path))
        self.questions: list[str] = lib["questions"]
        self.styles: list[str] = lib["styles"]
        self._featurize = FEATURIZERS[featurizer]
        # draws[style_index] = list of independent draws, each a list of
        # one answer per question.
        draws: dict[str, list[list[str]]] = lib["draws"]
        docs: list[tuple[int, list[str]]] = []  # (style_index, tokens)
        for key, style_draws in draws.items():
            for draw in style_draws:
                docs.append((int(key), self._fingerprint(draw)))
        self._idf = _build_idf([tokens for _, tokens in docs])
        self._ref_vecs = [(idx, _vec(tokens, self._idf)) for idx, tokens in docs]

    def _fingerprint(self, answers: list[str]) -> list[str]:
        return self._featurize("\n".join(answers))

    def classify(self, judge_answers: list[str], top_n: int = 3) -> list[StyleMatch]:
        """Rank styles by max cosine over each style's reference draws."""
        qv = _vec(self._fingerprint(judge_answers), self._idf)
        best: dict[int, float] = {}
        for idx, rv in self._ref_vecs:
            sim = _cosine(qv, rv)
            if sim > best.get(idx, -1.0):
                best[idx] = sim
        ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)
        return [StyleMatch(index=i, style=self.styles[i], score=s) for i, s in ranked[:top_n]]


def _build_idf(docs: list[list[str]]) -> dict[str, float]:
    n = len(docs)
    df: Counter[str] = Counter()
    for doc in docs:
        for term in set(doc):
            df[term] += 1
    return {term: math.log((n + 1) / (count + 1)) + 1.0 for term, count in df.items()}


def _vec(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = Counter(tokens)
    return {t: c * idf.get(t, 0.0) for t, c in tf.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0
