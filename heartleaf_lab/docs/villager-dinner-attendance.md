# How the starter villager decides which dinner to attend

A dive into `talking_villager` — the core policy behind the deployed opponents
(`chatty_villager`, `friendly_villager`, `shy_villager`, `fatherly_villager` are
thin wrappers that just pass a different "soul" prompt). Source:
`coworld-heartleaf/players/talking_villager/talking_villager.nim` (+ `decisions.nim`),
read at master `c0dc3df`. All line numbers are from that file.

## Two facts that drive how we recruit them (verified in source, 2026-07-07)

1. **A host stands OUTSIDE its own door, visible — not inside.** `gatherAtHouseGoal`
   ("keep the bot **visible outside** one house") targets `desiredHouseGatherPoint =
   (house.x + w/2 + slot_offset, house.y + h + 4)` — a spot just **below the door on the
   main map**. So the occupancy heatmap's pre-dinner clusters are villagers standing at
   their doors advertising, reachable by chat. (They only step *inside* at the enter/dinner
   phase.) Earlier notes that said "gone inside to prep" were wrong.

2. **Accepting an invite is NOT time-gated; only *sending* one is.** `enforceTimePolicy`
   blocks a villager's own `say_to_person` **host-invite** before 4 PM (`InviteStartMinutes`),
   but there is **no time gate on accepting**: `inferSocialCommitment` (heard attendance
   phrase → commit to that house) has **zero minute checks**, and nothing blocks
   `go_to_party` early. So **a villager can commit to OUR invite before 4 PM** — via its LLM
   hearing our line and replying "I'll come". CAVEAT: the *deterministic* accept path
   (`bestVisiblePartyHouse` → `go_to_party`) is effectively gated early by `acceptsPartyCrowd`
   (before 4 PM it wants a visible crowd of 2–4; after 4 PM/`LatePartySearchMinutes` it
   accepts anyone). And a villager keeps *gathering* until its gardens are exhausted or 5 PM
   (`shouldGather`), so pre-4 PM it's out in the gardens, not idle.
   **Implication:** inviting in the gardens *before 4 PM* can work — but it relies on the
   villager's **LLM** hearing us and choosing to accept (ungated), not on the deterministic
   crowd path (gated). Whether that fires in practice needs an empirical test, and note the
   LLM may be absent in league pods (then only the crowd-gated path exists → early invites
   land weakly). Measure before committing to an early-invite strategy.

## TL;DR

**The LLM proposes; deterministic guardrails dispose.** Each frame the villager may
kick off an async LLM call that returns one of 9 actions (incl. `go_to_party`).
But that suggestion is run through a four-stage pipeline that infers commitments
from chat, enforces a hard time schedule, and **locks the bot onto a committed
party house** — and the whole thing has a **fully deterministic fallback** that
plays competently with no LLM at all. The actual "which party" choice is a
**crowd-following heuristic**: go to the visible house with the **most people**
(nearest as tiebreak), commit to it, and honor that commitment unless you arrive
and find yourself alone.

## The day's schedule (everything keys off the clock)

`bot.minutes` is clock-minutes; the game day runs 8 AM → 10 PM (`common.nim`).
The strategic thresholds:

| Constant | Value | Meaning |
|---|---|---|
| `DayStartMinutes` | 8:00 AM | gather from here |
| `HostPrepMinutes` | 3:00 PM | if you have lots of food, start prepping to host |
| `InviteStartMinutes` / `LatePartySearchMinutes` | 4:00 PM | invites allowed; start actively seeking a party |
| `HouseEnterMinutes` | 5:00 PM | stop gathering; commit to a house |
| `DinnerMinutes` | 6:00 PM | dinner window — force attend a party |
| `PartyLeaveMinutes` | 8:00 PM | party is over |
| `DayEndMinutes` | 10:00 PM | go home |

Food bands that modulate behavior: `LowHostFood=2`, `MediumHostFood=6`,
`HighFoodForInvites=6`, `StrongHostFood=12`.

## The decision pipeline — `applyDecision` (2334)

Every stored decision (LLM's, or the deterministic fallback) passes through:

1. **`inferSocialCommitment` (1948)** — read a commitment out of *chat*. If the
   message is a host invite ("come to my place") → commit to hosting your own
   house. If it's an attendance message (`isAttendanceMessage`, 1934: "I'll come",
   "count me in", "see you", "coming to", …) and names/implies a house → commit to
   attending that house. A mentioned house name or the target person's house fills
   in `houseIndex`.
2. **`enforceTimePolicy` (2206)** — the clock overrides the LLM:
   - before 4 PM: block invites; keep gathering (too early),
   - ≥ 5 PM + still "keep gathering" → switch to prep (find a party / stand at own house),
   - ≥ 6 PM (dinner): **force `go_to_party`** unless already going to a party or home,
   - ≥ 10 PM: go home.
3. **`enforceCommitment` (2298)** — if `committedPartyHouse` is set, **force
   `go_to_party` to that house**, overriding whatever the LLM said — *unless* the
   bot is alone there (`commitmentHasCompany`, 1997, is false → drop the commitment
   and re-seek), with narrow exceptions for a committed host chatting/standing at
   their own house.
4. **Commitment update** — if the final action is `go_to_party` with a house, set
   `committedPartyHouse`. If it's a host-invite at your own home, set
   `hostCommitted`.

So the LLM can *nominate* a house or person, but time + commitment + crowd rules
dominate the outcome.

## "Which party" — `bestVisiblePartyHouse` (1716) + scoring

This is the workhorse for choosing a party. It scans all houses and keeps the
best-scoring one that is: **not your own home**, **owner currently present**
(`houseOwnerPresent`), and passing the crowd gate (`acceptsPartyCrowd`). Score
(`visiblePartyScore`, 1709):

```
score = crowd * 10_000  -  distance² / 16   (+2_000 if it's already your partyHouse)
```

**Crowd dominates by 10,000×; distance is only a tiebreak.** → *Go where the
people are; among comparable crowds, pick the closest.* A small stickiness bonus
keeps you from thrashing between houses.

### The crowd bar drops as dinner nears — `requiredPartyCrowd` (1650) / `acceptsPartyCrowd` (1670)

Early in the day the bot wants a *big* crowd before joining (so it doesn't waste
the day at a dud party); the bar falls as the deadline approaches:

| Time left to 5 PM | Crowd required |
|---|---|
| > 3 h | 4 |
| > 1.5 h | 3 |
| > 30 min | 2 |
| ≤ 30 min | 1 |
| after 4 PM (`LatePartySearch`) | 1 (accept anything) |

Food shifts it ±1 (low food → join smaller parties; lots of food → hold out for
bigger ones, because you'd rather host). Below the required crowd there's a
*probabilistic* accept whose odds rise as time runs out.

## Host vs. attend — `shouldHostOwnHouse` (1627)

Whether to run your own party instead of attending someone's:

- A guest already showed up at your house → **commit to hosting** (`hostCommitted`).
- You have `≥ StrongHostFood` (12) → host (you have enough to make it worth it).
- Otherwise wait a **host-patience window** (`hostWaitDuration`, scaled by food:
  more food → wait longer, up to 90 min) — host until then, else give up.
- Past 4 PM with no guest and not already committed → stop trying to host, go
  attend someone else's party.

So **food-rich villagers host; food-poor ones become guests.** (Reminder: only
the host scores, `= totalFood × guests` — so a poor villager attending a rich
host's party gives *the host* points, not itself. Guests get 0. See
[`replay-tools.md`] scoring note / `heartleaf.nim:2565`.)

## Commitment lifecycle

1. **Seek** (before commit): `dinnerGatherGoal` / `partyHouseIndex` pick a target —
   host own house, else best visible party, else *scout* houses in a rotating
   sweep (`scoutingHouseIndex`, 1735) to discover crowds.
2. **Commit**: once `committedPartyHouse` is set (via LLM `go_to_party`, inferred
   chat attendance, or a time-policy fallback), `enforceCommitment` **locks** the
   bot to that house every subsequent frame.
3. **Honor or abandon**: the commitment holds *while there's company*. If the bot
   reaches the house and `visibleOtherPlayerCount == 0`, `commitmentHasCompany`
   returns false → the commitment is cleared and it re-seeks. This prevents
   everyone stranding at an empty house.

## Chat's role (coordination, not the core choice)

Chat is how villagers *signal and read* commitments, layered on the LLM's
`say_to_person`. `maybeSendDecisionChat` (2661) holds a prepared line and only
emits it when the target is actually near (`visiblePlayerNear`) — the slow LLM
prepares *what/whom* ahead; a cheap per-frame proximity check fires it. Incoming
chat is scanned (`scanHeardChats`) and an attendance/invite phrase updates
commitments through `inferSocialCommitment`. (More on chat range/coordination in
[`chat-and-llm-coordination.md`].)

## Execution — turning "attend house H" into being counted at dinner

`decisionGoal` → for `LlmGoToParty` (2496): on the main map, `enterHouseGoal(H)`
walks to the door and **goes inside** (onto that house's home map); once inside
the right house, `firstDinerGoal` positions as a diner. Being inside the host's
home map is exactly what the scorer counts (`homeVisitors`: `mapIndex == host's
home map`). Pre-dinner (before `HouseEnterMinutes`) guests **gather outside** the
door (`gatherAtHouseGoal`, spaced by `DoorGatherSlots`) so the crowd is visible to
others — which is what *draws more guests* via the crowd-following rule above.

## The deterministic fallback — `fallbackDecision` (2260)

When the LLM is unavailable/invalid the bot still plays a competent game, purely
by clock + food + commitment:

```
committed & has company     → go to committed party
≥ 10 PM                      → go home
≥ 6 PM  (dinner)             → go to best-visible / fallback party
≥ 5 PM  (house-enter)        → prep: find a party, or stand at own house
≥ 3 PM & food ≥ 6            → stand at own house (prep to host)
still worth gathering        → keep gathering
else                         → go to best-visible party (commit)
```

This is the important part for us: **the whole attend/host strategy works with no
LLM.** The LLM mainly adds richer chat and person-targeting; the *structure* is
deterministic.

## Takeaways for Cady

- **Which party = most people, nearest.** A crowd-following heuristic
  (`crowd×10000 − dist`) with a bar that relaxes toward dinner is the whole game
  of choosing where to attend. We can replicate this deterministically — no LLM
  required to be competitive at attendance.
- **Commit, then honor-unless-alone.** The stickiness (commit to a house, only
  bail if it's empty) is what avoids the failure mode of everyone milling between
  doors and nobody reaching a quorum by dinner.
- **Host if food-rich, attend if food-poor**, gated on the clock (host-patience
  window; hard pivot at 4 PM). Since only hosts score, our *own* scoring path is
  hosting with a real crowd — but understanding attendance tells us how to **draw
  that crowd** (be a visible, early, committed presence; the bar to join us drops
  as dinner nears).
- **The timeline is the skeleton**: gather → 4 PM seek/invite → 5 PM commit/enter
  → 6 PM dinner → 8 PM leave. Cady's current gather-only loop stops at a 5 PM
  cutoff but has no attend/host phase; this doc is the blueprint for adding one
  once nav/actions are rock solid.
