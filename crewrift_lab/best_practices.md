# Crewrift best practices

Crewrift-specific practices for the improvement loop — layered on top of the
**game-agnostic** [`../best_practices.md`](../best_practices.md) (read that first;
these are additions, not replacements). Distilled from real work in this lab; treat
as defaults and **warn the human if a request would contravene one** before
proceeding. Add to this file as we learn more about *this game's* failure modes.

## Scoring (read before interpreting results)

- **`-100` means DISCONNECT/CRASH only — NOT ejection.** A `-100` (and the all-seats
  variants) is an ops failure: the player container disconnected or crashed. Filter
  these out before computing any rate (see the ops-filter practice below). **Do NOT
  read `-100` as "got voted out."**
- **Getting EJECTED (voted out) carries NO points penalty — there is no score signal
  for it at all.** A loss after being ejected looks identical in `results.json` to any
  other loss. So you **cannot** infer the ejection rate from scores; "no `-100`s ⇒ not
  getting caught" is a FALSE inference. To know whether/when crewborg was ejected you
  **must read the logs/replay** (the meeting outcome / `player_died`-by-vote /
  `expand_replay` ejected-by-vote — `crewrift-report`'s `profile_replay` distinguishes
  killed-by-imposter vs ejected-by-vote). Always check the logs, not the score, for ejection.
- **Cleanest ejection signal for an IMPOSTER: it ended dead.** An imposter cannot be
  killed (only crew can), so an imposter dead at game end was **necessarily ejected by
  vote**. In an event warehouse, `player_state.alive` going False for the imposter slot
  (or a `died`/`player_died` event on that slot) = ejected — no meeting-tally parsing
  needed. So *imposter ejection rate = fraction of imposter games the policy ended
  dead*. (Crew deaths are ambiguous — killed vs ejected — and DO need the vote events.)
- **🚩 Meeting/voting ticks are NOT idle time — exclude them from EVERY idle / latency /
  ready / gap metric.** A body report or button press starts a meeting: `MeetingCallTicks`
  (72) + `VoteTimerTicks` (1200) ≈ ~1272 ticks during which nobody moves or kills, everyone
  is teleported home, and a body/unknown meeting **resets imposter kill cooldowns**. So any
  "idle-ready", "kill latency / dither", "ticks since cooldown ready", "ready→kill", or
  "inter-kill gap" number must drop meeting ticks. This has bitten the analysis repeatedly
  (the "~2000-tick inter-kill gap" and the "2077-tick wander" were both *meetings*, not
  hunting). **Two layers, BOTH required:** (1) filter `player_state.phase == 'Playing'` —
  drops the meeting *samples*; (2) **never subtract a raw tick delta across a Playing-filtered
  series** — the delta between two consecutive Playing samples STILL spans any meeting in
  between (~1272 ticks; and a *button* meeting doesn't reset the cooldown, so the `cd==0`
  guard won't even catch it). Instead **count Playing+ready samples × snapshot interval**, or
  bound the window explicitly at the next meeting. And: a **ready→kill window ENDS at the next
  meeting** (the meeting resets the cooldown), so a kill *after* a meeting does NOT convert
  that ready moment — attribute it to the post-meeting ready event. (Reference impl:
  `tools/positioning_viz/extract_positions.py` — sample-count idle + meeting-aware window.)

## Evaluation

- **Crewmate and imposter are two different policies — never judge them merged.**
  The same code in the two roles has different objectives, different action sets
  (kill/vent only exist for imposters), and different score structures. An aggregate
  win-rate routinely hides one role being broken. **Always decompose eval by role**,
  and target experience requests at matched roles when a change was role-specific.
  Force your policy's role by pinning its roster `slot` + `game_config_overrides.slots` — exact shape in
  [`crewrift-gameplay.md` → Forcing roles in evaluations](docs/crewrift-gameplay.md) (an
  array of `{"role": …}` objects, not bare strings — the common mistake).

## Reading games (replays & logs)

- **`expand_replay` needs a version-matched game build; for league episodes it will
  usually `hash failed`.** It re-simulates recorded inputs through the local crewrift
  `sim` and stops on the first hash mismatch, so a downloaded league replay built by a
  different game version emits only a few early events. For hosted/league episodes,
  **prefer crewborg's own logs (version-independent) and the visual viewer** (which
  uses the episode's own game image). `expand_replay` is reliable for locally-generated
  replays and the bundled fixture. (Details: [`docs/crewrift-replays.md`](docs/crewrift-replays.md) §B.)
- **League episodes are not in the `/v2/episode-requests` table** — `coworld episodes
  -p crewborg:vN` returns `[]`. Discover them via `/stats/policy-versions` → `/episodes`
  (what the `coworld-episode-artifacts` downloader does). Don't conclude "no episodes."
- **Confirm what's in a log before querying it; don't assume.** crewborg's trace
  default has changed over time (per-tick `decision_snapshot`/metrics moved off by
  default). Run the **event histogram** recipe first so an empty `select` means "didn't
  happen," not "wrong query / not captured at this trace level."
- **Identify crewborg's slot by name *and* version.** A single league episode can carry
  several crewborg versions, and every crewborg slot's log is JSON — a `head -1 | jq`
  test only proves "a crewborg log," not *which version*. Map slot→policy from
  `episode.json` (`policy_results[]`), not `results.json`.

## Perception & the scene contract

- **The game owns the scene vocabulary; re-derive from source when in doubt.** The
  Sprite-v1 object-id ranges, labels, and camera offsets (in
  [`docs/crewrift-player.md`](docs/crewrift-player.md) and crewborg's
  `perception/constants.py`) are verified against `Metta-AI/coworld-crewrift`:
  `src/crewrift/{sim,global}.nim`, but they are the **game's to change**. If perception
  misbehaves after a game bump, suspect drift and check the Nim source before trusting
  the decoder.
</content>
