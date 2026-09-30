---
name: paintbot-pw-replay
description: "Use when someone wants to unpack or look inside a Paintbot PW replay or episode — 'what happened in this match', 'what happened at tick X', 'who killed seat 5', 'why did we lose this one', 'trace this replay', 'show me the glory breakdown'. Re-simulates the tape hash-exactly with pw_trace, builds the episode tables (pw_episodes.py) and prints the per-episode metric summary (pw_metrics.py). Agent-drivable: `pw.py doctor|episodes|metrics|viz|report ... --json` (one JSON envelope, exit 0/1/2/3)."
---

# Paintbot PW replay unpacking

Turn one episode (or a batch) into verified facts: every shot, hit, kill, pickup, capture,
glory award and shout, plus sampled per-tick state. Everything comes from a re-simulation
that checks the recorded state hash every tick, so the numbers are exact unless a column
says `inferred`. Tool references: [pw_trace.md](../../../docs/tools/pw_trace.md) (the re-simulation),
[pw_episodes.md](../../../docs/tools/pw_episodes.md), [pw_metrics.md](../../../docs/tools/pw_metrics.md),
[pw_viz.md](../../../docs/tools/pw_viz.md), [pw_match_report.md](../../../docs/tools/pw_match_report.md),
[deployed_ref.md](../../../docs/tools/deployed_ref.md). Contract: [docs/tools/tables.md](../../../docs/tools/tables.md); every tool:
[docs/tools/README.md](../../../docs/tools/README.md) (`pw.py tools --json` lists them).

## Procedure

Run from the repo root (`personal_labs_paintbot_pw/`).

1. **Check the lab is ready** (`doctor` lists each problem with its fix command). If the league
   moved to a new tag, `deployed-ref --write` moves `paintbot_pw_lab/tools/release.env` to it
   (exit 1 then means "rebuild") and `build` builds that tag:

   ```bash
   uv run python paintbot_pw_lab/tools/pw.py doctor --json                 # 0 ready; 1 release.env behind (code stale) or league check rate-limited; 3 missing (see next[])
   uv run python paintbot_pw_lab/tools/pw.py deployed-ref --write          # 0 = current; 1 = release.env moved: rebuild
   uv run python paintbot_pw_lab/tools/pw.py build                         # builds the tag in tools/release.env
   ```

   `uv run python paintbot_pw_lab/tools/pw.py release` prints that tag and which binaries exist.

   A newer build replays older rules hash-exactly, so the current tag reads every older tape.

2. **Get the episode.**
   - Hosted, ours or a league round: `fetch_artifacts.py --ereq <ereq> --out paintbot_pw_lab/episode_data`
     (shared `coworld-episode-artifacts` skill). Public league episodes need no auth:
     `https://softmax.com/api/observatory/v2/rounds?league_id=<league>&limit=3`, then
     `/v2/rounds/<round_id>/episodes`; save the row as `episode.json` and download its
     `replay_url` (gzip is fine) as `replay.gz` in the same directory. One call per list; back off on 429.
   - Local: `pw.py local match A.bas B.bas --seed S --record DIR` (or `local screen … --record DIR
     --record-seeds LIST`) writes `NAME.replay` plus the `NAME.meta.json` naming each seat's policy.
     A bare `paintbot-headless --record NAME.replay` needs that sidecar written by hand (schema in
     tables.md) if you want policy identity.

3. **Trace and build tables** (cached; ~1 s per episode first time):

   ```bash
   uv run python paintbot_pw_lab/tools/pw.py episodes <episode dir | batch dir | NAME.replay> --json
   ```

   Add `--window A:B` for every-tick state in a moment you care about, `--vis-every 24` for who
   saw whom. Any `FAILED [code]` line means that episode is **not** evidence; see the code table
   in [pw_episodes.md](../../../docs/tools/pw_episodes.md). Never quote numbers from a failed one.
   With `--json`, the same thing is `failures[]` in the envelope and exit code 1.

4. **Summarize**:

   ```bash
   uv run python paintbot_pw_lab/tools/pw.py metrics <same roots> [--policy <name or policy_version_id>]
   ```

   Read the team lines first: result, glory, Elo outcome score, and the glory composition
   (start − countdown + awards by kind − settled). Then per-policy combat, heart presence, idle.

5. **Answer the specific question** with the tables:

   ```bash
   uv run python paintbot_pw_lab/tools/pw.py episodes <root> --sql \
     "select t, seat, victim, weapon, distance from kills where t between 1200 and 1500 order by t"
   ```

   Useful queries: kills around a tick (`kills`, `damage`); what a seat was doing
   (`states where seat = N and t between A and B`: position, goal, aim, hp, command); which
   hearts flipped and who was credited (`captures`); why glory moved (`glory`); what a team
   shouted and who heard it (`shouts`). In Python: `pe.load_episode(path)["damage"]`.

6. **Report** exact vs inferred plainly. Seconds = ticks / 24. Team 0 = Ember (even seats),
   team 1 = Azure (odd seats).

## Movement diagrams and match report

7. **Show the moment**: "show me seat N's movement from 0:40 to 1:05":

   ```bash
   uv run python paintbot_pw_lab/tools/pw.py viz movement <episode> --from 0:40 --to 1:05 --seats 5 --json
   uv run python paintbot_pw_lab/tools/pw.py viz movement <episode> --from 960 --to 1560 --team 0 --bbox 0,-2500,4000,1000 --no-shots --json
   uv run python paintbot_pw_lab/tools/pw.py viz timeline <episode> --json          # meter, glory, kills, captures, heart ownership
   uv run python paintbot_pw_lab/tools/pw.py viz gif <episode> --from 0 --to 12s --team 1 --json
   ```

   The image and a JSON of the plotted data land in
   `paintbot_pw_lab/analysis/pw_viz/<episode>/<command>[-selectors].png` (the envelope's
   `result.images`; `--out FILE` overrides). Times are ticks (`1500`), seconds (`62.5s`) or m:ss
   (`1:10`) and must fall inside the match: the sample league episode lasts 1:08.7, so a
   `--from 1:10` window is refused with exit 2 and the match lengths, and a `--to` past the end is
   clamped (reported in `result.window`). Legend: kill × at the
   killer's spot, death ○, capture ◆, pickup ▲, dashed grenade ring, shot rays (hit = line to
   the victim, miss = short dotted ray). Trails break at death and respawn. **Look at the PNG**
   (Read it) and check one event against `--sql` before describing it. Add `--fine` for
   tick-exact paths (it re-traces the episode with every-tick states for the window).

8. **Across episodes**: the same window as small multiples (`movement ROOT... --policy KEY`;
   each panel says which side the policy played and against whom); where a policy goes or dies
   (`heatmap ROOT --policy KEY [--kind deaths] [--normalize-side]`); two policies compared
   (`occupancy ROOT --policy A --policy B`, with the Bhattacharyya overlap in the title).
   Reference: [docs/tools/pw_viz.md](../../../docs/tools/pw_viz.md).

9. **One-page report** to hand to James:

   ```bash
   uv run python paintbot_pw_lab/tools/pw.py report <episode dir | batch dir> [--out DIR] --json
   ```

   Writes `pw_report/report.html` (+ `report.json`, timeline, one panel per top moment) per
   episode: result, how it was decided, Elo outcome, glory composition, timeline, top moments
   (first captures, hearts taken, kill bursts, elimination), seat table, and replay links.
   Link it with its path; it is a local file.
   Reference: [docs/tools/pw_match_report.md](../../../docs/tools/pw_match_report.md).

   Diagram and report pitfalls:
   - **Side is not behaviour.** Two policies on opposite sides look different on the raw map.
     `occupancy` rotates Azure onto Ember's side by default; use `--normalize-side` for heatmaps
     that pool both sides.
   - **Replay deep links:** the Observatory replay wrapper does not forward `t=<tick>` to the
     viewer, so the link opens at 0:00: always give the tick (or m:ss) with the link.
   - **Moment ranking is a display heuristic**, not a win-probability swing. Do not quote a
     moment's weight as evidence.
   - `--fine` re-traces with every-tick states for the window; the result is cached as its own
     variant beside the default cache (`pw_cache@<variant>/`), so it never replaces it.

## Pitfalls

- **The fetcher's `replay.json` is the raw tape**, not JSON. The reader sniffs bytes; do not
  rename or "fix" it.
- **Team from metadata, not parity guesses.** The reader checks `game_config.slots` against
  seat parity and fails the episode on disagreement. A public round-listing row has no slots,
  so the episode is flagged `team_from_parity`.
- **One row per (episode, policy)** for any statistic; 8 seats of one policy are not 8 samples.
- **Misses that are not misses.** Rays that reached a spawn-shielded or trench-dodging cog look
  like misses to the engine; they are in `shots.inferred_*`, never counted as hits.
- **A hash mismatch is a finding, not noise.** Build the recording's own tag
  (`pw.py build <tag>`, then `--tag <tag>`) before concluding anything else.
- **Losing glory is zeroed.** The loser's final glory is 0 whatever it earned; the composition
  line shows what `settleGlory` took (`settled`).
- Local runs are for mechanisms, never evidence about the league field.

## Autonomous use

- **Preconditions:** run from the repo root; `uv run python paintbot_pw_lab/tools/pw.py doctor --json` exits 0 (on 1 with
  failure code `stale` run `deployed-ref --write` then `build`; on 1 with `rate_limited` /
  `api_unavailable` wait and retry, or use `doctor --offline`; on 3 run each command in `next[]`). The episode is on
  disk (hosted directory or `NAME.replay`).
- **Commands:** `uv run python paintbot_pw_lab/tools/pw.py episodes ROOT --json`, then `metrics ROOT --json`, `viz <command> ROOT
  ... --json`, `report ROOT --json`. Traces are cached per episode, so re-running is cheap.
- **Reading the envelope:** `ok` is true only on exit 0. `result` holds the payload
  (`episodes`: `result.episodes[]`; `metrics`: `result.team[]`, `result.policy[]`, `result.seat_metrics[]`;
  `viz`: `result.images[]`, `result.data[]`, `result.window`; `report`: `result.reports[]`); `failures[]` lists every
  episode that did not verify; `outputs[]` every file written; `next[]` the suggested follow-up.
- **Exit codes:** 0 use the result. 1 some episodes failed: use the rest, report the failures by
  id and code, never quote a failed episode. 2 a bad argument or unknown selector (policy, seat,
  a window past the match end): read `failures[0].message` and `result.valid`, fix, rerun. 3 a
  build is missing: run `next[0]` and rerun.
- **Human gates:** none. This skill only reads local files and writes under
  `paintbot_pw_lab/analysis/` or next to the episode. Fetching public episodes is an anonymous
  read (keep it small; back off on 429).

