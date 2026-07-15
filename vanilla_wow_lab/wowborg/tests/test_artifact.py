"""Unit tests for the evidence-bundle artifact upload."""

from __future__ import annotations

import zipfile
from pathlib import Path

from wowborg.artifact import build_bundle, upload_evidence


def make_runtime_dir(tmp_path: Path) -> Path:
    rt = tmp_path / "rt"
    rt.mkdir()
    (rt / "trace.jsonl").write_text('{"kind":"session_start"}\n', encoding="utf-8")
    (rt / "action-results.jsonl").write_text('{"sequence":1}\n', encoding="utf-8")
    (rt / "state.json").write_text("{}", encoding="utf-8")
    return rt


def test_build_bundle_includes_only_existing_files(tmp_path: Path) -> None:
    rt = make_runtime_dir(tmp_path)  # no heartbeat.json
    zip_path = tmp_path / "bundle.zip"
    members = build_bundle(rt, zip_path)
    assert members == ["trace.jsonl", "action-results.jsonl", "state.json"]
    with zipfile.ZipFile(zip_path) as bundle:
        assert sorted(bundle.namelist()) == sorted(members)
        assert bundle.read("trace.jsonl") == b'{"kind":"session_start"}\n'


def test_upload_evidence_via_file_url(tmp_path: Path) -> None:
    rt = make_runtime_dir(tmp_path)
    destination = tmp_path / "out" / "evidence.zip"
    members = upload_evidence(rt, upload_url=f"file://{destination}")
    assert members == ["trace.jsonl", "action-results.jsonl", "state.json"]
    with zipfile.ZipFile(destination) as bundle:
        assert "trace.jsonl" in bundle.namelist()


def test_upload_evidence_none_without_url(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("COWORLD_PLAYER_ARTIFACT_UPLOAD_URL", raising=False)
    assert upload_evidence(make_runtime_dir(tmp_path)) is None


def test_upload_evidence_swallows_failures(tmp_path: Path) -> None:
    rt = make_runtime_dir(tmp_path)
    assert upload_evidence(rt, upload_url="ftp://nope") is None
