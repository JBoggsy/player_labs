# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-02 09:28. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`crewrift_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Crewrift-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

## 2026-07-02 — prime rounds 391–394 survey
- **The prime field pivoted under us**: from 2 entrants to 11 (mostly notsus/aaln forks by other
  players) between sessions. Any lever verdict measured against the old field (esp. the 4-way
  vote-threshold refutations) needs re-checking before being treated as binding in the new field.
- **In the 11-entrant field, crew wins come from ejections, not tasks**: 5–8 crew hitting 8/8 tasks
  and losing is the modal loss; both of our crew wins-with-few-tasks were vote-driven. v89's tight
  vote gate casts 0 votes in most crew games → we under-participate in the only crew win condition.
  (Survey-level signal, n=32 crewborg games — needs warehouse confirmation.)
- **survey.py tweak**: episodes with human-written reasons now always make the interesting-episodes
  shortlist (cap/per-type limits only govern auto-filled rows). Unflagged-but-interesting episodes
  still can't render — mint their links manually (POST /v2/coworlds/replays/session).

## 2026-07-02 — warehouse deep-dig on rounds 391–394 (/tmp/prime_wh)
- **Kill conversion, refined**: when isolated with a crew target AND kill-ready, notsus converts
  9/9, relhalpha 7/8, crewborg 2/5. Plus we accumulate the longest unready isolation windows
  (mean 421 ticks vs relh 94) — we hang around crew while on cooldown instead of timing approach
  to readiness. First kill median tick 3402 = slowest in field (jordan 1126, notsus 2155).
- **Voting is two problems, not abstention**: participation is fine (2.9% no-vote). (1) Meeting-1
  paralysis: 12 skips vs 5 votes on the first meeting (field leaders skip ~0); (2) accuracy 47%
  overall = bottom tier (mv 75.7%, richard 77.1%, relh 68.1%). Also we get EJECTED as crew 5
  times (most in field, tied) — 20% of crew games we die to votes, not knives.
- **relhalpha's winning crew pattern**: 28 emergency-button calls (10x anyone else) + 83%
  later-meeting vote accuracy + best crew win rate (52%). Proactive meetings dominate this meta.
- **Ghosts do task but resume SLOWLY**: median 964 ticks death→first ghost completion vs 111–239
  for the aaln forks; 5/19 crew deaths yield zero ghost tasks. Mid-field completions/death (2.79).
- **Warehouse mechanics**: /tmp/expand-043 still hash-clean on crewrift_prime 0.4.31 (fork bumps
  remain sim-identical); 2/48 trace warnings. duckdb queries must run from
  crewrift_lab/tools/event-warehouse/crewrift-event-warehouse (root venv lacks duckdb).

## 2026-07-02 — suspicion-data + kill-gate session (three tracks)
- **`CREWBORG_TRACE_GROUPS=all` does NOT enable the suspicion feature trace** —
  `CREWBORG_TRACE_SUSPICION_FEATURES` is a separate env gate (events.py:144). Result: 0 of ~700
  hosted episodes from "all-telemetry" versions carry `ranking[].features`; build_dataset_runtime
  produces 0 rows on every real episode ever played. "All telemetry" should mean ALL — add the
  flag to the standing recipe (pending James OK).
- **fetch_artifacts `--no-logs` silently dropped policy-artifact ZIPS** (they were gated on
  want_logs) — cost a full 692-ep re-pull. Fixed: separate `--no-artifacts` flag + completeness
  check. When a fetch skips a category, verify what else that category gated.
- **v82 lesson "witness gate barely matters (99.7% exactly-1-crew-visible)" did NOT replicate in
  v89 data** — 100% of unconverted ready+in-range ticks had ≥2 crew in rendered view; the field
  now buddies up (11-entrant meta). Window-conditioned lessons rot when the field pivots; recheck
  before reuse (same lesson as the vote-lever refutations).
- **Kill failure is at the strike, not the approach**: ready+truth-in-range converts 19.6% vs
  field 84-91%; the witness veto (isolation radius 48px = 2.4x kill range) + meeting cooldown
  confiscation (body reports reset unused kcd 0→500, vote freeze pauses it) + committed-victim
  mismatch explain it; the v82 near-miss press-loop is FIXED since v84 (kill-press escape).
- **Ghost fix pattern**: death detection already existed (ghost HUD → self_alive flip); the
  latency was nav-shaped (wall-aware A* + hold-still-on-unreachable + anchor filters). The parked
  branch had the full fix; `git branch --no-merged` before re-implementing (2nd occurrence).

## 2026-07-02 — ghost A/B + killtrace verdicts (subagent runs)
- **Ghost straight-line nav REFUTED, and the metric was confounded**: death→first-ghost-completion
  is dominated by MEETING-LOCKED ticks (movement frozen ~1300t/meeting, meetings often start right
  after the kill). On Playing-phase ticks both arms are ~241-250 median — already inside the
  111-239 competitor band; ghosts ALREADY noclip at full speed while Playing. The league "964"
  overstated the gap ~4x. ALWAYS compute ghost latency on Playing-phase ticks. Do not merge/retry
  straight-line ghost nav (100v100, primary reversed p=0.69, conversion 45% vs 68% worse p=0.06).
- **Kill gate: H1 (witness-veto starvation) confirmed 367:2 over H3; H3 also MOOT** — the A-press
  kills the server-nearest in-range crew regardless of Hunt's committed target (replay-verified:
  committed blue, killed purple). But the 19.6% ready+in-range conversion figure did NOT replicate
  (69.7% truth-based in the pinned probe) — the earlier number was contaminated (isolation windows
  spanning vote-freezes). Dominant ready-time cost is CONTACT: 96% of kill-ready ticks have no
  visible victim (recon), median ready→kill 8t once seen. The big lever remains post-kill
  re-approach / victim finding, with URGENCY_FULL_TICKS 240→80 as the designed cheap A/B.
- **hunt_block telemetry** exists on branch worktree-agent-a17e8a614aabde1c4 (commit 1547423) —
  per-ready-tick gate outcome/committed victim/witness geometry; debug-gated, 3 tests. Merge-worthy
  for future kill work even though the A/B lever is a separate decision.
- **coworld CLI 0.1.26 → 0.1.27 required** (manifest 'promo' field rejection on run-episode);
  both subagents hit it independently. Bumped on main.

## 2026-07-02 — suspfit v4 A/B verdict (deterministic arms)
- **A/B NEUTRAL — primary had no headroom in deterministic arms**: crew vote precision 93% (13/14)
  vs 91% (21/23), p=1.0 — the v89 tight gate's deterministic fallback votes are witnessed-dominated
  and were ALREADY precise; the old model's live noise (58-66% precision) shows up in LLM-on play
  and probes, not in the deterministic path. The refit instead REDUCED vote volume (14 vs 23 in
  ~70 crew games; honest 0.9 crossings are rarer), imp-ejections/crew-ep 0.47 vs 0.56, crew win
  18% vs 24% (p=0.41). Timeouts/ops 0 both. NOT shipped on this evidence.
- **The real payoff of honest calibration is the vote-BAR lever it unlocks**: v4's OOF 0.7+lead
  band = 94% precision. The four vote-bar refutations on file were all measured under the OLD
  noisy posterior — with an honest posterior, lowering the crew vote bar to ~0.7+lead is a
  NEW experiment, not a retry. Candidate design: new weights + VOTE_PROBABILITY 0.7 + lead>=0.2
  vs v89 base, primary = imposters-ejected/crew-ep UP + precision >= 75%.
- Curiosities (not pre-registered, treat as hypotheses): cand imposter win 89% vs 67% (p=0.06);
  more crew ejected by the FIELD in cand crew-eps (38 vs 21, p=0.04) — suspicion weights also
  feed the imposter deflection view; worth a look before any ship.

## Chat accuracy & effectiveness study (2026-07-02, worktree-chat-accuracy-effectiveness)

New field-wide investigation (not crewborg-specific): is crew chat accurate, and does
accusing (crew or imposter) actually move votes/win rate? Built `crewrift_lab/chat_effectiveness/`
(design: `docs/designs/2026-07-02-chat-accuracy-effectiveness-design.md`). Reused
`suspicion_lab`'s `chat_stances()`/`replay_parse.py` read-only rather than re-parsing chat.

### Detector validated at 97.5% stance / 87.7% target agreement vs the warehouse's LLM `suss` job (n=200)
The cheap regex accusation-target detector (first non-self color named in an accuse/defend line)
is NOT ground truth — quantified it against Bedrock-labeled chat on the same 200 fresh episodes.
A manual 10-row spot-check found the expected failure mode: a line naming 3 colors before the
actual accusation ("Blue dead... Pink sus: no alibi") got mis-targeted to the FIRST color, not the
accused one. ~88% target accuracy is a real ceiling on this detector, not a bug to fix reflexively —
any future consumer of `chat_stances()` for target attribution inherits this same ceiling.

### CRITICAL gotcha found (and fixed) before it silently corrupted results: the event-warehouse keys chat_suss by episode.json's internal `id`, not the directory-stem join key this whole pipeline uses
`build_warehouse.py`'s `eid = meta.get("id") or ep.name` means `chat_suss.episode_id` is usually
the opaque internal id. Everything else in `chat_effectiveness/` (and this lab's existing
suspicion_lab convention) joins on the directory/replay-filename STEM instead. Without a remap,
this join silently zero-matches (n_matched=0) rather than erroring — the report would have printed
"detector validation not yet run" after a real, paid Bedrock run. Fixed via
`validate_detector.build_episode_id_map()` (needs the raw episode dirs, new required `--episodes`
flag). METHOD LESSON: a join that can silently return empty is worse than one that crashes — audit
every cross-tool join key explicitly, don't assume two systems share an ID convention just because
both call it "episode".

### `top_n`/`random` roster selectors hit a real backend 500 (query timeout on the champion-ranking join) — pin explicit `policy_ref`s as the workaround
Two consecutive `top_n`-roster xreq creates 500'd with `psycopg.errors.QueryCanceled` on the
`eligible_champions`/`mean_reward` ranking query (different backing coworld_id each time — not
a fluke). Resolving the roster manually (`coworld results <division_id>` for rank +
`coworld memberships --active-only` for each player's `is_champion` policy label) and pinning
`policy_ref`s sidesteps the expensive query entirely and worked immediately. Also hit 3 more
transient network-level failures today (TLS handshake timeout, read timeout, server-disconnect)
across different endpoints — the Observatory backend was demonstrably flaky this session,
independent of anything in this repo.

### Historical suspicion_lab corpus is NOT uniformly usable for outcome/win analysis — only entries with a full 4-file scrape (episode.json+replay.json+replay.json.z+results.json) work
The most-recent scraped batch (2026-06-25) has ONLY `episode.json` per dir (an interrupted/partial
scrape) — `results.json` (needed for win/role) is absent. The June 12-13 batch has all 4 files.
Used a symlinked subset (2,999 dirs, 2,976 with matching expanded replays) from the complete
end for the historical cross-check rather than the full 287k-dir corpus (which would also mix
6 months of policy-version drift into one "stability check," defeating its purpose).

### `num_episodes` per experience request caps at 100 (not documented in this lab's memory before) — split a bigger ask into multiple xreqs
Original design wanted ~240 episodes ("~20 Prime rounds"); the API rejects anything above 100/request.
Ran 2×100 back-to-back instead. `fetch_artifacts.py --watch` crashed twice on `ReadTimeout` fetching
`policy-artifact` telemetry zips (large, unneeded for this study) before it occurred to skip them —
`--no-artifacts --no-logs` is the move whenever a study only needs `replay.json`+`results.json`,
both to reduce payload and to dodge the most failure-prone endpoint.

### Headline numbers (fresh pull, 200 eps, top-8 current champions, natural roles)
Crew accusation accuracy ranges 9.5% (softmaxwell-crewborg, n=21) to 70% (jordan-crewborg-aaln,
n=63); **crewborg 48.4%** (n=122) — mid-pack, not a standout either direction. Same-meeting
"target actually voted" ranges from 0% (notsus-as-imposter, n=7, deflection working) to 100%
(several crew). Full breakdown + seat-normalized win-rate association in
`crewrift_lab/chat_effectiveness/data/report.html` (gitignored; rebuild via the package README).
Historical (June, n=2,976) cross-check shows the SAME qualitative pattern (crewborg/crewborg-aaln
crew accuracy 43-46%, well below several smaller bots' 85-93%) — this is a stable trait, not a
one-window artifact, though the historical policy versions predate the current champions.

### FOUND (via this study) — `replay_parse.py`'s per-meeting `Meeting.ejected_slot` is silently NEVER set: 0/73 meetings in a live sample
A suspiciously uniform `p_target_ejected = 0.0` across every single policy/role row was the tell
(this lab's own "a near-perfect 0/N split is a tooling-artifact tell" lesson, confirmed again). Root
cause: the `phase: Playing/GameOver` event that closes a meeting fires at the SAME tick as the
`died` (ejection) event, but is processed FIRST in the stream — so by the time `died` is handled,
`pending_meeting.end_tick` is already non-None and the `if pending_meeting.end_tick is None` guard
(replay_parse.py, the `died` branch) silently skips setting `ejected_slot`. `game.ejections` (the
raw list) IS reliably populated — only the per-`Meeting` convenience field is broken. Fixed
LOCALLY in `chat_effectiveness/tools/extract_accusations.py` (bucket each `game.ejections` tick into
its meeting's `[call_tick, next_call_tick)` window) rather than touching the shared, read-only
`suspicion_lab/tools/replay_parse.py` — but this bug is real and upstream: **any other consumer of
`Meeting.ejected_slot` (suspicion_lab's own `features.py` doesn't use it, only votes/reports/button-calls,
so it's silently escaped notice so far) will get the same silent zero.** Worth fixing at the source
if anything else ever wants per-meeting ejection outcomes.
