# RL action-alignment investigation

Date: 2026-08-06  
Verdict: use zero-tick observation-to-action alignment

## Question

Should observation `O_t` supervise the replay mask recorded for tick `t` or
tick `t+1`?

## Instrument

GV40 provides a precise clock: while alive, Select changes `own aim` by -5
brads per tick, B changes it by +5, and holding both or neither changes it by
zero. `measure_action_alignment.py` compared each consecutive observed aim
transition against replay actions at offsets -1, 0, and +1.

The corpus was three exact-version, hash-validated replay reconstructions with
POV seats 0 and 8 from each: episode prefixes `48a54116`, `86674af1`, and
`1432f4db`. Transitions other than 0 or +/-5 brads were excluded as respawn or
other non-controller discontinuities.

## Result

| Action offset | All matches | All eligible | Accuracy | Turn matches | Turn commands | Turn accuracy |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| -1 | 27,535 | 30,704 | 89.68% | 9,224 | 11,435 | 80.66% |
| **0** | **30,401** | **30,704** | **99.01%** | **11,134** | **11,436** | **97.36%** |
| +1 | 27,548 | 30,704 | 89.72% | 9,225 | 11,424 | 80.75% |

## Interpretation

The same-tick action is decisively the action selected from the same-tick
observation. Its consequences appear in the next observation. The small zero-
offset residual is concentrated in two POVs and is consistent with resets or
other state changes that survive the simple +/-5 filter; it does not support a
neighboring offset.

The SFT dataset now defaults to `action_delay_ticks=0`. The option remains
configurable for future protocol investigations.
