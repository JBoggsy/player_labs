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
