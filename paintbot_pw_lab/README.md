# Paintbot PW knowledge map

What the lab knows about paintbot-pw, where each piece lives, and how to check it is
still true. Start here, after [AGENTS.md](AGENTS.md).

Every mechanics document opens with a **Currency** block naming the paintbot-pw commit it was
verified against. The game ships several releases a day, so check where things stand first:

```sh
uv run python paintbot_pw_lab/tools/pw.py doctor --json          # release pin vs league, builds, env
uv run python paintbot_pw_lab/tools/pw.py deployed-ref --json    # + diffstat of rule files since the docs' commit
```

Two pins, on purpose (`tools/release.env`): **the tools** follow the league (`PW_RELEASE_TAG`,
coworld-v0.3.79 = `d0728ab1` on 2026-09-29), while **the docs** stay at the commit their line
citations are exact for (`PW_DOCS_SHA` = `570174a2`, coworld-v0.3.78, rules 47 teams). 0.3.79
changed only the neural lane and training internals; the BASIC teams game is identical.

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
| **Scoring and rank (canonical)** | The meter decides the winner; `scores` are the winner's glory, loser and draws 0. League Elo rates the **glory margin** (`margin_scale: 1000` since 2026-09-28): each episode counts as `clamp(0.5 + (our glory - their glory) / 2000, 0, 1)`, so a 500-glory win is 0.75, a 0-glory win a draw, and a forfeit 0 or 1. Verified at `570174a2` (rules 47) and live settings, 2026-09-29. | [mechanics.md §1](docs/mechanics.md#1-the-one-thing-to-get-right-winning-glory-and-rank) |
| Glory awards | Countdown −1/s; +10 per 30 s with no team pickup; +20 per glory heart; league config: +5 per life behind and +10 per extra cog out of the match, each every 5 s (engine defaults 1 and 1). | [mechanics.md §1.2](docs/mechanics.md#12-how-glory-is-earned-and-lost-rules-37-47) |
| Rules | Hearts and capture, lives and respawn, gun/spray/grenade, armor, trenches, disguises, lake, vision cone and hearing, maps and modes. | [mechanics.md](docs/mechanics.md) |
| Policy language | Polyworld BASIC; per-tick decision; 50,000 instructions and 125,000 work units per decision; 128 KiB source; PRINT limits. | [policy-surface.md §2-3](docs/policy-surface.md) |
| Failure modes | Compile error fails the whole episode; runtime error or budget overrun disables that seat for the episode; a rejected file forfeits only its seat. | [policy-surface.md §4](docs/policy-surface.md) |
| Host API | Self fields, fog-gated players/pickups, public hearts and capture state, map geometry, actions, `shout`, the advisor oracle, FFA-only names, the neural-BASIC ZIP lane. | [policy-surface.md §5](docs/policy-surface.md) |
| Starters | `base.bas` (league baseline), `jev.bas` (base plus LLM advisor), `ffa.bas` / `ffa_blind.bas` (Heartland). | [policy-surface.md §6](docs/policy-surface.md), [reference/](reference/) |
| Leagues and field | Main teams ladder: two policies per episode, each filling a whole team, seed 2026, 12 episodes every 10 min. Leaders (2026-09-28): Aaron L (two entries) and David B (the game's maintainer; a neural policy and an LLM-advisor policy). Heartland (FFA-kin) opened 2026-09-28. | [field.md](docs/field.md) |
| Evaluation budget | Experience-request fields, the roster trap (pin all 8 opponent seats), credits (~0.3 per episode). | [field.md §Experience requests](docs/field.md) |
| Community | Forum empty; wiki is a stale README copy; the maintainer's guide carries the only measurements. | [community.md](docs/community.md) |
| Evidence pipeline | Artifacts, the `POLYWORLDREPLAY` tape, hash-checked re-simulation (one build replays older rules), local runs. The tools built on it are indexed in [docs/tools/README.md](docs/tools/README.md). | [evidence-pipeline.md](docs/evidence-pipeline.md) |

## Instruments

The tools, their agent contract and "which tool answers which question" are indexed in
[docs/tools/README.md](docs/tools/README.md) (generated from `tools/pw.py tools --markdown`).
The skills that drive them are listed in [AGENTS.md](AGENTS.md#agents-start-here). In short:
hash-checked replay expansion (`pw_trace`) feeds per-episode Parquet tables (`pw_episodes`),
one metric library (`pw_metrics`), fights and anomaly flags, movement diagrams and match reports,
the A/B adapter with paired and SPRT tests (`compare`), the local 16-seat harness at the league's
rules and glory config (`pw_local`, about 1.5 matches/s), public-data scouting (`pw_scout`),
intent telemetry and its audit (`pw_intent`), the miner adapter, a win-probability model, and an
SPSA tuner.

