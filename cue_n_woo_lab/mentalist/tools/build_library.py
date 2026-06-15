"""Build mentalist's shipped reference library from the probe's generation cache.

The probe cache (probe/cache/generations.json) holds two independent temp-0.7
draws per style ("refs" and "tests") for the same 3 private questions mentalist
asks at runtime — both graduate into the player library as reference draws
(multi-draw k-NN cuts sampling noise, player-design §5).

Run from the repo root:
    uv run python cue_n_woo_lab/mentalist/tools/build_library.py
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.normpath(os.path.join(HERE, "..", "..", "probe"))
OUT = os.path.normpath(os.path.join(HERE, "..", "data", "library.json"))


def main() -> None:
    cache = json.load(open(os.path.join(PROBE, "cache", "generations.json")))
    styles = json.load(open(os.path.join(PROBE, "concepts.json")))
    n = len(styles)
    assert len(cache["refs"]) == n and len(cache["tests"]) == n, "cache/style count mismatch"
    draws = {str(i): [cache["refs"][str(i)], cache["tests"][str(i)]] for i in range(n)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(
        {"questions": cache["questions"], "styles": styles, "draws": draws},
        open(OUT, "w"),
        indent=1,
    )
    print(f"wrote {OUT}: {n} styles x {len(draws['0'])} draws x {len(cache['questions'])} questions")


if __name__ == "__main__":
    main()
