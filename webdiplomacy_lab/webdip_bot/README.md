# webdip_bot — webDiplomacy players

One image holds every agent. The launcher's child process is `python -m webdip_bot.bot`,
and it plays the personality named by `WEBDIP_POLICY`. That is baked at build time with
`docker build --build-arg POLICY=<name>`; the default is `machiavelli`. The image is built
`FROM` the published webdiplomacy 0.7.7 player image (pinned by digest) and adds the
`diplomacy` package (AGPL-3.0) as a fallback adjudicator. A separate pinned Nim
builder compiles the native adjudicator; only its extension and license notices
are copied into the runtime image.

## Modules

| Module | What it is |
| --- | --- |
| `bot.py` | Phase loop. Reads context and public files, chooses, saves with Ready, diffs saved orders, and prints one `decision` JSON line per phase (`trace` holds activation counters, plus `rejected` and `compute_ms`). `policy_class()` resolves `name[:KEY=VAL,...]` through personalities and config overrides. |
| `dumbbot.py` | DumbBot (David Norman's heuristic) on webDip's map graph, after the MIT port in diplomacy/research. Used for retreats, builds, seeds and opponent models. |
| `search.py` | **SearchBot.** Owns decision state, phase dispatch and movement setup; selects the opponent model and evaluator. |
| `search_lookahead.py` | Winter builds/disbands ranked by a reduced spring search, and spring plans re-ranked by a simulated autumn. |
| `search_moves.py` | DumbBot seeds, single/pair/triple/convoy alternatives, coordinate ascent, restarts, candidate retention and mixed selection. |
| `opponent_model.py` | Adaptive belief/history updates, competent/random sampling and level-0/1/2 opponent plans. Add a model class and registry entry to select it through `OPP_MODEL`. |
| `evaluation.py` | Projected/learned evaluator registry, fast/package scoring, risk aggregation and diplomacy adjustment. Reads live config weights; SearchBot selects the evaluator when a decision starts. |
| `search_orders.py` | Order keys/conversion, cached map adapter and package adjudication. `search.py` retains the imports used by NashBot and diagnostics. |
| `check_search_parity.py` | Differential capture/compare against a baseline image: full orders, RNG, exact score digests, memory, traces and optional modes. See the module docstring for invocation. |
| `fastadj.py` | Imports the native `adjudicate` entry point; retains `Adjudicator` as the Python test reference. Both implement Hold/Move/Support. `check_fastadj.py` compares production results with the package on non-convoy orders, tolerating package auto-disbands of dislodged units. |
| `adjudicator_native.nim` | Native integer/boolean resolver and Nimpy boundary. Python owns order conversion, scoring and RNG. |
| `check_native_adjudicator.py` | Exhaustive tiny-board and seeded larger-plan native/reference comparisons, including exact boolean results. |
| `nash.py` | **NashBot.** Regret matching over candidate plans for all seven powers (SearchBot-paper style), then a best response to the opponents' average strategies. |
| `valuefn.py` | Ridge-regression position evaluation, fitted by `tools/value_fit.py`, with weights in `value_weights.json`. `LearnedEvaluator` blends its prediction with projected centre value. |
| `personalities.py` | The roster: base policy + config overrides + motto. |
| `field/` | Frozen arena opponents: `dumbbot_v1` (Calhamer) and `random_legal` (equivalent to the league filler). |
| `arena.py` | Local-only dispatcher: picks this seat's policy by slot from argv. |
| `config.py` | Every weight and switch, with defaults. |

## Personalities

| Name | Base | Style |
| --- | --- | --- |
| random | random_legal | uniform-random legal orders (the platform's filler) |
| calhamer | frozen DumbBot v1 | classic yardstick |
| machiavelli | search | default search weights, level-0 opponents |
| bismarck | search | attack-heavy weights, shrugs off losses |
| metternich | search | defensive, share objective |
| talleyrand | search | maximizes SC² share |
| napoleon | search | spring moves re-ranked by a simulated autumn |
| kissinger | search | level-1 opponents (they best-respond too) |
| kutuzov | search | learned evaluation |
| blucher | search | attack-heavy weights, level-0 opponents |
| nash | nash | regret-matching equilibrium |
| kissinger2 | search | level-2 opponents (best responses to level-1 plans) |
| fabius | search | level-1 opponents, risk aversion and defensive weights |
| garibaldi | search | level-1 opponents and attack-heavy weights |
| rasputin | search | level-1 opponents, mixed selection among top plans |
| castlereagh | search | level-1 opponents and hostility-based centre values |

## Opponent belief

`OPP_LIKELIHOOD="competent"` combines matching past DumbBot samples with evidence
that the observed order is sensible: Hold/Move, or a support/convoy involving the
power's own provinces. `"dumbbot"` uses only sample matches with smoothing. Each
observation updates per-power log-odds against uniform-random legal orders; the
sigmoid gives the next DumbBot sample share. `OPP_MODEL="dumbbot"` forces that
share to 1 while retaining the same sampling and history machinery.

`update_beliefs` consumes the pending movement record and fetches the matching
public history phase. It calls `update_hostility` first (decay, then count attacks
and supports into our previous provinces), then `update_type_beliefs`. Hostility
is tracked even when `DIPLO=0`; the evaluator decides whether to use it.

## How to tune / extend

`config.py` is the canonical flat tuning surface. `policy_class` applies the named
personality's overrides, then explicit `name:KEY=VAL,...` overrides. For example:

```python
from webdip_bot.bot import policy_class

Bot = policy_class("kissinger:SEARCH_RESTARTS=2,SEARCH_SOFTMAX_T=0.5")
# Construct Bot with the usual variant, board, country, phase, turn and RNG.
```

Config remains a live module: resolving a policy does **not** reset unspecified
values. Use a fresh process, or explicitly restore defaults, between experiments.
Scalar overrides convert to the existing value's type. List values use JSON, but
the outer comma splitter does not support multi-element JSON lists; set those
through a personality or directly in config rather than changing parser behavior.
`WEBDIP_SEARCH_BUDGET_S` supplies the budget default at import time; an explicit
`SEARCH_TIME_BUDGET_S` override takes precedence.

| Concern | Knobs (all names remain in `config.py`) | Implementation / extension point |
| --- | --- | --- |
| Opponent samples and competence | `OPP_MODEL`, `OPP_MODEL_LEVEL`, `OPP_LEVEL1_SHARE`, `OPP_PRIOR_LOGODDS`, `OPP_LOGODDS_CLIP`, `OPP_LIKELIHOOD`, `SEARCH_OPPONENT_SAMPLES` | `opponent_model.py`: subclass `OpponentModel`, add an `OPPONENT_MODELS` entry |
| Seeds, ascent and coordinated orders | `SEARCH_SEEDS`, `SEARCH_PASSES`, `SEARCH_RESTARTS`, `SEARCH_PAIRS`, `SEARCH_TRIPLES`, `SEARCH_CONVOYS` | `search_moves.py`: `seed_plans`, `ascend`, `joint_alternatives` |
| Candidate retention and mixed play | `SEARCH_SOFTMAX_T`, `SEARCH_SOFTMAX_POOL`, `SEARCH_ROLLOUT_POOL` | `search_moves.py`: `remember`, `select_mixed` |
| Static score and risk | `SEARCH_EVAL`, `SEARCH_SC_WEIGHT`, `SEARCH_POS_WEIGHT`, `SEARCH_DISLODGED_WEIGHT`, `SEARCH_OBJECTIVE`, `SEARCH_LEARNED_WEIGHT`, `SEARCH_RISK`, `SEARCH_FAST_ADJ` | `evaluation.py`: subclass `PositionEvaluator`, add an `EVALUATORS` entry |
| Diplomacy | `DIPLO`, `DIPLO_HOSTILE`, `DIPLO_GRUDGE`, `DIPLO_PEACE`, `DIPLO_STAB_YEAR`; history decay: `DIPLO_DECAY` | `PositionEvaluator.diplomacy_adjust`; `OpponentModel.update_hostility` |
| Lookahead | `SEARCH_ROLLOUT`, `SEARCH_ROLLOUT_POOL`, `SEARCH_ROLLOUT_SAMPLES`, `SEARCH_ROLLOUT_STATIC_WEIGHT`, `SEARCH_BUILDS`, `SEARCH_BUILD_CANDIDATES` | `search_lookahead.py`: `rollout_rerank`, `rollout`, `search_adjustments`, `spring_value` |
| Time budget | `SEARCH_TIME_BUDGET_S` | Clock checks in movement, lookahead and Nash; preserve check locations when refactoring |
| Convoy conversion | `SEARCH_CONVOY_APPROX` | `search_orders.py`: `fast_orders` |
| Heuristic and equilibrium policies | Proximity, size, seasonal attack/defense, strength, competition, build and alternative weights; `NASH_CANDIDATES`, `NASH_ITERS`, `NASH_EVAL_SAMPLES` | `dumbbot.py`, `nash.py` |

The following extension examples illustrate code shape; they are not registered
in the shipped image and do not change any existing personality. Put a real class
and its registry entry in the owning module. Components keep a bot reference and
read its current memory/config, so `observe` can replace memory and nested spring
search can temporarily change config. Selection runs at construction and at each
`choose` call. Unknown evaluator strings retain projected scoring; unknown opponent
model strings retain full-DumbBot-share behavior.

Opponent example: an adaptive alias must override `dumb_share`, because the built-in
implementation treats every model name other than `adaptive` as fixed DumbBot.

```python
# In opponent_model.py (math is already imported):
class AdaptiveExample(OpponentModel):
    def dumb_share(self, country):
        lo = self.bot.memory.get("logodds", {}).get(str(country), config.OPP_PRIOR_LOGODDS)
        return 1.0 / (1.0 + math.exp(-lo))

OPPONENT_MODELS["adaptive_example"] = AdaptiveExample
# Select with kissinger:OPP_MODEL=adaptive_example.
```

Evaluator example: retain projected scoring and its exact arithmetic. Override
`center_value` to change fast-path centre valuation; override `score_package`
separately if that new behavior must also apply to the package fallback.

```python
# In evaluation.py:
class ProjectedExample(PositionEvaluator):
    def center_value(self, sc, fu, fo, moved, dislodged, units, orders, projected, me):
        return sc

EVALUATORS["projected_example"] = ProjectedExample
# Select with kissinger:SEARCH_EVAL=projected_example.
```

Search example: change the number of seeds/restarts through config first. For a
new seeding algorithm, the function boundary is an ordered list of `(score, orders)`
pairs, best first. Here is the existing shape, with no behavior change:

```python
# Shape of seed_plans in search_moves.py:
def seed_plans(bot, slots):
    seeder = DumbBot(bot.variant, bot.board, bot.country, bot.phase, bot.turn,
                     bot.rng, board_model=bot.b)
    seeds = []
    for _ in range(config.SEARCH_SEEDS):
        candidate = seeder.choose(slots)
        seeds.append((bot.evaluator.evaluate(candidate), candidate))
    seeds.sort(key=lambda item: -item[0])
    bot.trace["search_seed_score"] = round(seeds[0][0], 1)
    return seeds
```

## Contracts and parity checks

- All components share the same RNG. Sample generation, set/dict iteration, stable
  sorting and even unused draws affect later decisions. Preserve their order.
- Keep floating expressions and reduction order, including Python 3.12 `sum`.
  Fast scoring sums positional values then divides; package scoring divides each
  term before adding. Package scoring does not apply learned or diplomacy terms.
- Order equality/dedup keys intentionally omit convoy path/flag fields. Ascent
  improves only above `best_score + 1e-9`; retained lists keep their identities.
- `spring_value` constructs a plain SearchBot with the same RNG and shared log-odds,
  temporarily changes six search settings and restores them in `finally`. It uses
  the nested decision's rounded trace score.
- Convoy approximation ignores fleet dislodgement. With approximation disabled,
  ordinary evaluation falls back to the package; opponent improvement rejects
  unconvertible contexts and rollout skips unconvertible samples instead.
- Nash keeps the SearchBot phase interface and shared state. `search.py` re-exports
  `_key`, `dipmap` and `fast_orders` for existing callers; internal components call
  each other directly.

From the repository root, build and check the immutable golden corpus:

```bash
docker buildx build --platform linux/amd64 --load -t webdip-bot:refactor webdiplomacy_lab/webdip_bot
docker run --rm --platform linux/amd64 -v "$PWD/webdiplomacy_lab:/lab:ro" \
  --entrypoint /opt/.venv/bin/python webdip-bot:refactor \
  -m webdip_bot.golden check /lab/webdip_bot/tests/golden.json
```

The golden check covers 334 Kissinger/Machiavelli decisions and order signatures.
For refactors, also run `check_search_parity.py` against a preserved baseline image
(see its module docstring). It checks full orders, RNG primitives/state, exact
score digests, memory, candidate ordering, non-timing traces and config restoration;
optional cases cover lookahead, beliefs, mixed play, all personalities and scripted
binding budgets. Finite fixtures do not prove every position. Equal real-time
budgets can visit different candidates after performance changes.

When changing adjudication or order conversion, also run the package comparison:

```bash
docker run --rm --platform linux/amd64 -v "$PWD/webdiplomacy_lab/local_runs:/runs:ro" \
  --entrypoint /opt/.venv/bin/python webdip-bot:refactor \
  -m webdip_bot.check_fastadj /runs 2
```

The replay directory must already exist; it is read-only input. Profile a decision
with `-m webdip_bot.profile_search /runs kissinger` using the same mount.
For a frozen golden position, use
`-m webdip_bot.profile_search /lab/webdip_bot/tests/golden.json kissinger --case 56`
with the `/lab` mount above. Add `--no-profile --warmup 1` for unprofiled timings.
The JSON record includes fixture hash, config, runtime, full-decision/choose times,
behavior digest and (when enabled) per-function profile data. Reject budget-hit
runs and require equal behavior digests before comparing timings. Performance
comparisons need matched fixtures and interleaved baseline/candidate runs under
concurrent load; correctness-check runtimes alone are not speedup evidence.


## Native build and reference checks

The Dockerfile pins the Nim 2.2.4 linux/amd64 builder by digest, Nimpy by commit and
archive SHA-256, and the existing player runtime by digest. It compiles
`adjudicator_native.nim` with `-d:release --app:lib --threads:on`, without unsafe
math flags, then checks import and an empty-board result in the actual Python 3.12
runtime. Nim and Nimpy license notices are included under `/opt/webdip_bot/licenses`.
No global compiler install is required; use the Docker build command above.

`fastadj.adjudicate` always calls the extension. A missing extension is an import
error, not a silent switch to slower Python. Local host imports of search therefore
need a compatible compiled extension; the supported test/run environment is the
linux/amd64 image. `Adjudicator(units, orders).run()` is retained only as the explicit
Python reference for verification. When changing resolution rules, update both
implementations and compare them before accepting a change:

```bash
docker run --rm --platform linux/amd64 --entrypoint /opt/.venv/bin/python \
  webdip-bot:refactor -m webdip_bot.check_native_adjudicator
```

This checks 174,089 tiny-board/seeded/empty inputs. Also run golden, exact search
parity and the package comparison above. The native boundary accepts the same
province-level unit/order tuples and returns two lists of Python bools. The resolver
preserves dependency traversal and both guesses for cycles. All RNG operations,
learned/diplomacy valuation and floating reductions stay in Python; the convoy
approximation and package fallback rules are unchanged.
