# Crewrift tentative lessons — archived session buffer

**Session:** 2026-07-02, the chat-accuracy/effectiveness field study
(branch `worktree-chat-accuracy-effectiveness`, merged 2026-07-21). Routed here
at merge time — the live buffer had been rotated many times since this session.

---

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

## Chat TACTICS deep-dive: silence + one rigid "sus + vote" template beats crewborg's rich, hedged, directive-less analysis (2026-07-02)

Follow-up to the chat-effectiveness study: read/quantified the actual chat text (not just the
regex-classified accusation rows) for the top-3 (jordan-crewborg-aaln, crewborg-mv,
crewrift-prime-crewborg-aaln-hunter-relhalpha) and bottom-3 (crewborg, rowdaboat-notsus,
softmaxwell-crewborg) by same-meeting ejection conversion, across all 481 fresh-pull meetings where
one of them spoke (`/tmp/chat_eff_expanded` + `outcomes.parquet` slot→policy join; ad-hoc scripts,
not added to the durable pipeline).

### THE FINDING: the top-3 are silent 82-87% of meetings, and the ENTIRE non-silent vocabulary is one template: "saw COLOR, COLOR sus, vote COLOR"
Across 1,166 sampled messages from the 3 top performers there are exactly **2 distinct message
shapes, period**: `"no read, skipping"` (84.1%) or the single fixed template (15.9%) — zero
hedging, zero questions, zero defense, zero variation. All three use the byte-identical template
string, strongly implying shared chat-gen code (an "aaln"-lineage fork) rather than 3 independent
strategies — **n=1 unique strategy here, not n=3**, don't over-generalize the sample size.
Compare: crewborg has 83 distinct message shapes across 244 messages (never silent, 0% skip-rate),
rowdaboat-notsus has 340 distinct shapes across 415 (also never silent); both are far more varied
and evidence-rich (crewborg: 90.6% cite a witnessed-behavior claim; room/spatial detail in 42%).

### The explicit "vote X" directive rate is the single cleanest correlate of conversion
Substantive-message-only rates: jordan/crewborg-mv/relhalpha-hunter close **100%** of their
accusations with an explicit "vote COLOR" (same-meeting ejection 65/59/53%). rowdaboat-notsus
closes 20.5% (ejection 26%). softmaxwell-crewborg closes 38.2% (ejection 24%, but n=34 substantive
msgs, small). **crewborg closes 0.8%** — it labels suspicion ("X sus: they were tailing me" + a
composable justification clause) but essentially never tells the room what to DO with it (checked
for "eject/kick/remove/get out" alt-phrasing too: 0/244) — and converts only 18%. First-mover rate
(literally message index 0 in the meeting) shows the same split: aaln-lineage 30-36% when they
speak; crewborg and rowdaboat effectively 0% (crewborg NEVER speaks first in this sample).

### Persuasion vs. correctness — the top style converts WRONG accusations almost as well as right ones
Split same-meeting ejection by whether the accusation was actually correct: **jordan converts wrong
accusations 63.2% of the time vs. 65.9% for correct ones — almost no discrimination.**
crewborg-mv/relhalpha show more separation (72%/32%, 62%/39%) but still convert wrong calls at a
rate crewborg/rowdaboat never hit even when RIGHT (crewborg: correct 28.8% vs wrong 15.3%;
rowdaboat: correct 42.2% vs wrong 10.5% — a real accuracy-sensitive gap, but a much weaker overall
lever). **Read this as: the top style's "effectiveness" is substantially persuasion/anchoring power
(speak first, be terse, be unhedged, always name an action) — not superior detection.** crewborg's
detection is comparable-to-better in places (48% accuracy vs jordan's 70%, but wrong-call
ejection-rate discrimination is actually healthier); its bottleneck is entirely on the
close-the-loop side.

### Actionable, low-risk lever for crewborg (not yet built, not yet tested)
Two structural gaps, independent of suspicion-model quality: (1) append an explicit `vote <color>`
(or equivalent action verb) whenever chat already names a suspect — currently near-zero-cost
labeling with no call to action; (2) don't always wait to hear the room first — when suspicion is
already high pre-meeting, consider speaking early rather than only ever reacting. Both are meetings/
chat-generation changes, not suspicion-model changes — genuinely separable from the open "evidence
warming" suspicion lever. NOT yet designed, NOT yet A/B'd — this is read/pattern evidence, not a
verdict; the field-eval discipline (pre-registered A/B, deterministic-for-gameplay) still applies
before shipping anything derived from this.