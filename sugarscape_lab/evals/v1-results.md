# V1 pairwise results

Date: 2026-08-05

All requests used canonical `sugarscape:0.1.4`, 16 episodes, random seeds, and
alternating seat order. All 48 episodes completed with zero policy fallbacks.

## Score matrix

| Pair | Mean score | Mean delta | Wins | Paired t-test | Wilcoxon |
| --- | --- | ---: | ---: | ---: | ---: |
| abundance vs longevity | 3247.9 vs 3323.2 | -75.3 | 7-9 | 0.717 | 0.632 |
| abundance vs health | 3265.4 vs 3604.4 | -339.0 | 6-10 | 0.126 | 0.211 |
| longevity vs health | 3387.5 vs 3400.6 | -13.1 | 6-10 | 0.960 | 0.717 |

None of the score deltas is distinguishable from zero at this sample size. The
within-episode score-difference standard deviations were 815, 838, and 1014,
respectively, so the apparent health lead over abundance is not yet a promotion
signal.

## Supporting outcomes

| Pair | Mean population | Mean wealth per living agent |
| --- | --- | --- |
| abundance vs longevity | 20.88 vs 21.44 | 155.55 vs 155.39 |
| abundance vs health | 21.69 vs 22.88 | 150.66 vs 157.85 |
| longevity vs health | 22.81 vs 21.56 | 148.64 vs 157.20 |

The score decomposition is useful but not causal: health's higher mean score
against abundance combines more survivors and higher wealth, while against
longevity it combines fewer survivors and higher wealth.

## Activation evidence

Representative episode `ereq_34f794fd-e6d7-4029-a431-ab362c8a6bcf`:

- abundance chose something other than game-greedy on 658/2381 decisions
  (27.6%);
- longevity changed from greedy on 744/2565 decisions (29.0%);
- both received every requested action, with zero fallbacks.

Representative health episode
`ereq_b758b07b-905b-45b1-bf3c-1f7259d7a240`:

- health changed from greedy on 716/2479 decisions (28.9%);
- `clean_safe` activated 2355 times and `starvation_rescue` 124 times;
- `cleaner_than_greedy` never activated.

## Mechanics finding

The canonical default configuration inherits DTL CLI defaults:
`agentSpiceMetabolism=[0,0]`, `environmentMaxSpice=0`, no diseases, and no
pollution production. This explains the traces: longevity always reported sugar
as the scarce resource, and health never found a candidate cleaner than greedy.

The three source policies have distinct objectives, but the default world
collapses their primary signals toward the same sugar-harvest decision. A v2
should preserve the high-level philosophies while giving longevity and health a
behaviorally distinct default-world tie-break:

1. Keep abundance as the immediate-harvest control.
2. Give longevity a future-patch or risk-adjusted resource objective rather than
   another immediate sugar maximum.
3. Give health a low-exposure, minimum-sufficient-resource objective when
   pollution is tied, rather than maximizing runway as its first tie-break.

Do not claim any policy increases per-policy happiness from this batch. The game
reports happiness only in global final statistics, while the competitive score
and population metrics are slot-specific.

## Tooling note

The streaming artifact helper exhausted its retries because its generic job
artifact routes did not find Sugarscape results, replays, or logs. The current
Coworld CLI and API client's episode-request routes successfully returned all
results and representative policy logs, so this was downloader route drift, not
missing episode output.
