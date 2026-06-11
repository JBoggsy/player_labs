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

## Current objective — MAKE CREWBORG VOTE

In league play (LLM-off deterministic path) crewborg **always skips meetings** — **0
player-votes across 42 eval episodes, in *both* roles**. It is the **only** player in the
field that never votes; every stronger player votes players out. The suspicion machinery
exists (`strategy/suspicion.py` → `believed_imposters` / `top_suspect`) but never produces
a vote. **Wire it into real player-votes.** Cross-cutting: helps the **crewmate** (vote
imposters out to win) *and* the **imposter** (deflect / push wrong ejections).

Active policy: **v19** (champion, `358ec5fb`). **v20** (ground-truth tick + kill-CD 500)
sits on `main`, not built/uploaded — fold the voting change in, or sequence after.

## The data that motivates this — manual role-RR eval (42 eps vs rotated top-7, 2026-06-10)

(Opponents pinned + rotated through roles so each is tested in both — de-confounds the
earlier `top_n` run. Episodes in `/tmp/rr_eval/`.)

- **v19 IMPOSTER (21):** win **52%**, kills **1.52** (only ever 1–2, never 3+). Kills
  predict wins: 1 kill → 40%, 2 kills → 64%.
- **v19 CREWMATE (21):** win **38%**, all-8 tasks **18/21** — *best task completion in the
  field*, yet 2nd-worst crew win. Tasks don't win; the meeting/social layer does.
- **v19 VOTES: 0 player-votes, ~99 skips, 0 timeouts** (both roles) → **always skips**.
  (The old vote-timeout actuator bug is gone — 0 timeouts — it reliably casts; the cast is
  just always "skip".)
- **Field comparison** (each player in both roles, ~9 imp / ~33 crew eps):
  - Strongest crewmate **truecrew v14** (55% win); strongest imposter **truecrew v14**
    (100% win) / **crewborg-optimizer-what** (best killer **2.56** @ 78% — a *tuned
    crewborg fork*, so the architecture has real kill headroom).
  - **Every player stronger than v19 votes players out, in both roles. v19 never does.**
  - Imposter **kill lever**: strong imps get 1.9–2.6 kills vs v19's 1.52.
- **Two levers:** (A) **MAKE IT VOTE** ← this direction (cross-cutting, attributable,
  machinery exists); (B) imposter kills (v20's kill-CD 500 is a first nudge).

## Working lens — the score-anomaly filter

Scoring (`docs/crewrift-gameplay.md` §6): win +100 · task +1 (×8) · kill +10 ·
vote-timeout −10. "Clean success": crew **8** (all tasks, lost) / **108** (won); imposter
**20/30** (lost, 2–3 kills) / **120/130/140** (won). Join scores to crewborg by
`policy_version_id`, never by slot. Round episodes are queryable cheaply:
`coworld episodes --round <id> --policy crewborg --json`.

## Tooling/state already in place (use these for this work)

- **Tracing**: per-tick traces/metrics upload as an **uncapped artifact zip** (default
  `jsonl@artifact`); pull with `coworld-episode-artifacts`. The per-tick `decision_snapshot`
  has a `voting` section (`cursor_slot`/`cursor_on_skip`/`candidates`/`vote_confirmed`) and
  meeting events (`meeting_vote_selected`, `vote_cast`) — use these to **see** vote decisions.
- **Ground-truth tick** threads through perception/belief/all tracing (v20). Offline nav-bake
  fixed the spawn freeze. A/B with the `crewrift-ab` skill.

## Status — voting rule + suspicion refactor LANDED (not yet committed/built)

Implemented this session (all 290 crewborg tests pass, ruff clean; on `main`, uncommitted):

1. **Suspicion refactor — one probability, no `confirmed_imposters` set.** Witnessed
   kills/vents are now `kill`/`vent_use` **point events on the perpetrator's event log**
   (`_log_witnessed` in `suspicion.py`), mapped to `WITNESSED_LOG_LR` by `_evidence_log_lr`.
   `witnessed_imposters(belief)` derives the caught set for tracing. `_recompute` iterates
   `belief.roster` only. Consumers updated: `events.py`, `strategy/meeting/context.py`.
2. **New signal — being tailed (`tailing_self`).** `event_log.py` logs a player sustained
   within `TAIL_SELF_RADIUS_SQ=64²` of *us* (target_color None = me). `_tailing_self_log_lr`
   is a **logistic in duration** (`MAX=ln40`, midpoint 30t, steepness 0.2): 15t→P≈0.32,
   30t→0.72, 50t→0.94 (over the flee bar). Strong, needs no death.
3. **Vote rule (A) — clear leading suspect.** `top_suspect` now fires on near-certainty
   (`P ≥ VOTE_PROBABILITY=0.8`) **or** a clear lead (`P ≥ VOTE_LEAD_MIN_P=0.5` *and* ahead
   of runner-up by `VOTE_LEAD_MARGIN=0.2`); a flat field → skip. (Was: absolute 0.8 only ⇒
   never fired.)
4. **Accusation chat + no default opener.** Removed `MEETING_CHAT="no read, skipping"`.
   Deterministic path now **accuses then votes** the suspect (`build_accusation` in
   `strategy/meeting/accusation.py` → `"<color> sus: <reasons>"`, reasons ranked by each
   cue's log-LR, capped at `MAX_REASONS=3`) and stays **silent + skips** a flat field.
   Chat coupled to vote (accuse exactly whom we vote). Imposter = silent+skip (empty
   suspicion) — deflection is part B.
5. **Accuse mode (renamed Flee) + tailing recalibration.** Tailing now saturates at a
   *moderate* **P ≈ 0.72** (`TAIL_SELF_LOG_LR_MAX = ln 6.5`, was ln 40 / 0.94) — below
   the flee/near-certain bars. New: when **actively tailed** by a suspect over
   `ACCUSE_THRESHOLD=0.6` (`active_tail_suspect`, ~34 t of live tail), the selector
   drops tasks → **Accuse mode** (`modes/accuse.py`): walk to the emergency button and
   `call_meeting` (new intent; actuator `_resolve_call_meeting` mirrors report). The
   opened meeting accuses+votes the tail via the path above. **Replaces Flee entirely**
   (no more run-away; `flee_from` intent + `FleeMode` removed). The button is **one-shot
   per game** (`buttonCalls=1`): the selector tracks `_button_call_spent` (set when
   inside the button rect) and falls back to tasks after, resetting on a new game
   (`Lobby`/`RoleReveal`). `believed_imposters` (P≥0.9) is now belief-state only (seeds
   the vote), gates no reactive mode. Trigger is **only** active tailing (per James), per
   the AskUserQuestion answers.

**Remaining for this direction:**
- **Carve-out dropped** (per James): the "chat anyway when *we* called the meeting" idea — gone, not doing it.
- **Part B:** imposter deflection (never vote a teammate; push a crewmate ejection; bluff chat).
- **Not committed, do not push** (James's standing instruction this session). Fold into
  v20 (tick + kill-CD) and A/B vs v19 before any league push.

## Voting / accuse code map

- `strategy/suspicion.py` — `top_suspect` (clear-leading-suspect), `active_tail_suspect`
  (Accuse trigger), `witnessed_imposters`, `_evidence_log_lr`, `_tailing_self_log_lr`.
- `modes/attend_meeting.py` `_decide_deterministic` — accuse+vote / silent+skip.
- `modes/accuse.py` — `AccuseMode` → `call_meeting` (go to button).
- `strategy/rule_based.py` — selector: Accuse trigger + sticky commit + button-spent tracking.
- `strategy/meeting/accusation.py` — `build_accusation` (the `<color> sus: <reasons>` line).
- `action.py` `_resolve_call_meeting` (button press), `_resolve_vote` (ballot cursor).
