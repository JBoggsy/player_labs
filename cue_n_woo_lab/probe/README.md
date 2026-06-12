# probe/ — Cue-n-Woo worker spike

Throwaway-ish research scripts that probe the live FLAS/Gemma judge worker directly
to settle player-design questions before building. **Not player code.** Findings are
written up in [`../docs/probe-findings.md`](../docs/probe-findings.md).

The worker (`https://cue-n-woo-worker.softmax-research.net`) serves unsigned requests
at normal priority (no auth/VPN), so these run from a laptop with no local GPU. It is
slow and shared (~1 generation / 10s), so generation-heavy probes batch + cache.

| File | What it does |
|---|---|
| `worker_client.py` | Unsigned client mirroring the game's `/generate` + `/choice-logprobs` wire format and both-orderings scoring. Reused by all probes. |
| `concepts.json` | The 61 hidden styles (copied from the game repo's `data/concepts.json`). |
| `probe_classify.py` | Finding 2: cheap TF-IDF NN style classification, full 61-way confusion. |
| `probe_scoring.py` | Finding 3: in-style vs plain vs off-topic answer matchups under the real scorer. |
| `probe_style_leverage.py` | Finding 3: is the optimal short answer style-dependent? (choice calls only — fast) |
| `build_cache.py` | Finding 4: generate + cache a reference/test library (slow; one big worker run) → `cache/generations.json`. |
| `classify_offline.py` | Finding 4: offline featurizer bake-off (char n-grams vs word, 1–3 questions) over the cache. No worker calls. |

Run examples are in the findings doc. `cache/` is git-ignored generation output.
