# Imposter kill→WIN: close parity in the meeting (validated, +14.4pp)

**Status:** Implemented + A/B-validated on branch `worktree-imposter-kill-to-win`
(commits `1178f31` code/tests, `e910c83` docs). **Not submitted to any league.**
Uploaded as policy `crewborg-paritypush:v1` (`db8d8ee2-2a27-46ae-bef0-b49c2a7f0453`).

This is a **self-contained change record** so the improvement and its mechanism
survive the merge into `main` even if the shared living docs
(`WORKING_CONTEXT.md`, `TENTATIVE_LESSONS.md`, `version_log.md`) conflict with a
parallel branch. The canonical spec lives in [`../../design.md`](../../design.md)
§7.2 / §10.4; this doc is the *why + the evidence + the merge guide*.

---

## The problem it fixes

crewborg's imposter **kills are competitive** with the best champions (~1.5/game,
≥2-kill ~50%) but its imposter **win rate lagged badly** (~50% vs notsus ~100% /
Aaron ~91% in a champion tournament). **The win was lost *after* the kills.**

Located with the event warehouse (`/tmp/sweep_wh`, 170-ep sweep):

- **Conditioning win on the SAME kill count** isolates conversion from kill-rate:
  crewborg @1 kill wins **0.39** vs notsus **1.00**; @2 kills **0.63** vs **1.00**.
- **Loss decomposition** (n=39 crewborg imposter losses; `died`=ejection validated —
  zero overlap with kill victims, 93% were the plurality vote target):
  - **64% — an imposter got voted out** (ejection).
  - The rest **stall at 3 crew / 2 imposters — exactly one removal from parity —
    and never close it.** (~3 kills leaves 3c/2i; the win needs a 4th kill *or* a
    crew ejection.)
- **notsus closes that gap in the MEETING:** ~**1.10 crew-ejections/win** (8/10
  games) vs crewborg's ~0.4, and is **never ejected** (0/29 vs crewborg 17–25%).
  Crew vote a notsus imposter 10.9% of the time vs a crewborg imposter **31.3%**.

Two code-level causes, both confirmed from the warehouse:

1. **crewborg's deterministic imposter meeting path is passive.** It only acts on a
   *real* leading suspect or an *existing* heat pile; otherwise it **skips** (vote
   skip-rate ~39% vs notsus 5%). It never *manufactures* the parity-closing vote.
2. **crewborg often doesn't know its teammate.** It votes the teammate **21–23%** of
   casts (champions 0%) and **follows** the teammate **46%** of intervals (notsus
   26%) — impossible if `teammate_colors` were populated. Root cause: teammate
   identity is a brittle **one-shot RoleReveal capture**.

## The fix (two coupled changes)

1. **`parity_closing_vote_target`** (`strategy/meeting/imposter.py`), wired as path 3
   of `_decide_imposter` in `modes/attend_meeting.py` (after proactive-deflect and
   bandwagon, before skip): when the board is **exactly one removal from parity**
   (`crew_alive − imp_alive == 1`) **and** a **live teammate is known**
   (`alive_imposter_count(belief) >= 2`), *manufacture* a coordinated
   fabricated-accusation+vote onto the best non-teammate crewmate instead of
   skipping. Target rank is a **shared deterministic key** (existing votes, then
   lowest slot) so both imposters converge on the *same* crewmate and their ballots
   **stack into a plurality**.

   **Why it's safe** (and sidesteps the prior "aggression raises ejection" result —
   which was about *killing*, not voting): the two gates mean it fires **only** when
   the parity math + teammate exclusion are trustworthy (so it never votes our own
   teammate when the reveal was missed), and **only** when a single ejection *wins
   the game* (so exposure is bounded to that one meeting).

2. **Widened RoleReveal teammate latch** (`types.py`): latch role-reveal icon colors
   (id range `9500+`, which the engine renders nowhere else) into `teammate_colors`
   **on sight**, rather than gating on `phase == "RoleReveal"` AND `"IMPS"` parsed
   that exact frame — surviving a one-frame parse blip or an initial-connect race.
   (NOTE: this fixes the *parse/timing* miss, not the *never-saw-the-reveal* miss —
   see the teammate-detection TODO in the root `TODO.md`.)

Tests: `tests/test_imposter_meeting.py` (+8: push fires/gates/coordinates/excludes
teammate) and `tests/test_belief.py` (+2: widened latch). Full suite **470 passed**.

## The validation (A/B)

Design: 6 **pinned-champion 1v1 blocks** — both imposter slots = subject, all 6 crew
= one champion (homogeneous, kills mixed-field variance), 2 forced imposters, vs
`crewborg-base`. 80 eps/champion, fired in two matched batches; fully-pinned roster ⇒
**no field-drift confound**. Recomputed on **clean episodes** (ops-failures dropped,
symmetric 4 vs 7) at **n≈955 imposter-slots/arm**:

| metric | base | candidate | Δ |
|---|---|---|---|
| **imposter win** | 43.7% | **58.1%** | **+14.4pp, p < 1e-9** |
| kills/slot | 1.48 | 1.43 | flat — *not* a kill effect |
| vote skip-rate | 26.3% | 23.6% | ↓ — mechanism firing |

Per champion (win base→cand): forgeling +46, jordan-aaln +17, crewborg-mv +15,
notsus +13 (all individually significant), aaln +0, softmaxwell −5 (noise). **5/6
positive.** Batch-1 alone (n=240) was a more modest +5.9pp (p=0.20, underpowered);
the per-batch baseline/candidate differences are within sampling noise, so the
larger combined estimate is not an artifact.

**Caveats:** the win effect is *diluted* across all games (the push only fires in
games that reach a parity-closing meeting with a known teammate), so the conditional
effect is larger. The candidate was uploaded *without* trace env, so the mechanism
was confirmed indirectly (skip-rate↓) rather than via a `meeting_decision
path=parity_push` trace — enable `CREWBORG_TRACE_GROUPS` on the next build to log it.

## Follow-ups (parked in root `TODO.md`)

- **Bulletproof teammate detection** — the widened latch doesn't help a connect-race
  that never sees the reveal; add reveal-independent inference (latch any color we
  *witness* killing/venting — definitional imposter, already in
  `suspicion.witnessed_imposters`), and measure the teammate-known rate with traces.
- **Stronger + more-frequent social deception** — add self-defense/counter-deflection
  when crewborg is the heat target (attacks the 64%-ejection axis), build crew
  suspicion earlier (alive-count-scaled voting, à la notsus `socials.nim`), richer
  fabricated-evidence variety, and lean on the meeting LLM.

## Merge guide (for whoever integrates this into `main`)

**Code (keep as-is — additive):**
- `strategy/meeting/imposter.py` — adds `alive_imposter_count` + `parity_closing_vote_target` (new functions, no edits to existing ones).
- `modes/attend_meeting.py` — adds the import + path-3 block in `_decide_imposter` (inserted before the existing skip; existing paths unchanged).
- `types.py` — the RoleReveal latch (~L716) becomes "latch `reveal_player_colors` on sight, else fall back to the old `IMPS`-text branch".

**Likely conflicts with parallel meeting/voting branches** (`direction2-voting`,
`direction3-emergency-meetings`): `_decide_imposter` ordering in `attend_meeting.py`,
and the shared living docs. Resolution intent:
- Preserve the **path order**: proactive-deflect → bandwagon → **parity-push** → skip.
  The parity-push must stay *before* the deadline skip.
- Living docs (`WORKING_CONTEXT.md`, `TENTATIVE_LESSONS.md`, `version_log.md`,
  `TODO.md`): take the **union** of both sides' additions — none of my entries
  replace existing content.
- If `design.md` §10.4 conflicts, keep both branches' meeting paths; this doc is the
  authoritative description of the parity-push if reconstruction is needed.
