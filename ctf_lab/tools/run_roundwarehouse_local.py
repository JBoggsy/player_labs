"""Run Reporter Lab's CTF roundwarehouse component over local episode artifacts.

This is a host adapter, not a fork of the reporter. Reporter Lab remains the
authoritative implementation: this script supplies its standard Reporter v2
``episodes``, ``platform``, and ``output`` imports, then persists the component's
three emitted parts locally.

Usage:
    uv run --with wasmtime python ctf_lab/tools/run_roundwarehouse_local.py \
        --episodes ctf_lab/scratch/eval_v39_training/episodes_h050 \
        --out ctf_lab/scratch/eval_v39_training/reporter_h050

The component is deliberately an explicit input in the output manifest. Rebuild it
in Reporter Lab when its source changes; do not copy or modify reporter logic here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable

try:
    from wasmtime import Engine, Store, WasiConfig
    from wasmtime.component import Component, Linker, Variant
except ImportError as exc:
    raise SystemExit(
        "wasmtime is required; run this tool with `uv run --with wasmtime python ...`"
    ) from exc


DEFAULT_COMPONENT = (
    Path.home()
    / "coding/role_repos/reporter_lab/.tools/build/ctf-roundwarehouse.component.wasm"
)


@dataclass(frozen=True)
class Episode:
    episode_id: str
    metadata: dict
    results: bytes
    replay: bytes
    source_dir: Path


def _episode_dirs(roots: Iterable[Path]) -> list[Path]:
    found: dict[str, Path] = {}
    for root in roots:
        candidates = [root] if (root / "episode.json").is_file() else root.rglob("episode.json")
        for metadata_path in candidates:
            episode_dir = metadata_path.parent if metadata_path.is_file() else metadata_path
            metadata_file = episode_dir / "episode.json"
            results_file = episode_dir / "results.json"
            replay_file = episode_dir / "replay.json"
            if not (metadata_file.is_file() and results_file.is_file() and replay_file.is_file()):
                continue
            metadata = json.loads(metadata_file.read_text())
            episode_id = metadata.get("id")
            if not episode_id:
                raise ValueError(f"{metadata_file} has no episode id")
            prior = found.get(episode_id)
            if prior is not None and prior != episode_dir:
                raise ValueError(f"duplicate episode {episode_id}: {prior} and {episode_dir}")
            found[episode_id] = episode_dir
    return [found[episode_id] for episode_id in sorted(found)]


def load_episodes(roots: Iterable[Path]) -> list[Episode]:
    episodes = []
    for episode_dir in _episode_dirs(roots):
        metadata = json.loads((episode_dir / "episode.json").read_text())
        episodes.append(
            Episode(
                episode_id=metadata["id"],
                metadata=metadata,
                results=(episode_dir / "results.json").read_bytes(),
                replay=(episode_dir / "replay.json").read_bytes(),
                source_dir=episode_dir,
            )
        )
    if not episodes:
        raise ValueError("no complete episode artifact directories found")
    return episodes


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_component(component_path: Path, episodes: list[Episode]) -> tuple[dict, int]:
    by_id = {episode.episode_id: episode for episode in episodes}
    engine = Engine()
    store = Store(engine)
    wasi = WasiConfig()
    wasi.inherit_stderr()
    scratch = tempfile.mkdtemp(prefix="ctf-roundwarehouse-")
    wasi.preopen_dir(scratch, "/scratch")
    store.set_wasi(wasi)

    component = Component.from_file(engine, component_path)
    linker = Linker(engine)
    linker.add_wasip2()
    root = linker.root()

    episodes_import = root.add_instance("softmax:reporter/episodes@0.1.0")
    episodes_import.add_func(
        "results", lambda _store, episode_id: by_id[episode_id].results
    )
    episodes_import.add_func(
        "replay", lambda _store, episode_id: by_id[episode_id].replay
    )
    episodes_import.close()

    platform = root.add_instance("softmax:reporter/platform@0.1.0")

    def platform_get(_store, path: str, query: str) -> str:
        del query
        prefix = "/v2/episode-requests/"
        if not path.startswith(prefix):
            raise ValueError(f"unexpected platform request: {path}")
        episode_id = path.removeprefix(prefix)
        return json.dumps(by_id[episode_id].metadata)

    platform.add_func("get", platform_get)
    platform.close()

    emitted: dict[str, tuple[str, object]] = {}
    output = root.add_instance("softmax:reporter/output@0.1.0")

    def emit(_store, name: str, value: object) -> None:
        emitted[name] = (value.tag, value.payload)

    def log(_store, level: str, message: str) -> None:
        print(f"[roundwarehouse {level}] {message}", file=sys.stderr)

    output.add_func("emit", emit)
    output.add_func("log", log)
    output.add_func("progress", lambda _store, _percent, _note: None)
    output.close()
    root.close()

    instance = linker.instantiate(store, component)
    request = SimpleNamespace()
    setattr(request, "run-id", "rrun_local_ctf_roundwarehouse")
    setattr(request, "subject", Variant("episodes", [ep.episode_id for ep in episodes]))
    setattr(request, "params", None)
    summary = instance.get_func(store, "run")(store, request)
    if isinstance(summary, str):
        raise RuntimeError(summary)
    return emitted, getattr(summary, "parts-emitted")


def write_outputs(
    output_dir: Path,
    emitted: dict[str, tuple[str, object]],
    *,
    component_path: Path,
    episode_roots: list[Path],
    expected_parts: int,
) -> None:
    expected_names = {"manifest", "events", "player_stats"}
    if set(emitted) != expected_names or expected_parts != len(expected_names):
        raise RuntimeError(
            f"unexpected reporter outputs: names={sorted(emitted)}, parts={expected_parts}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_tag, manifest_payload = emitted["manifest"]
    if manifest_tag != "json":
        raise RuntimeError(f"manifest was {manifest_tag}, expected json")
    reporter_manifest = json.loads(manifest_payload)
    (output_dir / "manifest.json").write_text(
        json.dumps(reporter_manifest, indent=2, sort_keys=True) + "\n"
    )

    for name in ("events", "player_stats"):
        tag, payload = emitted[name]
        if tag != "file":
            raise RuntimeError(f"{name} was {tag}, expected file")
        media_type = getattr(payload, "media-type")
        if media_type != "application/vnd.apache.parquet":
            raise RuntimeError(f"{name} media type was {media_type}")
        (output_dir / f"{name}.parquet").write_bytes(bytes(getattr(payload, "bytes")))

    adapter_manifest = {
        "schema_version": "ctf.local-roundwarehouse-adapter.v1",
        "component_path": str(component_path.resolve()),
        "component_sha256": _sha256(component_path),
        "episode_roots": [str(root.resolve()) for root in episode_roots],
        "reporter_manifest": "manifest.json",
        "outputs": ["events.parquet", "player_stats.parquet"],
    }
    (output_dir / "local_run.json").write_text(
        json.dumps(adapter_manifest, indent=2, sort_keys=True) + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--episodes",
        type=Path,
        action="append",
        required=True,
        help="episode directory or a root containing episode directories; repeatable",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--component",
        type=Path,
        default=Path(os.environ.get("CTF_ROUNDWAREHOUSE_COMPONENT", DEFAULT_COMPONENT)),
    )
    args = parser.parse_args()

    if not args.component.is_file():
        raise SystemExit(f"Reporter component not found: {args.component}")
    episodes = load_episodes(args.episodes)
    print(
        f"Running {args.component} over {len(episodes)} episodes...",
        file=sys.stderr,
        flush=True,
    )
    emitted, parts = run_component(args.component, episodes)
    write_outputs(
        args.out,
        emitted,
        component_path=args.component,
        episode_roots=args.episodes,
        expected_parts=parts,
    )
    reporter_manifest = json.loads((args.out / "manifest.json").read_text())
    print(
        f"Wrote {args.out}: {reporter_manifest['events_written']} events, "
        f"{reporter_manifest['player_stats_rows']} player rows, "
        f"{reporter_manifest['episodes_ok']}/{reporter_manifest['episodes_total']} episodes ok"
    )
    if (
        reporter_manifest["episodes_failed"]
        or reporter_manifest["episodes_ok"] != len(episodes)
    ):
        raise SystemExit("Reporter did not cleanly expand every requested episode")


if __name__ == "__main__":
    main()
