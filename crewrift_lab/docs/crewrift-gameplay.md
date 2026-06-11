# Crewrift: the game

A comprehensive, **gameplay-perspective** guide to Crewrift — the rules, roles,
flow, mechanics, scoring, and strategy. This is the lab's self-contained game
reference: read it to understand Crewrift *as a game* so you can reason about how a
player should behave, set strategic direction, and judge play quality. It is
deliberately **not** about the wire protocol or implementation.

- For **what a player must do over the websocket** (Sprite-v1 I/O, the scene
  vocabulary), see [`crewrift-player.md`](crewrift-player.md).
- For **building a player image**, see [`designs/building_players.md`](designs/building_players.md).
- For **reading a finished game** (replays/logs), see [`crewrift-replays.md`](crewrift-replays.md).

> **Sourcing & validity.** Rules and parameters here are taken from the game source
> (`Metta-AI/coworld-crewrift`: `src/crewrift/sim.nim`, `README.md`) and the
> `notsus` reference bot's strategy notes, **validated against crewrift `d9f6b30`
> (v0.1.40)**. Concrete numbers are *current* values and **version-dependent** — a
> game bump can change them; re-check `sim.nim` if precision matters. **Rules**
> (what the game enforces) are marked as such; **strategy** (how to play well) is
> guidance, not enforced.

---

## 1. The premise

Crewrift is a **social-deduction** game in the *Among Us* lineage: a crew of players
share a 2-D map. Most are **crewmates** with a list of tasks to finish; a hidden few
are **imposters** trying to kill the crew without being caught. Nobody is told who
the imposters are (imposters know each other; crewmates know no one). Play alternates
between a **real-time action phase** (moving, doing tasks, killing, hiding) and
**meetings** (discussion + a vote to eject a suspect). It is a game of **hidden
roles, asymmetric information, and persuasion** as much as movement.

The two sides have fundamentally different goals, action sets, and information — so
**a crewmate policy and an imposter policy are effectively two different problems**
(this is why lab evaluation always decomposes by role).

---

## 2. Setup & roles *(rules)*

- **Players:** 8–16 per game (`MinPlayers=8`, `MaxPlayers=16`); the default lobby is
  **8**. Players connect, wait until enough have joined, then the game starts after a
  short countdown (`StartWaitTicks` = 5 s).
- **Imposters:** **2 by default** at 8 players, auto-scaled with lobby size:
  `ratioImposterCount = (N − 3) // 2` for `N ≥ 5` (8→2, 10→3, 12→4, 14→5, 16→6),
  capped at `N − 1`. Everyone else is a crewmate.
- **Identity is color.** Each slot is one of 16 fixed colors (red, orange, yellow,
  light blue, pink, lime, blue, pale blue, gray, white, dark brown, brown, dark teal,
  green, dark navy, black). Players are referred to by **color**, not name/slot.
- **Role reveal** (`RoleRevealTicks` = 5 s) at game start tells you your role:
  - **As a crewmate**, you see *all* players arrayed — **including the imposters,
    undifferentiated** (you can't tell who's who yet).
  - **As an imposter**, you are shown **your fellow imposters** (the team), and you
    gain the imposter abilities (kill, vents). You must *remember* your teammates'
    colors — the reveal is brief.
- **Everyone starts at the emergency button** at the bottom of the map.

### Forcing roles in evaluations

By default roles are assigned randomly each episode. To **fix** who is crew vs. imposter
(e.g. to measure your policy purely as an imposter), an experience request sets
`game_config_overrides.slots` — the authoritative shape, straight from the game's config
schema (`Metta-AI/coworld-crewrift`: `coworld_manifest.json` → `config_schema.slots`):

- `slots` is an **array of objects**, one per slot — **not** an array of role strings.
- Each object: `{"role": "crew"|"imposter", "color"?: <one of the 16 colors above>, "token"?: <str>}`.
  Only `role` matters for role control; `color`/`token` are optional (auto-assigned).
- The default roster is **8 slots** (6 crew + 2 imposter). Roles attach to **seats**:
  your policy gets the role of whichever slot you pin its roster participant to
  (via the request's `roster[].slot`; a round-robin participant visits every open
  seat's role). Supply the **full** array — the override replaces the whole `slots` key.

```json
"game_config_overrides": {"slots": [
  {"role": "imposter"}, {"role": "crew"}, {"role": "crew"}, {"role": "crew"},
  {"role": "crew"}, {"role": "crew"}, {"role": "crew"}, {"role": "imposter"}
]}
```

The mechanics of putting this in a request (and a local schema check that catches a
wrong shape before POST) are in the **`coworld-experience-requests`** skill.

---

## 3. Win & loss conditions *(rules)*

Checked continuously (`checkWinCondition`, `sim.nim`):

- **Crewmates win if EITHER:**
  1. **All tasks are completed** (every crewmate's task list done — `allTasksDone`), or
  2. **All imposters are eliminated** (voted out / dead — `aliveImposters == 0`).
- **Imposters win if** they reach **parity**: `aliveImposters ≥ aliveCrewmates`
  (enough crew killed/ejected that imposters are no longer outnumbered).
- **Hard time cap:** a game cannot exceed `MaxTicks` ≈ 10 000 ticks (**~7 minutes**
  at 24 Hz). (Crew benefit from the clock only insofar as finishing tasks wins;
  imposters are racing it — see strategy.)

So the crew has **two win paths** (tasks *or* deduction) and the imposters have
**one** (kill enough, fast enough, without getting voted out).

---

## 4. Game flow & phases *(rules)*

The game moves through these phases (the player can detect the current one from the
on-screen interstitial text + UI; see [`crewrift-player.md`](crewrift-player.md) §6):

| Phase | What's happening | Duration |
| --- | --- | --- |
| **Lobby** | Waiting for enough players; then a countdown | until full + `StartWaitTicks` (5 s) |
| **RoleReveal** | You're shown your role (+ teammates if imposter) | `RoleRevealTicks` (5 s) |
| **Playing** | The real-time core: move, tasks, kills, hiding | until a meeting or a win |
| **Voting** | A meeting: discuss (chat) + cast a vote | `VoteTimerTicks` (**10 s** — short!) |
| **VoteResult** | Who (if anyone) was ejected | `VoteResultTicks` (3 s) |
| **GameOver** | Win/loss shown; connections close | `GameOverTicks` (15 s) |

**Playing ⇄ Voting** alternates: any body report or emergency-button press
interrupts Playing with a meeting, after which (if no win) play resumes. A player
processes the stream at **24 ticks/second** (`TargetFps`).

---

## 5. Core mechanics *(rules)*

### Tasks (crew's job)

- Each crewmate has **8 tasks** (`TasksPerPlayer`). A **radar** on screen points
  roughly toward your next task (guesses can be wrong, especially for far/colinear
  tasks).
- To complete one: navigate **onto the task tile** (around walls), then **stand
  still and hold the action button** for `TaskCompleteTicks` (**3 s**). **Any
  movement resets it** — you must restart.
- **Reward:** **+1** per task completed (`TaskReward`). Completing *all* tasks (across
  the crew) is a crew win.
- Dead crew (ghosts) can still finish tasks — they still count toward the task win
  and score.

### Movement & the map

- The map is a 2-D ship of named **rooms** connected by corridors, with **walls**
  (a *walkability map* defines passable cells).
- **Movement has momentum.** Input is "hold a d-pad direction"; the avatar
  accelerates while held and decelerates after release (it is **not** grid-step
  movement). Smooth navigation needs a controller that accounts for this (the notsus
  README recommends A\* pathing + a small PID-style motion controller).

### Killing (imposter ability)

- An imposter's kill is gated by a **cooldown** (`KillCooldownTicks` — sim default
  **500 ticks ≈ 21 s**; the repo's local `config.json` lowers it to 100 for testing,
  so the live value is config-dependent). A HUD bar fills as it recharges.
- When ready, the imposter must be **within `KillRange` = 20 world px** of a victim
  and press the action button. The victim dies and leaves a **body** at that spot.
- **Reward:** **+10** per crewmate killed (`KillReward`) — the single biggest
  per-action payout, and it accrues **even in a loss**.
- **Vents:** imposters can enter **vents** to traverse the map quickly and disappear
  from sight — the primary tool for repositioning after a kill.

### Bodies & reporting

- A body stays on the floor until reported. **Either side** can report it (standing
  on it + action) — an imposter reporting their own kill is a **"self-report."**
- Reporting **starts a meeting** (Voting phase). So does the emergency button.

### Meetings & voting

- **Triggers:** a body report, **or** the emergency button.
- **Emergency button:** each player may press it **once per game** (`ButtonCalls=1`);
  it starts a meeting from anywhere.
- **The meeting is short — `VoteTimerTicks` = 10 s.** In it players **chat** and
  **vote**:
  - **Chat** is text (capped: 32 chars/line, up to ~10 lines; `MessageCooldownTicks`
    ≈ 4 s between messages, so realistically ~2 messages per player per meeting).
  - **Vote:** select a player (or **skip**) with the d-pad cursor and confirm. **A
    cast vote cannot be changed.** The majority outcome ejects that player (or no one
    on skip).
- **Penalty:** **−10** for **not voting and not skipping** (`VoteTimeoutPenalty`) —
  abstaining is punished; *skip* is a free, valid vote.

### Death, ghosts & disconnects

- A killed or ejected player becomes a **ghost**: still on the map, can still **do
  tasks** (for score + the task win), but **cannot vote** or interact with the living.
- **Disconnect/timeout is heavily penalized:** a player that fails to connect or
  drops mid-game eats **−100** (`ConnectionTimeoutPenalty`; `Connect/DisconnectTimeoutTicks`
  = 30 s). Operationally: *don't crash* — a flaky player is worse than a weak one.

---

## 6. Scoring & incentives *(rules + how they shape play)*

Per-player score (`sim.nim` reward constants; the README lists the first five):

| Event | Points | Pushes you to… |
| --- | ---: | --- |
| **Win the game** | **+100** | …treat winning as paramount — it dwarfs everything else. |
| **Complete a task** | **+1** | …keep doing tasks; steady points even in a loss (crew). |
| **Kill a crewmate** | **+10** | …kill whenever safely possible (imposter); high value. |
| **Not voting (nor skipping)** | **−10** | …**always cast some vote**, even skip. |
| **Standing still w/ tasks left** | **−1** | …don't idle; the penalty recurs ~every 20 s you're stationary with unfinished tasks and no active task (`StuckPenalty`, `StuckPenaltyTicks`=20 s). |
| **Disconnect / timeout** | **−100** | …stay connected and exit cleanly; never crash. |

**Reading the incentives:**

- **Winning is everything** (+100). Don't trade the game to farm small rewards.
- **For crew**, tasks are the reliable accumulator (+1 each, and a win path); idling
  bleeds points; abstaining in a meeting is a hard −10.
- **For imposters**, kills are gold (+10 each) and pay out *even when you lose* — so
  an imposter who can't win should still hunt. But blending in (faking tasks, moving)
  matters because survival-to-parity is the win.
- **−100 disconnect** dominates the whole table — robustness beats cleverness.

---

## 7. Crewmate strategy *(guidance)*

The crew's job: finish tasks **and/or** correctly identify imposters, without
throwing away crewmates on bad votes.

- **Do tasks efficiently.** Pick a task and commit (momentum makes oscillating
  between two near tasks costly); plan a route (a TSP-ish ordering beats greedy when
  tasks cluster). Completing tasks is both points and a win path that **denies the
  imposters time**.
- **Stick together.** Moving as a group means a kill has **witnesses** (you instantly
  learn an imposter's color), and gives you **mutual alibis** for the vote. The
  tension: grouping is safer but slower on tasks, and the clock matters.
- **Watch and remember.** Track who was where and with whom — that's your evidence at
  the next meeting. Useful tells:
  - Someone **next to a body who didn't report** it.
  - Someone seen **venting** (near-proof of imposter).
  - **Task-counter check:** a player "doing a task" who leaves without the global task
    counter changing **faked it** — they can't actually complete tasks, i.e. imposter.
  - **Spatial contradiction:** a claimed location that conflicts with where they were
    seen (implies venting / lying).
- **Vote carefully — but always vote.** Ejecting a crewmate is a large setback (one
  fewer task-doer and toward imposter parity), so **be nearly certain** before voting
  a color; otherwise **skip** (never abstain → −10). Use room names to anchor reports
  ("body in Hydroponics").
- **Talk.** Silence reads as suspicious and wastes the only deduction channel. In a
  10-second meeting, be concise and concrete ("I was with red in MedBay").

---

## 8. Imposter strategy *(guidance)*

The imposters' job: cut the crew down to **parity** before tasks finish or they're
voted out — while looking like crew.

- **Blend in.** Do everything a crewmate appears to do: travel to task tiles and
  **fake** them (stand as if working), move with purpose, talk in meetings. Erratic
  motion or idling near tasks you never complete is a tell.
- **Race the clock.** With a long kill cooldown (~21 s) and a ~7-minute cap, **kills
  must come quickly** — wait too long and the crew finishes tasks and wins. Treat
  cooldown-ready as "find a kill now."
- **Kill clean.** Isolate a single crewmate (ideally one who's wandered off), kill
  **without witnesses** (mind `KillRange`), then **leave immediately** — vent or take
  corridors **away** from the body so you're not the one standing near it.
- **Manage the body.** A fresh body is a liability; getting far away before it's found
  is key. **Self-reporting** (kill, then report it yourself) clears the body and lets
  you play the confused discoverer — but doing it *every* time is a pattern, so use it
  sparingly and randomly.
- **Coordinate with your co-imposter.** Vote together (each ejected crewmate helps
  both of you), back each other's alibis, and avoid implicating your teammate. Know
  who they are (from the role reveal) and don't kill toward your own disadvantage.
- **Work the meeting.** Two approaches: **passive** (let crew suspicion build, then
  add fuel) or **active** (accuse a specific crewmate early and have your partner
  echo it). The goal is to get *crewmates* ejected and sow enough doubt that you're
  never the target.

---

## 9. Social deduction & voting *(guidance, both sides)*

Meetings are where the game is often decided, under a **brutal 10-second clock**:

- **For crew:** the meeting is for **information and coordination** — clear known-good
  players ("I watched green do a task"), surface concrete tells (body proximity,
  venting, fake tasks, contradictions), and converge a majority onto a real imposter.
  Caution dominates: a wrong ejection usually loses the game.
- **For imposters:** the meeting is for **manipulation** — deflect, cast doubt,
  manufacture or echo accusations against crew, and protect your partner. Voting out
  *anyone* crew is progress toward parity.
- **Universal:** **say something** (silence is suspicious and wastes the channel), be
  **specific** (vague claims don't move votes in 10 s), and **always cast a vote**
  (skip when unsure — abstaining is a guaranteed −10).
- **LLM-driven meetings** (suspectra's approach, and a notsus option) feed the
  collected evidence to a model to produce the accusation/defense/vote. The hard part
  noted by the game authors: LLMs tend to **cosplay** the game (say dramatic things)
  rather than **play** it (make the locally-correct deductive move), so prompts must
  push toward the actual game objective, and the model must be fast enough for the
  10-second window.

---

## 10. Meta-strategies & emergent play *(guidance)*

Higher-order tactics that emerge from the rules (largely from the notsus README's
"Metta Strategies" — treat as community strategy, not enforced mechanics):

- **Emergency-button cooldown reset.** The notsus README notes crew can **disrupt
  imposters by calling meetings** (each call is asserted to reset the imposter kill
  cooldown). If the crew coordinates button-presses, imposters must blend by doing the
  same — but each player only gets **one** press, so this is a finite, spendable
  resource, not a loop. *(Asserted by the notsus README; verify against `sim.nim` if
  you build a policy around it.)*
- **Task-counter as a lie detector.** Because everyone sees the **global task
  counter**, a player who "does a task" without the counter advancing is exposed as
  faking → imposter. Crew can deliberately watch one player complete a task to clear
  or condemn them.
- **Forced-group / one-task-at-a-time protocols.** The crew can agree to move as one
  body and watch each member complete a task in turn; whoever can't is the imposter.
  Powerful but slow — and the task/time clock punishes disorganization.
- **The coordination problem.** These group metas require ~8 independently-authored
  bots (different teams, even different languages) to **converge on the same protocol**
  with no shared channel beyond in-game chat. A policy that can *signal and follow* a
  meta has an edge; one that can't gets exploited by one that can.

---

## 11. Quick-reference parameters

Current values (`sim.nim` @ crewrift `d9f6b30`, 24 ticks/s; **version-dependent**):

| Parameter | Value | Note |
| --- | --- | --- |
| Frame rate | **24 Hz** | `TargetFps`; one logical frame/tick |
| Players | **8–16** (default 8) | `MinPlayers` / `MaxPlayers` |
| Imposters | **2** @ 8 players | `(N−3)//2`, scales with lobby |
| Tasks per crewmate | **8** | `TasksPerPlayer` |
| Task completion | **3 s** still | `TaskCompleteTicks`=72 |
| Kill cooldown | **~21 s** | `KillCooldownTicks`=500 (local cfg: 100) |
| Kill range | **20 world px** | `KillRange` |
| Emergency presses | **1 / player** | `ButtonCalls` |
| Meeting / vote timer | **10 s** | `VoteTimerTicks`=240 |
| Vote result screen | **3 s** | `VoteResultTicks`=72 |
| Chat msg cooldown | **~4 s** | `MessageCooldownTicks`=100 |
| Idle penalty window | **20 s** | `StuckPenaltyTicks` |
| Disconnect timeout | **30 s** | `Connect/DisconnectTimeoutTicks` |
| Max game length | **~7 min** | `MaxTicks`=10 000 |
| Reward: win / task / kill | **+100 / +1 / +10** | |
| Penalty: no-vote / idle / disconnect | **−10 / −1 / −100** | |

---

## See also

- [`crewrift-player.md`](crewrift-player.md) — the player's wire contract (how the
  game above is *observed and acted on* over Sprite-v1).
- [`designs/building_players.md`](designs/building_players.md) — building a player image.
- [`crewrift-replays.md`](crewrift-replays.md) — reading a finished game's replay/logs.
- `crewrift/notsus/README.md` (vendored) — the reference bot's extensive strategy notes.
- Authoritative game source: `Metta-AI/coworld-crewrift`: `src/crewrift/sim.nim`
  and the game `README.md` (rules, scoring). Re-check these if anything here is stale.
</content>
