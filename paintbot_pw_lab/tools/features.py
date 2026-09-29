"""Paintbot PW feature adapter for the `coworld-hypothesis-miner` engine.

Consumes the rows `miner_rows.py` writes: one per (episode, our policy), built from
hash-checked episodes (pw_episodes.py), pw_metrics.py, pw_fights.py and pw_flags.py, plus our
PWI intent summary when our seat logs exist. Exposes the `adapter` and `METAS` names the engine loads.

Feature rules (coworld-hypothesis-miner SKILL.md):
- timing features use the match's last tick + 1 for "never happened";
- rates are per minute of match (1,440 ticks) or shares of an explicit denominator, so
  long and short matches compare; a feature whose denominator is 0 is left out of that
  row (unknown), never set to 0;
- score components are excluded per `score_kind`. The ladder score is the Elo outcome of
  the glory margin, and glory = match-length countdown + quiet-supplies + behind-in-lives +
  behind-in-cogs + glory-heart awards, settled to 0 for the loser (docs/mechanics.md §1).
  The win itself is decided by the heart meter, which is hearts held over time. So match
  length, glory hearts, the longest supply gap, cogs out, lives left and hearts held never
  "explain" the score. Deaths also feed behind-in-lives glory (for the side that is behind),
  which the `deaths_per_min` blurb says.
- `change_hint` names the BASIC module of our policy (base.bas lineage) that owns the
  behavior: targeting (Gun), footwork, dry route, territory squads (heart selection), cover
  seats, supplies, refuse-a-fight (retreat), grenade, stall check, comms (shout).
"""

from __future__ import annotations

from variance_miner import Episode, FeatureMeta

TICKS_PER_MINUTE = 1440  # 24 ticks per second
# The engine ranks by a swing in score units and emits nothing under 0.3 (variance_miner
# `ranked_hypotheses(min_vp=0.3)`). Elo outcome and win are 0-1, which could never clear it,
# so the adapter reports them as outcome points, 0-100 (0.5 Elo outcome = 50 points).
SCORE_SCALE = 100.0

# Features that are arithmetic parts of the score or of the win condition, by score kind.
# The meter is hearts held over time; elimination (every cog out of lives) also ends and decides
# the match, so lives left and cogs out are win conditions too.
WIN_CONDITION = {"hearts_held_mean", "captures_completed_per_min", "cogs_out_end", "team_lives_end"}
SCORE_COMPONENTS = {
    "elo": {"match_minutes", "glory_hearts_per_min", "longest_supply_gap_min"} | WIN_CONDITION,
    "win": WIN_CONDITION,
}


def _meta(name: str, kind: str, blurb: str, hint: str) -> FeatureMeta:
    return FeatureMeta(name=name, kind=kind, blurb=blurb, change_hint=hint)


METAS: dict[str, FeatureMeta] = {
    # timing (never = match ticks + 1)
    "first_capture_tick": _meta("first_capture_tick", "timing", "tick our team first completed a heart capture",
                                "territory squads: send the opening squads to the nearest neutral heart sooner"),
    "first_death_tick": _meta("first_death_tick", "timing", "tick one of our cogs first died",
                              "footwork / refuse-a-fight: survive the opening contact"),
    "first_kill_tick": _meta("first_kill_tick", "timing", "tick one of our cogs first killed an enemy",
                             "targeting: fire earlier and lead better in the first contact"),
    "first_heart_lost_tick": _meta("first_heart_lost_tick", "timing", "tick the enemy first took a heart we owned",
                                   "cover seats: hold a defender on owned hearts"),
    # presence
    "first_blood": _meta("first_blood", "presence", "our team made the match's first kill",
                         "targeting / footwork: win the first engagement"),
    "lost_heart_at_all": _meta("lost_heart_at_all", "presence", "the enemy took at least one heart we owned",
                               "cover seats: defend owned hearts"),
    "friendly_fire_at_all": _meta("friendly_fire_at_all", "presence", "we hit a teammate at least once",
                                  "targeting: widen the teammate-in-line hold-fire check"),
    "grenade_used": _meta("grenade_used", "presence", "we threw at least one grenade",
                          "grenade: throw when the charge matches the distance"),
    "vm_disabled_suspect": _meta("vm_disabled_suspect", "presence", "a seat issued only empty commands for its last 240+ alive ticks (inferred)",
                                 "runtime: find the BASIC error or budget overrun that stops the seat"),
    "vm_error_logged": _meta("vm_error_logged", "presence", "a seat log shows `BASIC error:` (our logs only)",
                             "runtime: fix the error in the log; mine gameplay only after ops are clean"),
    # counts, rates and shares
    "gun_enemy_accuracy": _meta("gun_enemy_accuracy", "count", "enemy hits per gun ray fired",
                                "targeting: lead, drift correction and fire gate"),
    "long_range_shot_share": _meta("long_range_shot_share", "count", "share of rays whose aim target was 2,500-5,250 units away (inferred band)",
                                   "targeting: tighten the range gate before firing"),
    "shots_per_min": _meta("shots_per_min", "count", "gun rays fired per minute of match",
                           "targeting: fire gate and gun wait"),
    "kills_per_min": _meta("kills_per_min", "count", "enemy kills per minute of match",
                           "targeting / footwork: convert contacts into kills"),
    "deaths_per_min": _meta("deaths_per_min", "count", "our deaths per minute (also pays behind-in-lives glory to the side behind)",
                            "footwork / refuse-a-fight: take fewer losing fights"),
    "kd": _meta("kd", "count", "enemy kills per death", "footwork / refuse-a-fight: trade better"),
    "trade_share": _meta("trade_share", "count", "share of our deaths whose killer a teammate killed within 72 ticks",
                         "territory squads: keep squad-mates within trade range"),
    "friendly_hp_per_min": _meta("friendly_hp_per_min", "count", "HP we removed from teammates per minute",
                                 "targeting: hold fire when a teammate is in the line"),
    "alive_share": _meta("alive_share", "count", "share of seat-ticks alive", "footwork / refuse-a-fight: stay alive"),
    "heart_reach_share": _meta("heart_reach_share", "count", "share of alive ticks within capture reach of a heart",
                               "territory squads: spend more time on hearts"),
    "contested_share": _meta("contested_share", "count", "share of alive ticks in reach of a contested heart",
                             "territory squads: avoid or win contested hearts"),
    "water_share": _meta("water_share", "count", "share of alive ticks in water (slow)", "dry route: route around water"),
    "trench_share": _meta("trench_share", "count", "share of alive ticks in a trench", "footwork: use trench cover"),
    "stuck_share": _meta("stuck_share", "count", "share of alive ticks sampled as stuck toward an unchanged goal (sampled heuristic)",
                         "stall check / dry route: detect and escape stuck walks sooner"),
    "idle_share": _meta("idle_share", "count", "share of decision ticks with an empty command",
                        "runtime / hold logic: never idle without a goal"),
    "pickups_per_min": _meta("pickups_per_min", "count", "supplies taken per minute (any kind)",
                             "supplies: take more (or fewer) supplies"),
    "grenade_effective_share": _meta("grenade_effective_share", "count", "grenade blasts with at least one enemy victim per throw",
                                     "grenade: charge to the distance, wait for clusters"),
    "shouts_per_min": _meta("shouts_per_min", "count", "shouts per minute", "comms: shout less (enemies hear) or more"),
    "capture_reset_share": _meta("capture_reset_share", "count", "capture attempts that reset without owning the heart, per start",
                                 "territory squads: commit to a heart or leave it"),
    "contests_per_min": _meta("contests_per_min", "count", "heart contests per minute", "territory squads: pick hearts the enemy is not on"),
    # score or win components (excluded per score kind, listed so a lab member sees why)
    "match_minutes": _meta("match_minutes", "count", "match length in minutes (glory countdown: a score component)",
                           "not a behavior"),
    "glory_hearts_per_min": _meta("glory_hearts_per_min", "count", "glory hearts taken per minute (glory award: a score component)",
                                  "glory hearts: detour for visible glory hearts"),
    "longest_supply_gap_min": _meta("longest_supply_gap_min", "count", "longest stretch without a pickup (quiet-supplies award)",
                                    "supplies"),
    "cogs_out_end": _meta("cogs_out_end", "count", "our cogs out of lives at the end (behind-in-cogs award)", "not a behavior"),
    "team_lives_end": _meta("team_lives_end", "count", "our lives left at the end (behind-in-lives award)", "not a behavior"),
    "hearts_held_mean": _meta("hearts_held_mean", "count", "mean hearts held (the meter: win condition)", "not a behavior"),
    "captures_completed_per_min": _meta("captures_completed_per_min", "count", "captures completed per minute (drives the meter)",
                                        "territory squads"),
    # engagements and opening duels (pw_fights.py)
    "engagement_win_share": _meta("engagement_win_share", "count", "engagements our team won, per engagement our seats joined",
                                  "targeting / footwork: win the fights we take"),
    "first_hit_share": _meta("first_hit_share", "count", "engagements where our team hit first",
                             "targeting: fire first (lead and fire gate)"),
    "outnumbered_share": _meta("outnumbered_share", "count", "engagements where we had fewer participants",
                               "territory squads / refuse-a-fight: fight together or not at all"),
    "outnumbered_win_share": _meta("outnumbered_win_share", "count", "engagements won while outnumbered, per outnumbered engagement",
                                   "refuse-a-fight: the outnumbered test"),
    "opening_duel_win_share": _meta("opening_duel_win_share", "count", "heart contests where our team made the opening kill",
                                    "territory squads: arrive at contested hearts together"),
    # anomaly flags (pw_flags.py), per minute of match
    "stuck_flags_per_min": _meta("stuck_flags_per_min", "count", "stuck runs per minute (sampled)",
                                 "stall check / dry route: escape blocked walks sooner"),
    "oscillating_flags_per_min": _meta("oscillating_flags_per_min", "count", "walk-goal flip-flops per minute (sampled)",
                                       "territory squads: stop re-targeting between hearts"),
    "idle_alive_flags_per_min": _meta("idle_alive_flags_per_min", "count", "idle stretches of 2 s+ per minute",
                                      "hold logic: always have a goal"),
    "death_alone_per_min": _meta("death_alone_per_min", "count", "deaths with no living teammate within 1,000 units, per minute",
                                 "territory squads: keep the squad together"),
    "heart_lost_with_allies_per_min": _meta("heart_lost_with_allies_per_min", "count", "hearts lost with a teammate nearby, per minute",
                                            "cover seats: contest captures on owned hearts"),
    "wasted_grenade_share": _meta("wasted_grenade_share", "count", "grenade blasts that hurt no enemy, per throw",
                                  "grenade: wait for a target inside the blast"),
    "long_wade_per_min": _meta("long_wade_per_min", "count", "water stretches of 3 s+ per minute", "dry route: route around water"),
    # intent telemetry (our seats with PWI logs only)
    "intent_heart_switches_per_min": _meta("intent_heart_switches_per_min", "count", "chosen-heart changes per minute (PWI)",
                                           "territory squads: stop re-targeting hearts"),
    "intent_share_retreat": _meta("intent_share_retreat", "count", "share of PWI lines in retreat mode",
                                  "refuse-a-fight: the outnumbered test"),
    "intent_share_supply": _meta("intent_share_supply", "count", "share of PWI lines walking to supplies",
                                 "supplies: the wanted-supply rule"),
    "intent_share_fight": _meta("intent_share_fight", "count", "share of PWI lines in contact", "footwork / targeting"),
    "intent_share_heart": _meta("intent_share_heart", "count", "share of PWI lines walking to or holding a heart",
                                "territory squads"),
}


def _ratio(numerator, denominator):
    if numerator is None or not denominator:
        return None
    return float(numerator) / float(denominator)


def adapter(row: dict) -> Episode | None:
    score_kind = row.get("score_kind", "elo")
    score, ticks = row.get("score"), row.get("ticks")
    if score is None or not ticks:
        return None
    m, team, timing = row["metrics"], row["team_metrics"], row["timing"]
    never = float(ticks) + 1.0
    minutes = ticks / TICKS_PER_MINUTE
    alive = m.get("alive_ticks")
    candidates = {
        "first_capture_tick": team.get("first_capture_tick"),
        "first_death_tick": timing.get("first_death_tick"),
        "first_kill_tick": timing.get("first_kill_tick"),
        "first_heart_lost_tick": timing.get("first_heart_lost_tick"),
    }
    features: dict[str, float] = {key: never if value is None else float(value) for key, value in candidates.items()}
    their_first = timing.get("enemy_first_death_tick")
    features["first_blood"] = float(their_first is not None and (timing.get("first_death_tick") is None
                                                                 or their_first < timing["first_death_tick"]))
    features["lost_heart_at_all"] = float(timing.get("first_heart_lost_tick") is not None)
    features["friendly_fire_at_all"] = float(timing.get("first_friendly_hit_tick") is not None)
    features["grenade_used"] = float((m.get("grenade_throws") or 0) > 0)
    features["vm_disabled_suspect"] = float((m.get("vm_disabled_suspect_seats") or 0) > 0)
    shots = m.get("shots")
    optional = {
        "gun_enemy_accuracy": m.get("gun_enemy_accuracy"),
        "long_range_shot_share": _ratio(m.get("gun_shots_band_2500_5250"), shots),
        "shots_per_min": _ratio(shots, minutes),
        "kills_per_min": _ratio(m.get("kills"), minutes),
        "deaths_per_min": _ratio(m.get("deaths"), minutes),
        "kd": m.get("kd"),
        "trade_share": _ratio(m.get("deaths_traded"), m.get("deaths")),
        "friendly_hp_per_min": _ratio(m.get("dealt_hp_friendly"), minutes),
        "alive_share": m.get("alive_share"),
        "heart_reach_share": m.get("heart_reach_share"),
        "contested_share": _ratio(m.get("contested_reach_ticks"), alive),
        "water_share": _ratio(m.get("water_ticks"), alive),
        "trench_share": _ratio(m.get("trench_ticks"), alive),
        "stuck_share": _ratio(m.get("stuck_ticks"), alive),
        "idle_share": m.get("idle_share"),
        "pickups_per_min": _ratio(sum(m.get(f"pickups_{k}") or 0 for k in ("grenade", "spray", "medkit", "armor", "uniform")), minutes),
        "grenade_effective_share": _ratio(m.get("grenade_blasts_effective"), m.get("grenade_throws")),
        "shouts_per_min": _ratio(m.get("shouts"), minutes),
        "capture_reset_share": _ratio(team.get("capture_resets"), team.get("capture_starts")),
        "contests_per_min": _ratio(team.get("contests"), minutes),
        "match_minutes": minutes,
        "glory_hearts_per_min": _ratio(m.get("glory_hearts_taken"), minutes),
        "longest_supply_gap_min": _ratio(team.get("longest_supply_gap_ticks"), TICKS_PER_MINUTE),
        "cogs_out_end": team.get("cogs_out_end"),
        "team_lives_end": team.get("team_lives_end"),
        "hearts_held_mean": team.get("hearts_held_mean"),
        "captures_completed_per_min": _ratio(m.get("captures_completed"), minutes),
    }
    fights = row.get("fights")
    if fights:
        engaged = fights.get("engagements")
        optional.update({
            "engagement_win_share": _ratio(fights.get("engagements_won"), engaged),
            "first_hit_share": _ratio(fights.get("engagements_first_hit"), engaged),
            "outnumbered_share": _ratio(fights.get("engagements_outnumbered"), engaged),
            "outnumbered_win_share": _ratio(fights.get("won_when_outnumbered"), fights.get("engagements_outnumbered")),
            "opening_duel_win_share": _ratio(fights.get("opening_duels_won"), fights.get("opening_duels")),
        })
    flags = row.get("flags")
    if flags:
        optional.update({
            "stuck_flags_per_min": _ratio(flags.get("stuck"), minutes),
            "oscillating_flags_per_min": _ratio(flags.get("oscillating"), minutes),
            "idle_alive_flags_per_min": _ratio(flags.get("idle_alive"), minutes),
            "death_alone_per_min": _ratio(flags.get("death_alone"), minutes),
            "heart_lost_with_allies_per_min": _ratio(flags.get("heart_lost_with_allies"), minutes),
            "wasted_grenade_share": _ratio(flags.get("wasted_grenade"), m.get("grenade_throws")),
            "long_wade_per_min": _ratio(flags.get("long_wade"), minutes),
        })
    intent = row.get("intent")
    if intent:
        features["vm_error_logged"] = float(intent["vm_errors"] > 0)
        if intent["intent_lines"] > 0:
            optional.update({
                "intent_heart_switches_per_min": _ratio(intent["heart_switches"], minutes),
                "intent_share_retreat": intent.get("mode_share_retreat"),
                "intent_share_supply": intent.get("mode_share_supply"),
                "intent_share_fight": intent.get("mode_share_fight"),
                "intent_share_heart": intent.get("mode_share_heart"),
            })
    features.update({key: float(value) for key, value in optional.items() if value is not None})
    for name in SCORE_COMPONENTS.get(score_kind, set()):
        features.pop(name, None)
    notes = {"team": str(row.get("team")), "result": str(row.get("result")), "source": str(row.get("source")),
             "opponents": ",".join(row.get("opponents", [])), "score_kind": score_kind}
    return Episode(episode_id=f"{row['episode_id']}:{row['policy_key']}", score=float(score) * SCORE_SCALE,
                   features=features, notes=notes)
