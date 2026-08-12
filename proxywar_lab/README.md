# proxywar_lab

The **Proxy War** corner of [player_labs](../README.md) — where we build, evaluate,
and improve player policies for **Coworld Proxy War**, an agent-layer wrap of the
OpenFront.io real-time territorial strategy engine, by 0xNad/Auri.

This README orients newcomers (human or agent). Three pointers do most of the work:

- **[`AGENTS.md`](AGENTS.md)** — the operating model *for this lab*: the improvement
  loop in Proxy War terms, and the lab's practices.
- **[`docs/recon/proxywar-2026-08-11.md`](docs/recon/proxywar-2026-08-11.md)** — the
  founding deep-dive: game dynamics, protocols, schemas, league model, and the full
  gotcha list, with `file:line` citations into the game repos.
- **[`WORKING_CONTEXT.md`](WORKING_CONTEXT.md)** — live cross-session state. Read first.

> **Status (2026-08-12): lab founded; recon complete; no policy yet.** The league
> (`league_cb60d526-…`) has 25 champions in Competition; a mystery "James Botts"
> entrant sits near the bottom of the table (resolve before submitting). The hosted
> package advances several versions per day — **always resolve the canonical version
> live** (`uv run coworld list | grep proxywar`) rather than trusting any doc,
> including this one. Recon baseline: 0.1.35 (2026-08-11); its game contract was
> still byte-identical at 0.1.39 (2026-08-12), with commissioner-side changes only
> (map quarantines, per-round seating shuffle) — see `WORKING_CONTEXT.md`.

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
| `0xNad/ProxyWar-starter-agent` | `~/coding/coworlds/ProxyWar-starter-agent` | RETIRED relay/HTTP path — reference only, do not build against |

The main repo is a normal public clone (not James's; safe to branch locally, never
push without asking). `git -C ~/coding/coworlds/ProxyWar pull` before relying on it —
the hosted package auto-advances ahead of the repo's checked-in manifest.

## Layout

```
proxywar_lab/
  README.md              this file
  AGENTS.md              operating model: the loop in Proxy War terms
  WORKING_CONTEXT.md     live cross-session state — read first
  TENTATIVE_LESSONS.md   this session's candidate-lessons buffer (auto-rotated)
  docs/
    recon/               the founding deep-dive + future recon addenda
    reports/             hosted experiment evidence and verdicts
    designs/             policy design docs
  tools/
    rotate_lessons.sh    SessionStart hook (archive the lesson buffer)
  lessons_archive/       rotated per-session lesson buffers
```

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
