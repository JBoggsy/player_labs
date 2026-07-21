"""Cross-check PLAYER_COLOR_NAMES against the game source at the deployed ref.

The game renamed its player palette on 2026-06-24 (coworld-crewrift 1cbd4de) and
crewborg's ``PLAYER_COLOR_NAMES`` silently kept the old names for a month — every
slot >= 1 mis-labelled — until the v107 audit caught it (fixed in 2a13256). This
test turns the next palette rename into a test failure instead of a silent bug:
it parses ``PlayerColorNames`` out of the crewrift source cache that
``tools/build_expand_replay.sh`` fetches (``crewrift_lab/.cache/crewrift-src/<ref>``)
and diffs it against ``perception/constants.py``.

DEPLOYED_REF tracks the league's deployed game (see tools/versions.env — the
CREWRIFT_REF comment block explains why the build pin itself stays behind). Bump
it here when the league redeploys and you've fetched the new source
(``tools/build_expand_replay.sh --ref <new>``).

Skips when the source cache is absent (fresh clone / CI without the .cache dir),
so it only guards machines that actually have the deployed source on disk.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from crewrift.crewborg.perception.constants import PLAYER_COLOR_NAMES

# The league's deployed game version: v0.4.68 = commit 34a97a3 (as of 2026-07-21).
DEPLOYED_REF = "34a97a3"

_LAB_ROOT = Path(__file__).resolve().parents[3]  # crewrift_lab/
SIM_NIM = _LAB_ROOT / ".cache" / "crewrift-src" / DEPLOYED_REF / "src" / "crewrift" / "sim.nim"


def _parse_player_color_names(source: str) -> tuple[str, ...]:
    """Extract the ``PlayerColorNames* = [ "red", ... ]`` string list from sim.nim."""
    match = re.search(r"PlayerColorNames\*\s*=\s*\[(.*?)\]", source, re.DOTALL)
    assert match, "PlayerColorNames list not found in sim.nim — did the game move it?"
    return tuple(re.findall(r'"([^"]*)"', match.group(1)))


@pytest.mark.skipif(
    not SIM_NIM.exists(),
    reason=f"crewrift source cache absent ({SIM_NIM}); "
    f"fetch it: tools/build_expand_replay.sh --ref {DEPLOYED_REF}",
)
def test_player_color_names_match_deployed_game_source() -> None:
    game_names = _parse_player_color_names(SIM_NIM.read_text())
    assert game_names, "parsed an empty PlayerColorNames list from sim.nim"
    assert PLAYER_COLOR_NAMES == game_names, (
        f"PLAYER_COLOR_NAMES is out of sync with the deployed game ({DEPLOYED_REF}). "
        f"The game renders/labels players by ITS list; update perception/constants.py. "
        f"ours={PLAYER_COLOR_NAMES} game={game_names}"
    )
