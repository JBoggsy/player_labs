"""harvest_liars.py — the liar-ledger telemetry consumer.

Contract: scan harvested telemetry (loose telemetry.jsonl and
policy_artifact_*.zip archives) for domain.honor_liar events, dedupe the
per-tick repeats to distinct (episode, color) lies, GATE each lie on the
episode's results.json ground truth (the in-game witness has measured false
positives — an honest member must never be distrusted from our own bad
eyesight), aggregate per pubkey, and render the crewborg-honor-distrust/v1
document the agent's strategy/honor_society.py distrust seam loads.
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from harvest_liars import DISTRUST_SCHEMA, PALETTE, render_distrust, scan_liars  # noqa: E402


LIAR_PUB = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _liar_line(pub: str, color: str, tick: int = 100) -> str:
    return json.dumps({
        "kind": "trace", "tick": tick,
        "event": "domain.honor_liar", "name": "domain.honor_liar",
        "data": {"color": color, "pub": pub},
    })


def _noise_lines() -> list[str]:
    return [
        json.dumps({"kind": "trace", "tick": 1, "event": "domain.honor_claim",
                    "name": "domain.honor_claim", "data": {"color": "red", "pub": LIAR_PUB}}),
        json.dumps({"kind": "trace", "tick": 2, "event": "domain.phase_change",
                    "name": "domain.phase_change", "data": {"from": "Lobby", "to": "Playing"}}),
        "not json at all {",
        # honor_liar as a substring of other content must not count:
        json.dumps({"kind": "trace", "tick": 3, "event": "domain.chat_received",
                    "name": "domain.chat_received", "data": {"text": "honor_liar hoax"}}),
    ]


def _results(imposter_colors: set[str]) -> str:
    """A results.json where exactly the given palette colors' slots are imposters."""

    return json.dumps({"imposter": [1 if PALETTE[i] in imposter_colors else 0 for i in range(8)]})


def _write_episode(root: Path, name: str, lines: list[str], *, zipped: bool,
                   results: str | None = None) -> None:
    ep = root / "episodes" / name
    if zipped:
        art = ep / "artifacts"
        art.mkdir(parents=True)
        with zipfile.ZipFile(art / "policy_artifact_0.zip", "w") as zf:
            zf.writestr("telemetry.jsonl", "\n".join(lines) + "\n")
    else:
        ep.mkdir(parents=True)
        (ep / "telemetry.jsonl").write_text("\n".join(lines) + "\n")
    if results is not None:
        (ep / "results.json").write_text(results)


def test_scan_finds_liars_in_loose_and_zipped_telemetry(tmp_path) -> None:
    root = tmp_path / "episodes"
    _write_episode(tmp_path, "ep_loose", _noise_lines() + [_liar_line(LIAR_PUB, "green")],
                   zipped=False, results=_results({"green"}))
    _write_episode(tmp_path, "ep_zipped", [_liar_line(LIAR_PUB, "red")],
                   zipped=True, results=_results({"red"}))
    liars, sources, episodes = scan_liars([root])
    assert sources == 2 and episodes == 2
    assert set(liars) == {LIAR_PUB}
    entry = liars[LIAR_PUB]
    assert entry["events"] == 2                       # one confirmed lie per episode
    assert entry["episodes"] == {"ep_loose", "ep_zipped"}
    assert entry["colors"] == {"green", "red"}
    assert entry["refuted"] == 0 and entry["unverified"] == 0


def test_scan_refutes_witness_errors_via_results_ground_truth(tmp_path) -> None:
    # The accused color's seat was actually CREW: a witness misattribution, not a
    # lie. It must be tallied as refuted and NEVER reach the distrust list.
    _write_episode(tmp_path, "ep1", [_liar_line(LIAR_PUB, "green")],
                   zipped=False, results=_results(set()))  # nobody imposter
    liars, _, episodes = scan_liars([tmp_path / "episodes"])
    entry = liars[LIAR_PUB]
    assert entry["events"] == 0 and entry["refuted"] == 1
    doc = render_distrust(liars, episodes)
    assert doc["liars"] == []                          # refuted-only key: not distrusted


def test_scan_marks_resultless_events_unverified(tmp_path) -> None:
    _write_episode(tmp_path, "ep1", [_liar_line(LIAR_PUB, "green")], zipped=False)  # no results.json
    liars, _, episodes = scan_liars([tmp_path / "episodes"])
    entry = liars[LIAR_PUB]
    assert entry["events"] == 0 and entry["unverified"] == 1
    assert render_distrust(liars, episodes)["liars"] == []  # fail-closed toward trust


def test_scan_dedupes_per_tick_repeats(tmp_path) -> None:
    # The in-game liar sweep re-emits honor_liar every meeting tick; the harvest
    # counts distinct (episode, color) lies, not raw lines.
    lines = [_liar_line(LIAR_PUB, "green", tick=t) for t in (100, 101, 102, 500)]
    _write_episode(tmp_path, "ep1", lines, zipped=False, results=_results({"green"}))
    liars, _, _ = scan_liars([tmp_path / "episodes"])
    assert liars[LIAR_PUB]["events"] == 1


def test_scan_empty_corpus_is_clean(tmp_path) -> None:
    _write_episode(tmp_path, "ep1", _noise_lines(), zipped=True)
    (tmp_path / "episodes" / "ep2" / "artifacts").mkdir(parents=True)
    # A zip without telemetry.jsonl (an opponent artifact shape) is skipped.
    with zipfile.ZipFile(tmp_path / "episodes" / "ep2" / "artifacts" / "policy_artifact_1.zip", "w") as zf:
        zf.writestr("other.txt", "hi")
    liars, sources, episodes = scan_liars([tmp_path / "episodes"])
    assert liars == {} and sources == 1


def test_render_distrust_document_shape(tmp_path) -> None:
    _write_episode(tmp_path, "ep1", [_liar_line(LIAR_PUB, "green")],
                   zipped=False, results=_results({"green"}))
    liars, _, episodes = scan_liars([tmp_path / "episodes"])
    doc = render_distrust(liars, episodes)
    assert doc["schema"] == DISTRUST_SCHEMA
    assert doc["episodes_scanned"] == 1
    assert doc["liars"] == [{
        "pub": LIAR_PUB, "lie_events": 1, "episodes": ["ep1"], "colors": ["green"],
        "refuted_witness_errors": 0, "unverified": 0,
    }]
    # The document round-trips through the agent-side loader.
    out = tmp_path / "honor_distrust.json"
    out.write_text(json.dumps(doc))
    from crewrift.crewborg.strategy import honor_society

    old = None
    try:
        import os

        old = os.environ.get(honor_society.ENV_DISTRUST)
        os.environ[honor_society.ENV_DISTRUST] = str(out)
        honor_society.reset_distrust_for_tests()
        assert honor_society.is_distrusted(LIAR_PUB)
    finally:
        import os

        if old is None:
            os.environ.pop(honor_society.ENV_DISTRUST, None)
        else:
            os.environ[honor_society.ENV_DISTRUST] = old
        honor_society.reset_distrust_for_tests()
