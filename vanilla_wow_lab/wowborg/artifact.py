"""Policy-artifact bundle upload — the retention-proof evidence channel.

Hosted platform contract (same one the players SDK's ``TraceOutputs`` uses): the episode
runner injects ``COWORLD_PLAYER_ARTIFACT_UPLOAD_URL``; a policy PUTs a zip there, and the
bundle is later fetchable per slot via ``GET /jobs/{job_id}/policy-artifact/{idx}`` —
policy-scoped and NOT subject to the hosted stdout log cap or the log-retention gap that
blanked our first smoke's evidence (session 3).

We bundle the shim runtime dir's evidence files at session end: our ``trace.jsonl``, the
Nim client's ``action-results.jsonl`` and final ``state.json``/``heartbeat.json``. No
dependency on the players SDK — the upload is a plain PUT (mirrors
``players.player_sdk.trace_outputs._upload_zip``).
"""

from __future__ import annotations

import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ARTIFACT_UPLOAD_ENV = "COWORLD_PLAYER_ARTIFACT_UPLOAD_URL"
BUNDLED_FILES = ("trace.jsonl", "action-results.jsonl", "state.json", "heartbeat.json")


def build_bundle(runtime_dir: Path, zip_path: Path) -> list[str]:
    """Zip the evidence files that exist; returns the member names bundled."""
    members: list[str] = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in BUNDLED_FILES:
            source = runtime_dir / name
            if source.is_file():
                bundle.write(source, arcname=name)
                members.append(name)
    return members


def upload_bundle(zip_path: Path, upload_url: str) -> None:
    if upload_url.startswith("file://"):
        destination = Path(upload_url.removeprefix("file://"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(zip_path, destination)
        return
    if upload_url.startswith(("http://", "https://")):
        request = urllib.request.Request(  # noqa: S310 — runner-provided upload URI
            upload_url,
            data=zip_path.read_bytes(),
            method="PUT",
            headers={"Content-Type": "application/zip"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            response.read()
        return
    raise ValueError(f"unsupported artifact upload URL: {upload_url!r}")


def upload_evidence(runtime_dir: Path, *, upload_url: str | None = None) -> list[str] | None:
    """Bundle + upload; returns bundled member names, or None when no URL is configured.

    Never raises — evidence upload is best-effort and must not fail the slot.
    """
    url = upload_url if upload_url is not None else os.environ.get(ARTIFACT_UPLOAD_ENV)
    if not url:
        return None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "wowborg-evidence.zip"
            members = build_bundle(runtime_dir, zip_path)
            upload_bundle(zip_path, url)
            return members
    except Exception as exc:  # noqa: BLE001
        print(f"WOWBORG-SHIM evidence upload failed (non-fatal): {exc!r}", flush=True)
        return None
