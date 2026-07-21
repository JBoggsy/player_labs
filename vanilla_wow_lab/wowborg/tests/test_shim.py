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


def test_richard_environment_maps_character_creation_fields() -> None:
    env = richard_environment(
        Path("/tmp/rt"),
        {
            "KING_NIMROD_CHARACTER_RACE": "orc",
            "KING_NIMROD_CHARACTER_CLASS": "warrior",
            "KING_NIMROD_CHARACTER_GENDER": "male",
        },
    )
    assert env["KING_RICHARD_CHARACTER_RACE"] == "orc"
    assert env["KING_RICHARD_CHARACTER_CLASS"] == "warrior"
    assert env["KING_RICHARD_CHARACTER_GENDER"] == "male"


def test_assets_argument_from_env_or_argv() -> None:
    from wowborg.shim import assets_argument

    # Primary path: the 0.1.31 wrapper exports the asset service URL as env
    assert assets_argument([], {"VANILLA_WOW_ASSET_SERVICE_URL": "http://g/player/assets"}) == (
        "--assets=http://g/player/assets"
    )
    # Fallback: an argv-passed --assets survives
    assert assets_argument(["--assets=http://argv/assets"], {}) == "--assets=http://argv/assets"
    # env wins on conflict (same URL in practice)
    assert assets_argument(
        ["--assets=http://argv/assets"], {"VANILLA_WOW_ASSET_SERVICE_URL": "http://env/assets"}
    ) == "--assets=http://env/assets"
    assert assets_argument([], {}) is None


def test_session_duration_prefers_override_then_deadline(monkeypatch) -> None:
    from wowborg.shim import (
        DEFAULT_DURATION_SECONDS,
        TEARDOWN_MARGIN_SECONDS,
        session_duration_seconds,
    )

    assert session_duration_seconds({}) == DEFAULT_DURATION_SECONDS
    assert (
        session_duration_seconds({"KING_NIMROD_SESSION_DEADLINE_SECONDS": "1000"})
        == 1000 - TEARDOWN_MARGIN_SECONDS
    )
    assert (
        session_duration_seconds(
            {
                "WOWBORG_DURATION_SECONDS": "45",
                "KING_NIMROD_SESSION_DEADLINE_SECONDS": "1000",
            }
        )
        == 45.0
    )
    # tiny deadlines clamp to a sane floor
    assert session_duration_seconds({"KING_NIMROD_SESSION_DEADLINE_SECONDS": "10"}) == 30.0
