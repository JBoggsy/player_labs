"""Tests for Cady's entry-point URL handling."""

from __future__ import annotations

from cady.main import _with_username


def test_with_username_appends_to_existing_query() -> None:
    url = "ws://host:8080/sprite_player?slot=2&token=abc"
    out = _with_username(url, "Cady")
    assert out.startswith("ws://host:8080/sprite_player?")
    assert "slot=2" in out and "token=abc" in out
    assert "username=Cady" in out


def test_with_username_when_no_query() -> None:
    assert _with_username("ws://host/sprite_player", "Cady") == "ws://host/sprite_player?username=Cady"


def test_with_username_replaces_existing() -> None:
    out = _with_username("ws://h/p?username=old&token=x", "Cady")
    assert "username=Cady" in out and "username=old" not in out and "token=x" in out
