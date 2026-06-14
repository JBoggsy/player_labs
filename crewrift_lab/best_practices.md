# Crewrift best practices

Crewrift-specific practices for the improvement loop — layered on top of the
**game-agnostic** [`../best_practices.md`](../best_practices.md) (read that first;
these are additions, not replacements). Distilled from real work in this lab; treat
as defaults and **warn the human if a request would contravene one** before
proceeding. Add to this file as we learn more about *this game's* failure modes.

## Evaluation

- **Crewmate and imposter are two different policies — never judge them merged.**
  The same code in the two roles has different objectives, different action sets
  (kill/vent only exist for imposters), and different score structures. An aggregate
  win-rate routinely hides one role being broken. **Always decompose eval by role**,
  and target experience requests at matched roles when a change was role-specific.
  Force your policy's role by pinning its roster `slot` + `game_config_overrides.slots` — exact shape in
  [`crewrift-gameplay.md` → Forcing roles in evaluations](docs/crewrift-gameplay.md) (an
  array of `{"role": …}` objects, not bare strings — the common mistake).
- **Don't evaluate imposter changes only against the top-7 — kills are
  opponent-relative.** Imposter kill rate scales steeply with opponent *weakness*
  (measured: ~1.1 k/g vs the strongest crew → ~1.9 vs the weakest; corr ≈ −0.35 with
  opponent leaderboard score), because strong crew rarely isolate and the kill is
  witness-gated. So the standing "pin the top-7 champions" A/B roster **caps kills
  regardless of policy and hides real gains** — `CREWBORG_NO_ISOLATION` read as a dead
  no-op vs the top-7 (1.27→1.24) yet was a clear win vs weak crew (1.69→1.92, imposter
  win 59%→73%, *fewer* ejections) and shipped on that basis (v29). When testing an
  imposter kill/aggression lever, **include a weak/mid-crew roster** (Crewrift ranks
  ~8–18), not just the leaders. This is the Crewrift instance of the game-agnostic
  "evaluate across the whole field's strength" rule in
  [`../best_practices.md` → Measurement](../best_practices.md).

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
