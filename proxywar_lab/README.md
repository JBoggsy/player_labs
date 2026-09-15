# proxywar_lab

This README orients newcomers (human or agent). Three pointers do most of the work:


## The game (one paragraph)

Proxy War turns the OpenFront RTS (claim territory, build economy, ally, betray,
nuke) into a **menu-selection decision game** for AI agents: every 100 game turns
(10 simulated seconds), each seated policy gets an observation + a menu of offered
`LegalAction.id`s and picks exactly one — plus, optionally, one `deal_*` action in a
free second **diplomacy slot** (structured, referee-observed promises: NAPs,
trade-security, joint attacks, support). You cannot make an illegal move. The league
runs rotating-map FFAs whose seat count (2/4/8/12/**16**) tracks the champion count;
win = first to **80% map control**; episode score is **1/0 for the winner** (territory
share only on timeout), EWMA'd into an OpenSkill-style ladder. 15 s per decision,
300–500 decisions per episode, ~25–90 min wall clock.

## Repos

| repo | where | what |
|---|---|---|
| `0xNad/ProxyWar` | `~/coding/coworlds/ProxyWar` | engine + agent layer + coworld adapter + commissioner (source of truth) |
| `0xNad/proxywar-coworld-starter` | `~/coding/coworlds/proxywar-coworld-starter` | public policy starter (Bedrock LLM plan-in-background + rule agent) |

The main repo is a normal public clone (not James's; safe to branch locally, never
push without asking). `git -C ~/coding/coworlds/ProxyWar pull` before relying on it —
the hosted package auto-advances ahead of the repo's checked-in manifest.

## Layout

## Quick commands

```sh
uv run coworld list | grep proxywar        # verify the canonical hosted version FIRST
uv run coworld results div_b54268ee-6b2f-4156-9c2a-8542645e31bc   # Competition standings
uv run coworld run-episode cow_1ce44ce9-42d1-4e08-a0d3-df559f9bd44e --verify-replay  # local episode
# Build/upload a policy (from a starter-derived dir with a Dockerfile):
docker build --platform linux/amd64 -t proxywar-agent:latest .
uv run coworld upload-policy proxywar-agent:latest --name <name> [--use-bedrock] \
  --run node --run /app/<player>.mjs
```

Upload freely; **submitting to the league is the human-gated step** (root
[`AGENTS.md`](../AGENTS.md)). New submissions pass a Qualifiers self-play crash check,
then auto-promote to Competition.
