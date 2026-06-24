# crewborg tools — path-prediction analysis

Replay-driven tooling for the **path-prediction module**
(`crewrift.crewborg.strategy.path_prediction`), which projects where a tracked
crewmate is heading — a probability distribution over candidate nav routes — so the
imposter's seeking logic can *follow a crewmate to their next room* once they leave
crewborg's view. These tools let you **see and score** that module on real replays
without running a live game.

There are three pieces:

| File | What it is |
| --- | --- |
| `replay_frames.py` | Loads one episode from a built **event warehouse** into per-tick ground-truth positions + crewborg's visibility windows + map geometry. Shared by the two tools below. |
| `path_prediction_ui.py` (+ `.html`) | A **live browser UI**: scrub/play a replay, pick an agent, watch its predicted routes (weighted by probability) sharpen as it moves and persist when it leaves view. |
| `path_prediction_eval.py` | **Offline scoring**: at every visible→obscured transition, compare the predicted destination to where the crewmate actually went. Emits a match-rate + CSV **and** per-instance overlay images. |

## Prerequisite: a built event warehouse (version-matched)

Both tools read a **crewrift-event-warehouse** dataset (per-tick `player_state`,
`player_visible_interval`, `map_geometry`). Build one from league rounds or from our
XP-request episodes — see `~/coding/role_repos/reporter_lab/crewrift-event-warehouse`.

⚠️ **expand_replay version coupling** (the #1 silent failure): the warehouse's
`CREWRIFT_EXPAND_REPLAY` helper must be built from the *exact* crewrift commit the
arena ran. As of 2026-06-24 arena `crewrift:0.1.54` ⇒ commit `42fed21`; the
helper `/tmp/expand-42fed21` and the checkout `~/coding/coworlds/coworld-crewrift`
(at 42fed21) are set up. A version skew yields sparse/hash-failed events (check
`manifest.json` `trace_warning` counts first). Reusable warehouses already built
this session: `/tmp/xp_imp_warehouse` (450 XP imposter episodes) and
`/tmp/crewrift_warehouse` (2 league rounds).

To build an XP-episode warehouse from `fetch_artifacts`-downloaded dirs, the adapter
`/tmp/make_wh_input.py` turns those into a warehouse `report_request.json`.

## `path_prediction_ui.py` — live prediction viewer

```sh
# list episodes in a warehouse:
uv run --with duckdb python crewrift_lab/crewrift/crewborg/tools/path_prediction_ui.py \
  --warehouse /tmp/xp_imp_warehouse
# serve one episode (then open http://localhost:8810):
uv run --with duckdb python crewrift_lab/crewrift/crewborg/tools/path_prediction_ui.py \
  --warehouse /tmp/xp_imp_warehouse --episode ereq_104afabe-6cc8-4be0-b763-4e2d1f3ed613
```

In the page: **agent dropdown** picks the crewmate to predict; **blue routes** are
candidate destinations with opacity/width ∝ probability; the **◇** marks the top
route's predicted position; the **VISIBLE/occluded** tag shows whether crewborg can
see the target this tick (the module is fed *only* visible sightings, so watch the
prediction coast when it flips to occluded). **Gold ring** = crewborg (slot 0),
**white ring** = the selected agent. Scrub the timeline or press **▶ play**.

Notes: predictions are computed server-side per agent on first selection (then
cached); the first dropdown change for a new agent takes ~a second. The nav graph is
crewborg's *real* baked croatoan mask (falls back to a room-rect-union only if the
bake can't load).

## `path_prediction_eval.py` — accuracy at visible→obscured transitions

The moment a crewmate leaves view is when prediction matters. For each such
transition this captures the prediction *at onset*, then uses ground truth to see
where they actually went. Headline metric = **destination-room match** (did the
predicted top destination's room equal the room they actually reached, by
re-acquisition or a horizon cap).

```sh
uv run --with matplotlib --with duckdb python \
  crewrift_lab/crewrift/crewborg/tools/path_prediction_eval.py \
  --warehouse /tmp/xp_imp_warehouse --episodes 20 --images 40 --out /tmp/pred_eval
```

Knobs: `--episode <id>` (single) or `--episodes N` (sweep); `--min-occlusion 24`
(ignore blinks); `--horizon 240` (don't blame the onset prediction for a wander
beyond this); `--images N` (sampled overlay PNGs). Outputs to `--out`:
`instances.csv` (one row per occlusion) + `images/` (overlay per sampled instance:
**orange** = actual path, **blue** = predicted weighted routes, white dot = onset,
diamond/star = predicted/actual destination, filename tags `match`/`MISS`).

stdout also reports the match rate **by confidence bucket** — the calibration check:
a useful module is right more often when it is confident. (First-draft baseline,
2026-06-24, 4 episodes: 43% overall, but 86% when pred_prob ∈ [0.4,0.7).)

## Tuning the module

The knobs live at the top of `strategy/path_prediction.py`: `ALIGN_GAIN`,
`EVIDENCE_DECAY`, `LOOKAHEAD_PX`, `CREW_SPEED_PX`, `REACQUIRE_DIST`. Change one, re-run
the eval to watch the match-rate / calibration move, eyeball a few miss images to see
*how* it fails. Unit tests pin the qualitative behavior:
`tests/test_path_prediction.py`.
