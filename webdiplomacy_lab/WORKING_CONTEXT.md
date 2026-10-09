# webdiplomacy_lab working context

Resolve live state (league settings, champion, policy versions, filler roster) through the
platform before acting. This file holds only the current state and next decision. The
unattended-loop recipe is [LOOP.md](LOOP.md). Measured lessons are in
[best_practices.md](best_practices.md).

## State (2026-10-07)

- **Gunboat champion (`webDiplomacy Gunboat`):** `webdip-dumbbot:v8` (policy version `41938ab8…`), submitted 2026-10-07.
  It is the Kissinger policy:
  - search with level-1 opponents and the competent-belief fix;
  - convoy approximation;
  - the modular SearchBot refactor with the Nim integer/boolean adjudicator.

  Its behaviour is bit-identical to v7 (golden contract `webdip_bot/tests/golden.json`, 334
  exact decisions), with decisions a median 27% faster.
  - Hosted check `xreq_38daed76…`: 0 exceptions, 0 rejected orders, max decision 2.8 s.
- **Final-policy decision:** in paired games, no variant beats plain Kissinger (risk
  aversion, build search, Castlereagh diplomacy, mixed strategy, Fabius, level 2, triples,
  rollout). Details are in `experiments/ledger.jsonl`.
- **League fillers (12):** Random, Calhamer, Machiavelli v3, Bismarck v2, Metternich v2,
  Talleyrand v2, Napoleon v2, Blücher v2, Kissinger v2, Fabius v1, Garibaldi v1, Rasputin v1.
  The Kissinger filler still runs the Python adjudicator, with identical behaviour.
- **Competition:** relh (`co-gas-webdiplomacy-relh:v2`) is the only other entrant. It scores
  about 0.0–0.03 per game in hosted tests against us and the fillers.
- **The continuous loop is wound down.** Crons are deleted and `evolve.py` is stopped at
  generation 53; its state is in `experiments/evolve_state.json`.

## Press league (`webDiplomacy`, classic-press) — 2026-10-08

- **Champion and only filler:** `webdip-castlereagh-press:v1` (policy version `16b527ba…`,
  player James Botts), submitted with `--auto-champion always`
  (`sub_f43cf004…`, membership `lpm_f0cad559…`, qualified and champion). Filler roster:
  that version, display name "Castlereagh". League games are therefore all-Castlereagh until
  other entrants arrive.
- **Policy:** `castlereagh_press` — the LLM press agent (`webdip_bot/press/`) over Kissinger
  search, model `z-ai/glm-5.3-flash` (upload flag), design in
  [`docs/designs/press-agent-design.md`](docs/designs/press-agent-design.md).
- **Evidence so far:** two local all-Castlereagh `classic-press-short` games (0 rejected
  orders, 0 exceptions; $0.32 and $0.35 per game; viewers under
  `local_runs/press-v1/game{1,2}/viewer.html`). Hosted health check
  `xreq_547d713f…` (2 `classic-press-short` episodes vs 6 bundled random bots): the real
  sidecar path works — 132 calls all HTTP 200, 0 exceptions, 0 rejected orders, $0.03–0.04
  per seat-game (the sidecar's spend header runs about 6% above summed `usage.cost`; treat
  the header as the billing number). No strength measurement exists yet: the opponents sent
  no press, and local runs are self-play.
- **Cost:** about $0.70 per full classic-press game with all seven seats on the LLM,
  metered against the league's spend limit.

## Press strength campaign (press-ab1)

**Measurement (James, 2026-10-08):** a frozen, diverse press field decides "better", in hosted
A/Bs. One candidate seat plus six field seats, `classic-press` (full game decides;
`classic-press-short` only for health/activation checks), baseline and candidates in the same
window, per-power score vs par (`tools/compare.py`). Pre-registered: about 150 episodes per arm
(per-seat score SD about 0.19); an interim look at about 50 per arm checks health and activation
only. The field also replaces the press league's filler roster once it is healthy.

**Field (frozen; ids in `experiments/press-ab1/make_request.py`):** none of it is the castlereagh
lineage.

| Seat | Policy | Model |
| --- | --- | --- |
| Bismarck (honest warmonger) | `webdip-bismarck-press:v3` | deepseek-v4.1-flash, reasoning off |
| Talleyrand (liar) | `webdip-talleyrand-press:v2` | qwen3.8-flash, reasoning off |
| Metternich (cautious, never lies) | `webdip-metternich-press:v4` | gemini-3.5-flash-lite, reasoning low |
| Machiavelli (stabber) | `webdip-machiavelli-press:v1` | glm-5.3-flash |
| Kissinger (silent) | `webdip-kissinger:v2` | – |
| Calhamer (silent) | `webdip-calhamer:v1` | – |

Model gotchas from the health checks: deepseek, qwen and minimax reason past a 2000-token
`max_tokens` even at effort `low` (the wake dies with `UnexpectedModelBehavior`); gemini-3.5-flash-lite
rejects reasoning off (HTTP 400); minimax-m3 made about one call per wake; qwen takes frequent
provider 429s.

**Candidates (siblings of v1):**
- `webdip-castlereagh-press:v2` (`532ce206`): open wake 100 s, 12 calls per wake. v1 hosted open
  wakes hit the 60 s limit 12/32; v2 2/16 in its field check.
- `webdip-castlereagh-press:v3` (`331786ae`): deal gate (own promises and dependent commits need a
  same-phase `assess_deal`), accept/counter/reject recommendation, power abbreviations. v1 made
  zero `assess_deal` calls in local game 2.

**Other items:** viewer follow-ups (`tools/game_viewer.py`): order arrows use the renderer's power
colours, not the viewer palette; label overlap with units in crowded provinces.

## Other open directions (not started)

- A better position evaluation: the measured bottleneck (see `TENTATIVE_LESSONS.md`).
- Diplomacy that changes the opponent model, not only centre values (gunboat).
