"""Unit tests for the shim supervisor's pure pieces (no processes, no Nim)."""

from __future__ import annotations

from pathlib import Path

from wowborg.shim import PACKAGED_PLAYER_ROOT, richard_environment


def test_richard_environment_maps_credentials() -> None:
    base = {
        "KING_NIMROD_REALM_HOST": "10.0.0.5",
        "KING_NIMROD_REALM_PORT": "3724",
        "KING_NIMROD_USERNAME": "COWORLD",
        "KING_NIMROD_PASSWORD": "secret",
        "KING_NIMROD_CHARACTER_NAME": "Nightsun",
        "PYTHONPATH": "/existing",
    }
    env = richard_environment(Path("/tmp/rt"), base)
    assert env["KING_RICHARD_REALM_HOST"] == "10.0.0.5"
    assert env["KING_RICHARD_REALM_PORT"] == "3724"
    assert env["KING_RICHARD_USERNAME"] == "COWORLD"
    assert env["KING_RICHARD_PASSWORD"] == "secret"
    assert env["KING_RICHARD_CHARACTER_NAME"] == "Nightsun"


def test_richard_environment_disables_autonomy_and_sets_runtime_dir() -> None:
    env = richard_environment(Path("/tmp/rt"), {})
    assert env["KING_RICHARD_AUTONOMOUS"] == "0"
    assert env["WOW_SDK_NIM_RUNTIME_DIR"] == "/tmp/rt"


def test_richard_environment_prepends_packaged_player_root() -> None:
    env = richard_environment(Path("/tmp/rt"), {"PYTHONPATH": "/existing"})
    assert env["PYTHONPATH"].split(":") == [PACKAGED_PLAYER_ROOT, "/existing"]
    env_no_existing = richard_environment(Path("/tmp/rt"), {})
    assert env_no_existing["PYTHONPATH"] == PACKAGED_PLAYER_ROOT


def test_richard_environment_skips_absent_credentials() -> None:
    env = richard_environment(Path("/tmp/rt"), {"KING_NIMROD_USERNAME": "A"})
    assert env["KING_RICHARD_USERNAME"] == "A"
    assert "KING_RICHARD_PASSWORD" not in env
