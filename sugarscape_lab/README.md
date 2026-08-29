# Sugarscape policy lab

This lab compares population movement policies for
[`coworld-sugarscape`](https://github.com/Metta-AI/coworld-sugarscape). The game
owns the simulation and delegates only each agent's destination choice. A policy
receives the current agent, its legal candidate cells, resource amounts,
pollution, occupancy, and the game's candidate welfare value.

## Objective and limits

Sugarscape computes happiness after movement from conflict, family, health,
social, and relative-wealth components. The player observation doesn't expose
friends, mates, children, neighboring identities, or candidate disease state,
so a policy cannot directly optimize family or social happiness. The initial
policies deliberately test three observable proxies:

- `abundance`: maximize immediate resource abundance and relative wealth.
- `longevity`: balance post-harvest sugar and spice runway to reduce starvation.
- `health`: avoid pollution while preserving a resource safety floor.

The hosted score is final living population wealth, not happiness. Results must
therefore report score and population as competitive outcomes while treating
the happiness mechanism as a policy hypothesis, not a measured per-policy fact.

## Evaluation discipline

Compare policies in matched, same-window experience requests on the current
Sugarscape version. Rotate slots or run both seat orderings, use multiple seeds,
and inspect `scores`, `population`, `mean_wealth`, `fallbacks`, and policy logs.
Do not infer a happiness improvement solely from a wealth-score increase.

The source contract used to start this lab was
`coworld-sugarscape@f085d424694b9a449a7f97b391d158aec37907b1`
(`sugarscape:0.1.4`).
