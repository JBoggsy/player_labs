# Paintbot PW knowledge map

What the lab knows about paintbot-pw, where each piece lives, and how to check it is
still true. Start here, after [AGENTS.md](AGENTS.md).

Every mechanics document opens with a **Currency** block naming the paintbot-pw commit
it was verified against. The deployed commit is the only one that matters, and the game
ships several releases a day. Check it first:

```sh
uv run python paintbot_pw_lab/tools/deployed_ref.py     # each league's release vs the docs
paintbot_pw_lab/tools/build_tools.sh                    # engine binaries at the pinned tag
```

Everything below is verified at `Metta-AI/paintbot-pw` `7b2b19f5` (tag `coworld-v0.3.65`,
rules 45), 2026-09-28, unless marked otherwise, and re-checked at `ab597b35` (0.3.67, the
same day): that release changes only art, terrain generation, `jev.bas` loop bounds and the
glory-heart pair count on big maps. `mechanics.nim`, `bots.nim`, `game.nim` and `basic.nim`
are unchanged; `sim.nim` citations past line 941 shift by +3. 0.3.68 (`ef82196`, live the
same evening) is a refactor with no rules change: config parsing moved from `game.nim` to
`match_config.nim` and `LiveRules = 45` was added, so `game.nim` and `sim.nim` line numbers
shift a little more. The onboarding report is
[`docs/reports/paintbot-pw-onboarding-2026-09-28.html`](../docs/reports/paintbot-pw-onboarding-2026-09-28.html). Where the maintainer's guide and the code
disagree, the code wins; the known mismatches are listed in
[mechanics.md §8](docs/mechanics.md).

## The game in one paragraph

Two teams of eight wheeled cogs (Red on even seats, Blue on odd) fight over ten heart
towers on Heartwick island. Standing near a heart for 72 ticks captures it; each owned
heart fills the team's meter at one point per second, and the first team to 900 wins
(five hearts for three minutes), or the higher meter at 10:00. Cogs have 3 HP, four
lives, a hitscan paint gun, and fog-gated pickups (grenade, spray can, shield, medkit).
The **score** is not the meter but **glory**: 600 minus one per second, plus awards,
kept only by the winner. Every seat is a BASIC script run inside the engine.

## What we know, and where

| Topic | What is established | Document |
| --- | --- | --- |
| Win condition vs score | The meter decides the winner; `scores` are the winner's glory, loser and draws 0. League Elo reads only win/draw/loss from the side means (`observatory_competitions/.../rankings/elo.py:150-195`), so a win with glory decayed to 0 rates as a draw, and an episode failure attributed to one policy is a forfeit loss for its side. | [mechanics.md §1](docs/mechanics.md), [field.md](docs/field.md) |
| Glory awards | Countdown −1/s; +10 per 30 s with no team pickup; +20 per glory heart; +5 per life behind every 5 s in the league config (engine default 1). | [mechanics.md §1](docs/mechanics.md) |
| Rules | Hearts and capture, lives and respawn, gun/spray/grenade, armor, trenches, disguises, lake, vision cone and hearing, maps and modes. | [mechanics.md](docs/mechanics.md) |
| Policy language | Polyworld BASIC; per-tick decision; 50,000 instructions and 125,000 work units per decision; 128 KiB source; PRINT limits. | [policy-surface.md §2-3](docs/policy-surface.md) |
| Failure modes | Compile error fails the whole episode; runtime error or budget overrun disables that seat for the episode; a rejected file forfeits only its seat. | [policy-surface.md §4](docs/policy-surface.md) |
| Host API | Self fields, fog-gated players/pickups, public hearts and capture state, map geometry, actions, `shout`, the advisor oracle, FFA-only names, the neural-BASIC ZIP lane. | [policy-surface.md §5](docs/policy-surface.md) |
| Starters | `base.bas` (league baseline), `jev.bas` (base plus LLM advisor), `ffa.bas` / `ffa_blind.bas` (Heartland). | [policy-surface.md §6](docs/policy-surface.md), [reference/](reference/) |
| Leagues and field | Main teams ladder: two policies per episode, each filling a whole team, seed 2026, 12 episodes every 10 min. Leaders (2026-09-28): Aaron L (two entries) and David B (the game's maintainer; a neural policy and an LLM-advisor policy). Heartland (FFA-kin) opened 2026-09-28. | [field.md](docs/field.md) |
| Evaluation budget | Experience-request fields, the roster trap (pin all 8 opponent seats), credits (~0.3 per episode). | [field.md §Experience requests](docs/field.md) |
| Community | Forum empty; wiki is a stale README copy; the maintainer's guide carries the only measurements. | [community.md](docs/community.md) |
| Evidence pipeline | Artifacts, the `POLYWORLDREPLAY` tape, hash-checked re-simulation (one build replays older rules), local runs, the verified per-seat stats probe, and the adapters still to build. | [evidence-pipeline.md](docs/evidence-pipeline.md) |

## Instruments

| Instrument | State |
| --- | --- |
| `tools/deployed_ref.py` | Working. League → coworld release → tag commit, vs `DOCS_SHA`. |
| `tools/build_tools.sh` | Working. Builds `paintbot-headless` (hash-checked replay validation, native local runs) and `replay_stats` into `tools/bin/<tag>/`, plus the engine `local.py` needs in `tools/.cache/<tag>/`. |
| Local match | `tools/bin/<tag>/paintbot-headless --bot reference/base.bas:16 --seed 2026 --ticks 2400`, or `local.py` from the worktree for per-seat logs. `--bot FILE:N` fills seats in order, so alternate flags for A vs B. Local runs cannot set the league's glory config. |
| Per-seat replay stats | Probe verified (source in [evidence-pipeline.md, appendix](docs/evidence-pipeline.md)); not yet a lab tool. |
| A/B (`compare.py`), miner (`features.py`), episode reader | Not built. Design in [evidence-pipeline.md §8](docs/evidence-pipeline.md). |
