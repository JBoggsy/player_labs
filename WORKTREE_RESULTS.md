# Worktree results — `worktree-imposter-kill-to-win`

> **Temporary handoff doc for the merging agent.** Read this to understand everything
> that happened in this worktree before integrating it into `main`. Safe to delete
> after merge — the durable knowledge also lives in the code, `design.md`,
> `docs/designs/imposter-parity-meeting.md`, `version_log.md`, and `TODO.md`.

## TL;DR

Fan-out **Direction 4: imposter kill→WIN conversion**. crewborg gets imposter kills on
par with the best champions but *wins far fewer games on the same kills*. I located the
gap in the **meeting** (not the kill), shipped a focused two-part fix, and **A/B-validated
it: imposter win 43.7% → 58.1% (+14.4pp, p < 1e-9), kills flat**. The change is on this
branch in 4 commits; **not submitted to any league** (that's the human's gate).

**Merge intent:** the code is additive and low-risk. The real merge care is (a) preserving
the `_decide_imposter` path order and (b) union-merging the shared living docs against the
parallel `direction2-voting` / `direction3-emergency-meetings` branches.

---

## 1. The mission

Improve **crewborg** (a competitive Player-SDK agent for **Crewrift**, an Among-Us-style
hidden-role game). Direction 4's brief: crewborg's imposter **kills are competitive**
(~1.5/game, ≥2-kill ~50%) but its imposter **win rate lags** (~50% vs notsus ~100% /
Aaron ~91% in a champion tournament). The win is lost *somewhere after the kills* — find
where (ejection vs parity-timing vs meeting/social), with evidence, and fix it.

Prior constraint honored: an A/B earlier this project confirmed that making crewborg **kill
more aggressively** raised its ejection rate with no win gain (reverted) — so the lever is
**not** "kill more/earlier." I did not re-tread that.

## 2. Diagnosis — *where* the gap is (the meeting), with evidence

Tooling: the event warehouse at `/tmp/sweep_wh` (170-ep sweep), queried via DuckDB. A
subagent ran the heavy decomposition; I verified the code-level causes directly.

**Conditioning win on the SAME kill count** separates conversion from kill-rate:

| | @1 kill | @2 kills |
|---|---|---|
| crewborg | 0.39 | 0.63 |
| notsus | **1.00** | **1.00** |
| Aaron (crewborg-aaln) | 0.64 | 0.78 |

→ The win leaks *after* the kills.

**Loss decomposition** (n=39 crewborg imposter losses; `died`=ejection validated: zero
overlap with kill victims, 93% were the plurality vote target):
- **64% — an imposter got voted out** (ejection).
- The rest **stall at 3 crew / 2 imposters — exactly one removal from parity — and never
  close it.** (~3 kills leaves 3c/2i; the win needs a 4th kill *or* a crew ejection.)

**How the top imposters differ:** notsus manufactures the parity-closing crew ejection *in
the meeting* (~1.10 crew-ejections/win, 8/10 games, vs crewborg ~0.4) and is **never ejected**
(0/29 vs crewborg 17–25%). Crew vote a notsus imposter 10.9% of the time vs a crewborg
imposter **31.3%**.

**Two code-level causes, both confirmed from the warehouse:**
1. **Passive meeting play.** crewborg's deterministic imposter path acts only on a *real*
   suspect or an *existing* heat pile; otherwise it **skips** (vote skip-rate ~39% vs notsus
   5%). It never *manufactures* the parity-closing vote.
2. **Doesn't know its teammate.** crewborg votes the teammate **21–23%** of casts (champions
   0%) and **follows** the teammate **46%** of intervals (notsus 26%) — impossible if
   `teammate_colors` were populated. Root cause: teammate identity is a brittle **one-shot
   RoleReveal capture** (`types.py` ~L716), missable by a connect race or a one-frame blip.

## 3. The fix (two coupled changes)

### (a) Parity-closing manufactured vote
`strategy/meeting/imposter.py` — two new functions:
- `alive_imposter_count(belief)` → `1 + (alive known teammates)`. Conservatively returns 1
  when no live teammate is known, which self-gates (b) below.
- `parity_closing_vote_target(belief, chat_accusers=None)` → the non-teammate crewmate to
  manufacture a vote against, or `None`. Fires **only** when `alive_imposter_count >= 2`
  (known live teammate) **and** `crew_alive − alive_imp == 1` (one ejection wins). Ranks crew
  by a **shared deterministic key** (existing votes, then lowest slot) so both imposters pick
  the *same* target and their ballots stack into a plurality.

`modes/attend_meeting.py` — `_decide_imposter` gets a new **path 3** (`parity_push`),
inserted *between* bandwagon and skip: if `parity_closing_vote_target` returns a target,
fabricate an accusation (reusing `fabricate_accusation`) and vote it; else fall through to
the existing skip. Order is now: proactive → bandwagon → **parity_push** → skip.

**Why it's safe** (and not a re-tread of the reverted kill-aggression): the two gates mean
it fires only when the parity math + teammate exclusion are trustworthy (never votes our own
teammate when the reveal was missed) and only when a single ejection *wins the game* (so
exposure is bounded to that one meeting). It's *voting* aggression at the parity-closing
moment, not *killing* aggression.

### (b) Widened RoleReveal teammate latch
`types.py` (~L716) — latch role-reveal icon colors (object id range `9500+`, which the engine
renders nowhere else) into `teammate_colors` **on sight**, rather than gating on
`phase == "RoleReveal"` AND `"IMPS"` text parsed that exact frame. Fixes the *parse/timing*
miss. (Does **not** fix the *never-saw-the-reveal* connect-race miss — see follow-up TODO.)

### Tests (470 pass, 13 pre-existing skips)
- `tests/test_imposter_meeting.py` (+8): parity push fires at gap==1; gated off without a
  known live teammate; never targets a teammate; prefers the heated crewmate; deterministic
  cold-pick; the mode manufactures chat+vote instead of skipping; `alive_imposter_count`.
- `tests/test_belief.py` (+2): the widened latch fires without the `IMPS` text.

## 4. Validation — the A/B

**Design (a "blocked 1v1" sweep — the human's idea):** 6 pinned-champion blocks. Each block
= both imposter slots pinned to the **subject** version, all 6 crew slots pinned to **one**
champion (homogeneous crew kills mixed-field variance), 2 forced imposters via
`game_config_overrides.slots`. Candidate = `crewborg-paritypush:v1`; baseline = `crewborg-base`.
Fully-pinned roster ⇒ **no field-drift confound** (so arms didn't even need the same window).
Champions: notsus, crewborg-aaln, jordan-crewborg-aaln, crewborg-mv, forgeling-focusfire,
softmaxwell-crewborg. Two batches (20 + 60 eps/champion) → **80 eps/champion**, **n≈955 clean
imposter-slots/arm** (ops-failures dropped, symmetric 4 vs 7).

| metric | base | candidate | Δ |
|---|---|---|---|
| **imposter win** | 43.7% | **58.1%** | **+14.4pp, z=+6.3, p < 1e-9** |
| kills/slot | 1.48 | 1.43 | flat — *not* a kill effect |
| vote skip-rate | 26.3% | 23.6% | ↓ — mechanism firing |

Per champion (win base→cand): forgeling +46, jordan-aaln +17, crewborg-mv +15, notsus +13
(all individually significant), aaln +0, softmaxwell −5 (noise). **5/6 positive.**

**Trust checks I ran:** confirmed the candidate version actually seated (slots 0–1 =
`crewborg-paritypush`, not a default); verified roster/roles resolved correctly; re-pulled
with `--force` after arms completed (a mid-run pull had produced fake 10% candidate
"ops-failures" that inflated the delta to +20.8pp — corrected); split by batch (batch-1
+5.9pp p=0.20, batch-2 +17.2pp; per-batch differences within sampling noise, so the combined
estimate is not an artifact — batch-1 was simply an underpowered low draw).

**Honest caveats:** the win effect is *diluted* across all games (the push only fires in games
reaching a parity-closing meeting with a known teammate) → conditional effect is larger. The
candidate was uploaded **without** trace env, so I confirmed the mechanism *indirectly*
(skip-rate↓ + win↑ + kills-flat) rather than via a `meeting_decision path=parity_push` trace.

## 5. Commits & merge surface

Branch `worktree-imposter-kill-to-win`, 4 commits off `main`:
- `1178f31` — code + tests (the fix).
- `e910c83` — docs+lessons: validated result (design.md §7.2/§10.4, version_log, WORKING_CONTEXT, lessons).
- `9c797c7` — TODO.md: the two parked follow-ups.
- `83f980a` — durable merge-proof docs (the design note, meetings.md, final lesson number).

**Files changed vs `main` (12):**

| file | kind | notes |
|---|---|---|
| `crewrift_lab/crewrift/crewborg/strategy/meeting/imposter.py` | **code** | +2 new functions (no edits to existing) |
| `crewrift_lab/crewrift/crewborg/modes/attend_meeting.py` | **code** | +import, +path-3 block in `_decide_imposter` |
| `crewrift_lab/crewrift/crewborg/types.py` | **code** | RoleReveal latch widened (~L716) |
| `crewrift_lab/crewrift/crewborg/tests/test_imposter_meeting.py` | test | +8 tests + a fixture |
| `crewrift_lab/crewrift/crewborg/tests/test_belief.py` | test | +2 tests |
| `crewrift_lab/crewrift/crewborg/design.md` | doc | §7.2 mode row + §10.4 path 3/4 |
| `crewrift_lab/crewrift/crewborg/docs/meetings.md` | doc | imposter path 3 `parity_push` |
| `crewrift_lab/crewrift/crewborg/docs/designs/imposter-parity-meeting.md` | doc | **NEW** self-contained record |
| `crewrift_lab/crewrift/crewborg/version_log.md` | doc | `crewborg-paritypush:v1` row |
| `crewrift_lab/WORKING_CONTEXT.md` | doc | answered the kill→WIN OPEN THREAD |
| `crewrift_lab/TENTATIVE_LESSONS.md` | doc | diagnosis + A/B + process lessons |
| `TODO.md` | doc | 2 follow-ups |

## 6. Merge guidance (READ THIS)

Parallel sibling branches likely to collide: **`worktree-direction2-voting`** and
**`worktree-direction3-emergency-meetings`** (both touch meeting/voting). Expect conflicts.

**Code:**
- `strategy/meeting/imposter.py` — my additions are new functions appended; should merge
  clean unless another branch also appended there.
- `modes/attend_meeting.py` — **the contention point.** Preserve the path order
  **proactive → bandwagon → parity_push → skip**: the parity-push must stay *before* the
  deadline skip. If another branch adds its own path (e.g. self-defense / a different vote
  policy), keep all paths and order them so the parity-push still owns the "one-from-parity,
  flat field" case before skipping.
- `types.py` — the latch change is a 2-branch if/elif at the RoleReveal block; if another
  branch also touched teammate capture, keep the "latch on sight" behavior.

**Docs (take the UNION — none of my additions replace existing content):**
- `WORKING_CONTEXT.md`, `TENTATIVE_LESSONS.md`, `version_log.md`, `TODO.md` — additive entries.
- `design.md` §10.4 / `docs/meetings.md` — if they conflict, keep both branches' meeting paths;
  **`docs/designs/imposter-parity-meeting.md` is the authoritative reconstruction source** for
  the parity-push if anything is lost.

**Post-merge sanity:** `PYTHONPATH=crewrift_lab/crewrift uv run pytest
crewrift_lab/crewrift/crewborg/tests` (expect 470 passed). Confirm the path order via
`tests/test_imposter_meeting.py::test_imposter_parity_pushes_instead_of_skipping_one_removal_short`.

## 7. Lessons learned (also in TENTATIVE_LESSONS.md)

- **Locate an imposter kill→win gap by conditioning win on kill count** — it cleanly separates
  "gets kills" from "converts kills," and immediately showed the leak is post-kill.
- **A directional result on a *confirmed mechanism* is worth powering up, not discarding.**
  Batch-1 read +5.9pp (p=0.20). Rather than calling it null, I added episodes (hosted is free)
  → +14.4pp at p<1e-9. The mechanism (skip-rate↓) was already visible, which justified the spend.
- **Re-pull A/B artifacts with `--force` only AFTER the arms report complete.** Pulling mid-run
  grabbed partial/running episodes that looked like a 10% candidate ops-failure and inflated the
  delta to a fake +20.8pp. Always recompute on clean, complete, symmetric-n data.
- **Upload an A/B candidate WITH trace env** (`CREWBORG_TRACE_GROUPS`) for a behaviour-path
  change, so the new path's firing is directly observable (`meeting_decision path=parity_push`)
  instead of inferred.
- **Parallel fan-out agents clobber shared host state.** Three other agents were concurrently
  building the host-global `players-crewborg:dev` tag and uploading to the shared `--name
  crewborg`. I built to a unique tag (`players-crewborg:parity-push`) and uploaded under a unique
  name (`crewborg-paritypush`) to isolate; and moved episode data off the shared `/tmp/ab` (a
  sibling agent was writing episodes into the same path). The registry push was also slow/flaky
  under contention (~7 min, intermittent broken pipes) — patience + retry, don't kill prematurely.

## 8. Parked follow-ups (in `TODO.md`)

1. **Bulletproof teammate detection** — the widened latch doesn't help a connect-race that
   never sees the reveal; add reveal-independent inference (latch any color we *witness*
   killing/venting — definitional imposter, already in `suspicion.witnessed_imposters`), and
   measure the teammate-known rate with traces. Drive teammate-vote/follow rates to ~0.
2. **Stronger + more-frequent social deception** — add self-defense/counter-deflection when
   crewborg is the heat target (attacks the 64%-ejection axis), build crew suspicion earlier
   (alive-count-scaled voting à la notsus `socials.nim`/`votereader.nim`), richer
   fabricated-evidence variety, and lean on the meeting LLM. Validate with the same 1v1 A/B harness.

## 9. Artifacts & identifiers

- Policy: **`crewborg-paritypush:v1`** = `db8d8ee2-2a27-46ae-bef0-b49c2a7f0453` (image built from
  commit `1178f31`, deterministic / no Bedrock). Separate name on purpose (see lesson on clobber).
- Baseline: `crewborg-base` = `de4a5c81-755f-4696-a0f1-e05292539d92`.
- A/B episode artifacts were under `/tmp/ab/{base,cand}/<champion>/` (ephemeral; the *results*
  are captured here and in the design note). Warehouse: `/tmp/sweep_wh`.
- The canonical durable spec is `design.md` §10.4; the canonical durable *evidence + merge guide*
  is `crewrift/crewborg/docs/designs/imposter-parity-meeting.md`.
