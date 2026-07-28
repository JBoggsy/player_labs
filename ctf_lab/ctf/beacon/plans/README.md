# Baked plans

Battle plans shipped in the beacon image (selected via `BEACON_PLAN`, config.py).
These are SNAPSHOTS of `ctf_lab/battle_plans/` taken at build time — re-copy
before building when the plan changed:

    cp ctf_lab/battle_plans/<name>.json ctf_lab/ctf/beacon/plans/

(The interpreter also searches ../battle_plans/ for local `uv run` use, so the
copy only matters for the image.)
