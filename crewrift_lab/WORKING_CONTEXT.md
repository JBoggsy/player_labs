# Crewrift working context

**What this is.** The live, high-signal state of *what we're working on right now* in
the Crewrift lab — the minimal set of cross-session facts worth carrying into the next
session. Read it on startup to resume; **update it as you learn** (keep it tight —
prune anything no longer load-bearing). **Clear and reseed it when we pivot to a whole
new direction** (a new objective/hypothesis class), keeping only the new objective.

This is *not* a log or a report archive: reports/replays live with their episodes,
finished work lives in git history / the [version log](crewrift/crewborg/version_log.md),
and durable preferences live in [`user_preferences.md`](user_preferences.md). This file
is the one-screen answer to "where are we and why."

> The active policy/version here is also the onboarding signal: a recorded objective
> below means onboarding is done — resume the loop (see [`AGENTS.md`](AGENTS.md)).

---

## 🧭 ACTIVE OBJECTIVE — LLM GAMEPLAY COMMANDER (design stored 2026-06-26)
A background LLM that steers *gameplay* (not meetings) by writing **priorities** into
`belief.commander` that the modes read to bias *how* they execute — never selecting a mode,
never blocking a tick. Design: **[`crewrift/crewborg/docs/designs/llm-commander.md`](crewrift/crewborg/docs/designs/llm-commander.md)**
(summary in `design.md` §10.6). **Decisions locked:** background daemon thread + sync Bedrock
`call_json` (one call in flight); `CommanderStrategy` wraps `RuleBasedStrategy` on the existing
`SynchronousStrategyRunner`; priorities flow via `StrategyResult.inferences` → `apply_inferences`
→ `belief.commander` (sticky, lock-protected handoff). Scope v1 = **gameplay only, meeting LLM
untouched**. Rule = **bias, don't force** (filter-then-rank / score-nudge, fall back to default
on stale/invalid). **Danger mode** (imposter, opt-in, traced `danger_reason`): `allow_witnessed_kill`
+ `skip_evade`. Mode injection points: `normal.py:85`, `search.py:266`, `recon.py:534`, `hunt.py:612`.
Gating `CREWBORG_LLM_COMMANDER=1` + backend (mirrors `CREWBORG_LLM_MEETINGS`). **Build phasing:**
scaffold → imposter levers + danger → crewmate levers → (later) EscortMode + unify w/ meetings.
NEXT: build phase 1 (scaffold + no-op fallback). Directly attacks the durable imposter
kill-efficiency gap.

## ✅ LLM MEETINGS CONFIRMED WORKING — v50, end-to-end (2026-06-26)
The v47 "NEXT" item below is DONE. The LLM was silently 403'ing (disabled) until two fixes landed:
(1) **SDK sidecar routing** — `players.player_sdk.llm.select_client` hit AWS Bedrock directly instead of
the pod's loopback proxy sidecar (`AWS_ENDPOINT_URL_BEDROCK_RUNTIME`); fixed in **coworld-tools PR #12**
(`bedrock_base_url`). (2) **Infra** — the Bedrock sidecar enabled for `crewrift_prime` experience-request
jobs (James). Built **v50** against coworld-tools `main` (Dockerfile + `versions.env` now install the SDK
from `coworld-tools/archive/<main-sha>.tar.gz#subdirectory=players`; `main` resolved via `git ls-remote`),
uploaded `--use-bedrock` + `USE_BEDROCK=true` + `CREWBORG_LLM_MEETINGS=1`. **10-ep eval: 101
`meeting_llm_decision`, ZERO fallbacks**, ~1.5–2s latency; it chats up to **7×/game**, deflecting as imposter
and demanding evidence as crew. NOT submitted. Also this session: **mid-game reconnect** added to the bridge
(retry a few times on a post-frame drop, resume if frames return — recovers transient blips that were `-100`s).
NB v49 (LLM, no SDK fix) was REJECTED from Prime qualifiers (mean score 0.7, 2 crashes); tournament Bedrock
403'd the SAME as XP requests (no tournament/XP difference).

---

## 💬 LLM MEETINGS LIT UP — v47 uploaded, NOT submitted, eval pending (2026-06-25)
Directly answers the "TODO: LLM crewborg chat" noted under JOB 2 (Aaron's imposter is chat-SILENT, Andre uses
LLM chat — chat is an exploitable axis). Design: `crewrift/crewborg/docs/designs/llm-meetings.md`.
- **What shipped (committed `0a2395c`, merged `523226d` into the search line; built + uploaded as
  `crewborg:v47` = `91616701-5528-44cc-beb6-3ae972b71597`).** The dormant LLM meeting brain now actually
  runs in the league: **Bedrock backend** in `strategy/meeting/llm.py` via the SDK helpers
  (`select_client`/`bedrock_enabled`/`resolve_model`/`call_json`); enable = `CREWBORG_LLM_MEETINGS=1` AND
  (`USE_BEDROCK` or `ANTHROPIC_API_KEY`); factory never raises → deterministic fallback. **Per-role prompts**
  `strategy/meeting/memory/{crewmate,imposter}.md` (crew = vote *restraint*; imposter = conversion/deflect,
  never out a teammate). **Full LLM vote authority** (no confidence downgrade; self-vote guard kept).
  **Timeout-derived deadline guard** (no call starts unless a 3s worst-case returns before the 48-tick
  auto-submit; 24 ticks/s, 240-tick=10s timer). Codex did a reviewed surgical impl. 367 tests pass, ruff clean.
- **v47 provenance VERIFIED:** md5 of llm.py/prompts.py/attend_meeting.py/search.py/opportunity.py/recon.py
  INSIDE the image == merged main → v47 = current best (search-line + recon + v46-revert) + LLM meetings.
  Uploaded with `--use-bedrock --bedrock-model us.anthropic.claude-haiku-4-5-20251001-v1:0` +
  `CREWBORG_LLM_TRACE_RAW=1` (first-version debug — drop later) + v25 trace/metrics env.
- **Gate-1: liveness PASS only** — the cert fixture has NO Voting phase, so the LLM meeting call was NOT
  exercised locally. Required env fix along the way: local `coworld` 0.1.20→**0.1.26** (couldn't parse
  crewrift 0.1.59 manifest); now in `uv.lock` on main.
- **NEXT (the real test):** experience-request eval of v47, role-decomposed vs the deterministic champion —
  confirm the LLM fires on Bedrock (`meeting_llm_decision` events, latency, **zero `meeting_llm_fallback`**),
  read raw chat/vote quality, and check crew vote-restraint doesn't regress. Then (Gate-2, James's call) submit.
- **Loose end:** ux.link DX feedback was appended (uncommitted) to `~/coding/metta_checkouts/metta_7/
  agent-plugins/default/skills/ux.link/FEEDBACK.md` (couldn't write the protected `~/coding/metta`).

---

## 🌙 OVERNIGHT (2026-06-25 → 26 AM): TWO autonomous jobs running (full autonomy granted, James asleep)
**MORNING: read `/tmp/prime_results.txt` (primary) and `/tmp/suss_big_results.txt`.** Logs:
`/tmp/prime_loop.log`, `/tmp/suss_pipeline.log`. Eval data persists on the cluster — re-run the
scripts if a job died (machine slept).

### JOB 1 (PRIMARY) — Prime natural round-robin loop `/tmp/prime_loop.sh` (pid was 4304)
James's refined ask: a PROPER natural experiment among only the GOOD policies — the **Crewrift PRIME
league** champions (the regular Crewrift league is full of bad policies you win by exploiting, not by
improving). Field = **crewborg:v43 (us) / crewborg-aaln:v17 (Aaron) / truecrew:v27 (Andre champ) /
truecrew:v28 (Andre latest, from Prime Qualifiers — Andre's policies keep improving so include latest
+ champ)**. 2 seats each (8), **natural roles (no force)**, target Prime Competition div_acbde92a.
Loop: ONE 100-ep request at a time, ≥30min between starts + waits for completion (serial — fixes the
backend overload the 8-parallel approach caused), then folds each batch into a GROWING warehouse
(`/tmp/prime_warehouse`, expand-0159, snapshot-every 50) + LLM suss pass, writes running standings to
`/tmp/prime_results.txt`. Up to 20 batches (~2000 eps). xreqs logged in `/tmp/prime_xreqs.txt`.
Analysis: `crewrift_lab/prime_summary.py` (win by role, kills, suss/vote accuracy per policy).

### JOB 2 — crew-vs-Aaron suss eval `/tmp/suss_pipeline.sh` (pid was 61210)
800 eps crewborg:v43=CREW vs 2× crewborg-aaln:v17 (Aaron) imposters (8 parallel xreq in
`/tmp/suss_big_xreqs.txt`) → fetch → warehouse → suss → `/tmp/suss_big_results.txt`. Measures our
suss/vote-rate vs Aaron + detection-vs-aggression. (Superseded in priority by JOB 1 but still good data.)
- **`suss` subcommand built + committed** to the reporter repo (`~/coding/role_repos/reporter_lab/
  crewrift-event-warehouse`, `suss.py` + CLI). `crewrift-event-warehouse suss --out <wh>` labels each
  meeting chat msg with who it accuses via **Bedrock Haiku 4.5** (us-east-1, AWS_PROFILE=softmax),
  cached by distinct text, → `events/key=chat_suss` (suss_target_*, is_suss, target_is_imposter).
  Validated: crew susses true imposter 66-80%; imposter deflection 0% (correct).
- **Big eval:** 800 eps (8× xreq in `/tmp/suss_big_xreqs.txt`), crewborg:v43=CREW slot0 vs 2×
  crewborg-aaln:v17 (Aaron) imposters, crew fill truecrew:v25+sussybuster:v3.
- **Pipeline** `/tmp/suss_pipeline.sh` (nohup): waits ≥760/800 → fetch → warehouse (expand-0159,
  snapshot-every 30) → suss → `crewrift_lab/suss_rate.py` → `/tmp/suss_big_results.txt`.
- Analysis scripts: `crewrift_lab/{suss_rate,aaron_compare,kill_latency,visibility_at_ready}.py`.
- Chat landscape: Andre=LLM/contextual (already cites the "following" tell); Aaron imposter SILENT
  (95/95 "no read, skipping"), crew mostly skip → doubly exploitable. TODO added: LLM crewborg chat.

## ✅ SHIPPED/CANDIDATE (2026-06-25): vantage-SEARCH + RECON imposter
- **v42 (vantage-SEARCH) SHIPPED to Crewrift PRIME.** v43 (+100-tick RECON) = measured-better candidate
  NOT yet shipped (kills 1.23→1.48, dither 28→1, in-view-at-ready 53→62%, ejection FLAT 24→25%; win
  27% vs 34% is noise). RECON tunable `CREWBORG_RECON_WINDOW` (default 100); ejection-flat ⇒ headroom up.

---

## Active league state (2026-06-23) — NIGHTLY LOOP WAS BROKEN; champion frozen at v31

- **Champion = v31** (nightly-2026-06-15 refit), Crewrift div `div_8d3ead22`, **rank
  11/18, score 46.2** (586 rounds). Field has advanced past us: Andre Jr (truecrew:v24)
  63.2, Aaron (sussybuster-aaln:v1) 56.9, RowDaBoat (softmax-sussyboi:v1) 54.5. Note:
  the division leaderboard scores **per PLAYER** (James Boggs), so every crewborg
  membership shows the same 46.2 — can't read a version's standing off it.
- **NIGHTLY CHAMPION LOOP SILENTLY BROKE 06-16→06-20** (FIXED 06-23): every night the
  refit/test/build PASSED but Gate-1 smoke CRASHED → aborted, "champion unchanged."
  Root cause: `coworld-local-run/scripts/smoke.py:ensure_manifest()` globbed the
  **shared** `coworld/` dir by newest mtime; with 3 labs downloading there, the
  Crewrift smoke ran a *Cue-n-Woo* game container (timed out at 240s). **FIXED**
  (committed): parse the `Manifest:` path `coworld download` prints instead of mtime.
  Verified: resolves crewrift→cow_50ee07cf, full Gate-1 PASS. Tonight's nightly should
  ship again. ⚠️ Refit AUC is also slowly *decaying* on the ballooning full corpus
  (0.812→0.809 by 06-20, 191k games) — the recency-window concern is now real.
- **STANDING EVAL IN FLIGHT (2026-06-23)** to locate v31 vs the current field,
  role-decomposed, vs the explicit live top-7 (truecrew:v24, sussybuster-aaln:v1,
  softmax-sussyboi:v1, daveey-notsus-tier5c:v1, truecrew:v21, jernau-crewrift:v14,
  kyle-int-boost:v5; opponents rotate seats, crewborg pinned slot 0):
  **CREW** `xreq_437780fd` (slot0=crew, 2 imp) + **IMPOSTER** `xreq_8babadbd`
  (slot0=imp + partner imp), 100 eps each. Monitoring in bg. ⚠️ `top_n`/`random`
  selectors now 500 (server statement-timeout on the champion-ranking query) — had to
  pin explicit policy_refs.

## NEW PROTOCOL (2026-06-24): XP requests run ONLY vs Aaron + Andre, opponents rotate roles
Future evals fill opponent seats *only* from Aaron's & Andre's policies (rest of field too
weak; new league coming). Champions: Andre Jr `truecrew:v24`, Aaron `crewborg-aaln:v3`,
Andre von Houck `truecrew:v21`, Aaron's Optimizer `sussybuster:v3` (re-resolve; they drift).
Our role stays FIXED (crewborg slot0); opponents sit at `slot:-1` so they rotate through all
seats → we play WITH and AGAINST each in both roles. See [user_preferences](user_preferences.md).

## ⭐ CURRENT BASELINE: v38 (= v34 gate 0.8 + aggressive reconnect) — 2026-06-24
Working baseline is **v38** (`76be842b`, `CREWBORG_WEIGHTS_VOTE_P=0.8` + bridge reconnect).
NOT submitted (Gate-2 still owed). Supersedes v34 (gate 0.8, no reconnect). Continue from v38.
- **Reconnect WORKED — the big result:** eval vs Aaron+Andre (598 eps) ops-failure rate
  **65%→3.0%**. The initial-connect-race −100s are largely gone; evals are trustworthy and
  (likely) league episodes stop bleeding −100s too.
- **v38 standing vs Aaron+Andre (clean):** crew **52.3%** CI[47,58] (n=300), imposter **43.2%**
  CI[38,49] (n=280) — imposter up sharply from v33's 36.5%. Overall 47.9%, mid-pack
  (Andre von Houck 54% / Andre Jr 49% / Aaron 48% / Aaron's Opt 46%). Eval xreqs:
  `/tmp/eval_v38_xreqs.txt`. PR: JBoggsy/player_labs#5.
- **Next lever:** imposter is still the weaker half (43% vs Andre von Houck's 54%) and the
  obvious place to push for overall win-rate. Also: the v25 mis-vote-risk check (own-ejection /
  team-crew-ejection at the lower gate) is still owed before submitting.

## ⭐ ACTIVE (2026-06-25): vantage-SEARCH imposter — CONFIRMATION EVAL RUNNING
New SEARCH mode (watch-a-room→follow-leaver) + **vantage-watching fix** (hold the in-room point
with LOS to the most crew, don't stand at the door — James caught it in replays). 20-ep look:
**kills/g 0.60→1.50, imp win 30%→45%, 0-kill 6/10→1/20** (above top imposters' ~1.05). v41=debug
build. **CONFIRMATION: v42** (vantage, non-debug, `players-crewborg:dev`) — 200 imposter eps vs
Aaron+Andre **LATEST uploads** (truecrew:v25, crewborg-aaln:v17, sussybuster:v3; round-robin),
slot0=imp+partner. xreqs `xreq_c151184b` + `xreq_a272c9bb` (2×100). Dashboard :8808. NB Aaron's
crewborg-aaln jumped v3→v17 and is now a strong imposter (~60% imp win in this eval).
- **Expander FIXED for 0.1.58:** arena redeployed crewrift 0.1.54→**0.1.58**; built
  **`/tmp/expand-0159`** from tag 0.1.59 (sim-compatible), verified trace_complete:true + 0%
  hash-fail + derived events (proximity/isolation) over a real episode. Warehouse "near-crew"
  diagnosis UNBLOCKED. (Local Gate-1 needs `--manifest` at cached 0.1.54 cow_50ee07cf — SDK can't
  validate the 0.1.58 manifest. Debug trace must be BAKED as ENV, not --secret-env.)
- **Next after eval:** warehouse the 200 v42 eps (expand-0159) → confirm "near crew" rose from
  6.64/g (the mechanism); if kills hold ~1.5, consider Gate-2 (submit). Win<kills (conversion gap).

## PRIOR OBJECTIVE (2026-06-24): fix the IMPOSTER gap — under-killing, not ejection
James's principle: always work the highest-leverage gap (lesson logged). Imposter is it.
- **Loss structure (282 clean v38 imp eps, from results.json):** NO ejections (loss scores
  0/10/20/30, no −100s) — we lose by **under-killing**. **31% of our imposter games are 0-kill**
  (88/282, lost 75). Our kills 1.12/g in wins vs **0.63 in losses**; team (us+partner) 2.45 win
  vs 1.45 loss (need ~3 to reach parity in 8p/2imp). In 0-kill games we score 0 (survived, never
  ejected) and the partner still kills in 70/88 → victims exist, we just don't convert. Same root
  as the old v23/v24 thread: **too few kill ATTEMPTS, not bad aim.**
- **Diagnosis run IN FLIGHT:** v39 (= gate 0.8 + reconnect + `CREWBORG_TRACE=debug` baked,
  policy id pending) — 50 imposter eps vs Aaron+Andre (slot0=imp, 2-imp, opponents round-robin
  incl. the partner seat). `xreq_6e2dae51`. Full per-tick decision_snapshot trace (mode/intent/
  threats/kill-readiness) to see WHY we don't attempt — stuck in pretend? not pre-positioning for
  the cooldown window? (v38 default trace had empty decision_snapshot — needed debug level.)
- NB: `CREWBORG_TRACE=debug` must be baked as an ENV (distinct image digest) — `--secret-env`
  alone dedups to the same version (hit twice now).

### INVESTIGATION LOOP (James, 2026-06-24): compare imposter search/hunt behavior across policies
Hypothesis: **crewborg transitions to SEARCH too late → doesn't effectively shadow targets** (so
when the post-meeting kill window opens, it isn't pre-positioned on an isolated victim). Plan:
use the event warehouse to compare crewborg vs the top imposters' shadowing behavior.
- **Tool: `~/coding/role_repos/reporter_lab/crewrift-event-warehouse`** (well-documented). Turns a
  batch of episodes → policy-indexed Parquet/DuckDB star schema (`events` fact + `episode_players`
  dim), re-keying each slot to policy_name/role. `build` CLI then `serve` (DuckDB SQL dashboard
  :8765). Input = `report_request.json` files (round fetcher: `tmp/round-loop/fetch_round.py`).
- **The events that test the hypothesis:** `following_interval` / `chase_interval` (shadowing!),
  `isolation_interval` (was the victim isolated), `proximity_interval` (kill-range), `player_state`
  (heading/pos), plus `killed`/`body`/`vote`. All re-keyed to policy+role for cross-policy compare.
- **expand_replay version coupling VERIFIED:** arena `crewrift:0.1.54` ⇒ commit `42fed21`. Helper
  `/tmp/expand-42fed21` already built + the crewrift checkout (`~/coding/coworlds/coworld-crewrift`)
  is AT 42fed21; tested on a v39 replay → `trace_complete:true`, exit 0 (no hash-fail). Reporter
  Docker image `crewrift-event-reporter:local` also present.
- **Next:** build a warehouse over a batch that has crewborg AND the top imposters (Aaron/Andre) as
  imposters — i.e. point it at league rounds (where all policies appear) or our rotating evals —
  then query following/isolation lead-times by policy to test the "search too late" hypothesis.

### FINDING (2026-06-24): imposter gap = shadow COMMITMENT, not search timing
Warehouse built over 2 league rounds (443 eps, `/tmp/crewrift_warehouse`, expand-42fed21, 0% hash-fail).
Compared shadowing (`following_interval`+`chase_interval`) by imposter policy:
- "Search too late" REFUTED: crewborg shadows often (13.5/game, 4th) and early (median tick 1902).
- **Real diff: crewborg's shadows are too SHORT and rarely convert.** avg shadow 158 ticks (LOWEST of
  18 policies, median 65) vs top imposters 188–387; only **10% of crewborg shadows end in target death
  vs 21–27%** for truecrew:v21 (2.21k), daveey (2.13k), crewborg-aaln (2.06k), Lively (2.04k). 89% of
  crewborg shadows end in 'separation' (target escaped). Monotonic across all 18 policies:
  longer shadow → more conversion → more kills/g.
- **Fix direction: shadow COMMITMENT** — lock Search onto `select_victim()` and hold the shadow at
  kill-range through the cooldown/kill window instead of flitting between targets. (Maps to the parked
  "stalk a committed victim" lever + the existing `select_victim` in opportunity.py.)
- Reusable tool now set up: `~/coding/role_repos/reporter_lab/crewrift-event-warehouse`, helper
  `/tmp/expand-42fed21`, round fetcher `reporter_lab/tmp/round-loop/fetch_round.py` (wrap in retry —
  it dies on transient urllib resets and only writes report_request.json after a full round).
- NEEDS James's direction on whether to implement shadow-commitment as the next crewborg change.

### CORRECTED FINDING (2026-06-24): on CONTROLLED XP data, the gap is ISOLATION-CREATION (not shadowing)
James: dropped the natural-league analysis (misleading opponent mix) and rebuilt the warehouse over
450 of THIS SESSION'S XP imposter episodes (`/tmp/xp_imp_warehouse`, crewborg slot0=imp vs Aaron/Andre,
expand-42fed21, 0% hash-fail). Apples-to-apples result:
- Shadowing is NORMAL: crewborg 13.2 intervals/game (= truecrew 13.1), per-shadow conversion 11%
  (≈ truecrew 10%). The natural-league "short-shadow/poor-commitment" finding was an opponent-mix
  artifact — SUPERSEDED.
- **Real gap = isolation OPPORTUNITIES:** crewborg gets alone-with-a-crew **1.84×/game vs truecrew 4.44,
  crewborg-aaln 3.45, sussybuster 3.83 — half the field.** ZERO isolation in **21% of crewborg's
  imposter games vs 8-9%** for peers. Yet crewborg's iso→kill conversion is the BEST (19% vs 11-15%).
  So: execution is great, it just doesn't MANUFACTURE enough 1-on-1s. Timing fine (median iso ~3200).
- **Fix direction: PROXIMITY/PRESENCE, not "engineering" isolation** (James corrected the frame — you
  can't control other players). Root cause is upstream: crewborg is NEAR a crew member only **6.64×/game
  vs truecrew 12.4, sussybuster 11.9, crewborg-aaln 9.1** — ~half the field's co-location with crew. It
  then converts near→alone slightly worse too (28% vs 36%). So it gets ~half the isolation opps simply by
  being around crew half as much. WHERE: crewborg over-camps **Shuttle Bay (15% of presence vs 4% for
  others)** — a low-yield room — and barely visits the peripheral wing (Med Bay 3%, Reactor/Engineering/
  engines ~0-1% vs peers' 2-8%) where stragglers isolate. Even in the Bridge (equal presence 36% vs 37%)
  truecrew gets 2× the iso opps (1.59 vs 0.74) → also micro-positioning within shared rooms. Versions in
  the sample: crewborg = v38 76be842b(296)+v31(95)+452371ca(48); truecrew = v21 ec9266b9(115)+v24
  fe68a21e(107) pooled; crewborg-aaln d359bd4f(98); sussybuster 765ec3d3(52).
  **Lever: position where crew actually are** (follow population to high-traffic task rooms + circulate
  the periphery), not camp Shuttle Bay. conversion/execution is already best-in-field (19%) — don't touch it.
- Reusable XP-warehouse recipe: `make_wh_input.py` (in /tmp) turns fetch_artifacts dirs → warehouse
  report_request.json; build with CREWRIFT_EXPAND_REPLAY=/tmp/expand-42fed21.
- NEEDS James's direction: implement isolation-creation as the next crewborg imposter change?

## ⭐ ACTIVE BUILD (2026-06-24): new simple SEARCH mode + path-prediction prerequisite
James scrapped BOTH the occupancy-density seeking AND the group-follow/peel-off idea for a
SIMPLER plan. New SEARCH algorithm (PRETEND mode removed; agent starts in SEARCH):
1. pick a random nearby room → 2. enter, look for crew → 3. if crew present, idle at a task
spot near the entrance until a crewmate leaves → 4. follow that crewmate to their next room →
5. if all crew lost, back to 1. Old PRETEND/SEARCH logic cold-stored in `modes/_deprecated/`
(DEPRECATED, DO NOT USE); live pretend.py/search.py are no-op placeholders (imposter idles —
DON'T eval imposter play until rebuilt). 13 deprecated-behavior tests skipped.
- **Step 4 needs good path projection FIRST (James's asterisk) → BUILT (first draft):**
  - **`strategy/path_prediction.py`** — `PathPredictor`: per-frame probability distribution over
    candidate nav ROUTES (tasks + room centers) a tracked crewmate is walking; scores observed
    motion vs each route's direction with exponential forgetting (recent motion wins / reversals
    recover), advances predictions through occlusion. Fed ONLY what crewborg saw (visibility-
    masked). NOT a bare heading vector — routes, per James. 4 unit tests. Tuning knobs at file top.
  - **Replay tooling (`crewborg/tools/`, documented in `tools/README.md`, linked from AGENTS.md):**
    `replay_frames.py` (load 1 episode from a warehouse → per-tick truth + crewborg visibility);
    `path_prediction_ui.py`+`.html` (LIVE browser UI :8810 — agent dropdown, weighted route overlay,
    scrub/play, watch predictions sharpen + coast through occlusion); `path_prediction_eval.py`
    (scores predictions at every visible→obscured transition: destination-ROOM match rate + CSV +
    per-instance overlay PNGs actual-vs-predicted, `uv run --with matplotlib --with duckdb ...`).
  - **First-draft accuracy (4 XP episodes, /tmp/xp_imp_warehouse):** 43% destination-room match
    overall, but **86% when confident (pred_prob 0.4-0.7)** vs 33% when unsure → module is
    informative (confidence tracks accuracy); first-draft tuning leaves most predictions low-conf.
    Next: tune ALIGN_GAIN/EVIDENCE_DECAY/LOOKAHEAD against the eval, then build the SEARCH mode.

## sweep2: threshold sweep vs Aaron+Andre, w/ tracing (DONE, 2026-06-24)
Re-ran the crew vote-threshold sweep vs ONLY Aaron+Andre champions (new protocol), 300 eps/arm,
opponents rotating, + the imposter baseline. Dashboard: `xp_dashboard.py` (see skill).
- **CREW win% by gate (clean games only):** v33/0.9=**50.0%** (n=200, WORST) · v34/0.8=**55.3%**
  (n=94) · v35/0.7=54.1% (n=74) · v36/0.6=52.4% (n=63) · v37/0.5=53.2% (n=77). v34–v37 cluster
  tightly ~4pp over v33; v33-vs-rest p=0.39 (underpowered — see ops note). Sweep1 (vs top-7)
  independently had 0.9 WORST at p=0.031 → direction solid, magnitude uncertain.
- **⚠️ ~65% ops/connect-timeout rate this run** (1177/1800 episodes degenerate −100, correctly
  ops-filtered) gutted per-arm n (63–94 of 300). The disconnect problem is the next lever →
  SDK aggressive-reconnect work (task #3).
- **IMPOSTER baseline vs Aaron+Andre (v33):** crew ~50% but **imposter 36.5%** — well behind every
  opponent's imposter rate (Andre von Houck 53.6%, Aaron 44.0%, Andre Jr 41.2%). **Imposter is
  our weak half vs the strong field** — louder strategic signal than the vote threshold now.
- xreq IDs: `/tmp/sweep2_xreqs.txt`. (Did NOT yet mine the trace logs for own-ejection /
  team-crew-ejection — the v25 mis-vote risk check is still owed before pushing the gate lower.)

## PRIOR EXPERIMENT — crew vote-threshold sweep vs top-7 (DONE, 2026-06-23)

Mechanism: `WEIGHTS_VOTE_PROBABILITY` (suspicion.py crewmate vote gate) made env-tunable via
`CREWBORG_WEIGHTS_VOTE_P` (default 0.9; committed). Arms = ENV-baked images v33=0.9(ctrl)/
v34=0.8/v35=0.7/v36=0.6/v37=0.5. Eval vs **top-7**, slot0=crew, 2 imp, 150 eps/arm.
**RESULT (crew win%, ops-filtered):** 0.9=**31.9%** / 0.8=35.5% / 0.7=40.4% / 0.6=31.4%(noisy
dip) / **0.5=44.5% (+12.6pp vs ctrl, p=0.031 SIGNIFICANT)**. Trend up as gate drops; 0.6 = noise.
**Mechanism confirmed across ALL arms:** win-when-it-votes 58–72% vs win-when-it-skips-all 9–28%;
lowering the gate moves games from skip-bucket→vote-bucket (35→81 voting games at 0.9→0.5).
⚠️ measured crew WIN only — did NOT measure own-ejection / team-crew-ejection (the v25 risk);
sweep2 (above, w/ logs) closes that gap. NOT submitted.

## Prior league state (2026-06-11)

- **v24** (`b725a6e1`) = self-vote fix (v22) + kill-sooner. **Submitted** `sub_e6969016`
  (provisional, pending the large A/B). **v22** `sub_9a4b4fa9` and **v21** `sub_2c8afd84`
  (still the buggy champion) are now both superseded — retire once v24 places.
- **Large 2-imp A/B (DONE but CONFOUNDED):** `top_n` seated a **different slot-7 partner
  per arm** (v22 got Kyle/Aaron, v24 got a James Boggs crewborg), so the +23% win was a
  partner artifact. Kills (v24 1.93 vs v22 1.73, p=0.005) were more robust — v24 led in
  both the 30-ep and 200-ep batches even as partner-strength flipped — but not clean. (See
  the `top_n`-uncontrolled-roster tentative lesson.)
- **CONTROLLED 2-imp A/B DONE (trustworthy):** fixed roster, partner=slava2 both arms,
  only slot 0 differs (v22 `xreq_1c7f6bdf` / v24 `xreq_57de3453`, 100 eps/arm).
  **Kills +0.21/g (1.37→1.58, +15%), p=0.027 SIGNIFICANT** (robust — same ~+0.2 across all
  3 batches, different partners). **Win +6%, p=0.40 NOT significant** — kill gain doesn't
  reach wins; no ejection cost. **v24 kept** (self-vote fix + real kill bump, strictly
  better than v22). **Kill lever now genuinely improved but kill→win link is weak** →
  next direction should be imposter survival/meetings or crewmate, NOT more kill tuning.
- **v24 league debut (first 7 Competition rounds, 2026-06-11 22:45–23:52, ~480 eps):**
  leaderboard **rank 11/20** (44.15, tight mid-pack cluster 41.8–44.5). Seat-level
  (results.json, all crewborg seats): **crew 25.1% win** (n=406, tasks med 8/8, **0 vote
  timeouts**), **imposter 69.4% win** (n=121) @ **1.79 kills/g** — kill rate now
  field-top tier (top imposters 1.8–2.1) and only 1/121 zero-kill games, **but imposter
  WIN trails the top imposters (83–91%) by ~15–20pp**, and most imposter losses come
  *with* 2 kills (21/34) → the imposter gap is now **conversion** (survival/meetings/
  endgame), not kill volume. Crew gap to the best regulars (slava2 38%, RowDaBoat 35%)
  ≈ 10–13pp, and 77% of seats are crew → **crew is the volume lever**. Round trend:
  48% → ~38% win over the 7 rounds (n=80/round, borderline noise — watch it). Both
  findings confirm the standing call: next direction = imposter conversion or crewmate
  play, NOT more kill tuning. (~10% of league episodes double-seat crewborg — see the
  new tentative lesson before aggregating.)
- **RowDaBoat's edge decoded (2026-06-12, 480-ep stats + 40-replay aggregate):** the
  leader's dominance is ~all CREW-side: crew 39.2% win vs our 25.1% (imposter 74% @1.83
  kills ≈ ours). Mechanism: crew wins are a parity-vs-task race (ghosts keep tasking!),
  and RowDaBoat (a) almost never votes players (0.00 complicity in crew ejections over
  33 crew games; we're 1.04 votes-at-crew/g, 0.48 complicity), (b) burns the emergency
  button every game to reset imposter kill CDs (canned line "just resetting imposter
  cool downs", shared with truecrew), (c) reliably finishes 8/8. Crew ejections ran 14
  in 20 crew losses vs 4 in 20 wins; imposters ejected 2/40 games → our accuse/vote
  feature is likely negative EV as crew. Exemplars in `/tmp/rdb_focus` (77d55243,
  89c510fb, f3b7b1fa = RDB crew beating crewborg-as-imposter; 633ce75a = crewborg
  imposter winning via 2 kills + 2 engineered mis-ejections). Full details in the new
  tentative lesson. **Candidate directions:** crew = vote restraint (skip unless
  near-certain); imposter = engineer mis-ejections (the conversion lever we're missing).
- **XP-request API rebuilt (2026-06-11, metta #15572):** the body is now a single
  `roster` field (one entry per seat: `policy_ref`/`top_n`/`random` selector + `slot`
  pinning or `-1` round-robin); `requester`/`opponents`/`rotate_seats`/`player_selection`
  are gone. Skill docs (`coworld-experience-requests`, `crewrift-ab`) updated to match.

## NEW DIRECTION (2026-06-12, James): tune the suspicion system — learned from replays

James's calls: (1) evidence **instances** sum (not per-type max), (2) add
**exculpatory** evidence, (3) the main thing: build the data-science pipeline —
scrape all games, expand replays, fit evidence weights from ground truth, and adopt
any evidence type that earns weight. Design doc written:
`crewrift/crewborg/docs/designs/suspicion-learning.md` (scrape → expand → per-observer
dataset → logistic-regression fit → weights.json into the agent). Key enabler
verified: the upgraded expander (coworld-crewrift `42fed21`, PR #57) emits JSONL with
ground-truth roles, true kill attribution, player states, AND **exact per-(observer,
target) rendered-view visibility intervals** — so "did the player see it" is computed,
not modelled. ⚠️ Don't land instance-summing alone with current hand weights — it
raises posteriors and worsens mis-votes; land with fitted weights (design §1).
- **PIPELINE BUILT + FIRST MODEL FIT (2026-06-12):** `crewrift_lab/suspicion_lab/`
  (scrape_corpus → expand_corpus → build_dataset → fit → eval; see its README).
  Interim fit, 341 games / 35k rows: **full model CV AUC 0.811** (calibrated);
  **runtime-subset (existing event-log features only) AUC 0.739**; decision sim at
  P≥0.9 → 88% of votes hit imposters (live hand model: 42%), net +8.3/100 over
  always-skip. Fitted facts: `tasks_completed_watched` ≈ perfect exculpation (−9.0;
  needs a NEW runtime perception detector — top integration priority);
  `follow_death` strongest graded cue; `accusations_made` +1.1 (incriminating);
  `tailing` ~10× weaker than the hand LR 6.5. Weights:
  `suspicion_lab/models/v1-runtime/suspicion_weights.json`.
- **RUNTIME INTEGRATION DONE (2026-06-12, uncommitted→committed; NOT yet built/
  uploaded):** `suspicion.py` now loads `data/suspicion_weights.json` (vendored,
  v1-runtime fit) and scores with the FITTED model: instance-summed features with
  per-context dedup, exculpatory negative weights, exposure feature
  (`PlayerRecord.seen_ticks`, incremented in event_log), offline-sample unit contract
  (duration/24), witnessed kill/vent kept as a definitional floor. **Crewmate vote:
  P≥0.9 only, NO clear-leader rule** (held-out sim: ~100% imposter precision);
  **imposter deflection keeps the legacy clear-leader logic** (mis-ejections are its
  goal). Legacy hand model = fallback (`CREWBORG_SUSPICION_WEIGHTS=0`). 343 tests
  pass (39 legacy-pinned + 9 new fitted-path), ruff clean; Dockerfile already COPYs
  the data/ package. suspicion.md updated + provenance row added.
- **v2: SOCIAL DETECTORS + FULL-CORPUS REFIT DONE (2026-06-12, James's "get the
  full feature set into the player"):** new `strategy/social_evidence.py` in the
  fast loop (after event_log, before suspicion) maintains cumulative PlayerRecord
  counters: **watched task completions** (global `crew_tasks_remaining` HUD counter
  decrements by exactly 1 while exactly ONE visible living player ends a ≥56-tick
  task dwell — fake Pretend holds never decrement, so they can't trigger it), **chat
  stances** (offline-mirrored accuse/defend regex over `chat_log`, deduped by
  (tick,speaker,text) so per-meeting clears don't lose counts), and **attributed
  votes** (VoteDot carries voter+target slots! staged during Voting, committed once
  at meeting end: cast/skip/against-me/agreed-with-me). Only
  `button_calls_made`/`reported_bodies` are not yet wired (worth ~0.011 AUC) —
  CORRECTION (James, 2026-06-12): they ARE observable; the game's MeetingCall
  interstitial (4b9297d, deployed) shows the caller's icon + "<caller>
  pressed/reported" in the player view; crewborg's perception predates it and
  doesn't parse it yet. Next detector: parse the interstitial -> caller counters
  -> refit with button/reported -> full 0.812 ceiling. **Full corpus: 2,684 eps scraped,
  1,875 expanded, 196k rows. v2-runtime AUC 0.801 vs full-model ceiling 0.812**
  (v1 was 0.704); decision sim @ P≥0.9: 94% imposter precision, net +17.3/100.
  Weights re-vendored (`data/suspicion_weights.json`, intercept +0.392 — note an
  unseen player's baseline P≈0.6, behaviorally contained: vote needs 0.9, Accuse
  needs an active tail). 353 tests pass (10 new social-evidence), ruff clean.
  **SHIPPED (2026-06-12): v25 = the fitted model + v3 weights + interstitial caller
  parse.** Gate-1 PASS (weights verified in-image, 0 log errors). **Submitted + placed**
  (`sub_07dae14f`, `lpm_c04b55cc`) on James's explicit go-ahead. **A/B vs v24 (pinned
  roster, 40 eps × 2 configs): crew win 22%→35% (p=0.22), votes-at-crew 0.88→0.05/g,
  OWN ejections 52%→2%** (the evolved field — sussybuster-aaln, truecrew v20/21 — was
  voting accuse-heavy v24 out!), team crew-ejections 30→6; imposter scan clean (kills
  up p=0.01, win noise, ejections 11%→7%). v25 kept. **NATURAL EVAL DONE (200 eps, xreq_25c447f9 fixed-top-7 + xreq_911e10e1
  random-pool; random roles, all seats rotating):** **crew win 43.8%** (n=146, pv-id
  attributed) vs v24's 25.1% debut — above even RowDaBoat's 39.2% benchmark; imposter
  68.5% @1.43 k/g (held). Vote mechanism in the wild: votes-at-crew 0.01/g (batch A)
  / 0.23 (batch B) vs v24's 0.88; own ejections 2–3%; **19 imposter ejections in
  batch A's 100 games** (field baseline ≈5/100) — restrained votes actually convert
  to ejections now. Tasks faster (done-8 median ~3850 vs ~5300). v25 IS champion
  already (the random pool seated it as its own teammate — double-seats in batch B).
  Field shift: truecrew v20/v21 (Andre) now top this pool (54–60% win); RowDaBoat
  mid-pack. **NIGHTLY CHAMPION LOOP INSTALLED (2026-06-12, James):** user crontab
  `30 0 * * *` → `suspicion_lab/tools/nightly_refit.sh` (scrape → refit → gates
  [AUC≥0.70, ≥500 games, test suite, Gate-1] → vendor → build → upload → SUBMIT,
  auto, per standing instruction; logs in suspicion_lab/logs/). Caveats: skips if
  the machine sleeps through 00:30; aborts safely if softmax auth expires or
  Docker is down. **Remaining open items:** (a) retire stale memberships
  (v24/v22/v21 — v25 is placed+champion); (b) offline/runtime feature parity test;
  (c) the nightly fit uses the full corpus — consider a recency window if the
  field's drift outpaces accumulation.

## Prior objective — RAISE THE IMPOSTER KILL RATE (done: v24 shipped; kill→win link weak)

crewborg is a respectable mid-pack player (clean 50-game eval, 2026-06-11) but its
weakest dimension is **imposter kills: ~1.7/game vs the top imposters' ~2.0**, and in
this game that gap *is* the win gap (64% vs 80% imp win). With 2 imposters the win
ceiling is ~2 kills each (crew loses at parity), so the goal is concretely **convert
1-kill games into 2-kill games** — i.e. get *more kill attempts*, not better aim.

Active policy: **v22** (`40e29a8c`) — the self-vote bugfix, **submitted** to the
Competition league 2026-06-11 (`sub_9a4b4fa9`), currently **qualifying** in Qualifiers
(`lpm_dd5c96db`). **v21** (`52fc8572`) is still the live **champion** and carries the
self-vote bug — **retire it once v22 qualifies into Competition**
(`coworld retire-membership lpm_3e95ac16`). Don't retire before v22 places (the older
`competing` versions also have the bug).

## The diagnosis that motivates this (5 expanded replays + traces, 2026-06-11)

crewborg's imposter problem is **passivity, not skill**:
- **Kill conversion is ~100%** — `kill_attempted == kills` in every game. When it tries,
  it succeeds. The bottleneck is purely **too few attempts** (1–3/game vs a ~4–5 ceiling).
- **Mode-time is dominated by blending:** **54–74% `pretend`** (fake tasks), only
  **0.1–2.9% `hunt`**, with big idle gaps (764–983 ticks) between kills — far past the
  **500-tick kill cooldown**, so cooldown windows are wasted.
- **It never gets caught:** survived to the end / **never ejected** in all 5 games. It's
  spending the match buying a safety margin it isn't using → lots of unused aggression.
- **Root cause in code:** `SEARCH_LEAD_TICKS = 100` (opportunity.py) makes it position
  only in the *last fifth* of the cooldown, and Hunt requires an **already-visible**
  victim (`has_visible_victim`, no pre-positioning). So when the kill comes ready it's
  usually mid-pretend somewhere random and has to start hunting cold.

## BE_DUMB ceiling experiment — DONE, rejected (2026-06-11)

v23 (`2ba6a477`, v22 image + `CREWBORG_BE_DUMB=1`) vs v22, both imposter-pinned (1-imp)
vs top-7, 30 eps, connect-failure filtered:
- **v22 baseline:** 2.25 kills/g, **14% ejected**. **v23 BE_DUMB:** 2.47 kills/g (+10%),
  **40% ejected** (~3×). Mode shift confirmed (pretend 68%→0%, search 24%→97%, hunt
  1.9%→3.2%) — but **hunt barely moved despite 97% search**: the cap is the 500-tick
  cooldown + victim isolation, NOT blending time. **Pure aggression is a bad trade.**
- **Reframe (James):** crewborg's lower league kills (1.73 in 2-imp) vs solo (2.25) is
  **not** the partner stealing victims — a sloppy partner kills in obvious spots, the body
  is reported fast, and a **report resets every imposter's kill cooldown**, so we lose our
  CD window. Only lever on our side: **get our kill in ASAP**. (Parked otherwise.)
- v22 baseline data lives at `/tmp/ab_v22` (`xreq_9274d50f`); reuse as the A/B baseline.

## Current experiment — v24 "kill sooner", 2-IMPOSTER A/B (RUNNING)

Three changes (committed `2199e4c`): `SEARCH_LEAD_TICKS` 100→**250**; Pretend `DO_TASK`
holds a fake task **only while a crewmate is visible** (`has_visible_victim`); the hold
**stops** the instant the last crewmate leaves view (re-dispatch toward crew/victims).
v24 = `b725a6e1` (v22 env, NO BE_DUMB).

- **1-imp A/B (DONE, inconclusive-by-design):** v22 2.27 kills / v24 2.00, within noise
  (t≈1.3); mode shift confirmed (pretend 69%→48%, search 24%→45%, hunt 1%→3%). **But
  1-imp has no partner**, so it can't test the partner-report-CD-reset mechanism the
  changes target — and James's standing rule is now **always 2-imposter evals, never
  1-imp** (see [user_preferences](user_preferences.md)).
- **2-imp A/B (RUNNING):** crewborg slot 0 = imposter + slot 7 = partner imposter, 6
  crew, vs top-7, 30 eps each. baseline v22 `xreq_dff96e86`, v24 `xreq_a62759e9`. Measure
  crewborg's **own** kills (`results.json` by `policy_version_id`). **Ejection detection:
  the 1-imp "GameOver right after a vote" trick fails here** (game continues while the
  other imposter lives) — detect crewborg ejection from its trace role→dead or the replay.
- **Decision:** if v24 > v22 on crewborg's kills in 2-imp → the kill-sooner changes earn
  their place; if not → kill lever exhausted (2× confirmed search-time isn't it), pivot.
  Don't ship v24 without a 2-imp win.

## Remaining kill levers (if v24 helps but not enough)

- **Stalk a committed victim:** have Search lock onto `select_victim()` and shadow it at
  kill-range during cooldown (sharper than "walk hotspots until a victim is visible").
- **Partner-report CD reset** (parked): nothing we can do from our side beyond killing ASAP.

## Working lens — the score-anomaly filter

Scoring (`docs/crewrift-gameplay.md` §6): win +100 · task +1 (×8) · kill +10 ·
vote-timeout −10. Imposter "clean success": **20/30** (lost, 2–3 kills) /
**120/130/140** (won). Join scores to crewborg by `policy_version_id`, never by slot.
**Always filter connect/disconnect-timeout episodes (−100) before concluding** — they
corrupt win rates platform-wide (see tentative lessons).

## Imposter code map (for this work)

- `strategy/rule_based.py` `_select_imposter` — the gate: evade → report_body →
  (`self_kill_ready` & `has_visible_victim`)→hunt → (`ticks_until_kill_ready ≤
  SEARCH_LEAD_TICKS`)→search → else **pretend**. `CREWBORG_BE_DUMB` shortcut at the top.
- `strategy/opportunity.py` — `SEARCH_LEAD_TICKS`, `DEFAULT_KILL_COOLDOWN_TICKS=500`,
  `select_victim` (most-isolated reachable visible straggler), `has_visible_victim`,
  `unwitnessed`/`kill_urgency_ticks` (witness bar relaxes with urgency), `TEAMMATE_CLAIM_RADIUS`.
- `modes/hunt.py` / `modes/search.py` / `modes/pretend.py` / `modes/evade.py` — the modes.
- **Trace to verify:** per-tick `domain.decision_snapshot` (mode/intent) + `domain.kill_attempted`
  in the artifact `telemetry.jsonl`; expand replays with `tools/bin/expand_replay`
  (the `3ea899eb` build matches game 0.1.51) for objective kill ticks — but **trust
  results.json for kill COUNTS** (replay attribution is unreliable at simultaneous-body ticks).
