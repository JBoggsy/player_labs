# Working context — proxywar_lab

*The live, minimal, high-signal state of what we're working on right now.
Update as you learn; clear/reseed on a pivot.*

## Current objective

**Lab founded 2026-08-11; recon complete; no policy exists yet.** The founding
deep-dive (game dynamics, protocols, schemas, league model, gotchas — all
citation-backed) is [`docs/recon/proxywar-2026-08-11.md`](docs/recon/proxywar-2026-08-11.md).
Next: pick the first-policy direction with James (see "Next concrete steps").

## Facts worth carrying forward (verified 2026-08-12)

- **Repos**: `~/coding/coworlds/ProxyWar` (main; a normal public clone — pull
  before use, hosted package runs AHEAD of the checked-in manifest, ~4 versions/day
  observed); `~/coding/coworlds/proxywar-coworld-starter` (public starter, MIT);
  `~/coding/coworlds/ProxyWar-starter-agent` (RETIRED relay path, reference only).
- **Hosted canonical**: `proxywar 0.1.39` = `cow_e3b19156-63ca-47d2-9736-71b087b269a9`
  (2026-08-12; the founding recon was done against 0.1.35, whose `config_schema`,
  `variants`, and game env are **byte-identical** to 0.1.39's — the 0.1.36-39 deltas
  are commissioner-side only). Structured deals ON
  (`PROXYWAR_TUNE_STRUCTURED_DEALS=1` in the game runnable env).
- **League**: `league_cb60d526-ecfd-4836-ab3a-81fc6cf7dc42` "Proxy War".
  Divisions: Qualifiers `div_db67a8bc-0330-4c4f-8b79-e1e675e24128` (staging crash
  check, self-play, 2 attempts), Competition `div_b54268ee-6b2f-4156-9c2a-8542645e31bc`
  (25 members). Rounds every 30 min; seat rung = largest of {2,4,8,12,16} ≤ champion
  count (currently 16); map rotation by round number. **Quarantined from automatic
  scheduling (2026-08-11): Europe (12p, artifact timeouts) AND World/Britannia/
  NorthAmerica at both 12p and 16p (multi-hour round wall-times, pending
  engine-efficiency work)** — the effective 16p pool is now Pangaea, Asia, BlackSea,
  EastAsia, Oceania. `episodeIndex` rotates spawn slots. **Seating windows are now
  SHUFFLED per round** (repo `e3c04bd`, 2026-08-12): the old stable rolling_window
  gave mid-list entrants 86-100% episode exposure vs ~7-14% at the ends (measured
  live rounds 1270-1365), silently distorting EWMA scores. Scoring: episode 1/0
  (winner = 80% map control; territory share on timeout); ladder = win-rate EWMA,
  half-life 24 rounds, 5-round provisional gate.
- **Episode contract (16p)**: 500 decision steps × 100 turns, `max_decision_ms`
  **15000**, connect window 120 s, episode timeout 4500 s, no bots — every seat a
  policy, warships disabled, starting gold 200k, all seats profile `opportunistic`.
- **Standings (2026-08-12, post-seating-fix reshuffle)**: daveey 16.54 (975 rds) »
  Jordan 15.54 » Andre von Houck 13.65 » Calc 12.53 » SIAN VOIDCROWN 12.39 »
  CYAN HELLSTAR 11.80 » … » **James Botts rank 21, 0.5714 over 1087 rounds** (was
  0.0000/rank 23 a day earlier — the entrant is live and occasionally scoring, still
  unidentified). Known opponent policies: relh `co-gas-proxywar-relhalpha:v26`,
  0d1novizzz `xX_UwU_Senpai_420_Xx:v14`, docxology `daf-proxywar-v9:v1`, Ari Sklar
  `arisk-proxywar:v1`, Matt Van `mattvan:v2`.

## Open threads

- **UNRESOLVED: what backs the "James Botts" Proxy War entrant** (rank 23,
  0.0000 × 1066 rounds)? It appears in Competition standings, but
  `coworld memberships` shows no Proxy War policy under our account (only
  stencil/beacon/wowborg/sugarscape rows). Suspected auto-mirror (cf. beacon's
  CTF→Paintbot mirror). Must resolve before submitting anything so a new submission
  replaces rather than duplicates it.
- League mirror not yet stood up (`npm run league:mirror:watch` in the ProxyWar
  repo) — it captures `decisions.jsonl` + game-records for every policy in every
  mirrored episode; wanted as our scouting corpus before designing the policy.
- No `versions.env`-style pin exists yet for this lab; create one when we first
  build an image (pin the game repo commit + hosted cow version used for testing).
- First-policy architecture decision pending (James): starter-derived LLM
  plan-in-background vs deterministic-executor-with-background-planner (Keystone
  shape) vs pure deterministic. Recon §7 recommendation: deterministic executor +
  background planner, liveness-first, coalition/deal-aware, win-condition-focused.

## Next concrete steps

1. Resolve the existing James Botts entrant (what policy, which membership; retire
   or plan to replace it).
2. Stand up the league mirror and pull a first scouting corpus (daveey + top 5:
   what do their decisions look like? deal activity? win paths?).
3. Decide first-policy architecture with James; scaffold `proxywar_lab/proxywar/`
   player source from the starter as a baseline.
4. Certify + upload a liveness-hardened baseline (zero fallbacks in certification);
   run one hosted-shape local 16p episode to validate timing.
5. Only then iterate on strategy (submission = human gate).
