"""The M1 baseline source (strategy/STRATEGY.md + skills/motor): source contract checks that the
compiler cannot catch for us. It lints with no diagnostics, the motor skill passes the unit ABI,
the telemetry worst case fits, and the static roles and rule order match reference/base.bas."""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import strategy_basic as sb  # noqa: E402
import strategy_format as sf  # noqa: E402

STRATEGY = TOOLS.parent / "strategy" / "STRATEGY.md"


def load() -> sf.Strategy:
    return sf.parse_strategy(STRATEGY)


def test_lints_without_diagnostics():
    assert sf.lint_strategy(load()) == []


def test_motor_skill_passes_unit_checks():
    strategy = load()
    skill = (STRATEGY.parent / strategy.components["SK.motor"].code_path).read_text()
    assert sb.check_unit(strategy, "SK.motor", skill) == []
    subs = strategy.components["SK.motor"].interface["subs"]
    assert subs["sk_motor__act"] == 3 and subs["sk_motor__isqrt"] == 1


def test_telemetry_worst_case_fits_half_the_engine_limit():
    worst = sb.telemetry_worst_case(load())
    assert worst["events"] <= 64 and worst["bytes"] <= 512


def test_roles_are_base_squad_seats():
    # base.bas: member = (selfId / 2) MOD 8, seat = member MOD 4; seats 2 and 3 cover.
    strategy = load()
    roles = {line.split(" = ")[0].strip(): line for line in strategy.components["ST.roles"].fields["Roles squad"].split("\n")}
    cover = {s for s in range(16) if ((s // 2) % 8) % 4 >= 2}
    assert "seats " + ",".join(map(str, sorted(cover))) in roles["- cover"]
    assert "seats " + ",".join(map(str, sorted(set(range(16)) - cover))) in roles["- ring"]


def test_rule_order_matches_base_override_order():
    # base.bas: retreat overrides supply, supply overrides the squad target, which overrides the
    # carry/thief/heart default. Commitment keeps nothing between ticks.
    strategy = load()
    prio = {r.id: r.priority for r in strategy.rules}
    assert prio["R.fall_back"] > prio["R.resupply"] > prio["R.take_heart"] == prio["R.cover_heart"] > prio["R.default_goal"]
    commit = {p.name: p.value for p in strategy.components["ST.commitment"].params}
    assert commit == {"min_hold": 0, "preempt_margin": 0, "interrupt_at": 0}
