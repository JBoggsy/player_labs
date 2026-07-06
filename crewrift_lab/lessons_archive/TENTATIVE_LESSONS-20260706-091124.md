# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-02 17:05. This is THIS SESSION's lesson buffer. Write candidate
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

### "Tournament is broken" = dispatch OK, artifact routes still 403 — not a dispatch outage
Evidence: fired 2x100-ep xreq (v93 vs pinned top-7 Crewrift Prime field, explicit
policy_refs, natural roles) as a tournament substitute. Episode DISPATCH works fine
(submitted/running counts climb normally, started ~2min after create). But
`fetch_artifacts.py --watch` immediately fails every episode: "results artifact
unavailable / replay unavailable / no policy logs listed" — the same `/jobs/*`
403 "not a softmax team member" blocker already logged in WORKING_CONTEXT.md
(since 2026-07-02 ~22:20Z) is still live ~1.5-2.5h later. So "episodes aren't
running" as reported likely means "results/replays never surface" (which looks
identical to broken from the league leaderboard's perspective, since it also reads
those routes) rather than the k8s dispatch path being down.
Status: xreq_742da7f5-9107-450d-8f63-f7a73ed4af59 + xreq_7d1ccc1f-ba16-4fe6-819a-0ece28d76562
(100 ep each, v93 vs top-7) running; dashboard on :8811; fetchers backgrounded and
crash-safe — will backfill once /jobs/* unblocks. Re-login/relogin still untried-successfully
per WORKING_CONTEXT; may need platform-side escalation.

### FIXED: /jobs/* 403 was metta PR #17028 (opt-in elevation), not an outage
Evidence: PR #17028 ("feat(auth): opt-in elevation model") landed on origin/main —
Softmax team members are now treated as EXTERNAL by default; TEAM_AUTH-gated routes
(incl. per-episode job artifacts: results/replay/policy-logs for another player's
policy) need `X-Use-Elevated-Privileges: true`, sent via `coworld --elevated` (or
`softmax status --elevated`; no env-var form, flag-per-invocation only, refused for
ply_* tokens). Our local coworld pin was 0.1.27 (stale — no `--elevated` support);
bumped to 0.1.28 via `uv lock --upgrade-package coworld && uv sync`. Verified fix:
`fetch_artifacts.py --elevated` pulled results+replay+8 policy-logs cleanly for
episodes that 403'd moments earlier without the flag.
Action taken: added `--elevated` to fetch_artifacts.py (Client header), xp_dashboard.py,
and passthrough in crewrift-event-warehouse's build_warehouse.py/stream_eval.py.
NOT yet added: crewrift-survey/scripts/survey.py's replay-session-mint call (different
route, no evidence yet it needs elevation — don't add speculatively).
Status: OPEN — none of these scripts default `--elevated` to on; every future
invocation needs the flag explicitly until/unless we decide non-team-member-log
access is desired by default (the PR's whole point was to make that an explicit choice).

### `random`/`top_n` roster-fill query still 500s — NOT flaky, 3/3 reproduced
Evidence: fired a true tournament-style request (crewborg:v93 + 7x `{"random": true}`
seats, no game_config_overrides) against Crewrift Prime Competition division — 500
"canceling statement due to statement timeout" on the `eligible_champions` CTE
(joins policy_versions -> league_policy_memberships -> ... -> episode_policy_metrics,
computing mean_reward per champion since a ~1-month floor). Retried 3x back-to-back,
identical failure every time — this is a deterministic query-plan/timeout problem, not
transient contention. Confirms `WORKING_CONTEXT.md`'s existing "pin explicit
policy_refs" mitigation is still necessary, but note that mitigation is NOT equivalent
to "tournament-style" (random field) — it's a different, narrower question (see the
new tournament-style definition added to `coworld-experience-requests/SKILL.md`).
The division-leaderboard endpoint used by `experience_request.py resolve --division
--top N` is unaffected (different, cheap query) — only the xp-request roster-fill
path is broken. Worth reporting to platform: this may be a big part of why the
league/tournament itself looked "broken" (round dispatch/rostering may hit the same
query for the commissioner's own matchmaking).

### A belief field consumed by a later fold stage must not be set-and-cleared inside the same update
Evidence: types.py latched meeting_caller_color and then, three lines later, cleared it whenever
belief.phase == "Playing" — and derive_phase has no MeetingCall state, so phase stays "Playing" for
the whole interstitial. update_social_evidence runs after update_belief, so _bank_meeting_caller
never saw a non-None caller: reported_bodies/button_calls_made were 0 across all 3,238 v95
telemetry rows. Fix: clear only when the interstitial text is also gone (play truly resumed).
Status: fixed 2026-07-05, end-to-end tests added (test_belief.py, test_social_evidence.py).

### Unit tests that set latch fields directly can't catch latch-lifecycle bugs — add one fold-path test per latched signal
Evidence: test_social_evidence.py's caller tests set belief.meeting_caller_color by hand and passed
for months while the real update_belief path zeroed the feature in every live game. A single test
driving update_belief + update_social_evidence together (the fold order __init__.py uses) would
have caught it on day one.

### Check the fitted weights file before assuming a dead feature needs a refit
Evidence: reported_bodies/button_calls_made were zero at runtime, but v3-runtime
suspicion_weights.json holds healthy NONZERO coefficients (-0.26 / -1.59) because offline training
reads replay ground truth (expand_replay emits the caller slot), not runtime perception. So the
bug was train/serve skew, not a poisoned fit — fixing the runtime parser closes the skew with the
weights already shipped, and the planned refit becomes validation instead of a prerequisite.

### crewborg's crew deficit is a VOTING deficit, not a task or chat deficit (v96, 728 clean games)
Evidence: vs top-3 crew (crewborg-mv/scott/forgeling), crewborg skips votes 2x as often (1.76 vs
0.86/game, d=+0.78), calls half the meetings (0.30 vs 0.71, d=-0.65), casts half the player-votes
(0.64 vs 1.35, d=-0.61) — while chatting MORE (d=+0.38) and completing MORE tasks (6.79 vs 6.10,
d=+0.34). 256 clean crew losses had 6+/8 tasks done. Execution isn't the bottleneck; converting
reads into ejections is. This is the same "won't vote" pattern the v96 vote-bar-override targeted —
the fix clearly didn't fully land. Ghost-move-latency was LOWER not higher (hypothesis rejected, ns).

### crewborg's imposter deficit: same kills, but passive hunting + quiet meetings (v96, 728 clean games)
Evidence: vs top-3 imposters (relhalpha/jordan/sasmith), crewborg gets IDENTICAL kills (1.77 vs
1.78) but follows/tails 37% less (d=-0.80), chases 35% less (d=-0.46), chats 39% less as imposter
(d=-0.76), stays silent in more meetings (d=-0.46), and gets first kill ~20% later (d=+0.36). Kill
COUNT is not the gap — the social/meeting game (deflection via chat) and aggressive hunting are.
Differential method: per-(episode,seat) features from the event warehouse, Cohen's d + Mann-Whitney
vs pooled top-3, ranked by |d|. Descriptive/associational, not causal.

### Coworld 0.4.42 stopped zlib-compressing replay.json.z (it's raw CREWRIFT bytes now)
Evidence: build_warehouse's reporter zlib-decompresses replay.json.z and got "incorrect header
check" on every 0.4.42 episode (0.4.40 built fine). replay.json and replay.json.z are byte-identical
raw CREWRIFT format. Workaround: zlib.compress each raw replay in place before build_warehouse (magic
bytes b'CREWRIFT' = raw/needs-compress, b'\x78' = already zlib). expand_replay reads raw directly.

### Drop dead connect-timeout games at the GAME level before any win-rate stat — never per-seat
Evidence: v96 ranking eval (1500 games on coworld 0.4.42) had 772 games (51%) where ≥1 crew seat
connect-timed-out. These are DEAD games: zero kills/tasks/votes, no agent log written, auto-scored
as imposter wins. A per-seat ops-filter (drop the ct seat, keep the rest) COUNTS these as imposter
wins for the surviving seats → crew win rate reads 20% (contaminated) vs the true clean-game 33.7%.
Correct: drop the whole game if any seat has connect_timeout/disconnect_timeout. Verify "intact" =
exactly 2 imp / 6 crew + real gameplay. The team-Bradley-Terry model got this right (game-level
drop), the marginal analysis got it wrong — they disagreed by 14pp until reconciled.

### Heavy/LLM crewborg images connect-timeout ~24% of games under 0.4.42 — likely auto-forfeiting league games
Evidence: per-policy connect-timeout rate correlated with image weight — LLM images high
(forgeling 27%, softmaxwell 27%, crewborg 24%), deterministic forks low (crewborg-aaln 14%, scott
15%). Dead game's crewborg container produced NO agent log (never started). crewborg's rate rose
15% (v0.4.40, v96 validation) → 24% (v0.4.42) — the connect deadline tightened and crewborg's cold
start (LLM + Bedrock + honor seed + spaCy chat-NLP load) misses it. This costs ~a quarter of crew
games as instant auto-losses in the live league — plausibly a bigger standing lever than any skill
gap. Fix startup latency before more skill tuning; also halved this eval's effective N (1500→728).

### When a perception feature reads as always-zero, diff the claimed wire format against the vendored game source
Evidence: resolve.py's MEETING_CALL_TEXT premise ("<Color> reported" text lines) was actually
CORRECT — global.nim:1030 emits exactly that at ProtocolTextObjectBase 9000. Hours of suspecting
the regex/label were wasted relative to checking the belief-fold consumer first; but the vendored
source (.cache/crewrift-src/<hash>/src/crewrift/global.nim) settled every wire-format question
definitively and ruled out the whole perception layer in one pass.
