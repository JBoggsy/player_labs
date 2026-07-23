# CTF lab — user preferences

CTF-specific durable preferences layered on the root
[`../user_preferences.md`](../user_preferences.md) (which still applies).

## The "1v1" evaluation shape (James's standing term)

A **1v1** is a head-to-head experience request with **uniform policies per side**:
all 8 Red slots (even slots 0,2,…,14) are ONE policy and all 8 Blue slots (odd
slots 1,3,…,15) are the OTHER policy — one team of ours vs one team of theirs,
no mixed rosters, no `random`/`top_n` seats.

Concretely, the roster is 16 pinned entries alternating by slot parity (slot →
team is parity in CTF):

```json
{"roster": [
  {"player": {"policy_ref": "beacon:vN"},  "slot": 0},
  {"player": {"policy_ref": "<opponent>"}, "slot": 1},
  … alternating through slot 15 …
], "num_episodes": 10}
```

When James says "run 1v1s vs X" this is the shape to use (default 10 episodes
per opponent unless stated). It's the lab's standard instrument for measuring a
beacon version against a specific opponent (accuracy/item goals, recon, A/B
arms). Existing examples: `scratch/eval_v1{0..4}/xreq_body_*.json`.

## Strategic principle: lives > flag captures (posited 2026-07-23)

We'd rather tie than lose. Throwing lives at an entrenched enemy hands them a
life advantage they convert into a wipe or an uncontested capture. Design
implications: prefer holding ground over re-pushing at a numeric disadvantage;
respawned agents rejoin cautiously instead of trickling into contact; pushes
want full squads. (Posited — subject to revision if data shows aggressive
tempo outperforms.)

**FACT CORRECTION (2026-07-23 audit):** the mechanical support originally cited
here ("timeout = scoreless draw, costs 0") is wrong at the deployed 0.7.69.
GameVersion 21 makes a **time-limit draw -1 for BOTH sides** — the same as
losing (verified in the deployed sim's `TimeoutReward* = -1` AND empirically:
every drawn v24 episode's results.json scores all 16 players -1). Score-wise,
a tie IS a loss now; only a capture or wipe pays +1. The half of the principle
that survives: feeding lives still *enables the enemy's win paths*. The half
that doesn't: holding to a draw banks nothing — preserved lives are worthless
unless converted before tick 5000 (which is why the convert trigger is the
current lever).
