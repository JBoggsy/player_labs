# Crewrift working context

**What this is.** The live, high-signal state of *what we're working on right now* in
the Crewrift lab — the minimal set of cross-session facts worth carrying into the next
session. Read it on startup to resume; **update it as you learn** (keep it tight —
prune anything no longer load-bearing). **Clear and reseed it when we pivot to a whole
new direction**, keeping only the new objective.

This is *not* a log or archive: finished work lives in git history / the
[version log](crewrift/crewborg/version_log.md); durable disciplines live in
[`best_practices.md`](best_practices.md); durable prefs in
[`user_preferences.md`](user_preferences.md). This file is the one-screen "where are we."

> A recorded objective below = onboarding done; resume the loop ([`AGENTS.md`](AGENTS.md)).

---

## 🤖 PARALLEL TRACK — LLM GAMEPLAY COMMANDER (Phase 1 done; both LLMs live in-pod 2026-06-26)
A background LLM steers *gameplay* by writing **priorities** into `belief.commander` that the modes read to
bias execution — never selecting a mode, never blocking a tick. Design:
[`crewrift/crewborg/docs/commander.md`](crewrift/crewborg/docs/commander.md) (design.md §10.6).
**Phase 1 (scaffold + wiring + observability) BUILT & gated-off** — `strategy/commander/`, `belief.commander`,
`CommanderStrategy` on a `CloseAwareSynchronousStrategyRunner`, `apply_inferences`; modes do NOT yet read priorities.
`domain.commander_*` traces (incl. `env_seen`) via `CREWBORG_TRACE_GROUPS=commander`. **Bedrock-in-pod fix (KEY):**
sidecar mode STRIPS `USE_BEDROCK` and injects `AWS_ENDPOINT_URL_BEDROCK_RUNTIME`, so BOTH LLM factories now gate
Bedrock on that **endpoint**, not `USE_BEDROCK` (`strategy/commander/llm.py` + `strategy/meeting/llm.py`).
**Confirmed live in-pod** (Crewrift Prime XP, v64): commander 4637 `commander_call` ok / 0 errors; **meeting LLM
REVIVED** — 290 `meeting_llm_decision`, 0 `_fallback` (was 184/184 disabled). Infra issue:
[`docs/coworld-platform.md`](docs/coworld-platform.md).
**Phase 2 DONE** (commits `c2e83e9`..`0e19585`): imposter levers — `hunt_room`/`avoid_room` in Search,
`target_player` in Search-follow/Recon/Hunt (reachability-checked), + **danger mode** (`allow_witnessed_kill`
relaxes Hunt's witness gate; `skip_evade` suppresses post-kill Evade) with `commander_danger` tracing. All
bias-don't-force via `commander_of`/`filter_or_fallback`; disabled path byte-identical; 440 tests green.
**Phase 3 DONE** — crewmate levers (`target_room`/`target_task`/`posture`) in NormalMode + a debug knob
`CREWBORG_COMMANDER_FORCE='{...}'` that seeds `belief.commander` with a fixed sanitized priority each tick
(bypasses LLM/Bedrock) for deterministic control demos. **CONTROL CAPACITY DEMONSTRATED live (both roles)**
via a forced run (v67, 3 Prime eps, `target_room=Reactor`/`hunt_room=Observatory`): imposters → Observatory
is the #1 nav destination (29%, ~13 rooms, chance ~8%); crew → Reactor elevated to #2 (13%, ~1.6× chance) —
weaker because the task-room lever only steers among a crewmate's OWN assigned tasks (bias-don't-force). So the
commander provably drives both roles; the crewmate task lever is gentle by design. **STRENGTH KNOB added** (commits `ad00f1d`..`c22b05a`): `CommanderPriorities.strength` = `soft` (default,
byte-identical bias-with-fallback) | `hard` (stronger override). `hard`: Search targets a distant `hunt_room`
regardless of nearby-N; NormalMode loiters in `target_room` even with no assigned task there (new positioning
intent); `target_player` follow window 120→240 ticks. **Measured (forced Prime, soft→hard):** imposter
`hunt_room` adherence **29%→100%**; crew `target_room` **13%→67%**. So the commander now has a real steering
dial (settable by the LLM or via `CREWBORG_COMMANDER_FORCE`). 460 tests green; soft path byte-identical.
NEXT: tune — (1) imposter A/B (commander LLM on vs off) for kill efficiency, iterate the imposter prompt to emit
useful `hunt_room`/`target_player`/`strength`; (2) Phase 4 EscortMode for crew. Both roles wired + strength dial. Branch `worktree-labs-work`
(merged to origin/main @ `2ec14f9`); uploaded v55–v64, **none submitted**.

## 🎯 OBJECTIVE (REFRAMED 2026-06-30): fix crewborg's CREW play (voting-led)

**✅ UPDATE 2026-07-01 — the recent crew "collapse" was mostly a REGRESSION, now FIXED (crewborg:v75).**
Root cause: commit `1178f31`'s "robust teammate latch" made CREW mis-detect their own role as **IMPOSTER**
at RoleReveal (verified 15/15 A/B crew seats) and play the whole game as imposter → **0 tasks**. The crew
role-reveal also renders player icons in the 9500+ range, and the change had dropped the `IMPS`-text gate
that distinguished a crew reveal from an imposter one. **Fixed in v75:** role is now latched positively from
the RoleReveal **text** (`4e1d7c1`), `dead` split from role into a `self_alive` flag (`72a14a0`), and the
0x85 per-tick send reverted (`ab92f3c`, it was a net-harmful aggravator). **Measured (`xreq_300b95e7`, 100 ep
natural-roles vs the Prime field):** crew task completion **2.7 → 5.96** (median 7; 25/68 seats do all 8),
0-task "wanderer" seats **~45% → 4%** (the normal early-death baseline). Direct belief-role telemetry wasn't
captured (v75 was uploaded without trace groups), but task recovery is the definitive downstream proof — a crew
seat completing 6–8 tasks cannot be running imposter play. Memory: `crewborg-role-latch-regression`.
**v75 NOT submitted** — v70 (deployed champion) is PRE-regression / healthy, so the bug never reached the
league; no rollback needed. Crew **win-rate** stays meta-capped (~12%, imposter-favored division), so the
**voting lever below is the real remaining crew front** — now measurable cleanly on a non-regressed build.

**⭐ v80 SUBMITTED → PRIME CHAMPION (2026-07-01).** After the "big imposter fixes" tested well (parallel
session), James gave the go-ahead: `crewborg:v80` (`d85ebab3`) submitted to Crewrift Prime (`sub_3fc853d2`) →
placed into Competition (`lpm_a95f8e29`), **competing + champion** (auto-champion=always; supersedes v77).
Post-submit tournament-style eval **COMPLETE: `xreq_c10927d1`** — 100 eps (100 completed / 0 failed),
natural/random roles, v80 + 7 `random` champion-pool seats, all rotating; dashboard on
http://localhost:8814. NB the v76–v80 version-log
entries (what the fixes were, exact commits) still need back-filling from the session that built them.

**🚨 v80 CARRIES THE ROLE-LATCH REGRESSION (found 2026-07-01, league survey + James's replay watch).**
The champion is throwing ~half its crew games: **49% of v80 crew games end 0-task** (66/135 league eps,
field 0-5%; task/g 2.58 vs 5.2-6.5; bimodal 0-vs-8) — the `1178f31` crew-latches-imposter fingerprint,
present in EVERY population (league + all xreqs). Inference (unverified in code): v80 was built on the
paritypush lineage without the v75 IMPS-text fix (`4e1d7c1`). Open q: why ~50% and not ~100% like the
original 15/15 repro. Survey: `/tmp/survey_v80_league.html` (196 league eps); artifacts `/tmp/v80_league_eps`;
warehouse building at `/tmp/v80_league_wh`. **Fix path: v81 = v80 imposter gains + `4e1d7c1` latch fix.**
Also: v80 is the only policy with ops crashes in the league set (6 disconnects) — separate issue.
League form context: lineage rank 9 is historical; v80's first champion round (276) scored 16 (rank 2).
Top of field = RelhAlpha ~15.8/round; league imposter gap vs top: win 73% vs 87-89%, K/g 1.55 vs 1.8+.

**Two active win fronts: CREW (new, primary) + imposter KILL→WIN (kept).** A 170-ep Prime sweep + 4-agent
diagnosis (2026-06-30) added the crew front and refined — NOT replaced — the old "kill→WIN conversion" thread
below (direction 4): crewborg is a **competent imposter (40–70% 1v1 win) and a losing crewmate (0–30%)**; v70 ≈ crewborg-base, so weights don't move outcomes — **change the MODES**. The crew
loss is a **social-deduction / voting failure**, not survival: crew skips ~49% of votes, hits a *crewmate*
~60% of the time it does vote, ejects 0.28 imposters/ep vs notsus's 0.60; notsus dies at the same rate but
WINS by **decisive + coordinated** voting (roster-shrinking bar, bandwagon to quorum, witnessed-tell + trust
signals). Full diagnosis + figures: `/tmp/sweep_report.html`. Memories: `crewborg-crew-weakness`,
`crewborg-v70-equals-base`, `crewrift-imposter-favored-meta`.

### ▶ FOUR FIX DIRECTIONS (set 2026-06-30; about to fan out — NOT yet pursued)
1. **Navigation / maneuver efficiency — CONFIRM FIRST.** James's intuition from watching replays: can
   crewborg move fast enough to catch up to / flee from other players? It is *unconfirmed* — investigate and
   prove it's real before building. A movement/maneuver deficit would underlie BOTH crew (can't flee/regroup)
   and imposter (can't close for the kill), so it's the foundational check.
2. **Voting gating.** Sweep the suspicion vote thresholds (`CREWBORG_WEIGHTS_VOTE_P`, `VOTE_PROBABILITY`,
   `VOTE_LEAD_*`) for the best value; **validate the suspicion mechanism** itself (the fitted crew model is
   miscalibrated live — ~100% precision in held-out sim vs ~40% in real games, a train/serve skew); and
   improve crew voting **coordination** (bandwagon onto the public vote pile; `strategy/meeting/chat_read.py`
   exists but is wired only to the imposter bandwagon path).
3. **Emergency-meeting effectiveness.** When crew calls a meeting after being followed, be **convincing +
   effective** enough to actually convict the chasing imposter — else we waste the meeting (and the team's
   task time) without removing the imp. Today crewborg is **accuse-happy** (6× notsus's button calls, 0.6 tail
   bar `suspicion.py:134`) but **vote-shy** (skips at the 0.9 bar) — it calls meetings it then squanders.
4. **Imposter KILL→WIN conversion (KEPT — also fanning out).** Kills are competitive (1.48 k/g ≈ Aaron's
   1.47, ≥2-kill 50% ≈ his 47%) but our **imposter win lags — 67% vs Aaron 91% / notsus 79%**: we get the kills
   then lose the game (ejected / fail to reach parity / lose the meeting). This session's witness-drop A/B
   confirmed the ejection backlash (dropping the no-witness gate → +13pp ejections, −6pp win, no kill gain).
   Fan out on what converts kills→WINS: imposter **meeting survival** (deflection/defense when accused), pacing
   kills to **reach parity**, and not getting **voted out for witnessed kills**. Detail + tournament table below.

---

### (direction 4 — DETAIL, STILL ACTIVE) imposter KILL→WIN CONVERSION, not kill count

**🏆 TOURNAMENT REALITY CHECK (the headline for the next session).** Ran a proper 100-ep champion
tournament (`xreq_b1f12adf`: 8 `random` Prime champions per episode — the live API redraws per episode —
full round-robin; 78 clean, 22 dropped to platform connect-timeouts). **crewborg v70 came LAST of the 3
Prime champions.** Per-seat-game:

| champion | win% | imposter k/g | ≥2-kill | **imposter win%** | crew win% | tasks |
|---|---|---|---|---|---|---|
| Aaron (crewborg-aaln:v17) | **30%** | 1.47 | 47% | **91%** | 8% | 5.5 |
| notsus v5 | 26% | 1.60 | 65% | 79% | 5% | 5.5 |
| **crewborg v70 (us)** | **19%** | 1.48 | 50% | **67%** | 6% | 5.8 |

**THE NEW LEVER — kill→WIN conversion, not more kills.** Our kills are competitive (1.48 ≈ Aaron's 1.47,
≥2-kill 50% ≈ his 47%), but our imposter **win rate is 67% vs Aaron's 91% / notsus's 79%** — we get the
kills then LOSE the game more. Aaron wins 91% on the SAME kill count. So this whole session's optimization
of *kills* (witness-drop = real +19pp ≥2-kill vs our OLD self, v63 vs v54) closed the kill gap but NOT the
win gap. The actual frontier is **surviving the meeting / reaching parity / not getting voted out for
witnessed kills** — likely the witness-drop's ejection backlash against competent crew (Aaron/notsus vote
well). NB v70 ran with the **meeting LLM ACTIVE** here (xreq=k8s pods) and was still last → the LLM isn't
buying wins in this field. notsus (the "minimal baseline") out-kills us (1.60).

**OPEN THREAD for next session:** pull the replays where crewborg out-kills but LOSES — is it (a) ejection
(witnessed-kill backlash → voted out), (b) failing to reach parity (kills too slow/late), or (c)
meeting/survival? That diagnosis sets the next fix. Re-run the tournament for more power (22% ops-failures
gutted the sample); field is only 3 champions (broaden via `included_players` if wanted). Also still OPEN:
does the meeting LLM fire in LEAGUE (dispatch) rounds (sidecar gap) — v66 fell back; verify on v70's league
rounds.

### ✅ ANSWERED + FIXED (2026-06-30, branch `worktree-imposter-kill-to-win`): the gap is the MEETING
Warehouse decomposition of the 170-ep sweep (`/tmp/sweep_wh`): conditioning win on the SAME kill count,
crewborg @1 kill wins 0.39 vs notsus 1.00, @2 wins 0.63 vs 1.00 — the win leaks AFTER the kills. Of 39
crewborg imposter LOSSES: **64% = an imposter voted out** (a), the rest **stall at 3-crew/2-imp — one removal
from parity — and never close it** (b). notsus closes via the MEETING (1.10 crew-eject/win vs our ~0.4) and is
NEVER ejected. Code causes: deterministic imposter meeting path **skips** (39% vs notsus 5%) and crewborg
often **doesn't know its teammate** (votes it 21-23%, follows it 46% vs notsus 0%/26%) — RoleReveal capture is
a brittle one-shot.
**FIX (`crewborg-paritypush:v1`, commit `1178f31`):** (1) `parity_closing_vote_target` — one removal from
parity AND known live teammate ⇒ manufacture a coordinated fabricated-accusation+vote on a non-teammate
crewmate instead of skipping (self-gated `alive_imposter_count>=2`; only gap==1). (2) Widened RoleReveal
teammate latch (types.py). 470 tests pass.
**A/B (6 pinned-champion 1v1 blocks, both imposters=subject vs `crewborg-base`, 80 eps/champ, clean n≈955/arm):
imposter win 43.7% → 58.1%, Δ=+14.4pp, p<1e-9; kills flat (1.48→1.43); skip-rate 26.3%→23.6% (mechanism).**
5/6 champions positive (forgeling +46, jordan-aaln +17, crewborg-mv +15, notsus +13, aaln +0, softmaxwell −5
noise). NOT submitted. Next: confirm via ejection-rate decomposition (needs replays + warehouse); upload a
trace-enabled build to log `meeting_decision path=parity_push`; broaden to natural-roles to de-mask.

---
### (prior framing kept for reference) crewborg's IMPOSTER KILL EFFICIENCY
**⭐⭐ `crewborg:v70` is the Crewrift PRIME CHAMPION (2026-06-26)** — the **meeting-LLM-ON** ship
(`lpm_60b71147`, champion=True; supersedes v69). v70 = v69's confirmed imposter combo (witness-drop)
+ meeting LLM turned on (commander OFF), on the merged commander codebase. Meeting LLM verified firing
pre-submit (probe `xreq_bc2878d1`: 22 `meeting_llm_decision`, 0 fallback). **⚠️ OPEN: does the meeting
LLM fire in LEAGUE (dispatch) rounds, or only xreq (k8s)?** — v66 fell back in league; verify once v70's
league rounds run. (v71 = nightly refit, currently `qualifying`.) Prior champion lineage below:
**`crewborg:v69`** was the Crewrift PRIME CHAMPION — the **deterministic** ship:
the confirmed witness-drop-after-1st-kill imposter combo (v63 vs v54 natural roles: +19pp ≥2-kill /
+14pp win / +0.32 kills, p=0.038) + inert 72t Evade re-approach (EVADE_TICKS=72), **LLM OFF** (the
meeting LLM only fires in k8s/xreq pods, never league/dispatch rounds — sidecar not wired there — so an
LLM-on build just adds weight + silent fallback in league). Submission saga: v66 (LLM-on) and the first
v69 tries REJECTED with "league has no submission division" (Prime was missing its Qualifiers staging
division / stale `qualifiers_division_name` config); after a **backend fix**, v69 re-submit placed +
auto-championed. Local↔image SDK parity now done (pyproject installs `players[bedrock]` from the
coworld-tools tarball). Earlier (now-historical) note on the v66 rejection follows:
**⚠️ `crewborg:v66` submitted to Crewrift PRIME 2026-06-26 but REJECTED — `notes="league has no submission
division"` (PLATFORM/league-config issue, NOT our play; same as v49).** Prime was migrated 2026-06-24 to an
among-them-commissioner + "Qualifiers" division flow; direct `coworld submit --league <prime>` now has no
submission division. v42 placed pre-migration; the nightly places in the REGULAR Crewrift league
(`league_605ff338`), not Prime. **v66's placement games were FINE** (mean +8, imposter 1.33 kills/g). ALSO:
in league-round pods the **meeting LLM FELL BACK** (0 decisions vs 17 in the xreq probe) — the Bedrock
sidecar is wired for experience-requests but NOT league rounds, so the LLM-on build plays DETERMINISTICALLY
in league. **The shippable, confirmed gain is the deterministic witness-drop** (v63 vs v54 natural roles:
+19pp ≥2-kill / +14pp win / +0.32 kills, p=0.038). NEXT: resolve Prime submission routing (owner/qualifiers
flow) and/or verify the sidecar in league pods before relying on the LLM. v66 = confirmed imposter combo +
meeting LLM (commander OFF) on the merged codebase. v59/v60/v62/v64 = other worktree's LLM-commander thread;
v61 = v54+debug; v53/v58/v65 = inconclusive/superseded arms.

**✅ CONFIRMED BASELINE — v54, 300 eps, NATURAL ROLES, vs Aaron(v17)+Andre(v28), Prime 0.4.9, meeting-aware
(`/tmp/v54base_wh`; 2026-06-26).** This is the authoritative current diagnosis (the v50 numbers were a
different config; the pinned-2-imp A/Bs MASKED the gap — see lessons).

| imposter | n | win% | kills/g | **≥2-kill** | 0-kill | post-kill in-view@ready | post-kill nearest-crew |
|---|---|---|---|---|---|---|---|
| **crewborg** | 60 | 80% | **1.52** | **52%** | 8% | **47%** | **95px** |
| Aaron | 246 | 86% | 1.97 | 82% | 2% | 76% | 14px |
| Andre | 164 | 92% | 1.97 | 82% | 2% | 81% | 18px |

Crew: crewborg win 3% / tasks **6.0/8 (best tasker)**; Aaron 3%/5.7, Andre 6%/4.5 — crew win ~3-6% for
all (imposter-dominated field, not discriminating).

**Root cause = POST-KILL subsequent-kill CONVERSION (the ~30pp ≥2-kill gap, CONFIRMED real in natural play):**
- crewborg ≥2-kill **52% vs Aaron/Andre 82%**; our **first** kill positioning is fine (first-cd in-view
  73% / 22px) — the fall-off is specifically **post-kill** (in-view 47% / 95px vs their 76-81% / 14-18px).
  Aaron/Andre stay glued (~14-18px) and snowball; we drift to ~95px median.
- Lever (unchanged) = **after a kill, re-establish contact with a killable ISOLATED victim / the cluster
  the victim peeled from, SUSTAINED across the cooldown** — the ~428t of random Search is the bigger
  culprit than Evade's 72t. **NOT solved.**
- ⚠️ v46 (Search → crew-densest room) regressed; v53 (Evade → densest crowd) neutral — **crowd-seeking is
  a dead end** (we kill ISOLATED victims; crowds = witnesses). Target the single lone victim, not density.

**Both prior fixes are INCONCLUSIVE (wrong eval config), NOT neutral** — they were A/B'd pinned-2-imp where
the gap was masked (≥2-kill 69% there vs 52% natural). **Re-test any post-kill fix in NATURAL roles.**

**ATTEMPT 1 (2026-06-26) — Evade → beeline to most-populated area: NEUTRAL.** Built `v53` (Evade
beelines to densest crew area off the occupancy grid) vs `v54` (old flee-Evade); 2× 100-ep
imposter-pinned A/B (P1 fixed-Andre co-imp; RR round-robin co-imp). Fully-clean episodes: kills
1.73→1.74 (P1), 1.71→1.69 (RR); no-kill & ≥2-kill identical. **Dead neutral, safe (0 disconnect
crashes; failures all platform connect_timeouts — recompute on FULLY-clean eps, see lessons).** Why:
we kill ISOLATED victims (~120-170px to next crew even at the kill), so beelining to the densest
CROWD heads into witnesses where Hunt's gate blocks the kill — the **v46 crowd-seeking dead-end,
re-confirmed**. Also Evade is only 72t of the 500t cooldown; Search's random-room wander over the
other ~428t undoes it.

**Next step (refined lever):** the post-kill re-approach must target the **single nearest ISOLATED
victim / the cluster the victim peeled from** (NOT the densest crowd), SUSTAINED across the whole
cooldown — the ~428t of random Search is the bigger culprit than Evade's 72t. Forks: (A) dedicated
re-approach state spanning Evade→Search that shadows the nearest reachable lone crew; (C) strengthen
Recon (longer post-kill window + head to a live/predicted single victim, not a stale last-seen).
Optional confirm: post-kill distance-curve on v53 vs v54 replays (needs a 0.4.9 warehouse — expand-043
covers only 0.4.3-0.4.7). Secondary direction the human raised: **crew-side — punish aggressive
imposters** (detect relentless proximity/kills to cut Aaron/Andre's imposter win, lift our crew win).

## Tools / data ready to use
- **STREAMING eval pipeline is now the default (built + live-validated 2026-07-01):**
  right after `create` returns an `xreq_…`, run `crewrift-event-warehouse` skill's
  `stream_eval.py --xreq … --out <wh> --expand-replay <bin>` in the background — it overlaps
  fetch (`fetch_artifacts.py --watch`, per-episode as each turns terminal) with INCREMENTAL
  warehouse builds (episodes `ok` in the manifest are never re-expanded; `episodes_cached` in
  the manifest counts hits). Validated on `xreq_307f10d6-2a6b-4c23-9be8-567f9a724417` (8 self-play
  eps): first build fired at 4/8 fetched (overlap confirmed), resume-after-completion cached 2+,
  final 8/8 ok. Design: `docs/designs/2026-07-01-streaming-xreq-eval-pipeline-design.md`.
  ⚠️ validation also showed `/tmp/expand-043` is going STALE vs prime 0.4.29 — 6/8 fresh episodes
  trace_warned (partial rows), though it exits 0 on some. Rebuild the expander from the arena's
  current commit before the next warehouse-dependent analysis (versions.env bump signal).
- **`tools/positioning_viz/`** — kill-ready spatial viewer (meeting-aware; see its README).
  Needs a **per-tick** warehouse (`--snapshot-every 1`); one exists at `/tmp/v50_pertick`
  (run #1, 100 eps). `/tmp/v50_warehouse` + `/tmp/v50b_warehouse` are the every-10 combined
  ~127-clean set used for the stats above.
- Behavioural analysis is now the **`crewrift-event-warehouse`** skill (cross-episode SQL over
  expanded replays) + **`tools/behavior_compare.py`** (per-game policy comparison). The old loose
  `crewrift_lab/` scripts (kill_latency, visibility_at_ready, aaron_compare, prime_summary,
  suss_rate) were retired/folded into those — all **meeting-aware** (count Playing samples, never
  raw tick deltas; see best_practices "meetings are not idle time").

## Load-bearing infra facts
- **Player SDK moved to `Metta-AI/coworld-tools`** (the `players` repo is **archived**).
  The build installs it from the coworld-tools **tarball** subdirectory
  (`Dockerfile` + `versions.env`; `main` resolved via `git ls-remote`). **`uv` can't lock
  coworld-tools** (broken `players/users/relh/co-gas` submodule → filed
  **coworld-tools issue #13**), so local `uv.lock` still points at the archived mirror — the
  hosted image is the source of truth for the SDK.
- **LLM meetings/commander on Bedrock**: upload with `--use-bedrock` + `CREWBORG_LLM_MEETINGS=1`
  / `CREWBORG_LLM_COMMANDER=1`. The pod runs a **loopback Bedrock sidecar**; the SDK routes to it via
  `AWS_ENDPOINT_URL_BEDROCK_RUNTIME` (coworld-tools PR #12). **CORRECTION (2026-06-26): sidecar mode
  STRIPS `USE_BEDROCK` from the player container** (treats it like a credential) and injects only the
  endpoint — so the SDK's `bedrock_enabled()` (USE_BEDROCK gate) reported "no LLM backend" in-pod and
  BOTH LLMs were silently disabled (meetings were 184/184 `_fallback`). **Fix:** crewborg now gates Bedrock
  on `AWS_ENDPOINT_URL_BEDROCK_RUNTIME` presence (`strategy/{commander,meeting}/llm.py`). Verify via
  `policy_artifact_<slot>.zip → telemetry.jsonl` (`domain.meeting_llm_decision` + `domain.commander_call`
  `outcome:ok`, not `_fallback` / `env_seen` all-false). Platform fix owed (keep injecting `USE_BEDROCK=true`)
  — see `docs/coworld-platform.md`.
- **Expander**: `/tmp/expand-043` (master sim `26ee08c`) handles **crewrift_prime
  0.4.3–0.4.7** (the fork's version bumps didn't change the sim). Use
  `CREWRIFT_EXPAND_REPLAY=/tmp/expand-043` for the warehouse.
- **Prime field** (Competition `div_acbde92a-…`): just **Aaron `crewborg-aaln:v17`** +
  **Andre `truecrew:v28`**. Prime league `league_a12f5172-0907-4d04-8bcb-ca02f5360e3a`.
  Evals: fully round-robin, natural roles (no pinning), vs those two. Heavy
  `connect_timeout` ops-failures are platform load, not us — re-run / probe small first.
