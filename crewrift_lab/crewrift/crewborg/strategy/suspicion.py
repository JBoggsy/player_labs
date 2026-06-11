"""Bayesian suspicion: posterior P(imposter) per player (design §10.1).

→ Canonical reference: ``docs/designs/suspicion.md`` — the living home for the
model, each evidence type's log-LR function (form + parameters + shape), the offline
fitting workflow, and the provenance log. Update that doc whenever a function or its
constants change.

Crewmate POV. For every other player we maintain `belief.suspicion[color]` = the
posterior **probability they are an imposter**, updated from a combinatorial prior
by the evidence we have observed. The score is a real probability, so thresholds
(e.g. the flee bar) are interpretable — no magic numbers.

**Prior.** With `P` players and `K` imposters, a crewmate knows the `K` imposters
are among the other `P − 1`; by symmetry each other player's marginal prior is
`K / (P − 1)`. `K` is derived from the player count via the game's auto formula
(`(P − 3) // 2`), overridable by `belief.imposter_count`.

**Update.** Work in log-odds: `logit(P) = logit(prior) + Σ_e logLR(e)` over observed
evidence `e`. `P = sigmoid(logit)`. The log-LR of each graded cue is a simple,
hand-written **function of the event's features** (`_*_log_lr` below), not a flat
constant — because the relationship isn't flat (a skilled imposter flees rather than
dwelling). The function forms and their constants are the **parameterization** (and
the learnable surface — there is no learning machinery yet).

**Evidence**, by type, contributes its most-suspicious instance (we aggregate with
`max` per type), so an unbounded event log can't inflate the posterior and there's
no double-counting; and because role is a fixed latent, evidence **persists** (no
time decay):

- Near-certain (`WITNESSED_LOG_LR` ⇒ P ≈ 1): detected from frame-to-frame transitions
  on the tape (§5.1) — *witnessed kill* (lone kill-range neighbour of a just-killed
  victim) and *witnessed vent* (emergence / submersion, line-of-sight via the `shadow`
  mask) — and recorded as `kill` / `vent_use` point events on the perpetrator's log, so
  every signal lives in one place (there is no separate "confirmed" set).
- Graded functions over the event log (§5.2): **vent dwell** (weak, ~flat past a
  pass-through), **body proximity** (log-LR *decreases* with dwell — brief is the
  only window on a fleeing killer), **follow-to-death** (log-LR *increases* with how
  long the shadowing lasted), and **being tailed** (`tailing_self`, a logistic in how
  long someone shadowed *us* — needs no death; saturates at a *moderate* P ≈ 0.72, a
  strong reason to call a meeting and accuse but not on its own near-certain).

`believed_imposters` (which gates Flee) is every alive player with `P ≥
FLEE_PROBABILITY`. Crewmate-only — an imposter knows the truth, a ghost doesn't flee.

v1 simplifications (documented for later): naive-Bayes independence between evidence
types; positive-evidence-only (the prior is the baseline — no exculpatory terms);
and a static `K / (P − 1)` prior without redistributing the imposter budget as
players are caught/die (a proper joint model is a refinement).
"""

from __future__ import annotations

import math

from crewrift.crewborg.action import KILL_RANGE_SQ
from crewrift.crewborg.strategy.occupancy import (
    neighbors_within,
    players_in_rect,
    rect_visible,
)
from crewrift.crewborg.types import Belief, PerceptionFrame, PlayerEvent, PlayerEventKind, PlayerRecord

# Each evidence type contributes a log-likelihood-ratio, log(P(e|imp)/P(e|crew)), to
# the posterior. Witnessed kill/vent are definitional near-certainties (a constant).
# The graded event-log cues use simple, hand-written **per-event functions** of the
# event's features (duration, distance) — `_*_log_lr` below — because the
# relationship is not flat: a skilled imposter *flees* rather than dwelling, so e.g.
# body-proximity is MORE suspicious when brief. The function form + its constants ARE
# the parameterization (no learning machinery yet); docs/designs/suspicion.md §3
# documents each shape and §6 how to (re)fit the constants from replays. Keep code
# and doc in sync, and log changes in the provenance table (§7).

# Near-certain catches (we saw it happen): an overwhelming log-LR ⇒ P ≈ 1.
WITNESSED_LOG_LR = math.log(1e6)

# vent dwell — weak: a real venter teleports (caught by the transition detector), so
# merely standing on a vent is a ~flat cue once it is more than a pass-through.
VENT_CROSS_TICKS = 3  # ≤ this many ticks on a vent tile is just crossing it ⇒ neutral
VENT_DWELL_LOG_LR = math.log(8.0)

# body proximity — DECREASING in dwell: brief presence is the only window on a
# fleeing killer; a long camp at a corpse is (innocent) reporter behaviour. Full at
# first sight, fading linearly to 0 by BODY_FADE_TICKS.
BODY_NEAR_DIST = 16  # world px — "right next to it", not passing by
BODY_NEAR_LOG_LR = math.log(3.0)
BODY_FADE_TICKS = 48  # the log-LR fades to 0 over ~2 s of lingering

# follow-to-death — INCREASING in dwell (saturating): sustained shadowing of a player
# who then died is stalking. Gated on the target now being dead and the follow ending
# near the death.
FOLLOW_FULL_TICKS = 48  # the ramp reaches full at ~2 s of sustained proximity
FOLLOW_DEATH_WINDOW_TICKS = 72  # the follow ended ~within 3 s of finding the body
FOLLOW_LOG_LR = math.log(6.0)

# being tailed (``tailing_self``) — live evidence: a player shadowing *us* over time is
# a likely imposter lining up its target, and (unlike third-party follow) it needs no
# death. A **logistic in duration**: a brief brush ⇒ ~nothing, the ramp leaves zero
# around ~15 ticks, crosses the midpoint at ~30 ticks, and **saturates around P ≈ 0.72**
# (deliberately *moderate*, not near-certain — being tailed is a strong reason to call a
# meeting and accuse, but lots of crew move together, so it must not on its own clear the
# flee/near-certain-vote bars). Saturated LR ≈ log(6.5) against the combinatorial prior.
TAIL_SELF_LOG_LR_MAX = math.log(6.5)
TAIL_SELF_MIDPOINT_TICKS = 30  # logistic centre (P ≈ 0.5 here at a typical prior)
TAIL_SELF_STEEPNESS = 0.2  # 50 ticks ⇒ ~0.98 of max; 15 ticks ⇒ ~0.05 of max
# Once an *active* tail pushes our suspicion of the tailer to this, we are "sketched
# out" enough to stop and call a meeting (Accuse mode, ~34 ticks of sustained tailing).
ACCUSE_THRESHOLD = 0.6
# A tailing_self interval counts as *active* (they're tailing us right now) if it was
# extended within this many ticks — robust to a brief occlusion mid-tail.
ACCUSE_TAIL_RECENCY_TICKS = 6

# Flee a player once P(imposter) reaches this — a real probability, so the bar is
# interpretable (only near-certainty triggers the reactive Flee).
FLEE_PROBABILITY = 0.9
# Vote a player out once P(imposter) reaches this on its own — near-certainty (a
# witnessed catch, a saturated tail) clears the bar regardless of the field. A touch
# below the (reactive) flee bar: a vote is a deliberate, one-shot meeting decision.
VOTE_PROBABILITY = 0.8
# A vote also fires on a *clear leading suspect* short of near-certainty: the top
# posterior is over VOTE_LEAD_MIN_P (real evidence — more likely than not an imposter)
# AND leads the runner-up by at least VOTE_LEAD_MARGIN (it stands out, not a flat field).
# This is the "vote on a clear leader, skip when the posterior is flat" rule — ejecting
# an innocent helps the imposters, so a flat or low field skips.
VOTE_LEAD_MIN_P = 0.5
VOTE_LEAD_MARGIN = 0.2
# Clamp the prior away from 0/1 so its log-odds stays finite.
PRIOR_MIN, PRIOR_MAX = 1e-3, 0.99

# Max distance a player can walk in one tick (MaxSpeed/MotionScale = 704/256 ≈ 2.75,
# rounded up): a player materialising inside a vent from beyond this vented.
VENT_WALK_MARGIN = 3


def update_suspicion(belief: Belief) -> None:
    """Recompute `suspicion` (posterior P(imp)) + `believed_imposters` each tick.

    Run after `update_belief`/`update_event_log` so the strategy snapshot is current.
    """

    if belief.self_role in ("imposter", "dead"):
        belief.suspicion = {}
        belief.believed_imposters = set()
        return
    _detect_witnessed_kill(belief)
    _detect_witnessed_vent(belief)
    _recompute(belief)


# --- prior ------------------------------------------------------------------


def _imposter_count(belief: Belief) -> int:
    if belief.imposter_count is not None:
        return belief.imposter_count
    total = belief.total_player_count
    return 0 if total < 5 else max(0, min((total - 3) // 2, total - 1))


def _prior_imposter_p(belief: Belief) -> float:
    n_others = max(1, belief.total_player_count - 1)
    return min(max(_imposter_count(belief) / n_others, PRIOR_MIN), PRIOR_MAX)


# --- tier 1: near-certain transitions → witnessed events on the perpetrator --


def _frame_pair(belief: Belief) -> tuple[PerceptionFrame, PerceptionFrame] | None:
    """The (previous, current) tape frames, only if they are consecutive ticks."""

    frames = belief.recent_frames
    if len(frames) < 2:
        return None
    prev, curr = frames[-2], frames[-1]
    return (prev, curr) if curr.tick == prev.tick + 1 else None


def _log_witnessed(belief: Belief, color: str, kind: PlayerEventKind, *, target_color: str | None = None) -> None:
    """Record a witnessed catch as a point event on the perpetrator's log (latched).

    The detectors fire on a one-tick transition, so this is a point event
    (start == end == now). It carries no LR itself; ``_evidence_log_lr`` maps its
    presence to ``WITNESSED_LOG_LR``. A ``kill`` is deduped per victim so a persisting
    body can't re-log; ``vent_use`` is a genuine repeat each time someone vents.
    """

    # A witnessed catch is the strongest signal we have; never drop it on an ordering
    # gap. In production ``update_belief`` has already rostered any player visible in the
    # tape (and the perpetrator was, a frame ago), so this is a safety net, not the path.
    record = belief.roster.get(color)
    if record is None:
        record = PlayerRecord(color=color)
        belief.roster[color] = record
    if kind == "kill" and any(e.kind == "kill" and e.target_color == target_color for e in record.events):
        return
    record.events.append(
        PlayerEvent(kind=kind, start_tick=belief.last_tick, end_tick=belief.last_tick, target_color=target_color)
    )


def _detect_witnessed_kill(belief: Belief) -> None:
    pair = _frame_pair(belief)
    if pair is None:
        return
    prev, curr = pair
    for victim_color in curr.bodies:
        victim_pos = prev.players.get(victim_color)  # was this body's owner alive a frame ago?
        if victim_pos is None:
            continue
        killers = [
            color
            for color in neighbors_within(prev, victim_pos, KILL_RANGE_SQ, exclude=victim_color)
            if color not in belief.teammate_colors
        ]
        if len(killers) == 1:  # a single, unambiguous neighbour ⇒ the killer
            _log_witnessed(belief, killers[0], "kill", target_color=victim_color)


def _detect_witnessed_vent(belief: Belief) -> None:
    pair = _frame_pair(belief)
    if pair is None or belief.map is None:
        return
    prev, curr = pair
    venters: set[str] = set()
    for vent in belief.map.vents:
        x, y, w, h = vent.x, vent.y, vent.w, vent.h
        # (a) Emergence: vent + walk-margin in line of sight and clear last frame, occupied now.
        watched_clear = rect_visible(prev, x, y, w, h, margin=VENT_WALK_MARGIN) and not players_in_rect(
            prev, x, y, w, h, margin=VENT_WALK_MARGIN
        )
        if watched_clear:
            venters.update(players_in_rect(curr, x, y, w, h))
        # (b) Submersion: a player was in the vent last frame; vent still in sight, player gone.
        if rect_visible(curr, x, y, w, h):
            for color in players_in_rect(prev, x, y, w, h):
                if color not in curr.players:
                    venters.add(color)
    for color in venters:
        _log_witnessed(belief, color, "vent_use")


# --- tier 2: graded evidence from the event log -----------------------------


# --- per-event log-LR functions ---------------------------------------------
# Each maps one event's features → its log-likelihood-ratio contribution (0.0 =
# neutral). Simple closed forms; the constants above are the parameters.


def _vent_dwell_log_lr(event: PlayerEvent) -> float:
    return VENT_DWELL_LOG_LR if event.duration_ticks > VENT_CROSS_TICKS else 0.0


def _body_proximity_log_lr(event: PlayerEvent) -> float:
    if event.min_dist is None or event.min_dist > BODY_NEAR_DIST:
        return 0.0
    fade = max(0.0, 1.0 - event.duration_ticks / BODY_FADE_TICKS)  # brief ⇒ more suspicious
    return BODY_NEAR_LOG_LR * fade


def _follow_log_lr(event: PlayerEvent, belief: Belief) -> float:
    victim = belief.roster.get(event.target_color)
    if victim is None or victim.life_status != "dead" or victim.death_seen_tick is None:
        return 0.0
    if abs(victim.death_seen_tick - event.end_tick) > FOLLOW_DEATH_WINDOW_TICKS:
        return 0.0
    ramp = min(1.0, event.duration_ticks / FOLLOW_FULL_TICKS)  # longer shadowing ⇒ more
    return FOLLOW_LOG_LR * ramp


def _tailing_self_log_lr(event: PlayerEvent) -> float:
    """Logistic in how long the player shadowed *us*: a brief brush is ~nothing, the
    ramp leaves zero around ~12-15 ticks, crosses half at the midpoint, and saturates
    "very sketchy" by ~50 ticks (see the constants above for the calibration)."""

    x = TAIL_SELF_STEEPNESS * (event.duration_ticks - TAIL_SELF_MIDPOINT_TICKS)
    return TAIL_SELF_LOG_LR_MAX / (1.0 + math.exp(-max(-700.0, min(700.0, x))))


def _evidence_log_lr(belief: Belief, record: PlayerRecord) -> float:
    """A player's total log-LR: the most-suspicious instance per evidence type.

    Aggregating with ``max`` (not a sum over every event) keeps each type's
    contribution bounded and double-count-free even with an unbounded event log.
    A single witnessed catch (``kill``/``vent_use``) latches the near-certain LR;
    everything else is graded over the event log.
    """

    witnessed = WITNESSED_LOG_LR if any(e.kind in ("kill", "vent_use") for e in record.events) else 0.0
    vent = max((_vent_dwell_log_lr(e) for e in record.events if e.kind == "vent"), default=0.0)
    body = max((_body_proximity_log_lr(e) for e in record.events if e.kind == "near_body"), default=0.0)
    follow = max((_follow_log_lr(e, belief) for e in record.events if e.kind == "proximity"), default=0.0)
    tail = max((_tailing_self_log_lr(e) for e in record.events if e.kind == "tailing_self"), default=0.0)
    return witnessed + vent + body + follow + tail


# --- combine into the posterior ---------------------------------------------


def _recompute(belief: Belief) -> None:
    prior_logit = _logit(_prior_imposter_p(belief))
    suspicion: dict[str, float] = {}
    believed: set[str] = set()

    for color, record in belief.roster.items():
        if record.life_status == "dead":
            continue  # the dead are no threat
        logit = prior_logit + _evidence_log_lr(belief, record)
        p = _sigmoid(logit)
        suspicion[color] = p
        if p >= FLEE_PROBABILITY:
            believed.add(color)

    belief.suspicion = suspicion
    belief.believed_imposters = believed


def witnessed_imposters(belief: Belief) -> set[str]:
    """Colors we directly caught killing or venting (a ``kill``/``vent_use`` event on
    their log). These already drive P ≈ 1 via ``WITNESSED_LOG_LR``; this exposes the
    set for tracing/forensics — there is no separate ``confirmed`` state to maintain."""

    return {
        color
        for color, record in belief.roster.items()
        if any(e.kind in ("kill", "vent_use") for e in record.events)
    }


def active_tail_suspect(belief: Belief) -> str | None:
    """The player currently **tailing us** whom we're suspicious enough to accuse, or
    `None`. The most-suspicious color with an *ongoing* `tailing_self` interval and
    P ≥ `ACCUSE_THRESHOLD`. Drives Accuse mode: stop, go slam the meeting button, then
    accuse them. Crewmate-only by construction (suspicion is empty for other roles)."""

    best: tuple[str, float] | None = None
    for color, p in belief.suspicion.items():
        if p < ACCUSE_THRESHOLD:
            continue
        record = belief.roster.get(color)
        if record is None or record.life_status == "dead":
            continue
        if not _is_actively_tailing(record, belief.last_tick):
            continue
        if best is None or p > best[1]:
            best = (color, p)
    return best[0] if best is not None else None


def _is_actively_tailing(record: PlayerRecord, tick: int) -> bool:
    """True if this player's most recent `tailing_self` interval is still live (extended
    within `ACCUSE_TAIL_RECENCY_TICKS`)."""

    for event in reversed(record.events):
        if event.kind == "tailing_self":
            return tick - event.end_tick <= ACCUSE_TAIL_RECENCY_TICKS
    return False


def top_suspect(belief: Belief) -> str | None:
    """The live player to vote out — the **clear leading suspect**, or `None` (skip)
    when the posterior is flat. Used by Attend Meeting (§7.1).

    Two ways to clear the bar: near-certainty on its own (P ≥ `VOTE_PROBABILITY` — a
    witnessed catch or a saturated tail), or a clear lead short of that (P over
    `VOTE_LEAD_MIN_P` *and* ahead of the runner-up by `VOTE_LEAD_MARGIN`). A flat field
    — everyone near the prior — names no one, so we skip rather than eject at random.
    """

    if not belief.suspicion:
        return None
    ranked = sorted(belief.suspicion.items(), key=lambda kv: kv[1], reverse=True)
    color, p = ranked[0]
    if p >= VOTE_PROBABILITY:
        return color  # near-certain on its own
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    if p >= VOTE_LEAD_MIN_P and (p - runner_up) >= VOTE_LEAD_MARGIN:
        return color  # a clear leader over a non-flat field
    return None


def _logit(p: float) -> float:
    return math.log(p / (1.0 - p))


def _sigmoid(logit: float) -> float:
    logit = max(-700.0, min(700.0, logit))  # keep exp finite
    return 1.0 / (1.0 + math.exp(-logit))
