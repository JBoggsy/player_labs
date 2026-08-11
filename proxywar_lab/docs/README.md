# proxywar_lab docs — index

| doc | what it is | status |
|---|---|---|
| [`recon/proxywar-2026-08-11.md`](recon/proxywar-2026-08-11.md) | The founding deep-dive: game dynamics (OpenFront core), decision contract (observation/LegalAction/deal schemas), league model, artifacts/replays, consolidated gotchas, strategic implications. `file:line` citations into all three repos + the hosted 0.1.35 manifest. | current (2026-08-11) |
| `reports/` | Hosted experiment evidence and verdicts (empty — no experiments yet) | — |
| `designs/` | Policy design docs (empty — no policy yet) | — |

**Source-of-truth map** (where to look before trusting anything here):

- Hosted package truth: `uv run coworld list | grep proxywar` (the repo manifest LAGS it).
- Protocol truth: `~/coding/coworlds/ProxyWar/coworld-adapter/docs/player-protocol.md`
  + the `protocols.player` text in the downloaded hosted manifest.
- League/commissioner truth: `~/coding/coworlds/ProxyWar/coworld-adapter/commissioner/commissioners/{proxywar_app.py, ruleset_strategy_commissioner/configs/proxywar.yaml}`.
- Schema truth: `~/coding/coworlds/ProxyWar/src/server/agents/AgentTypes.ts` (observation),
  `LegalActionBuilder.ts` (menu), `AgentDecisionValidator.ts` (validation).
- Beware: `docs/PROXYWAR_START_HERE.md` / `OPERATOR_RUNBOOK` / `HOSTED_BETA` in the game
  repo describe the RETIRED self-hosted beta, not the coworld league.
