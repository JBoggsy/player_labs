"""Comms-v1 COM check evaluators: packet truth against the replay, payload claims, and decode
delivery, with adversarial packets and one real-engine transport fixture."""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import strategy_audit  # noqa: E402
import strategy_audit_comms as ac  # noqa: E402
import strategy_comms as cm  # noqa: E402

BOUNDS = [0, 0, 6399, 3199]
KEYS = cm.DEFAULT_KEYS
ACTED_T = "each sent packet decodes and its fields match the sender's replay state at the send tick."
DECODED_T = "teammates alive within 12.8 m of the sender decode it on the next tick, within decode capacity."
E_TRUE = ("the reported label was a visible body at the reported cell and an enemy in the replay. "
          "A corroborated misclassification fails this by design.")


def mapping(extra_checks=None, messages=None):
    checks = {cid: [{"level": "Acted properly", "text": ACTED_T, "reads": []},
                    {"level": "Result", "text": DECODED_T, "reads": []}] for cid in ac.WIRES.values()}
    checks["COM.enemy_sighting"].append({"level": "True", "text": E_TRUE, "reads": []})
    for cid, rows in (extra_checks or {}).items():
        checks[cid] = checks[cid] + rows
    return {"comms": {"version": 1, "keys": list(KEYS), "batch": {"receives": 8},
                      "messages": messages or {str(w): cid for w, cid in ac.WIRES.items()}},
            "codes": {"message": {cid: w + 1 for w, cid in ac.WIRES.items()}},
            "components": {**{cid: {"checks": rows} for cid, rows in checks.items()},
                           "SK.motor": {"checks": [], "unit_sha256": ac.MOTOR_SHA256}}}


class Param:
    def __init__(self, value):
        self.value = value


class Comp:
    def __init__(self, params):
        self.params = params

    def param(self, name):
        return Param(self.params[name]) if name in self.params else None


class Strategy:
    components = {"COM.pickup_taken": Comp({"event_window": 24})}


class Ep(dict):
    def __init__(self, ticks=20, shouts=(), visibility=(), pickups=(), events=(), bounds=BOUNDS):
        super().__init__(
            shouts=pd.DataFrame(list(shouts), columns=["t", "seat", "text", "heard_by", "bytes"]),
            visibility=pd.DataFrame(list(visibility), columns=["t", "seat", "sees"]),
            pickups=pd.DataFrame(list(pickups), columns=["t", "seat", "pickup", "pickup_kind", "x", "z", "ambiguous"]),
            events=pd.DataFrame(list(events), columns=["t", "kind", "seat", "data"]))
        self.meta = {"rules": 49, **({"bounds": bounds} if bounds else {})}
        self.summary = {"ticks": ticks}
        self.episode_id = f"ep{id(self)}"


def state(x=1000, z=1000, hp=10, disguised=False, charge=0, **cmd):
    return {"x": x, "z": z, "hp": hp, "disguised": disguised, "charge": charge, **cmd}


def send(msg, t):
    return {"kind": "PWC", "s": 1, "t": t, "m": msg.kind + 1, "w": msg.sender, "d": list(cm.payloads(msg, t, KEYS))}


def receive(msg, t_sent, at=None):
    return {"kind": "PWC", "s": 2, "t": t_sent + 1 if at is None else at, "m": msg.kind + 1, "w": msg.sender,
            "d": list(cm.payloads(msg, t_sent, KEYS))}


def shout(msg, t, heard_by=()):
    text = cm.encode(msg, t, KEYS)
    return {"t": t + 1, "seat": msg.sender, "text": text, "heard_by": list(heard_by), "bytes": len(text)}


def run(ep, seat, states, events, seat_logs=None, issues=(), m=None, physical=True):
    """physical: also record each logged send as its replay shout (the normal, consistent case)."""
    m = m or mapping()
    if physical:
        rows = ep["shouts"].to_dict("records")
        for event in events:
            if event["kind"] == "PWC" and event["s"] == 1:
                try:
                    msg = cm.unpack(*event["d"], event["t"], KEYS)
                except ValueError:
                    continue
                if not any(r["t"] == event["t"] + 1 and r["seat"] == msg.sender for r in rows):
                    rows.append(shout(msg, event["t"]))
        ep["shouts"] = pd.DataFrame(rows, columns=["t", "seat", "text", "heard_by", "bytes"])
    evidence = strategy_audit.Evidence(m)
    ac.audit_seat(ep, seat, states, events, list(issues), Strategy(), m, evidence, seat_logs or {seat: (events, [])})
    rows = {}
    for row in evidence.rows:
        rows.setdefault(row["check"], []).append(row)
    return rows


def statuses(rows, key):
    return [(r["status"], r["reason"]) for r in rows.get(key, [])]


# E sender seat 0 sees enemy body 3 at (2000, 1000) with 7 hp at tick 5.
def e_world(enemy=3, hp=7, disguised=False):
    states = {(t, b): state() for t in range(20) for b in range(16)}
    states[5, enemy] = state(2000, 1000, hp=hp, disguised=disguised)
    return states, [{"t": 5, "seat": 0, "sees": [enemy]}]


def e_msg(label=3, hp=7, cell=None, sender=0):
    return cm.Message(0, sender, label + 16 * (hp + 16 * 8), 0, ac.cell_of(2000, 1000, BOUNDS) if cell is None else cell)


def test_enemy_packet_truth_and_adversarial_fields():
    states, vis = e_world()
    ep = Ep(visibility=vis)
    good = run(ep, 0, states, [send(e_msg(), 5)])
    assert statuses(good, "COM.enemy_sighting.1") == [("pass", None)]
    assert statuses(good, "COM.enemy_sighting.3") == [("pass", None)]
    assert statuses(run(Ep(visibility=vis), 0, states, [send(e_msg(hp=6), 5)]),
                    "COM.enemy_sighting.1") == [("fail", "hp_mismatch")]
    assert statuses(run(Ep(visibility=vis), 0, states, [send(e_msg(cell=0), 5)]),
                    "COM.enemy_sighting.1") == [("fail", "cell_mismatch")]
    assert statuses(run(Ep(visibility=vis), 0, states, [send(e_msg(label=5), 5)]),
                    "COM.enemy_sighting.1") == [("fail", "label_not_visible")]
    wrong = send(e_msg(sender=2), 5)  # logged by seat 0 but the packet claims sender 2
    assert statuses(run(Ep(visibility=vis), 0, states, [wrong]),
                    "COM.enemy_sighting.1") == [("fail", "wrong_wire_or_sender")]
    assert statuses(run(Ep(visibility=vis, bounds=None), 0, states, [send(e_msg(), 5)]),
                    "COM.enemy_sighting.1") == [("unmeasurable", "map_bounds_missing")]


def test_enemy_claim_about_a_disguised_teammate_fails_truth():
    # Teammate body 2 in uniform answers to label 3 for observer 0: the packet matches the view
    # (Acted properly) but the body is a friend (True fails by design).
    states, vis = e_world(enemy=2, disguised=True)
    rows = run(Ep(visibility=vis), 0, states, [send(e_msg(label=3), 5)])
    assert statuses(rows, "COM.enemy_sighting.1") == [("pass", None)]
    assert statuses(rows, "COM.enemy_sighting.3") == [("fail", "friendly_body")]


def test_friend_label_requires_sender_disguise():
    states = {(t, b): state() for t in range(20) for b in range(16)}
    msg = cm.Message(8, 4, 5, 0, 0)
    assert statuses(run(Ep(), 4, states, [send(msg, 3)]), "COM.disguise_friend.1") == [("fail", "sender_not_disguised")]
    states[3, 4] = state(disguised=True)
    assert statuses(run(Ep(), 4, states, [send(msg, 3)]), "COM.disguise_friend.1") == [("pass", None)]
    assert statuses(run(Ep(), 4, states, [send(cm.Message(8, 4, 7, 0, 0), 3)]),
                    "COM.disguise_friend.1") == [("fail", "label_mismatch")]


def test_grenade_command_reconstruction():
    states = {(t, b): state() for t in range(20) for b in range(16)}
    target = (1900, 1000)  # 900 cm: need = (900 - 150) * 24 / 1130 + 1 = 16
    states[6, 0] = state(1000, 1000, charge=4)
    states[7, 0] = state(1000, 1000, cmd_charge=1, cmd_aim_x=target[0], cmd_aim_z=target[1])
    cell = ac.cell_of(*target, BOUNDS)
    assert statuses(run(Ep(), 0, states, [send(cm.Message(2, 0, 12, 0, cell), 6)]),
                    "COM.grenade_warning.1") == [("pass", None)]
    assert statuses(run(Ep(), 0, states, [send(cm.Message(2, 0, 11, 0, cell), 6)]),
                    "COM.grenade_warning.1") == [("fail", "release_mismatch")]
    states[7, 0] = state(1000, 1000)  # no traced command
    assert statuses(run(Ep(), 0, states, [send(cm.Message(2, 0, 12, 0, cell), 6)]),
                    "COM.grenade_warning.1") == [("unmeasurable", "command_not_traced")]


def test_pickup_taken_claim():
    states = {(t, b): state() for t in range(40) for b in range(16)}
    take = {"t": 10, "seat": 0, "pickup": 3, "pickup_kind": "armor", "x": 500, "z": 600, "ambiguous": False}
    cell = ac.cell_of(500, 600, BOUNDS)
    ok = cm.Message(5, 0, 3, 720 - 5, cell)
    assert statuses(run(Ep(ticks=40, pickups=[take]), 0, states, [send(ok, 15)]),
                    "COM.pickup_taken.1") == [("pass", None)]
    assert statuses(run(Ep(ticks=40, pickups=[take]), 0, states, [send(cm.Message(5, 0, 3, 720, cell), 15)]),
                    "COM.pickup_taken.1") == [("fail", "ready_in_mismatch")]
    assert statuses(run(Ep(ticks=40, pickups=[{**take, "ambiguous": True}]), 0, states, [send(ok, 15)]),
                    "COM.pickup_taken.1") == [("unmeasurable", "ambiguous_take")]
    assert statuses(run(Ep(ticks=40), 0, states, [send(ok, 15)]), "COM.pickup_taken.1") == [("fail", "no_take_event")]


def test_untraced_claims_stay_unmeasurable():
    states = {(t, b): state() for t in range(20) for b in range(16)}
    for msg, key, reason in ((cm.Message(4, 0, 100, 0, 9), "COM.glory_seen.1", "glory_heart_state_not_traced"),
                             (cm.Message(3, 0, 7 + 16 * 8, 3, 0), "COM.under_fire.1", "sound_cues_not_traced"),
                             (cm.Message(6, 0, 3, 0, 9), "COM.pickup_ready.1", "pickup_readiness_and_sight_not_traced"),
                             (cm.Message(7, 0, 2, 4, 9), "COM.disguise_alert.1", "evidence_source_not_logged")):
        assert statuses(run(Ep(), 0, states, [send(msg, 3)]), key) == [("unmeasurable", reason)]


def delivery_world(text, receivers=(2, 4), dead=(), extra_shouts=(), sender=0):
    states = {(t, b): state() for t in range(20) for b in range(16)}
    for seat in dead:
        states[6, seat] = state(hp=0)
    shouts = list(extra_shouts) + [{"t": 6, "seat": sender, "text": text, "heard_by": [1, *receivers], "bytes": 20}]
    return states, shouts


def test_decode_delivery_pass_miss_offset_dead_and_capacity():
    msg = cm.Message(8, 0, 1, 0, 0)
    text = cm.encode(msg, 5, KEYS)
    states, shouts = delivery_world(text)
    sender_events = [send(msg, 5)]
    logs = {0: (sender_events, []), 2: ([receive(msg, 5)], []), 4: ([receive(msg, 5)], [])}
    rows = run(Ep(shouts=shouts), 0, states, sender_events, logs)
    assert statuses(rows, "COM.disguise_friend.2") == [("pass", None)]
    assert rows["COM.disguise_friend.2"][0]["decoded"] == 2
    logs[4] = ([], [])
    assert statuses(run(Ep(shouts=shouts), 0, states, sender_events, logs),
                    "COM.disguise_friend.2") == [("fail", "receiver_missed_packet")]
    logs[4] = ([receive(msg, 5, at=7)], [])  # logged one tick late
    assert statuses(run(Ep(shouts=shouts), 0, states, sender_events, logs),
                    "COM.disguise_friend.2") == [("fail", "receiver_missed_packet")]
    states, shouts = delivery_world(text, receivers=(2,), dead=(2,))
    assert statuses(run(Ep(shouts=shouts), 0, states, sender_events, {0: (sender_events, []), 2: ([], [])}),
                    "COM.disguise_friend.2") == [("not_exercised", "no_eligible_receiver")]
    msg2 = cm.Message(8, 2, 3, 0, 0)  # sender seat 2: enemy seat 1 speaks first in delivery order
    crowd = [{"t": 6, "seat": 1, "text": "1" + "x" * 9 + "1" + "y" * 9, "heard_by": [4], "bytes": 20}] * 8
    states, shouts = delivery_world(cm.encode(msg2, 5, KEYS), receivers=(4,), extra_shouts=crowd, sender=2)
    rows = run(Ep(shouts=shouts), 2, states, [send(msg2, 5)], {2: ([send(msg2, 5)], []), 4: ([], [])})
    assert statuses(rows, "COM.disguise_friend.2") == [("not_exercised", "no_eligible_receiver")]
    assert rows["COM.disguise_friend.2"][0]["capacity_excluded"] == 1
    states, shouts = delivery_world(text, receivers=(2,))
    assert statuses(run(Ep(shouts=shouts), 0, states, sender_events, {0: (sender_events, []), 2: ([], [{"reason": "x"}])}),
                    "COM.disguise_friend.2") == [("unmeasurable", "receiver_log_invalid")]
    assert statuses(run(Ep(ticks=6, shouts=shouts), 0, states, sender_events, logs),
                    "COM.disguise_friend.2") == [("not_exercised", "delivery_after_episode_end")]
    assert statuses(run(Ep(shouts=[]), 0, states, sender_events, logs, physical=False),
                    "COM.disguise_friend.2") == [("fail", "shout_missing")]


def test_packet_claims_require_the_physical_shout():
    states = {(t, b): state() for t in range(20) for b in range(16)}
    states[3, 4] = state(disguised=True)
    msg = cm.Message(8, 4, 5, 0, 0)
    rows = run(Ep(), 4, states, [send(msg, 3)], physical=False)
    assert statuses(rows, "COM.disguise_friend.1") == [("fail", "shout_not_in_replay")]
    other = shout(cm.Message(8, 4, 5, 0, 0), 2)  # same packet, wrong tick: different scrambled text
    rows = run(Ep(shouts=[{**other, "t": 4}]), 4, states, [send(msg, 3)], physical=False)
    assert statuses(rows, "COM.disguise_friend.1") == [("fail", "shout_not_in_replay")]


def test_capacity_filter_matches_runtime_bytes():
    assert cm.replay_shape({"text": "1" + "x" * 9 + "1" + "y" * 9, "bytes": 20}) is True   # digits not required
    assert cm.replay_shape({"text": "1" + "\u00e9" * 9 + "1" + "y" * 9, "bytes": 29}) is False  # 29 bytes, not 20
    assert cm.replay_shape({"text": "abc", "bytes": 5}) is None                              # byte count disagrees
    msg = cm.Message(8, 2, 3, 0, 0)
    unsure = [{"t": 6, "seat": 1, "text": "1" + "x" * 9 + "1" + "y" * 9, "heard_by": [4], "bytes": 20}] * 7
    unsure.append({"t": 6, "seat": 1, "text": "odd", "heard_by": [4], "bytes": 9})
    states, shouts = delivery_world(cm.encode(msg, 5, KEYS), receivers=(4,), extra_shouts=unsure, sender=2)
    rows = run(Ep(shouts=shouts), 2, states, [send(msg, 5)], {2: ([send(msg, 5)], []), 4: ([], [])})
    assert statuses(rows, "COM.disguise_friend.2") == [("unmeasurable", "receiver_log_invalid")]


def test_grenade_division_truncates_toward_zero():
    assert ac.tdiv(-7, 2) == -3 and ac.tdiv(7, -2) == -3 and ac.tdiv(7, 2) == 3
    assert ac.motor_isqrt(1562499) == 1249 and ac.motor_isqrt(160001) == 400


def test_unexercised_invalid_logs_unknown_text_and_binding():
    states = {(t, b): state() for t in range(20) for b in range(16)}
    rows = run(Ep(), 0, states, [])
    assert statuses(rows, "COM.focus_call.1") == [("not_exercised", "no_sends")]
    rows = run(Ep(), 0, states, [], issues=[{"reason": "telemetry_gap", "t": 3}])
    assert statuses(rows, "COM.focus_call.1") == [("unmeasurable", "telemetry_gap")]
    changed = mapping({"COM.focus_call": [{"level": "Result", "text": "called targets die faster.", "reads": []}]})
    rows = run(Ep(), 0, states, [], m=changed)
    assert statuses(rows, "COM.focus_call.3") == [("unmeasurable", "no_evaluator_for_check_text")]
    swapped = mapping(messages={**{str(w): c for w, c in ac.WIRES.items()}, "0": "COM.focus_call",
                                "1": "COM.enemy_sighting"})
    rows = run(Ep(), 0, states, [], m=swapped)
    assert statuses(rows, "COM.enemy_sighting.1") == [("unmeasurable", "no_evaluator_for_check_text")]
    bad = {"kind": "PWC", "s": 1, "t": 4, "m": 1, "w": 0, "d": [123, 456]}
    assert statuses(run(Ep(), 0, states, [bad]), "COM.enemy_sighting.1") == [("fail", "packet_does_not_decode")]


GRENADE_TRUE = {"COM.grenade_warning": [{"level": "True", "text": "a grenade from the sender lands within 150 cm "
                                                                  "of the reported cell.", "reads": []}]}


def grenade_case(charges, throw_at=None, to=(1900, 1000), dead_at=None, ticks=40, extra_sends=(), gap_at=None,
                 held=None):
    """Sender 0 warns at t = 6 (release in 3) for (1900, 1000); `charges` maps tick -> state charge.
    `held` maps tick -> (cmd_charge, grenade, radar_until) for ticks before the charge starts."""
    states = {(t, b): state() for t in range(ticks + 1) for b in range(16)}
    for tick, charge in charges.items():
        states[tick, 0] = state(charge=charge)
    for tick, (command, grenade, radar) in (held or {}).items():
        states[tick, 0] = state(charge=0, cmd_charge=command, grenade=grenade, radar_until=radar)
    if dead_at is not None:
        states[dead_at, 0] = state(hp=0, charge=0)
    if gap_at is not None:
        del states[gap_at, 0]
    events = []
    if throw_at is not None:
        events.append({"t": throw_at, "kind": "grenade_throw", "seat": 0,
                       "data": json.dumps({"from": [1000, 1000], "to": list(to), "lands_at": throw_at + 10})})
    msg = cm.Message(2, 0, 3, 0, ac.cell_of(1900, 1000, BOUNDS))
    sends = [send(msg, 6)] + [send(cm.Message(2, 0, 2, 0, ac.cell_of(2400, 1000, BOUNDS)), t) for t in extra_sends]
    rows = run(Ep(ticks=ticks, events=events), 0, states, sends, m=mapping(GRENADE_TRUE))
    return rows["COM.grenade_warning.3"]


def test_grenade_held_past_the_estimate_and_thrown_on_target_passes():
    # Release estimated at 6 + 3, but the motor kept charging (need grew) and threw at post-step tick 15.
    rows = grenade_case({**{k: k - 5 for k in range(7, 15)}, 15: 0}, throw_at=15)
    assert [(r["status"], r["reason"]) for r in rows] == [("pass", None)]
    assert rows[0]["throw_tick"] == 15 and rows[0]["release_estimate_error"] == 14 - 9


def test_grenade_early_release_lands_short():
    rows = grenade_case({7: 1, 8: 2, 9: 0}, throw_at=9, to=(1350, 1000))
    assert [(r["status"], r["reason"]) for r in rows] == [("fail", "landed_elsewhere")]
    assert rows[0]["distance_cm"] > 150


def test_grenade_cancellations_fail_with_specific_reasons():
    rows = grenade_case({7: 1, 8: 2}, dead_at=9)
    assert [(r["status"], r["reason"]) for r in rows] == [("fail", "cancelled_by_death")]
    rows = grenade_case({7: 1, 8: 2, 9: 0})  # charge zeroed while alive (mister or radar pickup), no throw
    assert [(r["status"], r["reason"]) for r in rows] == [("fail", "charge_dropped_without_throw")]


def test_grenade_unknowns_end_gap_and_superseded():
    still = grenade_case({k: min(24, k - 5) for k in range(7, 21)}, ticks=20)  # charging at the last state
    assert [(r["status"], r["reason"]) for r in still] == [("unmeasurable", "after_episode_end")]
    last = grenade_case({**{k: k - 5 for k in range(7, 20)}, 20: 0}, throw_at=20, ticks=20)  # final-step throw
    assert [(r["status"], r["reason"]) for r in last] == [("pass", None)]
    gap = grenade_case({7: 1, 8: 2, 9: 3, 10: 0}, throw_at=10, gap_at=8)
    assert [(r["status"], r["reason"]) for r in gap] == [("unmeasurable", "replay_state_gap")]
    rows = grenade_case({**{k: k - 5 for k in range(7, 12)}, 12: 0}, throw_at=12, extra_sends=(9,))
    by_tick = {r["t"]: (r["status"], r["reason"]) for r in rows}
    assert by_tick[6] == ("unmeasurable", "superseded_by_newer_warning")
    assert by_tick[9] == ("fail", "landed_elsewhere")  # the newer warning named (2400, 1000); it landed at 1900


def test_grenade_disarmed_hold_then_real_charge_and_throw_passes():
    # Radar until 12: the order is held from the warning with zero charge, the charge starts at 13 and
    # the throw lands on target at 20. The first-zero rule would have called this charge_dropped.
    held = {k: (1, 1, 12) for k in range(7, 13)}
    rows = grenade_case({**{k: k - 12 for k in range(13, 20)}, 20: 0}, throw_at=20, held=held)
    assert [(r["status"], r["reason"]) for r in rows] == [("pass", None)]
    assert rows[0]["throw_tick"] == 20


def test_grenade_never_started_and_pre_start_cancellations():
    held = {7: (1, 1, 30), 8: (1, 1, 30), 9: (0, 1, 30)}  # the local s1_a0 seat 2 shape: radar, order dropped
    rows = grenade_case({}, held=held)
    assert [(r["status"], r["reason"]) for r in rows] == [("fail", "charge_never_started")]
    rows = grenade_case({}, held={7: (1, 1, 30)}, dead_at=8)
    assert [(r["status"], r["reason"]) for r in rows] == [("fail", "cancelled_by_death")]
    rows = grenade_case({}, held={7: (1, 1, 0), 8: (1, 0, 0)})
    assert [(r["status"], r["reason"]) for r in rows] == [("fail", "grenade_lost_before_start")]
    rows = grenade_case({}, held={k: (1, 1, 99) for k in range(7, 21)}, ticks=20)  # held to the last state
    assert [(r["status"], r["reason"]) for r in rows] == [("unmeasurable", "after_episode_end")]
    rows = grenade_case({})  # pre-start state without a traced command
    assert [(r["status"], r["reason"]) for r in rows] == [("unmeasurable", "command_not_traced")]


def test_grenade_rewarning_mid_charge_released_next_step_passes():
    # Already charged (5) at the warning tick 6; the next step releases (state 7: charge 0, grenade 0) with
    # a real throw on target. Started must come from state(t), not from the first scanned tick.
    rows = grenade_case({6: 5}, throw_at=7, held={7: (1, 0, 30)})
    assert [(r["status"], r["reason"]) for r in rows] == [("pass", None)]
    rows = grenade_case({6: 5}, held={7: (1, 0, 30)})  # same shape without any throw: an honest drop
    assert [(r["status"], r["reason"]) for r in rows] == [("fail", "charge_dropped_without_throw")]


def test_grenade_regression_shapes_from_local_audit():
    # Seat 4 at warning 476 and seat 12 at warning 440: the charge stopped early and the throw shares the
    # first zero-charge tick (grenade-failures.txt). Both stay landed_elsewhere.
    rows = grenade_case({7: 1, 8: 2, 9: 0}, throw_at=9, to=(1200, 1139))
    assert [(r["status"], r["reason"]) for r in rows] == [("fail", "landed_elsewhere")]
    rows = grenade_case({**{k: k - 6 for k in range(7, 15)}, 15: 0}, throw_at=15, to=(1424, 1037))
    assert [(r["status"], r["reason"]) for r in rows] == [("fail", "landed_elsewhere")]


def test_transport_in_engine(tmp_path):
    """Real pinned engine: every seat sends one friend label at tick 1 while not disguised."""
    import pw_cli
    import pw_episodes as pe
    import pw_intent
    try:
        pw_intent._handoff(pe.DEFAULT_TAG)
    except pw_cli.EnvironmentMissing:
        pytest.skip("handoff engine not built (paintbot_pw_lab/tools/build_tools.sh)")
    runtime = (TOOLS.parent / "strategy" / "compiler" / "runtime" / "comms.bas").read_text()
    code = [runtime, "SUB st__decoded()", "END SUB"]
    code += [f"cm__keys({i}) = {k}" for i, k in enumerate(KEYS)]
    code += ["cm__max_decode = 8", "cm__min_gap = 6", "rt__pe = 0", "rt__pb = 0", "cm__receive()",
             "IF worldTick = 1 THEN", "cm__send(8, selfId + 1 - 2 * (selfId MOD 2), 0, 0, 0)", "END IF",
             "cm__flush()"]
    policy = tmp_path / "friend.bas"
    policy.write_text("\n".join(code) + "\n")
    pw_intent.record_episode(policy, policy, 5, 0, tmp_path / "record", ticks=6)
    ep = pe.load_episode(pe.discover([tmp_path / "record"])[0], options=pe.TraceOptions(state_every=1, vis_every=1))
    assert ep.summary["verified"]
    states = {(int(r["t"]), int(r["seat"])): r for r in ep["states"].to_dict("records")}
    m = mapping()
    logs = {}
    for seat in range(16):
        events = []
        for line in (tmp_path / "record" / f"player-{seat}.log").read_text().splitlines():
            if line.startswith("PWC v=3 "):
                tick = int(line.split()[2][2:])
                for direction, message in cm.decode_batch(line.split(" b=")[1], tick, KEYS):
                    events.append({"kind": "PWC", "t": tick, "s": direction, "w": message.sender,
                                   "m": message.kind + 1, "d": list(cm.payloads(message, tick - (direction == 2), KEYS))})
        logs[seat] = (events, [])
    decoded = 0
    for seat in range(16):
        rows = run(ep, seat, states, logs[seat][0], logs, m=m, physical=False)
        assert statuses(rows, "COM.disguise_friend.1") == [("fail", "sender_not_disguised")]
        result = rows["COM.disguise_friend.2"][0]
        assert result["status"] in ("pass", "not_exercised"), result
        decoded += result.get("decoded", 0)
        assert statuses(rows, "COM.enemy_sighting.1") == [("not_exercised", "no_sends")]
    assert decoded > 0


def test_grenade_formula_requires_reviewed_motor():
    msg = cm.Message(2, 0, 3, 0, 100)
    changed = mapping()
    changed["components"]["SK.motor"]["unit_sha256"] = "different"
    rows = run(Ep(), 0, {}, [send(msg, 5)], m=changed)
    assert statuses(rows, "COM.grenade_warning.1") == [("unmeasurable", "grenade_motor_model_mismatch")]
