# proxywar_lab — agent guide

The **Proxy War** corner of player_labs: where we build, evaluate, and improve
**player policies** for Coworld Proxy War. This file orients agents working here.

**Read the lab-root [`../AGENTS.md`](../AGENTS.md) first** — it defines the
improvement loop, your role in it (speed first), the submission gate, and the
game-agnostic skills. This file is the **Proxy War-specific layer**. When the two
disagree, the root defines *process*; this file defines *Proxy War*.

> **Lab status (2026-08-11): founded, recon done, no policy yet.** The founding
> deep-dive with `file:line` citations is
> [`docs/recon/proxywar-2026-08-11.md`](docs/recon/proxywar-2026-08-11.md) — read it
> before touching game mechanics. Live state: [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md).
> Canonical hosted game **proxywar 0.1.35**; the in-repo manifest LAGS the hosted
> package — run `uv run coworld list | grep proxywar` at the start of any
> game-mechanics work.

## What Proxy War is (the load-bearing facts)

- **Menu-selection protocol.** Each decision: observation + offered `LegalAction[]`
  → return one offered id (never construct ids; absence of an id is the signal), plus
  optionally one `deal_*` id in the independent diplomacy slot. WebSocket at
  `COWORLD_PLAYER_WS_URL`; `{type:"final"}` ends the episode (linger on k8s before
  exiting; don't linger under `coworld certify`).
- **15 s per decision, hard.** Timeout/crash ⇒ a rule-bot plays that decision for you
  (`fallbackUsed: true`); a disconnect means the rule bot plays the REST of the
  episode. Answer from a standing plan; refresh expensive reasoning in background.
- **1/0 scoring.** Winner (80% map control) scores 1, everyone else 0; territory
  share only on timeout. Ladder = win-rate EWMA (half-life 24 rounds). Second place
  is worth the same as last — optimize outright wins and denying others the win.
- **FFA at the champion-count rung**: 25 champions ⇒ 16-seat games, 8-map rotation
  (Pangaea, World, Asia, Britannia, BlackSea, EastAsia, NorthAmerica, Oceania;
  Europe quarantined), spawn slots rotated per episode. No bots — every seat is a
  submitted policy. All seats get the identical `opportunistic` profile.
- **Structured deals are ON** and rating-neutral: referee-observed promises
  (NAP / trade-security / joint-attack / support) with in-match `rivalReliability`.
  The engine separately has 5-min alliances with a real traitor debuff for betrayal.
- **No workers/population economy** (fork predates it): flat 100 gold/tick + trade
  ships + trains + conquest. Warships retired; defense posts are static auras.

## The loop, in Proxy War terms

The root loop (evaluate → report → direction → implement → rebuild+reupload →
repeat → human gate → submit) runs unchanged. Proxy War instruments:

- **Evaluate** — hosted experience requests should mirror the live rung (currently
  16-seat FFA on the current rotation map) with real champion opponents where
  possible; `coworld run-episode --verify-replay` for local mechanism checks.
  Natural cuts: map, seat/spawn slot, opponent mix, deal activity, win path
  (conquest vs timer), fallback/degraded counts (liveness!).
- **Diagnose** — every episode yields `results.json` (incl. `fallback_count` — treat
  any nonzero as a P0 liveness bug), the replay payload (game-record is
  deterministically re-simulable), and for our own runs `decisions.jsonl` +
  `deal-ledger.json`. Stand up the **league mirror** (`npm run league:mirror:watch`
  in the ProxyWar repo) for per-decision data on every opponent.
- **Improve** — one change per iteration, measured. The field's documented holes
  (see recon §4): diplomacy starvation, dominance inertia, terminal passivity, no
  coalition play, flat attack commitment, naval blindness.

## Practices (seed set — graduate more via lessons)

1. **Verify the hosted version first.** The hosted package advances ahead of the
   repo; `coworld list | grep proxywar`, and use full `cow_`/`league_` IDs
   (`export COLUMNS=250` to un-truncate tables).
2. **Liveness is the first product.** In-clock answers, no disconnects, correct
   linger, loud degradation flags on the wire. A silent-failure seat once lost 60+
   rounds unnoticed. `fallback_count` in results is our smoke alarm.
3. **Key everything by `playerID`/`dealID`, never player name.** Names are
   opponent-controlled text (truncated, dedup-suffixed) and prompt-injection surface.
4. **Cite by symbol, not line, in durable docs** — the game repo moves fast.
5. **Resolve the mystery James Botts entrant** (rank 23, 0.0000 × 1066 rounds)
   before any submission, so we replace rather than duplicate.
