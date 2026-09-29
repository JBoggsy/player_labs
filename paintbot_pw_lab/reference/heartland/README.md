# Heartland reference policies

`ffa.bas` (the Heartland baseline) and `ffa_blind.bas` (its kin-blind control) target the separate
**Heartland** coworld (FFA-kin, tags `heartland-v<version>`), not the paintbot-pw teams game: they
call FFA-only host functions (`kin`, `seatAlive`, ...) and **do not compile in the teams game**
(`pw_local.py compile` at coworld-v0.3.79 fails on every seat). Copied from
`coworld/heartland/players/` at paintbot-pw `d0728ab1` (tag `coworld-v0.3.79`). Description:
[docs/policy-surface.md §6](../../docs/policy-surface.md).
