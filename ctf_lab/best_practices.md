# CTF best practices

CTF-specific practices for the improvement loop — layered on top of the
**game-agnostic** [`../best_practices.md`](../best_practices.md) (read that first;
these are additions, not replacements). Distilled from real work in this lab; treat
as defaults and **warn the human if a request would contravene one** before
proceeding. Add to this file as we learn more about *this game's* failure modes.

The graduation pipeline fills this in: candidate lessons accumulate in
[`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md), and `/lessons-review` promotes the
ones that recur across sessions into durable practices here. The live, evolving
game knowledge lives in [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md), [`docs/`](docs/),
and the buffer.

> Provenance note: the practices below graduated from the lab's first review
> (2026-07-13). The lab is young — most rest on a single intensive build/eval
> session (beacon v1→v5), but every one is verified by concrete eval results or
> a root-caused bug with a confirmed before/after, not by hunch.

## Winning — score and win paths

- **Scoring is win-only (+100/0): optimize win rate, never K/D.** Kills, deaths,
  and captures are recorded but award zero points; a kill-farming bot that never
  captures or wipes scores nothing. Evaluate by win rate (by team/seat) and by
  the *win path* — capture vs wipe vs time-limit tiebreak.
- **There are two live win paths; know which one a matchup runs on.** A capture
  ends the game instantly. When neither side captures (common vs the baseline
  before beacon's carry fix), the game is decided by wipe or the lives-remaining
  tiebreak — so survival is worth at least as much as attack, and eight identical
  rushers into a defended pedestal is a losing shape.
- **Against a superior fighter, capture faster instead of out-fighting.** Beacon
  could not win the attrition war with the elite baseline (0-20 across two
  versions of combat improvements), but adding an escort rung (attackers converge
  on a teammate carrier and move home with it) plus shifting defenders to attack
  (5→3) took the record to 4-11 with 4 captures — while deaths stayed high.
  Wins came from deliveries, not trades.

## Combat conduct

- **Friendly fire is ON — gate every fire decision before anything else.** An
  un-gated snap-fire overlay is a major self-own: beacon lost 6.1 deaths/game to
  its own team while the opponent scored zero kills. The fix is perceiving
  teammates (`player <own_color>`) and holding fire when one is within ~22px of
  the shot ray and closer than the target; it flipped the co-gas record 7-8 →
  19-0.
- **Cover use decides firefights against strong opponents.** Defenders with
  correct positioning logic still get wiped if they hold in the open against a
  peek-fire-duck opponent. Snap hold points to walkable cells hugging an
  obstacle; the offline bake already has the grid to compute cover cells.
- **Roles matter, but tune the split to the opponent.** The minimal loop
  (all-rush) was mechanically sound and strategically naive; adding
  attacker/defender roles was the first big lever. Against a passive opponent
  that barely attacks, idle defenders are wasted seats — biasing toward attack
  was part of the 0-20 → 4-11 swing.

## Perception pitfalls

- **The carried flag renders ~10px above the carrier — account for the draw
  lift.** The sim emits a carried flag at `carrier.y - CarriedFlagLift(10px)`, so
  a carry check tuned to logical distance (6px) never fires: `i_carry` was False
  across all 38,204 snapshots and carriers sat "stuck" on the enemy pedestal in
  steal mode. Fix: `_CARRY_DIST` ≥ 24px and test pedestal-before-carry. This took
  a 19-0 wipe record to 20-0 by instant capture. General rule for this game:
  distance thresholds against rendered objects must account for sprite
  draw-offsets vs the logical entity centre.

## Field and evaluation

- **Judge beacon field-relative, not solely against the champion.**
  `ctf-baseline-16` is a purpose-built Nim bot (enemy tracks, cover model,
  Dijkstra exposure-cost nav, peek-fire-duck) — beating it head-to-head is the
  division's hardest bar. Beacon decisively wipes both co-gas variants while
  losing to the baseline; that is "2nd-best in the division", which is real
  progress. The CTF league uses `team_blocks` seating, so 8v8 head-to-heads are
  exactly the league matchup shape.

## Tooling

- **CTF is a Crewrift fork — reuse, don't rebuild.** coworld-ctf keeps
  Crewrift's Sprite-v1 protocol, continuous movement, LoS, and replay infra
  verbatim; only the game layer (teams/guns/flags/fog) differs. crewborg's
  perception decoder + movement controller and cady's `run_sprite_bridge` wiring
  transfer directly (proven by the beacon build).
- **Use the structured observability stack, not stderr prints.** Beacon emits
  SDK TraceEvents (jsonl@artifact, cadence via `BEACON_DIAG_EVERY_TICKS`); the
  Nim `expand_replay_json` emitter supplies ground-truth events; and
  `event_warehouse.py` re-keys both feeds slot→policy/team/seat/role into
  DuckDB+Parquet, making cross-episode questions ("81 steals → 0 captures") a
  one-line SQL query. Known gotchas: fetch the private repo with `gh api
  tarball`, not curl; give DuckDB a pyarrow table (not a raw dict) and avoid the
  reserved name `table`; the artifact fetcher stores policy logs as a Python
  bytes-repr string — `ast.literal_eval` it before `splitlines`.
