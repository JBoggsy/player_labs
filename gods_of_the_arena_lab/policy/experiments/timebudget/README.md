# timebudget experiment

`dist.bas` is the uploaded `james-botts-gota:v5` file plus one change: melee and low-damage
classes (0, 3, 4, 5, 8, 9) chase-attack the anchor footman instead of walking to a standoff
point (`cfgChaseClass`, `mnChase` in the main block). It was patched on the assembled file
because `policy/modules/` was mid-edit by another session (punish module) at the time.
Analysis: `docs/designs/2026-09-17-time-budget-analysis.md`.
