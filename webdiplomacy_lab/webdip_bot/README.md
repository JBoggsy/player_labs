# webdip_bot — webDiplomacy players

One image holds every agent. The launcher's child process is `python -m webdip_bot.bot`,
and it plays the personality named by `WEBDIP_POLICY`. That is baked at build time with
`docker build --build-arg POLICY=<name>`; the default is `machiavelli`. The image is built
`FROM` the published webdiplomacy 0.7.7 player image (pinned by digest) and adds the
`diplomacy` package (AGPL-3.0) as a fallback adjudicator.

## Modules

| Module | What it is |
| --- | --- |
| `bot.py` | Phase loop. Reads context and public files, chooses, saves with Ready, diffs saved orders, and prints one `decision` JSON line per phase (`trace` holds activation counters, plus `rejected` and `compute_ms`). `policy_class()` resolves `name[:KEY=VAL,...]` through personalities and config overrides. |
| `dumbbot.py` | DumbBot (David Norman's heuristic) on webDip's map graph, after the MIT port in diplomacy/research. Used for retreats, builds, seeds and opponent models. |
| `search.py` | **SearchBot.** Owns decision state, phase dispatch and movement setup; selects the opponent model and evaluator. Build search and spring rollout remain here. |
| `search_moves.py` | DumbBot seeds, single/pair/triple/convoy alternatives, coordinate ascent, restarts, candidate retention and mixed selection. |
| `opponent_model.py` | Adaptive belief/history updates, competent/random sampling and level-0/1/2 opponent plans. Add a model class and registry entry to select it through `OPP_MODEL`. |
| `evaluation.py` | Projected/learned evaluator registry, fast/package scoring, risk aggregation and diplomacy adjustment. Reads live config weights; SearchBot selects the evaluator when a decision starts. |
| `search_orders.py` | Order keys/conversion, cached map adapter and package adjudication. `search.py` retains the imports used by NashBot and diagnostics. |
| `check_search_parity.py` | Differential capture/compare against a baseline image: full orders, RNG, exact score digests, memory, traces and optional modes. See the module docstring for invocation. |
| `fastadj.py` | Kruijswijk guess-and-check adjudicator (Hold, Move, Support), about 100x faster than the package. `check_fastadj.py` verified it: 0 mismatches over 10,416 real positions with random orders. Search normally approximates convoys before adjudication; with `SEARCH_CONVOY_APPROX=0`, convoy plans fall back to the `diplomacy` package. |
| `nash.py` | **NashBot.** Regret matching over candidate plans for all seven powers (SearchBot-paper style), then a best response to the opponents' average strategies. |
| `valuefn.py` | Learned position evaluation (ridge regression, fitted by `tools/value_fit.py`, weights in `value_weights.json`). Used as a drop-in evaluation it is exploited by the search (Kutuzov scored 0.33), so it survives only as a blend gene. |
| `personalities.py` | The roster: base policy + config overrides + motto. |
| `field/` | Frozen arena opponents: `dumbbot_v1` (Calhamer) and `random_legal` (equivalent to the league filler). |
| `arena.py` | Local-only dispatcher: picks this seat's policy by slot from argv. |
| `config.py` | Every weight and switch, with defaults. |

## Personalities

| Name | Base | Style |
| --- | --- | --- |
| random | random_legal | uniform-random legal orders (the platform's filler) |
| calhamer | frozen DumbBot v1 | classic yardstick |
| machiavelli | search | the champion line (`webdip-dumbbot` v4/v5) |
| bismarck | search | attack-heavy weights, shrugs off losses |
| metternich | search | defensive, share objective |
| talleyrand | search | maximizes SC² share |
| napoleon | search | spring moves re-ranked by a simulated autumn |
| kissinger | search | level-1 opponents (they best-respond too) |
| kutuzov | search | learned evaluation (negative result) |
| blucher | search | bred by `tools/evolve.py` (g2-0ed5) |
| nash | nash | regret-matching equilibrium |

## Opponent belief (important)

`OPP_LIKELIHOOD = "competent"` (the default since v5) classifies each opponent as
competent or uniform-random. It looks at whether that power's past orders are
*sensible*: holds, plain moves, and supports or convoys of its own units count as
sensible, while supports or convoys of other powers' units mark random play. The old
rule (match DumbBot samples or be called random) labelled strong search opponents as
random. That cost about 0.1 score in the local A/B and was visible in hosted
telemetry (`opp_random_samples`).
