# Inferring opponent battle plans

`tools/infer_battle_plan.py` reconstructs an opponent's observed field doctrine from
repeated CTF replays. It emits a machine-readable JSON timeline and a compact Markdown
report describing likely seat groupings and `move`, `hold`, or `maneuver` orders.

The result is deliberately phrased as inference. A replay proves where agents went and
when; it cannot prove the hidden condition, target name, or source-code order that sent
them there.

## Workflow

Pull a repeated 1v1 batch with replays:

```bash
uv run python .claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py \
  --xreq xreq_... --watch --elevated \
  --out ctf_lab/scratch/opponent_replays
```

Build the reader at the deployed CTF source ref:

```bash
ctf_lab/tools/build_expand_replay.sh
```

Infer the plan:

```bash
uv run python ctf_lab/tools/infer_battle_plan.py \
  --episodes ctf_lab/scratch/opponent_replays \
  --policy ctf-focusfire --version 63 \
  --out ctf_lab/scratch/focusfire_plan
```

This writes:

- `focusfire_plan.json` — `ctf.inferred-battle-plan.v1`, suitable for downstream
  visualization or comparison.
- `focusfire_plan.md` — the same timeline in a human-readable table.

## Method

The tool uses established movement-analysis primitives while staying small enough for
the exact CTF domain:

1. Re-simulate every replay with the version-matched reader. Hash validation rejects
   game-version drift.
2. Sample authoritative simulator positions every 12 ticks (0.5 seconds by default).
3. Mirror Blue into Red's left-to-right attack frame.
4. Divide the timeline into 120-tick (5-second) windows.
5. Classify each seat:
   - `hold`: its samples remain inside a bounded diameter;
   - `move`: its net displacement crosses the movement threshold;
   - `maneuver`: local or inconsistent motion that fits neither.
6. Infer groups from repeated proximity plus compatible motion across episodes. The
   complete-link rule prevents a weak proximity chain from merging distinct wings.
7. Label each inferred order with the nearest canonical CTF point of interest and emit
   confidence plus episode support.

The stop definition follows the same diameter-and-duration model used by
MovingPandas' `TrajectoryStopDetector`. Density clustering packages such as HDBSCAN
are useful for large, noisy point clouds, but they are unnecessary here: one CTF team
has exactly eight seats, simulator positions are exact, and seat identity is stable.
Keeping the calculation local avoids a new runtime dependency and makes every verdict
auditable.

## Important parameters

```text
--sample-ticks 12       replay position interval
--window-ticks 120      order-analysis duration
--hold-diameter 100     maximum spatial extent of a hold
--move-distance 80      minimum net displacement for a move
--group-radius 220      teammate proximity range
--group-threshold 0.55  required proximity/co-motion affinity
--min-support 0.5       minimum fraction of episodes supporting a window
--max-ticks 1440        opening horizon (60s); pass 0 for the full game
```

Tune these only against visible replay examples. In particular, cover-peeking should
remain a `hold`, while a genuine lane transition should become a `move`.

The default report stops at 60 seconds. After that, deaths, respawns, flag emergencies,
and opponent contact increasingly describe reactions rather than the authored opening
plan. Use `--max-ticks 0` when those reactions are the question.

## Reading the report

- High confidence with broad episode support is a stable doctrine candidate.
- A low-confidence group may be incidental co-location caused by contact or respawn.
- `maneuver` usually means local combat motion, failed navigation, or inconsistent
  reactions rather than a clean strategic order.
- A nearby POI name is a vocabulary label, not proof that the opponent literally uses
  that POI.
- Validate any counter-plan against representative replay windows before changing
  Beacon. The report summarizes sequence; it does not replace watching the trace.
