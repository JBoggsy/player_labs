#!/usr/bin/env python3
"""Download episode metadata, results, replay and accessible per-seat diagnostics.

Current routes are episode-request scoped. Legacy episode records resolve their
job ID through /v2/episode-requests/by-job/{job_id}. No watch URL is treated as
replay bytes. Normal participant access only; private opponent data is excluded.
See ../references/endpoint-map.md for the API contract and completeness rules.
"""

from __future__ import annotations

import argparse
import json
from itertools import islice
import sys
import time
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx


def log(msg: str) -> None:
    """Progress to stderr so stdout stays clean for any future piping."""
    print(msg, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- #
# Auth + server resolution
# --------------------------------------------------------------------------- #

def _softmax_auth():
    try:
        import softmax.auth as auth
    except ImportError as exc:  # pragma: no cover - environment guard
        sys.exit(f"Could not import softmax.auth ({exc}). Run inside `uv run`.")
    return auth


def default_server() -> str:
    """The official Observatory gateway, tracking wherever the user is logged in.

    `get_api_server()` is the login host the `coworld` CLI talks to (today
    https://softmax.com/api); the Observatory data API lives under its
    `/observatory` path. Deriving it here means this script follows the user's
    `softmax login` rather than hard-coding a host.
    """
    return _softmax_auth().get_api_server().rstrip("/") + "/observatory"


def load_token() -> str:
    """Return the current softmax auth token, or exit with a clear message.

    NB the current softmax.auth API is `load_current_token(server=...)`. Older
    tools call `load_current_cogames_token(api_server=...)`, which has been
    removed -- if you copy auth code from elsewhere and it errors, this is why.
    """
    auth = _softmax_auth()
    token = auth.load_current_token(server=auth.get_api_server())
    if not token:
        sys.exit("Not authenticated. Run: uv run softmax login")
    return token


# --------------------------------------------------------------------------- #
# HTTP client
# --------------------------------------------------------------------------- #

class Client:
    """Thin authenticated httpx wrapper over the Observatory data API."""

    def __init__(self, server: str, token: str, elevated: bool = False) -> None:
        headers = {"X-Auth-Token": token}
        if elevated:
            raise ValueError("Elevated access is not permitted for player-lab analysis.")
        self._http = httpx.Client(
            base_url=server.rstrip("/"),
            headers=headers,
            timeout=120.0,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def get_json(self, path: str, **params: Any) -> Any:
        r = self._http.get(path, params=params or None)
        r.raise_for_status()
        return r.json()

    def get_bytes_or_none(self, path: str) -> bytes | None:
        """GET bytes; return None (not raise) on a 4xx so one missing artifact
        does not abort the episode."""
        r = self._http.get(path)
        if r.status_code >= 400:
            return None
        return r.content

    def get_text_or_none(self, path: str) -> str | None:
        r = self._http.get(path)
        if r.status_code >= 400:
            return None
        return r.text


# --------------------------------------------------------------------------- #
# Normalized episode reference
# --------------------------------------------------------------------------- #

@dataclass
class EpisodeRef:
    """One episode plus the handles needed to fetch its artifacts.

    `record` is the raw source row (a league episode record or an
    experience-request episode row); it is written verbatim as episode.json.
    `job_id` resolves legacy records to an episode request. `replay_url` is a
    human watch link, not an artifact download URL.
    """

    ref_id: str                    # episode uuid or ereq_... id
    created_at: str
    job_id: str | None
    replay_url: str | None
    label: str                     # short human label (policy/version/status)
    record: dict[str, Any] = field(default_factory=dict)


def _tags(rec: dict[str, Any]) -> dict[str, Any]:
    return rec.get("tags") or {}


def _ref_from_episode_record(rec: dict[str, Any], label: str = "") -> EpisodeRef:
    """Normalize a `/episodes/{id}` league-episode record."""
    tags = _tags(rec)
    return EpisodeRef(
        ref_id=str(rec["id"]),
        created_at=rec.get("created_at") or "",
        job_id=tags.get("job_id"),
        replay_url=rec.get("replay_url"),
        label=label or "episode",
        record=rec,
    )


def _ref_from_ereq_row(row: dict[str, Any]) -> EpisodeRef:
    """Normalize a `/v2/episode-requests` experience-request episode row."""
    names = ",".join(
        sorted({p.get("policy_name", "?") for p in (row.get("participants") or [])})
    )
    status = row.get("status") or "?"
    return EpisodeRef(
        ref_id=str(row["id"]),
        created_at=row.get("created_at") or "",
        job_id=None if row.get("job_id") is None else str(row.get("job_id")),
        replay_url=row.get("replay_url"),
        label=f"{status} [{names}]" if names else status,
        record=row,
    )


# --------------------------------------------------------------------------- #
# Discovery modes
# --------------------------------------------------------------------------- #

def discover_by_policy(client: Client, name: str, version: int | None, want: int) -> list[EpisodeRef]:
    """Recorded episodes across exact policy versions, newest first.

    Both version and episode lists use current cursor pagination. Fetch full
    episode records only for the final selected IDs to retain identity metadata.
    """
    params: dict[str, Any] = {"name_exact": name}
    if version is not None:
        params["version"] = version
    versions = list(cursor_rows(client, "/stats/policy-versions", **params))
    if not versions:
        raise ValueError(f"No policy versions found for {name!r}, version={version}")
    selected: dict[str, dict] = {}
    for pv in versions:
        for row in islice(cursor_rows(client, f"/v2/policy-versions/{pv['id']}/episodes"), want):
            selected.setdefault(row["id"], row)
    ordered = sorted(selected.values(), key=lambda row: row.get("created_at") or "", reverse=True)[:want]
    return [_ref_from_episode_record(client.get_json(f"/episodes/{row['id']}"), label=name)
            for row in ordered]


def discover_by_ereq(client: Client, ereq_ids: list[str]) -> list[EpisodeRef]:
    """Explicit experience-request episode rows by id."""
    refs: list[EpisodeRef] = []
    for eid in ereq_ids:
        try:
            row = client.get_json(f"/v2/episode-requests/{eid}")
        except httpx.HTTPStatusError as exc:
            log(f"  ! {eid}: {exc}")
            continue
        refs.append(_ref_from_ereq_row(row))
    return refs


def discover_by_xreq(client: Client, xreq_id: str, want: int) -> list[EpisodeRef]:
    """All child episodes of one experience request, newest first."""
    rows = client.get_json(f"/v2/experience-requests/{xreq_id}/episodes")
    rows = rows if isinstance(rows, list) else rows.get("entries", [])
    refs = [_ref_from_ereq_row(r) for r in rows]
    refs.sort(key=lambda e: e.created_at, reverse=True)
    return refs[:want]


def discover_by_container(
    client: Client,
    *,
    pool_id: str | None,
    round_ids: list[str],
    division_id: str | None,
    want: int,
) -> list[EpisodeRef]:
    """Discover current round episodes, optionally resolving a division's rounds."""
    if pool_id:
        raise ValueError("Pool discovery was removed upstream; supply --round or --division.")
    if division_id:
        if round_ids:
            raise ValueError("Choose --round or --division, not both.")
        round_ids = [r["id"] for r in cursor_rows(client, "/v2/rounds", division_id=division_id)]
    by_id: dict[str, EpisodeRef] = {}
    for round_id in round_ids:
        for row in cursor_rows(client, f"/v2/rounds/{round_id}/episodes"):
            ref = _ref_from_ereq_row(row)
            by_id.setdefault(ref.ref_id, ref)
    return sorted(by_id.values(), key=lambda e: e.created_at, reverse=True)[:want]


def cursor_rows(client: Client, path: str, **params: Any):
    """Read every page of a current cursor-paginated endpoint."""
    while True:
        page = client.get_json(path, limit=100, **params)
        yield from page["entries"]
        cursor = page.get("next_cursor")
        if not cursor:
            return
        params["cursor"] = cursor


def discover_by_episode(client: Client, episode_ids: list[str]) -> list[EpisodeRef]:
    """Explicit league episode records by uuid."""
    refs: list[EpisodeRef] = []
    for eid in episode_ids:
        try:
            rec = client.get_json(f"/episodes/{eid}")
        except httpx.HTTPStatusError as exc:
            log(f"  ! {eid}: {exc}")
            continue
        refs.append(_ref_from_episode_record(rec))
    return refs


# --------------------------------------------------------------------------- #
# Per-episode artifact download (keyed off job_id)
# --------------------------------------------------------------------------- #

def _write_replay(content: bytes, out_dir: Path) -> None:
    """Write the raw replay blob plus its decompressed form.

    Replays are served zlib-compressed (magic 0x78). We keep the raw blob as
    replay.json.z and write the decompressed bytes as replay.json -- the
    directly-loadable form (it is the game's binary replay, named .json only to
    match what `coworld run-episode` writes and the replay-viewer recipe loads).
    """
    (out_dir / "replay.json.z").write_bytes(content)
    try:
        decompressed = zlib.decompress(content)
    except zlib.error:
        decompressed = content  # already uncompressed (defensive)
    (out_dir / "replay.json").write_bytes(decompressed)


def episode_dirname(ref: EpisodeRef) -> str:
    stamp = ref.created_at.replace(":", "").replace("-", "").replace(".", "")[:15]
    short = ref.ref_id[:16] if ref.ref_id.startswith("ereq_") else ref.ref_id[:8]
    return f"{stamp}_{short}"


def episode_is_complete(out_dir: Path, want_replay: bool, want_logs: bool,
                        want_artifacts: bool = True, want_results: bool = True) -> bool:
    if not (out_dir / "episode.json").exists():
        return False
    if want_replay and not (out_dir / "replay.json").exists():
        return False
    if want_results and not (out_dir / "results.json").exists():
        return False
    for wanted, marker, flag, directory, template in (
        (want_logs, "policy_logs_checked.json", "has_log", "logs", "policy_agent_{}.log"),
        (want_artifacts, "policy_artifacts_checked.json", "has_artifact", "artifacts", "policy_artifact_{}.zip"),
    ):
        if not wanted:
            continue
        marker_path = out_dir / marker
        if not marker_path.exists():
            return False
        try:
            rows = json.loads(marker_path.read_text())
        except (json.JSONDecodeError, OSError):
            return False  # Interrupted marker writes must be retried, not loop forever.
        if not isinstance(rows, list) or any(not isinstance(row, dict) or "position" not in row for row in rows):
            return False
        if any(row.get(flag) and not (out_dir / directory / template.format(row["position"])).exists()
               for row in rows):
            return False
    return True


def fetch_episode(client: Client, ref: EpisodeRef, out_dir: Path, *,
                  want_replay: bool, want_results: bool, want_logs: bool,
                  want_artifacts: bool = True) -> dict[str, Any]:
    """Contain one episode's transport/parse failure so bounded retries can progress."""
    try:
        return _fetch_episode(client, ref, out_dir, want_replay=want_replay,
                              want_results=want_results, want_logs=want_logs,
                              want_artifacts=want_artifacts)
    except (httpx.HTTPError, json.JSONDecodeError, OSError, ValueError, KeyError, TypeError) as exc:
        return {"ref_id": ref.ref_id, "dir": out_dir.name, "complete": False,
                "errors": [f"{type(exc).__name__}: {exc}"]}


def _fetch_episode(
    client: Client,
    ref: EpisodeRef,
    out_dir: Path,
    *,
    want_replay: bool,
    want_results: bool,
    want_logs: bool,
    want_artifacts: bool = True,
) -> dict[str, Any]:
    """Fetch available artifacts; only complete listings get durable markers.

    A successful empty listing means no accessible uploads, not universal
    visibility. Missing requested results/replay remain incomplete.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "episode.json").write_text(json.dumps(ref.record, indent=2))
    summary: dict[str, Any] = {"ref_id": ref.ref_id, "dir": out_dir.name,
        "results": False, "replay": False, "logs": [], "policy_artifacts": [], "errors": []}
    if ref.ref_id.startswith("ereq_"):
        ereq = ref.ref_id
    elif ref.job_id:
        row = client.get_json(f"/v2/episode-requests/by-job/{ref.job_id}")
        ereq = row["id"]
        (out_dir / "episode_request.json").write_text(json.dumps(row, indent=2))
    else:
        summary["errors"].append("No episode-request ID or job ID; cannot resolve artifact owner.")
        return summary
    base = f"/v2/episode-requests/{ereq}"
    for wanted, kind, filename in ((want_results, "results", "results.json"),
                                   (want_replay, "replay", "replay.json")):
        if not wanted:
            continue
        content = client.get_bytes_or_none(f"{base}/artifacts/{kind}")
        if content is None:
            summary["errors"].append(f"{kind}: unavailable")
        else:
            if kind == "replay":
                _write_replay(content, out_dir)
            else:
                json.loads(content)  # Reject an HTML/login response as results.
                (out_dir / filename).write_bytes(content)
            summary[kind] = True
    if want_logs or want_artifacts:
        for wanted, marker in ((want_logs, "policy_logs_checked.json"),
                               (want_artifacts, "policy_artifacts_checked.json")):
            if wanted:
                (out_dir / marker).unlink(missing_ok=True)
        listing = client.get_text_or_none(f"{base}/policy-artifacts")
        rows = json.loads(listing) if listing is not None else None
        if rows is None:
            summary["errors"].append("Accessible policy diagnostics listing unavailable")
        elif not isinstance(rows, list):
            raise ValueError("Expected policy-artifacts list")
        else:
            for wanted, flag, kind, folder, template, marker, key in (
                (want_logs, "has_log", "policy-logs", "logs", "policy_agent_{}.log", "policy_logs_checked.json", "logs"),
                (want_artifacts, "has_artifact", "policy-artifact", "artifacts", "policy_artifact_{}.zip", "policy_artifacts_checked.json", "policy_artifacts"),
            ):
                if not wanted:
                    continue
                marker_path = out_dir / marker
                marker_path.unlink(missing_ok=True)
                complete = True
                for row in rows:
                    if not row[flag]:
                        continue
                    position, version = row["position"], row["policy_version_id"]
                    content = client.get_bytes_or_none(f"{base}/{version}/{kind}/{position}")
                    if content is None:
                        complete = False
                        summary["errors"].append(f"{kind} seat {position}: unavailable")
                        continue
                    destination = out_dir / folder / template.format(position)
                    destination.parent.mkdir(exist_ok=True)
                    destination.write_bytes(content)
                    summary[key].append(position)
                if complete:
                    marker_path.write_text(json.dumps(rows, indent=2))
    if want_logs:
        content = client.get_bytes_or_none(f"{base}/artifacts/logs")
        if content is not None:
            (out_dir / "game_logs.log").write_bytes(content)
        else:
            summary["errors"].append("Optional combined game log unavailable")
    error = client.get_bytes_or_none(f"{base}/artifacts/error-info")
    if error is not None:
        (out_dir / "error_info.json").write_bytes(error)
    summary["complete"] = (
        (not want_results or summary["results"]) and (not want_replay or summary["replay"])
        and episode_is_complete(out_dir, want_replay, want_logs, want_artifacts, want_results)
    )
    (out_dir / "download.json").write_text(json.dumps(summary, indent=2))
    return summary


# --------------------------------------------------------------------------- #
# Watch mode: stream artifacts out of a still-running experience request
# --------------------------------------------------------------------------- #

# Episode-row statuses that mean the episode will never change again. Unknown
# statuses are treated as still-running (rechecked next pass); once the xreq
# itself is drained, row status is ignored so a stale row can't strand us.
TERMINAL_EPISODE_STATUSES = {"completed", "success", "failed", "error", "cancelled", "canceled"}


def select_watch_fetches(
    refs: list[EpisodeRef],
    out_root: Path,
    attempts: dict[str, int],
    *,
    want_replay: bool,
    want_logs: bool,
    want_artifacts: bool = True,
    want_results: bool = True,
    max_attempts: int,
    xreq_drained: bool,
) -> tuple[list[EpisodeRef], list[EpisodeRef], list[EpisodeRef], list[EpisodeRef]]:
    """Partition an xreq's episodes into (to_fetch, waiting, exhausted, done).

    Pure disk+status logic so it is unit-testable: an episode is `done` when
    its dir passes episode_is_complete, `waiting` while non-terminal (unless
    the whole xreq is drained), `exhausted` after max_attempts error-laden
    fetches, else `to_fetch`.
    """
    to_fetch: list[EpisodeRef] = []
    waiting: list[EpisodeRef] = []
    exhausted: list[EpisodeRef] = []
    done: list[EpisodeRef] = []
    for ref in refs:
        if episode_is_complete(out_root / episode_dirname(ref), want_replay, want_logs, want_artifacts,
                               want_results):
            done.append(ref)
            continue
        status = str(ref.record.get("status") or "").lower()
        if status not in TERMINAL_EPISODE_STATUSES and not xreq_drained:
            waiting.append(ref)
            continue
        if attempts.get(ref.ref_id, 0) >= max_attempts:
            exhausted.append(ref)
            continue
        to_fetch.append(ref)
    return to_fetch, waiting, exhausted, done


def _xreq_drained(detail: dict[str, Any]) -> bool:
    # A failed/cancelled parent can still have children executing or cancelling.
    total = detail.get("episode_count") or 0
    if any(detail.get(key, 0) for key in ("pending_count", "submitted_count", "running_count")):
        return False
    episodes = detail.get("episodes") or []
    if len(episodes) == total and total > 0:
        return all(row.get("status") in {"completed", "failed", "cancelled"} for row in episodes)
    finished = (detail.get("completed_count") or 0) + (detail.get("failed_count") or 0)
    return total > 0 and finished >= total


def _write_watch_index(
    out: Path,
    xreq: str,
    server: str,
    refs: list[EpisodeRef],
    done: list[EpisodeRef],
    exhausted: list[EpisodeRef],
    pending: int,
    drained: bool,
) -> None:
    index = {
        "server": server,
        "selection": {"xreq": xreq, "watch": True},
        "watch": {
            "total": len(refs),
            "fetched": len(done),
            "exhausted": len(exhausted),
            "pending": pending,
            "drained": drained,
        },
        "episodes": [
            {"ref_id": r.ref_id, "dir": episode_dirname(r), "label": r.label} for r in done
        ]
        + [
            {"ref_id": r.ref_id, "exhausted": True, "label": r.label} for r in exhausted
        ],
    }
    (out / "index.json").write_text(json.dumps(index, indent=2))


def watch_loop(
    client: Client,
    args: argparse.Namespace,
    server: str,
    *,
    want_replay: bool,
    want_results: bool,
    want_logs: bool,
    want_artifacts: bool = True,
) -> int:
    """Poll the xreq; fetch each episode as it turns terminal; exit when drained.

    Resume-safe by construction: completeness is judged from disk
    (episode_is_complete), so a killed run just picks up where it left off.
    watch_state.json bounds retries for episodes that fetch with errors
    (e.g. ops-failed episodes with no artifacts).
    """
    args.out.mkdir(parents=True, exist_ok=True)
    state_path = args.out / "watch_state.json"
    attempts: dict[str, int] = {}
    if state_path.exists():
        attempts = json.loads(state_path.read_text())

    while True:
        # One whole poll pass is guarded: a transient network/server hiccup
        # (httpx RemoteProtocolError, a 5xx, a timeout) used to kill the watcher
        # silently mid-stream. The loop is resume-safe by construction, so the
        # right response is to log loudly and retry after the poll interval.
        try:
            detail = client.get_json(f"/v2/experience-requests/{args.xreq}")
            drained = _xreq_drained(detail)
            refs = discover_by_xreq(client, args.xreq, args.num)
            to_fetch, waiting, exhausted, done = select_watch_fetches(
                refs, args.out, attempts,
                want_replay=want_replay, want_logs=want_logs, want_artifacts=want_artifacts,
                want_results=want_results,
                max_attempts=args.max_attempts, xreq_drained=drained,
            )
            for ref in to_fetch:
                ep_dir = args.out / episode_dirname(ref)
                log(f"  [watch] fetching {ref.ref_id[:16]} {ref.label}")
                s = fetch_episode(
                    client, ref, ep_dir,
                    want_replay=want_replay, want_results=want_results, want_logs=want_logs,
                    want_artifacts=want_artifacts,
                )
                for err in s["errors"]:
                    log(f"      ! {err}")
                if s.get("complete") and episode_is_complete(ep_dir, want_replay, want_logs, want_artifacts, want_results):
                    attempts.pop(ref.ref_id, None)
                    done.append(ref)
                else:
                    attempts[ref.ref_id] = attempts.get(ref.ref_id, 0) + 1
                    if attempts[ref.ref_id] >= args.max_attempts:
                        log(f"      ! {ref.ref_id[:16]}: giving up after {args.max_attempts} attempts")
                        exhausted.append(ref)
            state_path.write_text(json.dumps(attempts, indent=2))

            total = min(detail.get("episode_count") or len(refs), args.num)
            pending = max(0, total - len(done) - len(exhausted))
            _write_watch_index(args.out, args.xreq, server, refs, done, exhausted, pending, drained)
            log(f"[watch] fetched {len(done)}/{total} "
                f"(pending {pending}, exhausted {len(exhausted)}, drained={drained})")
            if drained and (pending == 0 or (not waiting and not to_fetch)):
                if pending:
                    log(f"[watch] incomplete: {pending} requested episodes have no fetched terminal record")
                log(f"[watch] done: xreq drained; {len(done)} fetched, {len(exhausted)} without artifacts.")
                return 1 if exhausted or pending else 0
        except httpx.HTTPStatusError as exc:
            if 400 <= exc.response.status_code < 500 and exc.response.status_code != 429:
                log(f"[watch] request cannot be read: {exc}")
                return 1
            log(f"[watch] request temporarily unavailable: {exc}")
        except (httpx.HTTPError, json.JSONDecodeError, OSError) as exc:
            log(f"[watch] !!! poll pass failed ({type(exc).__name__}: {exc}); "
                f"retrying in {args.interval:.0f}s")
        time.sleep(args.interval)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download full Coworld episode artifacts (replay, results, per-agent logs).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sel = parser.add_argument_group("discovery mode (pick exactly one)")
    sel.add_argument("--policy", help="Policy name; downloads that policy's recent league episodes.")
    sel.add_argument("--version", type=int, default=None,
                     help="With --policy: restrict to this policy version (default: all).")
    sel.add_argument("--ereq", action="append", default=[],
                     help="Experience-request episode id (ereq_...). Repeatable.")
    sel.add_argument("--xreq", help="Experience-request id (xreq_...); downloads all its child episodes.")
    sel.add_argument("--pool", help="Retired upstream; use --round, --division or --xreq.")
    sel.add_argument("--round", dest="round_ids", action="append", default=[],
                     help="Round id (round_...). Repeatable; results merge across rounds.")
    sel.add_argument("--division", dest="division_id", help="Division id (div_...).")
    sel.add_argument("--episode", action="append", default=[],
                     help="League episode uuid. Repeatable.")

    parser.add_argument("-n", "--num", type=int, default=None,
                        help="Max episodes for policy/xreq/pool/round/division modes (default 10; "
                             "unlimited in --watch mode).")
    parser.add_argument("-o", "--out", type=Path, default=Path("episode_data"),
                        help="Output directory (one subdir per episode + index.json).")
    parser.add_argument("--server", default=None,
                        help="Observatory API base URL. Default: <api-server>/observatory from `softmax login`.")
    parser.add_argument("--elevated", action="store_true",
                        help="Rejected: player-lab analysis uses normal participant access.")
    parser.add_argument("--no-replay", action="store_true", help="Skip replay downloads.")
    parser.add_argument("--no-results", action="store_true", help="Skip results downloads.")
    parser.add_argument("--no-logs", action="store_true", help="Skip per-agent policy-log downloads.")
    parser.add_argument("--no-artifacts", action="store_true",
                        help="Skip per-player policy-artifact zips (telemetry bundles).")
    parser.add_argument("--force", action="store_true",
                        help="Re-download episodes whose directory already looks complete.")
    parser.add_argument("--watch", action="store_true",
                        help="With --xreq: poll the experience request and download each episode's "
                             "artifacts as it completes; exit when all episodes are terminal and fetched.")
    parser.add_argument("--interval", type=float, default=15.0,
                        help="Watch mode: seconds between polls.")
    parser.add_argument("--max-attempts", type=int, default=3,
                        help="Watch mode: fetch attempts per episode whose artifacts keep erroring.")
    return parser.parse_args(argv)


def resolve_refs(client: Client, args: argparse.Namespace) -> list[EpisodeRef]:
    """Dispatch to exactly one discovery mode based on the selection args."""
    modes = [
        bool(args.policy),
        bool(args.ereq),
        bool(args.xreq),
        bool(args.pool or args.round_ids or args.division_id),
        bool(args.episode),
    ]
    if sum(modes) != 1:
        sys.exit("Pick exactly one discovery mode: --policy | --ereq | --xreq | "
                 "--pool/--round/--division | --episode")

    if args.policy:
        return discover_by_policy(client, args.policy, args.version, args.num)
    if args.ereq:
        return discover_by_ereq(client, args.ereq)
    if args.xreq:
        return discover_by_xreq(client, args.xreq, args.num)
    if args.pool or args.round_ids or args.division_id:
        return discover_by_container(
            client, pool_id=args.pool, round_ids=args.round_ids,
            division_id=args.division_id, want=args.num,
        )
    return discover_by_episode(client, args.episode)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.elevated:
        sys.exit("Elevated access is not permitted for player-lab analysis.")
    if args.num is None:
        args.num = 10**9 if args.watch else 10
    if args.watch and not args.xreq:
        sys.exit("--watch requires --xreq (streaming is per experience request).")
    want_replay = not args.no_replay
    want_results = not args.no_results
    want_logs = not args.no_logs
    want_artifacts = not args.no_artifacts
    server = args.server or default_server()
    args.out.mkdir(parents=True, exist_ok=True)

    if args.watch:
        with Client(server, load_token(), elevated=args.elevated) as client:
            return watch_loop(
                client, args, server,
                want_replay=want_replay, want_results=want_results, want_logs=want_logs,
                want_artifacts=want_artifacts,
            )

    with Client(server, load_token(), elevated=args.elevated) as client:
        refs = resolve_refs(client, args)
        if not refs:
            log("No episodes found for the given selection.")
            return 1
        log(f"Found {len(refs)} episode(s); downloading to {args.out}")

        summaries: list[dict[str, Any]] = []
        for i, ref in enumerate(refs, 1):
            short = ref.ref_id[:16] if ref.ref_id.startswith("ereq_") else ref.ref_id[:8]
            ep_dir = args.out / episode_dirname(ref)
            if not args.force and episode_is_complete(ep_dir, want_replay, want_logs, want_artifacts,
                                                      want_results):
                log(f"  [{i}/{len(refs)}] {short} {ref.label} — already present, skipping")
                summaries.append({"ref_id": ref.ref_id, "dir": ep_dir.name, "skipped": True})
                continue
            log(f"  [{i}/{len(refs)}] {short} {ref.label} {ref.created_at}")
            s = fetch_episode(
                client, ref, ep_dir,
                want_replay=want_replay, want_results=want_results, want_logs=want_logs,
                want_artifacts=want_artifacts,
            )
            for err in s["errors"]:
                log(f"      ! {err}")
            summaries.append(s)

    index = {
        "server": server,
        "selection": {
            k: v for k, v in {
                "policy": args.policy, "version": args.version,
                "ereq": args.ereq or None, "xreq": args.xreq,
                "pool": args.pool, "round": args.round_ids or None, "division": args.division_id,
                "episode": args.episode or None, "num": args.num,
            }.items() if v
        },
        "downloaded": len(summaries),
        "episodes": summaries,
    }
    (args.out / "index.json").write_text(json.dumps(index, indent=2))
    log(f"Done. Wrote {len(summaries)} episode(s) + index.json to {args.out}")
    return 0 if all(s.get("complete") or s.get("skipped") for s in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
