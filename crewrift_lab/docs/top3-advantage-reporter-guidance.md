# Guidance: making the top-3 advantage reporter find *skill*, not *outcome echoes*

Audience: the coding agent building/improving the reporter that compares the top-3
players per role (crew, imposter) against the rest of the field using a round's
event warehouse, to surface statistically differentiating stats.

Author context: this comes from the crewrift optimization lab
(`personal_labs_crewrift/crewrift_lab/`), which has run dozens of experiments and
A/Bs on this exact game and accumulated hard-won analysis discipline in
`crewrift_lab/best_practices.md`. The specific failure you're seeing — "the best
imposters are alive for the least time" — is a known and general disease with a
name, a mechanical test, and several fixes. All of them below.

## 1. Name the disease: outcome contamination

The reporter ranks players by an outcome (score/wins), then searches for stats
that separate the two groups. Any stat that is **causally downstream of the
outcome** will separate the groups *by construction*, and it will usually
separate them with the strongest p-values in the whole report, because it is
partly the same variable. Examples in Crewrift:

- **Time alive (imposter)** — good imposters end games fast, so they're "alive"
  less. This is the win, restated.
- **Game length** and anything scaled by it: total ticks in any state, total
  distance walked, total meetings attended, total chat messages.
- **Tasks completed (crew, raw total)** — winners' games run to task completion;
  losers' games get truncated by imposter wins. Total task count partly measures
  *whether you won*, not *how well you tasked*.
- **Kill count (imposter, raw)** — capped structurally by cooldown and
  body-meeting resets (this is a multiply-confirmed lab finding; ≥6 refuted
  experiments tried to move it). Raw kill differences are mostly game-length and
  noise.
- **Deaths / survival (crew)** — partly opponent-controlled, partly length.

A p-value cannot save you here. These stats are *genuinely* statistically
different between the groups; the statistics are fine. The problem is that the
finding is **tautological** — it can't inform anyone how to play better, which
is the entire point of the report.

## 2. The mechanical test every candidate stat must pass

Before a stat is allowed into the "advantages" section, apply this test:

> **Stratify by outcome and re-test.** Compare top-3 vs rest **within wins only**
> and **within losses only** (separately). A real skill difference survives in
> both strata. An outcome echo vanishes — it only "differentiated" because the
> top-3 win more.

This is cheap (two extra group-bys), fully mechanical, and it kills the
"alive least" class of finding automatically. Report the stratified effect, not
the pooled one. If a stat differentiates pooled but not within either stratum,
it goes to a clearly-labeled "outcome correlates (not actionable)" appendix or
is dropped.

Two cheaper screens to run first (to prune before the stratified test):

- **Length screen:** compute `|corr(stat, episode_length_ticks)|` across the
  *rest* population (not the top-3). Above ~0.5, the stat is presumptively a
  length proxy — either re-normalize it (see §3) or demote it.
- **Counterfactual question (for humans/design, not code):** *"Could a player
  deliberately act to change this stat, other than by winning?"* An imposter
  cannot choose to be alive less. They *can* choose to stay in line-of-sight of
  crew through kill cooldown. The first is an echo; the second is a lever.

## 3. Normalize by opportunity, not by game

Per-game totals are almost always wrong; per-tick rates are better; **per
opportunity** is what you actually want. The interesting question is never "how
much of X did they do" but "**given the chance to do X, how often / how fast /
how well did they do it**." Concretely for Crewrift, prefer:

| Instead of (contaminated) | Report (opportunity-conditioned) |
| --- | --- |
| kills per game | kill conversion: kills ÷ isolated-proximity windows while kill-ready (`isolation_interval` × kill-cooldown state) |
| time alive | time-to-first-kill from first kill-ready isolated contact; contact retention through cooldown (`player_visible_interval` continuity post-kill) |
| tasks completed | task completions ÷ task attempts (`task_attempt` outcome ratio); median task-attempt duration; time-to-first-task-start |
| votes for imposters | vote precision: correct-target votes ÷ votes cast (and suss precision via `chat_suss.target_is_imposter`) |
| bodies reported | report delay: ticks from `body_visible_interval` start to the report; passed-body-without-reporting rate |
| meetings survived | ejection avoidance *given accused*: survived votes ÷ meetings where ≥1 suss targeted them |

Additional normalization rules the lab learned the hard way (all in
`best_practices.md`, cited here because they bite reporters specifically):

- **Per-seat normalization.** If a policy holds more roster seats, its totals
  scale with seats, not skill. Always rate per seat-game.
- **Exclude meeting/voting ticks from every idle / latency / movement / gap
  denominator.** Meetings freeze the sim for everyone; including them dilutes
  and distorts all time-based rates.
- **Drop disconnect games at the game level.** A `-100` score means
  disconnect/crash (an ops failure), *not* ejection. One crashed seat poisons
  the whole game's comparative stats — drop the game, not the seat.
- **Never merge roles.** Crew and imposter are different games; every stat is
  computed and compared within-role only (you're already doing this — keep it).

## 4. Prefer segments where outcomes haven't diverged yet

Late-game data is maximally contaminated (the games that reach tick 3000 are a
biased subset). Early-game data is nearly a controlled experiment: every game
starts the same way. Add an **early-game panel** computed over a fixed window
that (almost) every episode fully contains — e.g. spawn → first meeting, or the
first kill-cooldown's worth of ticks:

- crew: time to first task start, first-task room choice, fraction of the
  window spent in `task_attempt`, distance-efficiency to first task
- imposter: time to first isolated contact, following/`chase_interval` rate,
  first-kill setup time, witness count at first kill

Differences here are behavioral by construction — no truncation, no
survivorship. This panel tends to produce the report's most actionable rows.

## 5. Fix the selection problem: don't rank and analyze on the same data

If "top-3" is defined by score **in the same round you then analyze**, you have
a winner's-curse machine: you selected the players whose stats broke favorably
*in this sample*, so stats correlated with score in this sample will
"differentiate" even for identical policies. Mitigations, in order of
preference:

1. **Rank out-of-sample:** define top-3 from *other* rounds (league standing,
   or the previous N rounds), then analyze this round's warehouse. This is the
   clean fix.
2. **Split-half within the round:** rank on odd episodes, compute differentials
   on even episodes.
3. If neither is possible, say so prominently in the report header — the reader
   must know the differentials are optimistically biased.

Also check group sizes: top-3 policies over one round can be a small-n group
(especially per role). Print n (episodes and seat-games) next to every stat and
refuse to report rows below a floor (~20 seat-games per group is a reasonable
default).

## 6. Statistical hygiene for a many-stats scan

You are scanning tens of stats × 2 roles — a multiple-comparisons factory.

- **Control the false-discovery rate** (Benjamini–Hochberg across the whole
  scan), or at minimum require both a p-threshold *and* an effect-size floor.
- **Report effect sizes, not just p** — Cliff's delta or rank-biserial fits
  these non-normal, truncated distributions. Rank findings by effect size, not
  p-value (with warehouse-scale n, trivial differences reach significance).
- **Run a rank-based test alongside the mean-based test** (Mann–Whitney next to
  Welch); disagreement means outliers/heavy tails — inspect before reporting.
- **Cluster by episode.** Multiple seats from one episode (and all pairwise
  events within it) are not independent samples. At minimum, aggregate to
  per-seat-game values first and test on those; never test on raw event rows.
- **Team-outcome stats carry a composition confound that per-seat
  normalization does not remove** — a crew seat's win rate reflects its 3–4
  teammates. Prefer individual-contribution stats (task throughput, vote
  precision); if you show team stats, label the confound.

## 7. Structure the report as an argument, not a leaderboard of p-values

The reader is an optimizer deciding what to change in a policy. For each
reported advantage, emit:

1. **The behavioral claim** in plain language ("top imposters keep the last
   victim's neighbors in view through kill cooldown"), not the column name.
2. **The opportunity-normalized stat** with both groups' values, effect size,
   n per group, and the outcome-stratified check result (§2) — showing it
   survived is what makes the row credible.
3. **A lever sentence:** what a policy would concretely do differently. If you
   can't write this sentence, the stat is probably an echo — demote it.

Order sections by role, and within role by effect size among stats that passed
§2. Keep the "outcome correlates" appendix (time alive, game length, raw
totals) — it's useful context — but visually and verbally separated so it can
never be mistaken for an advantage.

## 8. Crewrift-specific priors to encode (from refuted/confirmed lab experiments)

These tell you where differentiating signal is *likely* to be real, so the
reporter can prioritize stats near the known levers:

- **The whole game is a parity race.** Ghosts keep tasking, so crew never lose
  task capacity by dying; imposters' only resource is removing voters (kills +
  ejections) before tasks finish, and every crew mis-ejection is a free parity
  step for imposters. Express crew advantages in *task throughput per
  crew-tick* and *vote precision*; express imposter advantages in *contact
  maintenance*, *kill→win conversion*, and *meeting play* — not kill volume.
- **Kill volume is capped** (cooldown + body-meeting resets). Confirmed levers
  instead: keeping/regaining sight of crew through post-kill cooldown, and
  meeting behavior after kills (a parity-push vote strategy was worth +14.4pp
  win with kills flat). Conditioning win rate on kill count exposes the
  conversion gap.
- **Crew vote precision beats participation** — mis-votes are parity gifts
  (measured 2.2× more crew than imposters ejected league-wide). Suss accuracy
  (`chat_suss`) and vote-target correctness are high-value differentiators.
- **Ejection has no score penalty; the cleanest imposter-ejection signal is
  "imposter ended the game dead"** (imposters can't be killed, only ejected).

## 9. Minimal acceptance checklist

Before shipping a report version, verify:

- [ ] "Time alive," game length, and raw per-game totals appear **only** in the
      outcome-correlates appendix, never as advantages.
- [ ] Every advantage row shows: opportunity-normalized value per group, effect
      size, n per group, and passed the win/loss-stratified re-test.
- [ ] FDR control (or p + effect-size floor) applied across the full scan.
- [ ] Disconnect (`-100`) games dropped at game level; meeting ticks excluded
      from time-based denominators; per-seat normalization everywhere.
- [ ] Top-3 defined out-of-sample, or the report header flags the in-sample
      selection bias.
- [ ] Each advantage carries a one-sentence lever a policy could act on.

The one-line summary of all of the above: **stop asking "what is different
about winners' games" and ask "given the same opportunities, what do the top
players *do* differently" — and prove each answer isn't the outcome restated by
re-testing it inside wins and inside losses separately.**

## Appendix — sim/replay facts (verified against the crewrift source)

Answers to the reporter's data-availability questions, verified against
`tools/expand_replay.nim` at ref `34a97a3` (the lab's working helper binary,
`crewrift_lab/tools/bin/expand_replay`) and `src/crewrift/sim.nim`.

1. **Ballots exist.** `vote_cast` is emitted per voter per meeting: `player` =
   voter slot, `value.target_slot`/`target_label` or `value.target: "skip"`.
   If `events/key=vote_cast/` is missing from a warehouse build, the build used
   a stale helper — it's not a schema gap (the key exists even at d9f6b30).
   There is no explicit "ejected" event; derive the ejected slot by plurality
   tally of the meeting's `vote_cast` rows (max votes, no tie, ≥1 vote), or via
   fact 3.
2. **Body reports are attributed.** `vote_called_body`: `player` = reporter
   slot, `ts` = report tick, `value` has `body_owner_slot` + `room`.
   Report delay = that tick minus the start of the reporter's
   `body_visible_interval` for the victim. `vote_called_button` covers button
   meetings.
3. **Death cause is derivable.** A kill emits `kill` (killer = `player`,
   `value.victim_slot`) and suppresses the victim's `died` row. An ejection
   emits a bare `died` with no kill/body event. Rule: `kill` ⇒ killed; `died`
   without a matching `kill` ⇒ ejected. Shortcut: an imposter can never be
   killed, so imposter-dead-at-game-end ⇒ ejected, no vote data needed.
4. **`chat_suss` is a warehouse extension, not a replay fact.** It only exists
   after `crewrift-event-warehouse suss --out <warehouse>` runs (LLM labelling,
   needs AWS creds); it writes `events/key=chat_suss` with `is_suss`,
   `suss_target_slot/role/policy`, `target_is_imposter`.
5. **Phases:** `Lobby, Playing, Voting, VoteResult, GameOver, RoleReveal,
   GameInfo, MeetingCall` (emitted verbatim). Only `Playing` is action time —
   exclude everything else from time denominators. Meetings are ~1272 ticks and
   teleport everyone home; body/unknown meetings reset imposter kill cooldowns
   (button meetings only if configured).
6. **Disconnect:** `results.json` score `== -100` is the canonical
   disconnect/crash marker (never ejection — ejection has no score signal).
   Drop the whole game, not the seat. The helper also emits
   `disconnected`/`reconnected` and `player_state.connected` as corroboration.
7. **Do not reconstruct visibility from coordinates — occlusion is real.** The
   helper's `player_visible_interval`/`body_visible_interval` use the sim's
   rendered view + shadow mask (`visibility_basis: "rendered_view"`), i.e.
   canonical line-of-sight. Build contact-maintenance stats on those intervals
   joined against `kill` ticks and the kill-cooldown config in
   `episode_metadata`, never on raw distance (which sees through walls).
8. **Out-of-sample ranking sources:** (a) division leaderboard via the coworld
   API (`/v2/divisions/{id}/leaderboard`) — standing over many prior rounds;
   (b) prior-round per-policy win rates — `fetch_round.py` pulls any round,
   and warehouse `build` accepts multiple `--input` rounds, so rank on rounds
   N-1…N-k and analyze round N.
