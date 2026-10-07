"""Exercise authored communication effects through the pinned BASIC engine."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pw_intent


def test_grenade_warning_changes_movement_only_while_live(tmp_path):
    motor = Path(__file__).resolve().parents[2] / "strategy/skills/motor/skill.bas"
    declarations = [
        "DIM k_contacts__friend(15)", "DIM cm__rx_valid(63)",
        "DIM k_comms_danger__grenade_x(3)", "DIM k_comms_danger__grenade_y(3)",
        "DIM k_comms_danger__grenade_until(3)",
    ]
    code = "\n".join(declarations) + "\n" + motor.read_text() + """
k_comms_danger__clear_radius = 450
k_comms_danger__grenade_x(0) = selfX
k_comms_danger__grenade_y(0) = selfY
k_comms_danger__grenade_until(0) = 1
sk_motor__move_x = selfX + 100
sk_motor__move_y = selfY
sk_motor__avoid_grenades()
test__dx = sk_motor__move_x - selfX
test__dy = sk_motor__move_y - selfY
PRINT "ZONE "; worldTick; " "; sk_motor__evading; " "; test__dx * test__dx + test__dy * test__dy
sk_motor__quiet = 0
sk_motor__sneak(1)
PRINT "QUIET "; sk_motor__quiet
"""
    policy = tmp_path / "motor.bas"
    policy.write_text(code)
    pw_intent.record_episode(policy, policy, 5, 0, tmp_path / "record", ticks=2)
    for seat in range(16):
        log = (tmp_path / f"record/player-{seat}.log").read_text()
        assert "BASIC error" not in log and "disabled" not in log
        zones = [list(map(int, line.split()[1:])) for line in log.splitlines() if line.startswith("ZONE ")]
        assert zones[0][0:2] == [0, 1] and zones[0][2] > 450**2
        assert zones[1] == [1, 0, 100**2]
        assert log.count("QUIET 1") == 2
