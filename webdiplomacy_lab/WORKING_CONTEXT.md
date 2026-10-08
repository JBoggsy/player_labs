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

## Next decision: press player strength

The objective is to make `castlereagh_press` stronger. Decide first how to measure it:

1. **Measurement design (blocking, human decision).** Self-play never decides "better",
   and hosted XP is not spent on self-play (`../user_preferences.md`). The press league has
   no external entrants, and the only hosted non-own opponents (the bundled random bot,
   relh's gunboat bot) send no press. Options: wait for press entrants; evaluate a
   candidate against the current version only as a local mechanism check; or agree with
   the human a field of diverse press agents (different souls and models) and how its
   results may be used.
2. **Make the agent test deals before agreeing.** Game 2: 248 `send_press`, 178
   `record_commitment`, but 47 `search` and 30 `evaluate` calls. Candidate change: require
   an `assess_deal`/`search` before accepting or proposing a deal (HARNESS.md and skills),
   with activation tracing (searches and deal assessments per phase).
3. **Wake limits.** 20–25% of wakes end on the 60 s limit (local) and 3–5 of 16 hosted.
   Retune `PRESS_WAKE_SECONDS`, `PRESS_COMMIT_MARGIN_S` and `PRESS_REQUEST_LIMIT` for
   4-minute `classic-press` phases; check model latency (local p50 4.4 s, p90 15.6 s).
4. **Filler roster.** The press league's only filler is Castlereagh, so league games are
   self-play. A diverse roster (other souls, other models, plain Kissinger) needs the
   human's go-ahead and a check of the league LLM spend limit (all-LLM games cost about
   $0.75 each).
5. **Viewer follow-ups** (`tools/game_viewer.py`): order arrows use the renderer's power
   colours, not the viewer palette; label overlap with units in crowded provinces.

## Other open directions (not started)

- A better position evaluation: the measured bottleneck (see `TENTATIVE_LESSONS.md`).
- Diplomacy that changes the opponent model, not only centre values (gunboat).
