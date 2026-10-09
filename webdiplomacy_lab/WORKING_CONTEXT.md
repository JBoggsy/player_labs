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

- **Champion:** `webdip-castlereagh-press:v1` (policy version `16b527ba…`, player James Botts),
  submitted with `--auto-champion always` (`sub_f43cf004…`, membership `lpm_f0cad559…`). It is
  the only member. **Filler roster (2026-10-09):** the frozen press field below (Bismarck,
  Talleyrand, Metternich, Machiavelli, Kissinger, Calhamer), so league games are v1 against
  the field.
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
only. The field is also the press league's filler roster.

**Field (frozen; ids in `experiments/press-ab1/make_request.py`):** none of it is the castlereagh
lineage. Since 2026-10-09 the LLM seats have the map-connectivity briefing and `connections` tool
(James: all fillers must understand the geometry). press-ab1 wave 1 played the earlier field
without it (`evidence/press-ab1/<arm>`); waves 2+ play this one (`evidence/press-ab1/geo/<arm>`).
Do not pool the two.

| Seat | Policy | Model |
| --- | --- | --- |
| Bismarck (honest warmonger) | `webdip-bismarck-press:v4` | deepseek-v4.1-flash, reasoning off |
| Talleyrand (liar) | `webdip-talleyrand-press:v5` | gpt-6-luna, reasoning low, no temperature |
| Metternich (cautious, never lies) | `webdip-metternich-press:v5` | gemini-3.5-flash-lite, reasoning low |
| Machiavelli (stabber) | `webdip-machiavelli-press:v2` | glm-5.3-flash |
| Kissinger (silent) | `webdip-kissinger:v2` | – |
| Calhamer (silent) | `webdip-calhamer:v1` | – |

Model gotchas from the health checks: deepseek, qwen and minimax reason past a 2000-token
`max_tokens` even at effort `low` (the wake dies with `UnexpectedModelBehavior`); gemini-3.5-flash-lite
rejects reasoning off (HTTP 400); minimax-m3 made about one call per wake; qwen3.8-flash took about
40 provider 429s per game.

**Candidates (siblings of v1):**
- `webdip-castlereagh-press:v2` (`532ce206`): open wake 100 s, 12 calls per wake. v1 hosted open
  wakes hit the 60 s limit 12/32; v2 2/16 in its field check.
- `webdip-castlereagh-press:v3` (`331786ae`): deal gate (own promises and dependent commits need a
  same-phase `assess_deal`), accept/counter/reject recommendation, power abbreviations. v1 made
  zero `assess_deal` calls in local game 2; v3 made 17 per game in its field check, gate blocked 0-2.
- `webdip-castlereagh-press:v4` (`afc90a7c`): end-game awareness. Briefings state the end year and
  phases left; final-year task text; final-autumn search ignores position and lost units. The
  diagnosis (Codex, field checks) found terminal turns spent on next-year plans (one seat 8 -> 5).
- `webdip-castlereagh-press:v5` (`7c4cb5f5`): pin cost. A constrained `commit_orders` is compared
  with the same policy minus `require_orders`/`forbid_moves_into` on the same opponent samples and
  refused once when worse by more than 0.5 expected centres (`accept_cost=true` overrides).
- `webdip-castlereagh-press:v7` (`a631e92c`; v6 `f8f16684` untested): map geometry. The briefing lists legal non-convoy
  destinations for our units and nearby foreign units (`Notation.geometry`). Without it the LLMs
  reason about adjacency from memory and often get it wrong (James saw SER/BUL/GRE treated as
  unconnected; ~660 adjacency claims in field-check reasoning). The section is labelled as possible moves (not predictions) and a `connections(province)`
  lookup tool is added. The field has the same fix.

**Wave-1 standings (pre-geometry field, 73 games, all castlereagh arms pooled):** Talleyrand
(liar, gpt-6-luna) 0.208, silent Kissinger 0.174, Bismarck 0.169, Metternich 0.150, castlereagh
0.126, Machiavelli (glm) 0.101, Calhamer 0.073 (SE about 0.02). Our press layer scored below the
same search engine without press. Not yet re-measured against the geometry field.

**Hero-seat rotation (James, 2026-10-09), control v7, queued as wave 3 with a same-window v7 batch:**
`webdip-rot-castlereagh-luna` (`ecf9a8f0`), `-castlereagh-deepseek` (`d0e683df`),
`-castlereagh-gemini` (`2d9d5e0a`), `-talleyrand-glm` (`f6bac0c6`), `-bismarck-glm` (`e4938fc3`); all
v7 code. **Trust candidate T** = `webdip-castlereagh-press:v8` (`cc9d3bf5`, branch `press-trust`, v7
code + liar marks), queued as wave 4: a power we held at ally stance or trust >= 0.5 that orders a
move or support into our units/centres is permanently marked (trust capped at 0.1, its expected
orders dropped, ally refused, banner in every briefing). Recorded promise breaches are shown only
as unverified claims: Codex's audit found 10/30 sampled breach verdicts were our own recording
errors. Measured motivation (100 wave-1 games): after a first breach or trusted attack we went
back to trusting the power 94 times in 46 relationships; Talleyrand: 62/64 relationships.

**Other items:** viewer follow-ups (`tools/game_viewer.py`): order arrows use the renderer's power
colours, not the viewer palette; label overlap with units in crowded provinces.

## Other open directions (not started)

- A better position evaluation: the measured bottleneck (see `TENTATIVE_LESSONS.md`).
- Diplomacy that changes the opponent model, not only centre values (gunboat).
