# A/B: `crewborg:v106` (candidate) vs `crewborg:v100` (baseline)

Baseline n: crew 150  imposter 50  |  Candidate n: crew 205  imposter 58

## Target axis: `win_rate`
- **crew**: 23% → 20%  (**· noise**, p=0.543, z=-0.61)
- **imposter**: 64% → 45%  (**▼ REGRESSED**, p=0.046, z=-1.99)

## All metrics (baseline → candidate, Δ, verdict)

| metric | group | baseline | candidate | verdict (p) |
| --- | --- | ---: | ---: | --- |
| win_rate | crew | 23% | 20% | · noise (p=0.54) |
| win_rate | imposter | 64% | 45% | ▼ REGRESSED (p=0.05) |
| score_mean | crew | 0.23 | 0.20 | · noise (p=0.55) |
| score_mean | imposter | 1.92 | 1.34 | ▼ REGRESSED (p=0.04) |
| tasks_mean | crew | 6.47 | 6.22 | · noise (p=0.20) |
| kills_mean | imposter | 1.60 | 0.67 | ▼ REGRESSED (p=0.00) |
| penalty_mean | crew | 28.91 | 26.02 | · noise (p=0.51) |
| penalty_mean | imposter | 78.08 | 50.21 | ▲ improved (p=0.00) |
| no_vote_rate | crew | 0% | 0% | · noise (p=1.00) |
| no_vote_rate | imposter | 0% | 0% | · noise (p=1.00) |
| ops_fail_rate | crew | 0% | 1% | · noise (p=0.23) |
| ops_fail_rate | imposter | 0% | 0% | · noise (p=1.00) |
| imposter_no_kills_rate | imposter | 2% | 40% | ▼ REGRESSED (p=0.00) |
| crew_low_tasks_rate | crew | 17% | 17% | · noise (p=0.85) |
| crew_lost_nearly_won_rate | crew | 23% | 16% | · noise (p=0.09) |

## ⚠ Regressions (significant adverse moves — watch these)
- **win_rate / imposter**: 64% → 45% (p=0.05)
- **score_mean / imposter**: 1.92 → 1.34 (p=0.04)
- **kills_mean / imposter**: 1.60 → 0.67 (p=0.00)
- **imposter_no_kills_rate / imposter**: 2% → 40% (p=0.00)

## Next: the qualitative half

Numbers say *whether* it moved; they don't say *why*. Now read the two
batches' replays + logs side by side, steered by your context (target
dimension / specific opponent / specific fault) — see SKILL.md §Qualitative.

[wrote JSON: crewrift_lab/.tmp/ab_v106_v100/diff.json]
