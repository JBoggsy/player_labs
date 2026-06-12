"""Classifier sanity + leave-one-draw-out accuracy over the shipped library.

The honest held-out measurement (separate fresh draws) was done in the probe
(finding 4: ~96% top-1). Here we guard regressions cheaply: classifying each
library draw against ONLY the other draw's vectors must stay strong, and the
plumbing (questions/styles alignment, ranking shape) must hold.
"""
import json
import os

import pytest

from mentalist import config
from mentalist.classifier import DEFAULT_LIBRARY_PATH, StyleClassifier


pytestmark = pytest.mark.skipif(
    not os.path.exists(DEFAULT_LIBRARY_PATH),
    reason="library not built (run tools/build_library.py)",
)


def test_library_questions_match_config():
    lib = json.load(open(DEFAULT_LIBRARY_PATH))
    assert lib["questions"] == config.PRIVATE_QUESTIONS, (
        "library and runtime private questions diverged — fingerprints not comparable"
    )
    assert len(lib["styles"]) == 61


def test_classify_shape():
    clf = StyleClassifier()
    matches = clf.classify(["Arr matey, the dawn", "Hoist the colors", "A storm brews"], top_n=3)
    assert len(matches) == 3
    assert matches[0].score >= matches[1].score >= matches[2].score
    assert all(m.style for m in matches)


def test_cross_draw_accuracy():
    lib = json.load(open(DEFAULT_LIBRARY_PATH))
    n = len(lib["styles"])
    # Classify each style's second draw using a classifier whose library is
    # rebuilt with only first draws (and vice versa would be symmetric).
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(
            {
                "questions": lib["questions"],
                "styles": lib["styles"],
                "draws": {k: v[:1] for k, v in lib["draws"].items()},
            },
            f,
        )
        refs_only = f.name
    clf = StyleClassifier(library_path=refs_only, featurizer=config.CLASSIFIER_FEATURIZER)
    top1 = sum(
        clf.classify(lib["draws"][str(i)][1], top_n=1)[0].index == i for i in range(n)
    )
    os.unlink(refs_only)
    assert top1 / n >= 0.90, f"top-1 regression: {top1}/{n}"
