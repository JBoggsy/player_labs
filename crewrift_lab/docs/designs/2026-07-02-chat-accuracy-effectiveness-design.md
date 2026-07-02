# Chat accuracy & effectiveness study (field-wide)

**Status:** approved, implementation starting 2026-07-02.
**Owner track:** new investigation, adjacent to but distinct from the open
"suspicion evidence renovation (voting)" lever in `WORKING_CONTEXT.md`.

## Problem

Two questions about Crewrift Prime chat, asked field-wide (every player/policy
in the current league, not just crewborg):

1. **Accuracy (crew only).** When a crew member accuses someone in chat, how
   often is the accused actually the imposter? Broken down by player/policy.
2. **Effectiveness (crew + imposter).** Does an accusation actually move the
   room — does the accused get voted / ejected in that meeting? And does
   accusing (accurately or not) correlate with winning? Broken down by
   player/policy and role.

This is a new field-wide angle. It reuses infrastructure built for a narrower,
crewborg-centric purpose (`suspicion_lab/`) and for per-episode dissection
(`crewrift-event-warehouse`'s `suss` job), but neither answers this question
as posed today.

## Goals

- Per-player/policy crew accusation accuracy vs. ground-truth imposter
  identity, on the current (2026-07-02) 11-entrant Prime field.
- Per-player/policy same-meeting effectiveness: P(accused is voted) and
  P(accused is ejected | an accusation named them that meeting), for crew and
  imposter accusers separately.
- Per-player/policy win-rate association with accusation volume/accuracy,
  **seat-holding-normalized** (raw win rate is confounded by roster seat
  share — a standing lesson in this lab).
- A quantified confidence bound on the accusation-target detector itself
  (see Detector validation below) — not just a bare headline number.
- A persisted, queryable dataset + an HTML report, left behind for follow-up.

## Non-goals

- Causal inference. No randomized intervention on who accuses whom; all
  results are observational/associational and will be labeled as such.
- Touching crewborg's runtime suspicion model, its fit weights, or its
  in-flight "runtime-feature train→serve gap" rework — read-only reuse of
  `replay_parse.py` and `features.py::chat_stances()` only.
- A live/recurring dashboard. One-shot analysis producing a static report.
- Changing crewborg's or any other policy's behavior.

## Data plan

- **Primary:** fresh experience request(s) totaling ~20 Prime rounds (~240
  episodes) against the current 11-entrant field (natural roster, not forced
  roles — we want real chat behavior, not staged matchups). Pulled via
  `coworld-experience-requests` → streamed via `coworld-episode-artifacts` →
  built via `crewrift-event-warehouse` (or the lighter `replay_parse.py` path
  directly — decide in the implementation plan; the warehouse's DuckDB output
  is only needed if the report wants ad-hoc SQL, otherwise the parsed `Game`
  objects are enough).
- **Cross-check:** the existing 692-episode verified suspicion_lab corpus
  (current-era policy versions v82/v84/v85/v87–90, already scraped and
  hash-verified) as a larger-n stability check on headline numbers — reported
  separately, labeled "historical" vs. "current field," never silently
  blended.
- Field snapshot metadata (round IDs, pull date, entrant list + versions) is
  recorded in the report — this lab's field turns over fast (new versions
  ship hourly for some entrants) and stats go stale within days.
- Verify the expander (`/tmp/expand-043` as of the last session) still
  hash-matches the live Prime build before trusting any parsed chat/votes —
  a recurring gotcha in this lab (button-meeting divergence, version drift).

## Extraction & linking pipeline

1. **Chat → accusation events.** Reuse `suspicion_lab/tools/features.py`'s
   `chat_stances()` directly (not the full `build_dataset.py` pipeline, which
   restricts to crew observers and prior-meetings-only — the wrong shape for
   this study). Emit one row per `StanceTriple`
   (episode, meeting_idx, speaker_slot, stance, target_slot) for **every**
   speaker regardless of role.
2. **Ground truth join.** Target's and speaker's actual role from
   `replay_parse.py`'s `Game.players` (`player_state`-derived, not the
   join-time `player_manifest` — a documented gotcha in suspicion_lab's
   README).
3. **Same-meeting vote/ejection join.** That same `Meeting`'s `votes`
   (`Vote.voter_slot`/`target_slot`) and `ejected_slot` — this is the
   "did the room actually act on it" signal, deliberately same-meeting
   (not the cumulative prior-meetings-only shape suspicion_lab uses).
4. **Win outcome join.** Per-episode `win` flag and seat, from
   `episode_players`/`results.json`, aggregated with seat-holding
   normalization (per-seat-game rates, not raw per-policy averages — the
   lesson that corrected the earlier "crewborg worst crew" artifact applies
   here too).
5. **Detector validation.** Sample ~150–300 chat lines stratified across
   policies; run the warehouse's existing LLM-based `suss` labeling job on
   that sample; compute agreement/precision between the regex detector's
   (stance, target) call and the LLM's. Report this prominently as a
   confidence bound on everything downstream — if agreement is low (e.g.
   <70%), the report says so explicitly rather than presenting headline
   accuracy numbers as trustworthy.

## Metrics

- **Crew accusation accuracy** per player/policy: accused-is-actual-imposter
  rate, with a binomial CI. Players who emit near-zero chat (e.g. notsus
  lineage per a prior finding) get an explicit N/A row, not a silently
  dropped or zeroed one.
- **Same-meeting effectiveness**, crew and imposter separately: P(target
  voted) and P(target ejected | accused that meeting) vs. the meeting's base
  rate (1/candidates), per player/policy.
- **Win-rate association**: per player/policy, (accusation volume,
  accusation accuracy) vs. seat-normalized win rate. Report both a
  cross-policy correlation and per-policy point estimates; explicitly framed
  as associational, not causal.

## Deliverable

- New directory `crewrift_lab/chat_effectiveness/` with extraction/join
  scripts and a `dataset/accusations.parquet` (or DuckDB) output, queryable
  for follow-up — matches this lab's existing pattern (suspicion_lab,
  event-warehouse).
- `build_report.py` producing a static HTML report (styled like
  `crewrift-survey`'s output): field-snapshot metadata, the detector
  validation number up front, the three metric tables/charts, and explicit
  "observational, not causal" framing near the win-rate section.

## Affected files

- New: `crewrift_lab/chat_effectiveness/` (extraction, joins, report).
- New: this design doc.
- Possibly: read-only import of `suspicion_lab/tools/{replay_parse,features}.py`
  (no edits expected; if `chat_stances()` needs a small signature change to be
  reusable standalone, that's a minimal, additive change — not a rewrite).
- No changes to crewborg runtime code or committed suspicion model weights.

## Validation

- Manually spot-check ~10 accusation rows against actual replay chat text and
  vote outcomes before trusting aggregate output.
- The detector-validation number (regex vs. LLM agreement) is itself a
  reported artifact, not just an internal check.
- Confirm expander/version match before trusting parsed data (see Data plan).

## Risks / open questions

- Regex stance/target detection may have real precision/recall gaps —
  mitigated by, and explicitly bounded by, the LLM-sample validation step.
- Some policies chat/vote near-zero (e.g. Andre/notsus lineage per a prior
  finding) — their rows are N/A, handled explicitly.
- Field composition and versions shift quickly; report is a dated snapshot.
- Whether to build on the full `crewrift-event-warehouse` (DuckDB/Parquet) or
  work directly off `replay_parse.py`'s in-memory `Game` objects is left to
  the implementation plan — the warehouse adds SQL queryability but its `suss`
  job is only needed for the detector-validation sample, not the main
  extraction.

## Isolation

All implementation happens in a new git worktree
(`.claude/worktrees/chat-accuracy-effectiveness`, branch
`worktree-chat-accuracy-effectiveness`), separate from any in-flight crewborg
work on main.
