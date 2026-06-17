"""Build the axis reference-embedding matrix shipped in the mentalist_v4 image.

For each of the 326 single-axis values, we have (a) the judge's self-report under that
value alone, and (b) its Titan-v2 embedding. This bakes them into one npz:

  vectors : float32 [N, 1024]   L2-normalized Titan embeddings
  axes    : str [N]             axis name per row
  values  : str [N]             axis value per row
  texts   : str [N]             the self-report text (for trace/debug)

Source data lives in the probe cache (cache_srv2/ self-reports + embed_cache/ Titan
vectors), produced by probe_selfreport_v2.py and compare_matchers.py. Re-run those first
if the cache is missing. This script does NOT call the judge; it only re-embeds any
self-report not already in embed_cache (cheap Titan calls on the softmax profile).

Usage:
  uv run --with boto3 --with numpy python build_reference_embeddings.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np

PROBE = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "probe"))
sys.path.insert(0, PROBE)
import probe_selfreport_v2 as P  # noqa: E402

EMBED_CACHE = os.path.join(PROBE, "embed_cache")
TITAN_MODEL = "amazon.titan-embed-text-v2:0"
OUT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "axis_reference_embeddings.npz"))


def _client():
    import boto3
    return boto3.Session(profile_name="softmax", region_name="us-east-1").client("bedrock-runtime")


def embed(text: str, client) -> list[float]:
    key = hashlib.sha1(text.encode()).hexdigest()[:20]
    path = os.path.join(EMBED_CACHE, f"{key}.json")
    if os.path.exists(path):
        return json.load(open(path))
    body = json.dumps({"inputText": text or " "})
    r = client.invoke_model(modelId=TITAN_MODEL, body=body)
    vec = json.loads(r["body"].read())["embedding"]
    os.makedirs(EMBED_CACHE, exist_ok=True)
    json.dump(vec, open(path, "w"))
    return vec


def main() -> None:
    axes = P.load_axes()
    rows = [(ax, v) for ax in sorted(axes) for v in axes[ax] if P.is_cached(v)]
    missing = sum(1 for ax in sorted(axes) for v in axes[ax] if not P.is_cached(v))
    if missing:
        print(f"WARNING: {missing} single-axis self-reports not cached; run probe_selfreport_v2.py --refs-only")

    client = _client()
    vectors, axn, vals, texts = [], [], [], []
    for i, (ax, v) in enumerate(rows, 1):
        text = P.gen(v)  # cached self-report
        vec = np.asarray(embed(text, client), dtype=np.float32)
        vec /= np.linalg.norm(vec) + 1e-9
        vectors.append(vec)
        axn.append(ax)
        vals.append(v)
        texts.append(text)
        if i % 50 == 0 or i == len(rows):
            print(f"  embedded {i}/{len(rows)}", flush=True)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    np.savez_compressed(OUT,
                        vectors=np.vstack(vectors).astype(np.float32),
                        axes=np.array(axn), values=np.array(vals), texts=np.array(texts))
    print(f"wrote {OUT}  ({len(rows)} values, dim={vectors[0].shape[0]})")


if __name__ == "__main__":
    main()
