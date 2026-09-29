# pw_winprob.py: win-probability model and event credit (T14)

A logistic model of P(team wins the match | team-level state at tick t), fit on hash-checked
episodes through [`pw_episodes`](tables.md), scored on held-out episodes, and used to credit
each capture, kill and death with the change in win probability it caused (the Leetify / CS:GO
"win probability added" practice). It answers "which minutes and which events lost this game"
and gives the hypothesis miner per-(episode, policy) credit features.

Files: [`tools/pw_winprob.py`](../../tools/pw_winprob.py), tests in
[`tools/tests/test_pw_winprob.py`](../../tools/tests/test_pw_winprob.py).

**What it models.** The **heart-meter winner** only. The ladder ranks by the glory margin
([mechanics.md §1](../mechanics.md)); glory enters only as a feature. A draw has no label and is
excluded (counted).

## Commands

Run from the repo root.

```bash
# 1. A modest public league sample. No auth. Lists the newest completed rounds of the
#    Competition division, keeps completed episodes of the given coworld versions, saves
#    DIR/<ereq>/episode.json (the public listing row) + replay.gz (the public replay_url).
#    Capped at 40 episodes. Requests go through tools/pw_public.py (shared with pw_scout): 1 s
#    pause per request, backs off on 429/5xx (Retry-After), 3 retries. Episodes on disk are
#    skipped. --versions defaults to the version of the tag in tools/release.env.
uv run python paintbot_pw_lab/tools/pw_winprob.py fetch --out DIR [--max-episodes 40] [--rounds 6] \
    [--versions X.Y.Z] [--division div_...]

# 2. Fit + held-out evaluation + calibration + out-of-fold credit tables.
uv run python paintbot_pw_lab/tools/pw_winprob.py fit ROOT [ROOT ...] --out OUT [--sample-every 24] [--folds 5]

# 3. Credit another batch with a saved model (in-sample for episodes that were in the fit; it says how many).
uv run python paintbot_pw_lab/tools/pw_winprob.py credit ROOT [ROOT ...] --model OUT/model.json --out OUT2
```

ROOTs are anything `pw_episodes.load_batch` accepts: hosted episode directories and local
`paintbot-headless --record` tapes (e.g. `pw_local.py screen --record`). Episodes are traced
with the default build (the tag in `tools/release.env`) and cached as usual.

**Exclusions, always printed and counted in `report.json`:** load failures from
`pw_episodes` (with their code), `rules_below_47` (behind-in-cogs glory changed the game),
`not_16_seat_teams`, `not_heartwick`, `draw`. `fit` refuses with fewer than 4 usable episodes
(exit 1).

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py winprob fetch|fit|credit ... --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | `fetch --out DIR` (`--versions`, default the `tools/release.env` version; `--max-episodes` ≤ 40); `fit ROOT... --out DIR`; `credit ROOT... --model FILE --out DIR`; `--jobs` |
| Outputs | `fit`: `model.json`, `report.json`, `wp_ticks.parquet`, `wp_events.parquet`, `wp_policy.parquet`; `credit`: the three parquet tables; `fetch`: `DIR/<ereq>/{episode.json, replay.gz}` |
| `--json` result | `fetch`: `{out, episodes, already_present, skipped, versions}`; `fit`: `{report, model, verdict, held_out, episodes, event_summary}`; `credit`: `{credited, in_fit, exclusions, event_summary}` |
| Exit codes | 0 ok; 1 some episodes failed to load, `fit` had fewer than 4 usable episodes, or `fetch` found none of the wanted versions; 2 usage (`--max-episodes` above 40, a missing `--model`); 3 the public API is unreachable, or `pw_trace` is not built. A `fetch` still rate-limited (HTTP 429) after the retries is exit 1 with `failures[].code = "rate_limited"` (wait and rerun; saved episodes are skipped) |
| Idempotence / cache | fetch skips episodes on disk; fit/credit read the trace caches and overwrite `OUT/` |
| Typical next step | `credit` a batch of ours with the fitted model; feed `wp_policy.parquet` to diagnosis |

## Model

Rows: the `team_states` table, one row per `--sample-every` ticks (default 24 = 1 s), strictly
before the final tick. Every row is used twice, once from each team's view with the label
flipped, so the model is symmetric between teams except for the `side` feature. Each episode
weighs 1 in total (rows are weighted `1 / rows in episode`), so long matches do not dominate.
Standardized features, L2 logistic regression (`C = 1`). P(team 0 wins) = the average of the
team-0 view and 1 − the team-1 view.

| Feature | Definition |
| --- | --- |
| `own_meter`, `enemy_meter` | meter tick-points / meter target (21,600 on Heartwick) |
| `own_hearts`, `enemy_hearts` | control hearts held / hearts on the map |
| `own_lives`, `enemy_lives` | team lives left / 32 |
| `own_cogs_out`, `enemy_cogs_out` | cogs out of the match / 8 |
| `glory_diff` | (own − enemy unsettled glory) / 1000 |
| `lives_ratio` | log((own lives + 1) / (enemy lives + 1)) |
| `hearts_x_time` | (own − enemy hearts fraction) × t / 14,400 |
| `race` | log((enemy ticks-to-fill + 24) / (own ticks-to-fill + 24)); ticks-to-fill = meter left / hearts held, or the rest of the match + meter left with no hearts |
| `side` | 1 when the view is Azure (odd seats) |

A feature equal for both teams (time alone) gets zero weight in a mirrored model, so time only
enters as an interaction. Named constants at the top of the file: `SAMPLE_EVERY_TICKS`,
`MIN_RULES`, `C_REGULARIZATION`, `FOLDS`, `CALIBRATION_BINS`, `PHASE_BINS_SECONDS`,
`THIN_EPISODES` (60), `SWING_WINDOW_TICKS` (1,440).

## Evaluation (`report.json`, printed)

- **Held-out**: `GroupKFold` by `episode_id` (5 folds): every prediction comes from a model that
  never saw that episode. Log loss, Brier, accuracy, AUC (episode-weighted) for the model, a
  meter + hearts baseline, and a coin.
- **Calibration**: 10 bins of held-out predicted P with rows, episodes, mean predicted, observed.
- **By phase** (0–60, 60–120, 120–240, 240–600 s) and **by source** (hosted / local).
- **Verdict line**: "THIN DATA" below 60 decided episodes, and a warning when fewer than 60
  of them are league (hosted) episodes. Rows within an episode are highly
  correlated: the sample size is the episode count, not the row count.

## Credit tables (`OUT/`)

In `fit`, credit uses the **out-of-fold** model for each episode (never one that saw it).

`wp_ticks.parquet`: `episode_id`, `t`, `p_team0` (every state row, default every 6 ticks; the
final row is the known result, 1 or 0), `final`.

`wp_events.parquet`, one row per event:

| Column | Meaning |
| --- | --- |
| `kind` | `capture` (capture_complete), `kill` (enemy kill), `friendly_kill`, `death` (every death, including map and self deaths) |
| `seat`, `team` | the acting seat/team: capturer, killer, or the victim for `death` |
| `other_seat`, `weapon` | victim for kills, killer for deaths (null = map) |
| `t`, `t_before`, `t_after` | event tick; the last state row before it and the first at or after it |
| `wp_before`, `wp_after`, `delta_wp` | the acting team's P(win) at those rows and the change |
| `bracket_events` | captures + deaths sharing that (t_before, t_after] bracket; 1 = the change is this event's alone. Kill and death rows of one kill are one fact |

`wp_policy.parquet`, one row per (episode, `policy_key`), the miner's unit: `team` (null when
the policy is on both teams), `n_seats`, `n_captures`/`wp_captures`, `n_kills`/`wp_kills`,
`n_deaths`/`wp_deaths`, `n_friendly_kills`/`wp_friendly_kills` (sums of `delta_wp` over the
policy's seats), `wp_net`, `wp_start` (P at t = 0), `worst_minute_start_t` and
`worst_minute_drop` (the team's largest P(win) drop within any 60 s window).

`model.json`: features, scaler, coefficients, intercept, `fitted_episodes`, options.
Python: `WinModel.from_json(json.load(...)).team0_probability(team_rows(ep)[0])`.

## Verified (2026-09-29, coworld-v0.3.78)

Data: 40 public league episodes (rounds 2370–2373, coworld 0.3.78, fetched with `fetch`, no
auth: 5 API calls + 40 replay downloads) and 60 local recordings (`pw_local.py screen --record`: two
`@tune` variants of base.bas vs base.bas, seeds 201–215 and 301–315, both sides). All 100
traced hash-exactly; none excluded. `fit` on 100 episodes: ~30 s wall including first tracing.

Held-out results, league + local (100 episodes, 9,774 rows):

| | log loss | Brier | accuracy | AUC |
| --- | --- | --- | --- | --- |
| model | 0.418 | 0.138 | 0.797 | 0.893 |
| meter + hearts baseline | 0.695 | 0.251 | 0.478 | 0.47 |
| coin | 0.693 | 0.250 | 0.480 | 0.50 |

League only (40 episodes, flagged THIN): model log loss 0.365, accuracy 0.837, AUC 0.925;
the baseline 0.691 / 0.613 / 0.65. Calibration on the 100-episode fit is close in the tails
(0.0–0.1: predicted 0.03, observed 0.04; 0.9–1.0: 0.97 vs 0.98) and off by up to ~0.12 in the
middle bins (0.2–0.3: 0.25 vs 0.15; 0.6–0.7: 0.65 vs 0.76; 0.7–0.8: 0.76 vs 0.64), each bin
50–96 episodes.

What the data says (descriptive, from these 100 episodes):

- **Matches end by elimination.** 38 of 40 league and 57 of 60 local episodes ended with a
  team at 0 lives (median 1,861 ticks = 78 s in the league). Lives dominate the model
  (`lives_ratio`, `own_lives` carry the largest standardized weights); meter and hearts alone
  predict nothing held-out (AUC 0.47–0.65).
- `glory_diff` has a **negative** weight: the team behind in lives earns behind-in-lives
  glory, so glory lead marks the losing side mid-match.
- Mean credit per event (out-of-fold): kill +0.047, death −0.048, friendly kill −0.054,
  capture +0.014. With the league-only fit, capture credit is slightly negative (−0.024,
  271 captures): heart play barely moves P(win) when games end by elimination, and capture
  credit should not be read as "captures are bad".

Not verified / limits:

- **Thin data.** 40 league episodes is below the 60-episode bar; the league-only fit is
  descriptive. The 60 local episodes are base.bas-family mirror play, a different field.
- **Mild selection bias.** The feature set was revised once after seeing held-out scores
  (`time_frac` replaced by `lives_ratio` and `hearts_x_time`; log loss 0.451 → 0.418).
- **Credit is the model's immediate change, not a causal value.** A kill's later positional
  effect is not counted, and events sharing a 6-tick bracket share its change
  (`bracket_events` > 1: 15–28% of events by kind).
- `credit` with a saved model is in-sample for fitted episodes (the command prints how many).
- The public listing row has no `game_config.slots`, so team identity falls back to seat
  parity (`episodes.notes` = `team_from_parity`); results are checked against
  `participant_scores`.
- `fetch` duplicates a small part of what a scouting fetcher would do; use one fetcher once
  both exist.
- Other maps (100/126 hearts) and FFA-kin are excluded, not modelled.
