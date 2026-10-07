# compare.py — the Paintbot PW A/B adapter

Part of the [lab tool index](README.md) (dispatcher: `pw.py compare`).
`paintbot_pw_lab/tools/compare.py` answers "did the candidate beat the baseline?" from
downloaded episodes. It reads every episode through `pw_episodes` (hash-checked traces) and
`pw_metrics`, builds one row per (episode, arm policy), and hands the rows to the shared
`coworld-ab` engines: `ab_stats.py` for independent arms, `paired_stats.py` for paired,
head-to-head and sequential tests. The procedure around it is the
[`paintbot-pw-ab` skill](../../.claude/skills/paintbot-pw-ab/SKILL.md); request bodies come
from [`pw_ab_requests.py`](pw_ab_requests.md). Design rationale: plan §7
([`docs/designs/2026-09-29-tooling-plan.html`](../designs/2026-09-29-tooling-plan.html)).

## Commands

Run from the repo root. Pass every episode root of both arms (dirs, batch dirs or local
`.replay` files); arms are assigned by which policy an episode contains, not by directory.

```bash
# Full report (Markdown to stdout; --out writes the result JSON for compare_report.py and the
# experiment record; --json prints the agent envelope instead of the Markdown)
uv run python paintbot_pw_lab/tools/compare.py compare ROOT... --design paired \
    --baseline NAME:vN --candidate NAME:vM [--target elo_outcome|score_outcome] [--margin-scale 1000] \
    [--metrics a,b,...] [--xreq xreq_... --xreq ...] [--requests manifest.json] [--out out.json] [--json]

# Stop check while episodes stream in (same loading, one outcome score)
uv run python paintbot_pw_lab/tools/compare.py sprt ROOT... --design paired \
    --baseline NAME:vN --candidate NAME:vM [--target elo_outcome|score_outcome] [--margin-scale 1000] \
    [--h0 0 --h1 0.05 --alpha 0.05 --beta 0.05] [--out sprt.json] [--json]

# The current ladder's outcome (OpenSkill, margin_scale 600): request it explicitly
uv run python paintbot_pw_lab/tools/compare.py compare ROOT... --design paired \
    --baseline NAME:vN --candidate NAME:vM --target score_outcome --margin-scale 600 --out out.json

# HTML page from the JSON (shared renderer)
uv run python .claude/skills/coworld-ab/scripts/compare_report.py out.json --out ab.html \
    --eyebrow "Paintbot PW · A/B comparison" [--finding finding.md] [--verdict "..."]
```

Policies are given as an exact `policy_version_id`, `local:<name>` (local recordings; the bare
file name, e.g. `base.bas`, also resolves as their label), or `name:vN` resolved against the
episodes' own participants (an ambiguous or unknown label stops the run with exit 2 and
`result.valid`). `--tag`, `--jobs`, `--refresh` pass through to `pw_episodes.load_batch`.

## Outcome scores: current ladder versus historical

| Metric | Formula | Use |
| --- | --- | --- |
| `score_outcome` | `clamp(0.5 + (our mean result score − their mean result score) / (2 × margin_scale), 0, 1)`; attributable forfeit 0/1 | **The current ladder's quantity.** metta's OpenSkill ranking rates a two-team episode by this soft outcome (`openskill.py` at `dcdfc19a`, the `margin_scale` branch). The live paintbot-pw ladder (`league_ae677105…`) has `algorithm openskill`, `margin_scale 600`, so pass `--target score_outcome --margin-scale 600`. Read the scale from the league's `settings.ladder.ranking` before a batch; it can change without a game release. |
| `elo_outcome` (default `--target`, primary) | `clamp(0.5 + (our glory − their glory) / 2000, 0, 1)`; attributable forfeit 0/1 | Historical: the Elo ladder with `margin_scale 1000` that ran until the league moved to OpenSkill. Fixed at 1000 and unaffected by `--margin-scale`, so earlier results keep their meaning. |

`--margin-scale` must be positive and finite (otherwise exit 2). It changes only
`score_outcome`; its default, 1000, equals the historical scale, so a run without the flag
computes the same numbers as `elo_outcome` and never silently adopts the live scale. Scores
are the episode's result scores (`results.json` `scores`, checked by `pw_episodes` against the
hash-verified trace's settled team glory), averaged per team as OpenSkill averages a side.
Clipping matters at 600: any margin of 600 glory or more scores 0 or 1. The scale and both
formulas are written to the result JSON (`outcome`) and printed on the "Outcome scales" line.
OpenSkill rates a forfeited episode by rank (the failed side last), which the 0/1 forfeit
score approximates, as `elo_outcome` already did.

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py compare compare|sprt ROOT... --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | roots of both arms; `--design`, `--baseline`, `--candidate` (required); `--target` (`sprt`: `elo_outcome` or `score_outcome`), `--margin-scale` (positive; default 1000), `--metrics`, `--xreq`, `--requests`, `--h0/--h1/--alpha/--beta`, `--out FILE`, `--tag`, `--jobs`, `--refresh` |
| Outputs | `--out FILE`: the full result JSON with every row (the input of `compare_report.py`) |
| `--json` result | `compare`: the JSON below without `rows` (a count instead); `sprt`: `{decision, llr, lower, upper, n, estimate, stderr, h0, h1, alpha, beta, note, metric, outcome, design, arm_policy_keys, exclusions}`. `counts` holds `rows`, `excluded` and `exclusions` |
| Exit codes | 0 ok; 1 some episodes failed to load (listed as `LOAD FAILED` and in `failures[]`; the analysis still runs on the rest); 2 an unknown or ambiguous arm (`result.valid` lists the labels and keys), both arms resolving to one policy, pooled rules/coworld versions, both arms in one episode under paired/field, an unknown `--metrics` name, a non-positive or non-finite `--margin-scale`; 3 `pw_trace` not built |
| Idempotence / cache | traces are cached, so `sprt` can be rerun as episodes stream in |
| Typical next step | `compare_report.py RUN/ab.json` for the page, then review replays per arm |

## Designs

| `--design` | Episodes | Unit and tests | Groups |
| --- | --- | --- | --- |
| `paired` (recommended) | each arm vs the same opponent; pw_ab_requests gives one request per (arm, opponent, side, seed) | pairs keyed by (opponent, side, seed); seed = `game_config.seed` (hosted) or the engine seed (local). An explicit request seed fixes the world for every episode of that request, so use one single-episode request per (arm, opponent, side, seed): extra episodes replay one match (`duplicate_game`). Means: paired t, and the Wilcoxon signed-rank p must also be < 0.05. Rates: exact McNemar on discordant pairs | `all`, `red`, `blue`, `vs <opponent>` when there is more than one opponent |
| `h2h` | candidate vs baseline in one episode | `elo_outcome` and `score_outcome`: one-sample t vs 0.5; `win_rate`: exact binomial on decisive games (draws dropped); other metrics paired within the episode | `all`, candidate side |
| `field` | unpaired arms, e.g. vs a mix of leaders | Fisher (rates), Welch (means), as `ab_stats` always did | as `paired` |

All three: Benjamini-Yekutieli across every reported (metric, group) test, and no
`improved`/`regressed` verdict below 30 pairs or episodes per arm per group (`SMALL_N`).
`--metrics` restricts the report; fix the list before looking at the data, because every
extra metric and group makes the correction stricter.

## Rows, metrics and accounting

One row per (episode, arm policy). The policy's seats are summed within the episode;
`*_per_seat` metrics divide by its seat count (8 in the league). Ratios come from summed
numerators and denominators (pw_metrics).

| Metric | Kind | Definition |
| --- | --- | --- |
| `elo_outcome` (primary) | mean | historical Elo outcome score, `clamp(0.5 + (our glory − their glory)/2000, 0, 1)`; attributable platform failure = forfeit 0/1 |
| `score_outcome` | mean | current ladder outcome at `--margin-scale` (see "Outcome scores"); forfeit 0/1 |
| `win_rate`, `draw_rate` | rate | per episode; a draw is a non-win |
| `zero_glory_win_rate` | rate | won with 0 glory (worth 0.5 on the ladder, like a draw) |
| `first_capture_rate` | rate | our team completed the match's first capture (strictly earlier) |
| `hearts_held_mean` | mean | our team's heart-ticks / ticks |
| `kills_per_seat`, `deaths_per_seat`, `dealt_hp_enemy_per_seat`, `captures_per_seat`, `trade_kills_per_seat` | mean | policy sum / seats |
| `gun_enemy_accuracy`, `alive_share`, `heart_reach_share`, `idle_share` | mean | pw_metrics policy-level ratios |
| `vm_disabled_suspect_seats` | mean | seats flagged by pw_metrics' idle-to-the-end heuristic (inferred) |
| `ops_fail_rate` | rate, group `all` | platform-failed episodes / all episodes of the arm |

Every episode ends up as a row, a counted exclusion or a listed load failure; the counters
print on the "Exclusions and failure handling" line and go into the JSON:

| Counter | Meaning |
| --- | --- |
| `ops_fail_forfeit_scored` | platform failure attributed to one seat (`failed_policy_index`, error type not infrastructure, per metta `episode_failures.py`): both outcome scores and win scored as a forfeit, all other metrics unknown |
| `ops_fail_unattributed` | infrastructure failure: only `ops_fail_rate` counts it |
| `unfinished` | episode not terminal yet (streaming) |
| `load_<code>` | a completed episode that `pw_episodes` could not verify (`no_replay`, `trace_failed`, `identity`, `results_mismatch`); listed as `LOAD FAILED` |
| `mirror` | the arm policy sits on both teams |
| `neither_arm_policy` | episode without either arm policy |
| `duplicate_game` | same arm, opponent, side, engine seed and final hash as an earlier row: the deterministic engine replayed one game; kept once |
| `unpaired_baseline` / `unpaired_candidate` | paired design rows with no partner under their key |
| `h2h_missing_an_arm` | h2h episode holding only one arm |

The run refuses (exit 2 with a message) when rows span several `rules` or `coworld_version`
values, when an episode holds both arms under `paired`/`field`, or when the two specs
resolve to one policy. A `LOAD FAILED` episode makes the exit code 1 (the analysis still
runs on the rest). `Pairing diagnostics: pairs_with_different_engine_seeds` counts
pairs whose requested seed matched but whose engine seed did not: then the pairing only
matched the request, not the world.

## Result file (`--out`)

`ab_stats.emit_json`'s neutral contract (`baseline, candidate, target, analysis,
deltas[{metric, group, base, cand, n_base, n_cand, p, raw_p, effect, verdict}]`) plus, for
`paired`/`h2h`, each delta's `test` and `detail` (Wilcoxon p, discordant counts, draws), and:
`design`, `unit`, `arm_policy_keys`, `exclusions`, `load_failures`, `pairing`, `sprt` (the
SPRT at the given H0/H1, with its `metric`), `outcome` (`margin_scale` and both outcome
formulas), `requests` (`--xreq` ids and the `--requests`
manifest, stored verbatim) and `rows` (every analysed row). `n_base == n_cand` = pairs used
for paired tests.

## SPRT

`sprt` (and the `SPRT on <metric>` line of `compare`) tests one outcome score: `--target` when
it is `elo_outcome` or `score_outcome`, else the primary `elo_outcome`. It uses the mean
per-pair difference (paired), the candidate's mean outcome minus 0.5 (h2h), or the
difference of arm means (field). Normal approximation with estimated variance, the form
fishtest's GSPRT uses: `LLR = ((est − h0)² − (est − h1)²) / (2·var(est))`, stop at
`log((1−β)/α)` (accept H1) or `log(β/(1−α))` (accept H0). It always answers `continue` below
30 observations. Pre-register H0/H1/α/β. Secondary metrics after an SPRT stop are
descriptive: their fixed-sample p-values ignore the optional stopping.

## Verified (2026-09-29, build coworld-v0.3.78)

Re-checked at coworld-v0.3.79 (2026-09-29): `compare` and `sprt --design h2h` on 8 local
base-vs-jev recordings (16 rows, `--out` JSON rendered by `compare_report.py`), `--design
paired` on the same data refused (`an episode holds both arms`, exit 2), an unknown arm and an
unknown `--metrics` name (exit 2 with `result.valid`), and `--design field` on the 3 hosted
sample episodes.

- 160 local rules-48 recordings with the league glory config (seeds 1–20, both sides; FAKE
  arms, not evidence about any policy): `paired` base.bas vs nearby.bas (both vs jev.bas,
  40 pairs), a near-null arm (base.bas with one RNG constant changed), and `h2h` nearby.bas vs
  base.bas (40 episodes). All three designs and `sprt` ran end to end (about 26 s cold for 80
  episodes, traced in parallel); every verdict was inconclusive and the near-null arm showed
  no effect. Consistency check: jev.bas plays identically to base.bas without its oracle,
  so the paired estimate (+0.0190) equals the h2h estimate, as it must.
- Hosted rules-44 samples plus two synthetic platform failures on scratch copies: forfeit
  scoring by `failed_policy_index` side, infrastructure failure counted only in
  `ops_fail_rate`, the h2h/field arm-overlap refusal, `name:vN` resolution, and stored
  `--xreq`/`--requests`. `compare_report.py` rendered the paired JSON.
- Tests: `paintbot_pw_lab/tools/tests/test_pw_compare.py` (failure attribution, pairing,
  duplicates, rules pooling, policy resolution, test selection per design, sample rows,
  request bodies), `test_compare_margin.py` (the `score_outcome` formula against metta's,
  clipping, scale validation and exit 2, forfeit and infrastructure handling, SPRT and h2h
  target selection, CLI defaults and propagation, the hosted sample at scale 600 with
  `elo_outcome` unchanged) and root `tools/tests/test_paired_stats.py` (the statistics).

Measured on the fake local arms only (plan the first hosted batch with its own numbers):
per-pair difference SD of `elo_outcome` 0.40 (paired), per-episode SD 0.29 (h2h), single-arm
SD 0.31. So seed pairing reduced variance only slightly here, and an SPRT with H1 = +0.05
needs on the order of 330 pairs (paired) or 175 episodes (h2h); H1 = +0.10 needs about a
quarter of that.

## Not verified / limits

- No hosted A/B batch has been run, so pairing on hosted `game_config_overrides.seed` is
  unexercised. The source says an explicit override does reach the engine (every episode of
  that request plays that world), so seed-paired arms play identical worlds; league episodes
  do not play their API `seed: 2026` ([docs/field.md § Seeds](../field.md#seeds-what-actually-reaches-the-engine)). `pairs_with_different_engine_seeds`
  should therefore stay 0; a non-zero count means that chain broke.
- Hosted forfeit rows are exercised only on synthetic `episode.json` edits.
- Thresholds behind the inferred metrics (`vm_disabled_suspect_seats`, stuck, accuracy
  bands) are uncalibrated; see [pw_metrics.md](pw_metrics.md).
- A per-opponent group appears only with more than one opponent; each adds tests to the BY family.
