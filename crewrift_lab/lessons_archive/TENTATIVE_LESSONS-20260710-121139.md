# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-09 11:41. This is THIS SESSION's lesson buffer. Write candidate
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

### Historical episodes are mineable without a fresh xreq via POST /v2/episodes/search
Evidence: The new episode-search API (`POST /v2/episodes/search`, fields at `GET
/v2/episodes/search/fields`) takes a filter AST; `{"op":"includes","field":"policy.version_id","value":[pv]}`
returns every episode a version participated in. Rows carry INLINE `results` (per-seat
win/imposter/kills/tasks/names) + `tags.job_id`/`replay_url` — so a role-split win-rate
A/B needs ZERO downloads. v105 had 2505 episodes, v100 4844, 236 shared. Far better than
walking xreq details (the endpoint-map skill doc predates this API; update it).

### Seat-mapping gotcha: my account owns ALL crewborg versions under one player_id
Evidence: `results.*` arrays are seat-aligned but the `policies` list is NOT in seat
order. Two of my crewborg versions in one episode both show as "James Boggs"/"James Boggs (2)"
in results.names → unmappable to a version from the row. Fix: keep only episodes where my
player holds exactly ONE seat. This also makes the 236 v100-vs-v105 head-to-head games
useless for a clean per-seat read. Seat 0 (artifact idx 0) is reliably MY crewborg (only
seat emitting `domain.meeting_llm_decision`; opponent crewborgs only `_fallback`).

### The v105 matched-field bucket is throttled; the well-fired v105 episodes have scattered fields
Evidence: v105's stable 7-champion-field episodes are all 07-09T00 at ~28% seat-0 LLM
decision rate (throttled). The paced chunk that fired at 75% (1781 eps, 07-09T17) used a
`random` seat-fill field → shatters under exact-field matching (max 41 share a signature).
So "matched-field split" and "LLM actually fired" are in tension in the existing data:
the clean-roster episodes didn't fire, the fired episodes aren't roster-matched.
LLM-gate event names: `domain.meeting_llm_decision` vs `domain.meeting_llm_fallback` in
the policy-artifact telemetry.jsonl (NOT the substrings I first guessed).

### Gate-then-match on historical v105/v100 data is empty — a fresh paced A/B is unavoidable
Evidence: gated all 2290 shared-field episodes by seat-0 firing (>=60%, >=3 meetings,
streaming zips to memory). Only 26 v105 / 36 v100 passed, sharing exactly ONE field, with
per-role N of 2-4. Too small for any verdict (matched pooled: crew v105 0/2 vs v100 4/32;
imposter v105 2/4 vs v100 1/4). ROOT CAUSE: "LLM fired" and "roster matched" are
anti-correlated in the existing data — the 75%-firing v105 chunk used random seat-fill
(fields shatter), the stable-roster v105 chunk was throttled to 28% (fails the gate). So
the clean historical read James wanted doesn't exist; the search-API harvest was still the
right first move (cheap, no quota), but the answer is: run one small paced LLM-on matched
A/B. v100 CAN fire (34/62 sampled episodes >=60%), so it is a valid gated baseline for that
fresh run — refuted the worry that v100's pre-rework context structurally can't fire.

### v105-vs-v100 fresh A/B (400 eps): gate PASSED, crew win suggestive, but a NEW no-vote regression
Evidence: fired 200/arm matched (crewborg@0 + 7 fixed champions rotating, natural roles),
paced at 400 concurrent — LLM fired v105 71.6% / v100 81.9% (both arms genuinely exercised;
pacing held). Ops-filtered role-split: crew win 15%->22% (p=0.11, NOT sig — underpowered at
~160 crew/~40 imposter per arm), imposter 57%->59% (flat). compare.py flagged a significant
regression: no_vote_rate 0%->9% crew (p=0.00), 0%->14% imposter (p=0.02) — v105 sometimes
attends a meeting and casts no vote; v100 never. NOT explained by meeting_vote_gated /
budget_exhausted (present in v100 too); the only genuinely-new v105 event is
domain.meeting_spend (20848 in v105, 0 in v100) = the spend.py follow-up-budget gate. Suspect
a spend/budget exit path skips the tentative-vote submit. VERDICT: don't ship v105; root-cause
the no-vote path in spend.py, then re-run at ~300/arm if the crew signal holds. Confirms the
WORKING_CONTEXT power warning (200/arm too thin for the imposter split).

### v105 vote_timeout root cause: false self_alive → dead-mute idles a LIVE meeting → game's -10 penalty
Evidence: replay ground truth (expand_replay-34a97a3) showed "score red(James Boggs) -10 (for
failing to vote or skip)" in a meeting where crewborg was ALIVE. Mechanism: belief.self_alive
went falsely False (dead-mute at attend_meeting.py:161-171 idles the whole meeting, never reaches
the deadline auto-submit), while the game had us alive and owed a vote. NOT belief-clock lag (async
worker fine, loop_gap max 692ms once), NOT dead-mute behaviour itself (v100 dead-mutes 83x with 0
timeouts). The trigger is the v105 self_color ONE-SHOT LATCH: the camera-center sprite can latch a
NEIGHBOUR during the ~500 Playing ticks before the first meeting; the census self-death check
(types.py:776 `if entry.color==self_color: self_alive=False`) then misfires when that neighbour
dies. v100 re-derived self_color every tick so it self-corrected.

### THE reliable self-ID: the Coworld connection slot IS the colour index (zero CV)
Evidence: crewrift game sim.nim addPlayer defaults slot colour to `PlayerColors[order mod 16]`
where order = the resolved connection slot; only overridden by an explicit `slots[i].color` config
(our hosted game_config has none — verified). So slot N ⇒ PLAYER_COLOR_NAMES[N], exactly. This is
what suspectra does (`forcedSelfColorIndex = slot`). crewborg RECEIVES the slot in
COWORLD_PLAYER_WS_URL?slot=… but had been throwing it away and guessing via a fuzzy
nearest-sprite-to-center heuristic. Also: suspectra reads the EXACT center pixel; crewborg picks
nearest visible_player to center within a tolerance → can grab a neighbour in the spawn ring.

### Fix shipped (3 layers, 638 tests green): slot-seed + source-hierarchy + deadline-skip safety net
Evidence: (1) policy_player parses ?slot= → seeds Belief.self_color as authoritative (zero-CV
ground truth from tick 0). (2) self_color source hierarchy: authoritative voting-marker may correct
a PROVISIONAL sprite guess once, but nothing overwrites a marker/slot value (keeps the v102
anti-drift latch). (3) defense-in-depth: a believed-dead seat still submits a SKIP at the deadline
(idling-is-dangerous) — inert if truly dead (sim ignores dead inputs), saves the -10 if self_alive
is wrong. Belief-layer fix (2+3) handles it even if slot-seed is ever absent.

### "Lobby-stuck / dead-game" at 400-concurrent = OPPONENT connect-timeouts, NOT a crewborg bug
Evidence: v106-vs-v105 A/B (4×100 fired at once) showed v106 "stuck in Lobby" 60% vs v105 20%.
Root cause found via James's "is it us or the game?" fork: in stuck episodes ALL 8 seats have
0 tasks/0 kills/0 imposters — the GAME never ran. results.connect_timeout was on the IMPOSTER
seats (opponents), and connect_timeout==dead-game==stuck rate were IDENTICAL per arm (v105 27%,
v106 76%). Imposters failing to connect → no imposters → game sits in Lobby → GameOver, everyone 0.
crewborg (seat 0) connected fine and waited. CONFIRMED by a 50-ep tournament-style rerun at low
concurrency: dead-game 76%→0%, connect_timeout→0%, crewborg played 46/47. So the "regression" was
a CONCURRENCY artifact of 400 simultaneous episodes starving opponent pod connects — NOT v106 code.
LESSON: pace xreqs (≤~100-200 concurrent); a spike in all-zero/"stuck" episodes = platform connect
contention — check the connect_timeout array across ALL seats before blaming the policy.

### v106 vote_timeout: dead-mute path FIXED (0), but a rarer alive-seat timeout (~9%) remains
Evidence: matched A/B v106 had 0/172 vote_timeout (v105 8.6%) — the dead-mute-caused timeouts are
gone. But the 50-ep field run showed 4/47 (9%) timeouts with dead_mute_events=0 AND safety_skips=0
— crewborg ALIVE and un-muted still missed a vote in one meeting (likely LLM-latency/belief-clock
edge on the deciding call). SEPARATE, older mechanism the v106 fix didn't target; small n / tougher
random field may inflate it. Open: quantify vs a matched v105 field run before deciding it needs a fix.
UPDATE: 100-ep field run confirmed 6/81 (7%) — consistent with the 50-ep 9%, so the alive-seat
timeout is REAL (~7-9%), not small-sample noise. Still separate from the (fixed) dead-mute path.

### Concurrency ceiling confirmed: 100-ep single request = 0% dead-game; 400 simultaneous = 76%
Evidence: v106 tournament-style, ONE 100-ep request: dead-game 0/81, connect_timeout 0/81, LLM
decision 73%, crew win 29%, imposter win 56% — all healthy. vs the 4×100=400-at-once A/B that hit
76% dead-game. So a single request (≤100 concurrent) is safe; the multi-request-fired-together
pattern is what starves opponent connects. For matched A/Bs, fire arms as SEPARATE 100-ep requests
PACED (drain one before firing the next), not all at once.

### v106 SUBMITTED but stuck in `qualifying` limbo ~10h — commissioner never ran a qualifier round for it
Evidence: submitted crewborg:v106 to Crewrift Prime 2026-07-09 (`sub_cc707442…`, membership
`lpm_d02abdf8…`). ~10h later: status=`qualifying`, substatus=null (NO crash/DQ), `division_id=null`.
Episode-search proof: v106 has 0 `tag.source=tournament` episodes (only 350 experience-request = my
own runs); v100 champion has 2684 tournament episodes. The commissioner IS healthy (tournament
episodes minutes-fresh, 10:20 next day). So the league simply never scheduled v106 into a
qualifier/tournament round — a PLATFORM/commissioner placement issue, NOT a crewborg fault (no crash,
policy sound). NB the skill's `monitor` also has a bug: it terminates on the pre-existing champion's
'competing' status, and its membership lookup used limit=50 (v106 sits past 50) — use a targeted
poller by pv-id with limit>=200. Qualification-progress signal = count of `tag.source=tournament`
episodes for the pv (0 = never played), not just membership.status.
