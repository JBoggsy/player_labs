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
- **Health:** the hosted sidecar path works (132/132 calls in `xreq_547d713f`; 0 exceptions or
  rejected orders in every press-ab1 game inspected). The sidecar's spend header runs about 6%
  above summed `usage.cost`; budget against the header.
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

Per-model sidecar settings and failures: `docs/webdiplomacy-gameplay.md` (LLM players).

**Candidates.** Each is a sibling of its base so its A/B is attributable. Code lives on local
branches (not pushed): v2 `press-wakes`, v3 `press-dealcheck`, v4 `press-endgame`, v5
`press-pinning`, v7 and the rotation arms `webdip-press-strength`, v8 `press-trust`.

| Version | Base | Change | Activation (field checks) |
| --- | --- | --- | --- |
| v1 `16b527ba` | – | league champion | – |
| v2 `532ce206` | v1 | open wake 100 s, 12 calls per wake | open time limits 12/32 -> 2/16 |
| v3 `331786ae` | v1 | deal gate: own promises and dependent commits need a same-phase `assess_deal` | 17 assessments per game (v1: 0) |
| v4 `afc90a7c` | v1 | end-game awareness: end year and phases left in briefings; final-autumn search counts only owned centres | end year derived, terminal search ran |
| v5 `7c4cb5f5` | v1 | pin cost: constrained commits compared with the unconstrained plan on the same samples | 18 comparisons, 2 blocks, both overridden |
| v7 `a631e92c` | v1 | map connectivity in briefings ("could move to") + `connections(province)` tool | adjacency guesses in reasoning about 66 -> 21 per game |
| v8 `cc9d3bf5` | v7 | liar marks (below) | not yet observed |
| `webdip-rot-*` | v7 | castlereagh on gpt-6-luna `ecf9a8f0` / deepseek `d0e683df` / gemini-flash-lite `2d9d5e0a`; talleyrand soul on glm `f6bac0c6`; bismarck soul on glm `e4938fc3` | not yet observed |

v8 marks a power permanently when, while we held it at ally stance or trust >= 0.5, it orders a move
or support into our units or centres: trust capped at 0.1, its expected orders dropped, ally refused,
a banner in every briefing. Recorded promise breaches are shown only as unverified claims, because
Codex's audit found 10 of 30 sampled breach verdicts were our own recording errors.

**Results so far (mean score per seat; parity 0.143; not verdicts).**
- Wave 1, pre-geometry field, 100 games: Talleyrand 0.208, silent Kissinger 0.174, Bismarck 0.169,
  Metternich 0.150, castlereagh (all arms) 0.126, Machiavelli 0.101, Calhamer 0.073 (SE about 0.02).
- Wave 2, geometry field, 16 per arm: v7 0.150, v1 0.124, v3 0.112, v4 0.095, v5 0.090, v2 0.064
  (SE 0.011-0.030; every stratified comparison with v1 inconclusive). Field seats (92 games):
  Talleyrand 0.204, Kissinger 0.176, Metternich 0.174, Bismarck 0.171, Machiavelli 0.133, Calhamer 0.038.
- Pattern in both fields: our press layer scores below the same search engine without press, and
  the liar on gpt-6-luna leads.

**Running on the platform (2026-10-09 ~07:00 UTC):** wave 3 (rotation arms + v7 control `v7b`, 16
each) and wave 4 (v8, 16). Request ids: `experiments/press-ab1/waves.tsv` (wave, arm, policy,
xreq). Credits 9.0k at about 15 per full game. Local pollers were stopped at wrap-up; resume
artifact collection (it skips episodes already fetched) with, per request:
`uv run python .claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py --xreq XREQ --out webdiplomacy_lab/evidence/press-ab1/geo/ARM`.
Analyse with `wd.py seats/metrics` and `tools/compare.py BASE_DIR CAND_DIR --baseline ... --candidate ...`.
New waves: `HOME=<private softmax home> experiments/press-ab1/run_waves.sh WAVES EPISODES ARM=POLICY_VERSION ...`.

**Next decision.** Read waves 3 and 4. Then spend the remaining budget on v1, v7, v8 and the best
rotation arm toward the pre-registered sample, instead of topping up v2-v5 evenly. Submit only a
candidate that beats v1 (v7 is the likely floor for anything shipped).

**Other items:** viewer follow-ups (`tools/game_viewer.py`): order arrows use the renderer's power
colours, not the viewer palette; label overlap with units in crowded provinces.

## Other open directions (not started)

- A better position evaluation: the measured bottleneck (see `TENTATIVE_LESSONS.md`).
- Diplomacy that changes the opponent model, not only centre values (gunboat).
