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

## Voting code map (filling in — see investigation)

- `modes/attend_meeting.py` — the Voting-phase Mode. Deterministic path (LLM off) =
  chat opener then `_fallback_vote_target = top_suspect(belief) or VOTE_SKIP`; **always
  resolves to SKIP** ⇒ `top_suspect` never returns a target.
- `strategy/suspicion.py` — `top_suspect` / `believed_imposters` (the belief that *should*
  drive votes; investigate why it never fires a confident target).
- `action.py` `_resolve_vote` — the ballot-cursor actuator (sound now; 0 timeouts).
- *No role-specific meeting logic yet* — imposter and crewmate vote identically (confirm).
