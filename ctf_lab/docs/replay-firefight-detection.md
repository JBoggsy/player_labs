# Replay-verified firefight detection

`tools/find_firefights.py` identifies firefights from the authoritative rich combat
events emitted by Reporter Lab's CTF roundwarehouse component. It is intentionally
separate from Beacon's online `firefight_engagements` counter:

- the online counter is per bot and controls behavior;
- this detector is per replay and identifies one shared combat exchange for analysis
  and clip selection.

## Build the Reporter warehouse locally

The Reporter Lab implementation remains canonical. The local adapter supplies episode
artifacts to its unchanged Wasm component:

```bash
uv run --with wasmtime python ctf_lab/tools/run_roundwarehouse_local.py \
  --episodes ctf_lab/scratch/eval/episodes_focusfire \
  --episodes ctf_lab/scratch/eval/episodes_h050 \
  --out ctf_lab/scratch/eval/reporter_roundwarehouse
```

By default, the adapter uses:

```text
~/coding/role_repos/reporter_lab/.tools/build/ctf-roundwarehouse.component.wasm
```

Pass `--component` or set `CTF_ROUNDWAREHOUSE_COMPONENT` to select a different
Reporter build. The adapter records the absolute component path and SHA-256 in
`local_run.json`; the component records its coupled CTF source ref in `manifest.json`.
The adapter writes:

- `events.parquet`
- `player_stats.parquet`
- `manifest.json` — the Reporter's manifest
- `local_run.json` — local component/input provenance

This is a host boundary, not another event-expansion implementation. Changes to event
semantics belong in Reporter Lab.

## Detect firefights

```bash
uv run python ctf_lab/tools/find_firefights.py \
  ctf_lab/scratch/eval/reporter_roundwarehouse \
  --policy beacon \
  --version-id 8c7e2943-d9f9-4faa-96ec-f022509a93df \
  --opponent ctf-focusfire \
  --json ctf_lab/scratch/eval/firefights_focusfire.json
```

The output schema is `ctf.replay-firefights.v2`.

## Definition

A firefight is a spatially local, temporally connected exchange containing released
weapon actions from both teams. The detector:

1. Correlates `gun_fire` with `shot_impact` by `action_id`, so one shot is one action.
   It likewise correlates grenade throws/impacts and consumes each `spray_use`.
   `gun_trigger` alone is not fire: the player may die during windup.
2. Connects actions within a two-second continuation gap when their shooters are
   within the locality radius, a shot threatens the opposing shooter, or Reporter
   damage attribution proves the attacker/victim relationship.
3. Takes connected components of that spatiotemporal action graph. This follows the
   established density-connected clustering idea introduced by
   [DBSCAN](https://aaai.org/papers/kdd96-037-a-density-based-algorithm-for-discovering-clusters-in-large-spatial-databases-with-noise/),
   but keeps the domain-specific edge rule explicit instead of hiding it in a generic
   feature-space distance.
4. Requires at least two released actions from each team, five actions total, and one
   cross-team link. A one-sided fusillade or isolated ambush is combat evidence but is
   not mislabeled as a firefight.

The two-second continuation threshold is hysteresis: a reload, duck, or short re-peek
does not split one human-visible exchange. The general high/low evidence pattern is the
same one used by [hysteresis thresholding](https://scikit-image.org/docs/0.20.x/api/skimage.filters.html#skimage.filters.apply_hysteresis_threshold):
strong reciprocal evidence starts the event, while weaker connected evidence can
continue it.

## Weight and confidence

Every fight gets two different numbers:

- `weight` (0–100) is how important the fight should feel to a viewer:
  25% released-action volume, 20% team balance, 20% attributed damage, 15% casualties,
  10% participant breadth, and 10% duration. All volume terms saturate, so a very long
  spam exchange cannot grow without bound.
- `confidence` (0–1) is how strongly the replay proves this is one reciprocal exchange:
  team balance, cross-team graph links, direct damage evidence, and action count.

The report also exposes the unsummarized evidence: exact tick range, padded clip range,
location, unique action counts by team and weapon, damage by team, kills, attackers,
victims, balance, and cross-team links. A caller can choose a different ranking without
rerunning the replay.

`duel`, `skirmish`, and `teamfight` describe participant scale. `minor`, `standard`,
and `major` describe the computed weight; neither label asserts which team played well.

## Defaults and limits

```text
--max-gap 48           maximum continuation lull (2 seconds)
--radius 360           shooter locality radius
--threat-radius 110    impact-to-opposing-shooter threat radius
--min-team-actions 2   minimum released actions from each team
--min-total-actions 5  minimum released actions in the exchange
```

The detector does not infer line-of-sight through map geometry. Direct Reporter damage
attribution is conclusive; missed-shot association uses shooter/impact geometry and
should remain a visible, tunable heuristic. Human replay labels should be added before
claiming measured precision or recall across new maps or weapon mechanics.
