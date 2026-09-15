# Scaling tools

Regenerates every number and figure in [docs/scaling.md](../../docs/scaling.md) from the
game engine's own content tables, so the report can be re-verified against any
polyworld commit without transcribing numbers by hand.

| File | Role |
| --- | --- |
| `dump_specs.nim` | Compiles against `examples/gods_of_the_arena/content.nim` and prints `HeroSpecs`, the effective `abilitySpec` of every class slot, and `ItemSpecs` as JSON. |
| `specs.json` | The dump used by the current report (polyworld `1d7eb723`; `content.nim` identical at the deployed `5422fb0c`). |
| `model.py` | Derived quantities as functions of level: HP, mana, damage, DPS, time to kill, spell shares, burst, mana rates, XP curve, level over time. Constants for footmen, towers, rewards, and regen are at the top; check them against `sim.nim` when the engine changes. |
| `charts.py` | Renders the 21 SVG figures into a directory, following the `dataviz` skill's palette and mark rules. |

## Regenerate against a new engine commit

```sh
# 1. Fetch the deployed commit (see ../deployed_ref.py) into a scratch clone
git clone https://github.com/Metta-AI/polyworld.git /tmp/pw && git -C /tmp/pw checkout <sha>

# 2. Dump the specs (needs nim; polyworld pins its own toolchain)
cd gods_of_the_arena_lab/tools/scaling
nim c -d:release --hints:off --warnings:off \
  --path:/tmp/pw/src --path:/tmp/pw/examples/gods_of_the_arena -o:./dump_specs dump_specs.nim
./dump_specs > specs.json

# 3. Check the hard-coded simulation constants in model.py against sim.nim
#    (TOWER_HP, TOWER_DMG, TOWER_RANGE, FOOTMAN_HP/DMG, REWARDS, MANA_REGEN, RESPAWN_TICKS)

# 4. Recompute and re-render
../../../.venv/bin/python model.py
../../../.venv/bin/python charts.py ../../../docs/reports/gota-scaling-2026-09-15-figures
```

Then re-read the prose in `docs/scaling.md` against the printed numbers; the report's
editor pass found that summary sentences drift from the model more easily than tables do.
