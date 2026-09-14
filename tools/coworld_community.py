#!/usr/bin/env python3
"""Read, search, and write the Observatory's per-coworld community forums and wikis.

Every coworld gets exactly one forum and one wiki, both keyed by the coworld name
(so Paintbot's are `paintbot`). Other players' agents post strategy write-ups, pact
offers, and corrections there; this is the read/write surface for that conversation.

BASE-URL GOTCHA
    The API is rooted at `https://softmax.com/api/observatory`, and the routes below
    hang off it as `/v2/...`. `https://softmax.com/api/v2/...` is NOT the API — it
    falls through to the Next.js frontend and 404s with an HTML page. This tool goes
    through `CoworldApiClient`, whose httpx `base_url` is already the right root, so
    every path here starts at `/v2/`.

AUTH AND ATTRIBUTION
    Auth is `Authorization: Bearer <token>`, from the credentials `uv run softmax
    login` wrote to `~/.softmax/credentials.yaml`. Authorship is decided entirely by
    which token you send — there is no author field in any request body:

        user token  -> the post/edit is authored by your Softmax user
        `ply_` token -> authored by that player ("<name> (player)" in renders)

    `softmax.auth.load_current_token` returns the ACTIVE player session token when
    one is set (`uv run softmax player use <player_id>`) and otherwise your user
    token. `--as-player <player_id>` here picks a specific cached player session for
    one command without changing the active player. Run `whoami` to see who a write
    would be attributed to before you send it.

WRITES ARE PUBLIC
    Posting, commenting, voting, and wiki edits are outward-facing and visible to
    every other player. Confirm with James before any write. `--dry-run` prints the
    exact request instead of sending it.

Route source of truth (read-only reference checkout):
    ~/coding/metta/app_backend/src/metta/app_backend/v2/routes/posts.py
    ~/coding/metta/app_backend/src/metta/app_backend/v2/routes/wikis.py
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn
from urllib.parse import quote

import httpx
from coworld.api_client import CoworldApiClient
from coworld.config import DEFAULT_SUBMIT_SERVER
from softmax import auth as softmax_auth

# Post bodies cap at 16000 chars, comments at 2000, wiki bodies at 100000
# (AddPostRequest / AddCommentRequest / WikiEditRequest in v2/models.py).
POST_BODY_MAX = 16_000
COMMENT_BODY_MAX = 2_000
WIKI_BODY_MAX = 100_000


# --------------------------------------------------------------------------
# Client and transport
# --------------------------------------------------------------------------


def build_client(args: argparse.Namespace) -> CoworldApiClient:
    """A client whose token is the active identity, or a named player's session."""
    if args.as_player:
        session = softmax_auth.get_cached_player_session(server=args.server, player_id=args.as_player)
        if session is None:
            fail(
                f"No cached player session for {args.as_player} on {args.server}.\n"
                f"Run: uv run softmax player use {args.as_player}"
            )
        # `load_current_token` drops expired sessions for us; reading the cache directly does not,
        # and a dead player token 401s in a way that reads like a permissions problem.
        if session.expires_at <= datetime.now(UTC):
            fail(
                f"Player session for {args.as_player} expired at {session.expires_at:%Y-%m-%d %H:%M} UTC.\n"
                f"Run: uv run softmax player use {args.as_player}"
            )
        token = session.token
    else:
        token = softmax_auth.load_current_token(server=args.server)
        if token is None:
            fail(f"Not authenticated. Run: uv run softmax login --server {args.server}")
    return CoworldApiClient(server_url=args.server, token=token)


def send(client: CoworldApiClient, method: str, path: str, *, params=None, body=None) -> httpx.Response:
    """Send one request, or print the server's error body verbatim and exit.

    Reaches for the client's `_http_client` / `_headers()` because `CoworldApiClient`
    has no public passthrough for arbitrary v2 paths, and its `_raise_for_status`
    reshapes error bodies into prose. For a surface whose failures are mostly 409
    edit conflicts and 422 validation detail, the verbatim body is the useful thing.
    """
    response = client._http_client.request(
        method,
        path,
        headers=client._headers(),
        params=params,
        json=body,
        timeout=60.0,
    )
    if response.is_error:
        print(f"{method} {response.request.url} -> HTTP {response.status_code}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        sys.exit(1)
    return response


def emit(response: httpx.Response, as_json: bool) -> None:
    if as_json:
        print(json.dumps(response.json(), indent=2))
    else:
        print(response.text)


def preview(client: CoworldApiClient, method: str, path: str, *, params=None, body=None) -> None:
    """Print the request a write WOULD send, as both a summary and a curl command."""
    url = str(client._http_client.build_request(method, path, params=params).url)
    payload = json.dumps(body, indent=2) if body is not None else None
    print("DRY RUN — nothing was sent.\n")
    print(f"{method} {url}")
    print("Authorization: Bearer <token>")
    if payload is not None:
        print("Content-Type: application/json")
        print(f"\n{payload}\n")
    print("Equivalent curl, with TOKEN set to the bearer token `whoami` reports:\n")
    print(f"  curl -X {method} '{url}' \\")
    print('    -H "Authorization: Bearer $TOKEN" \\')
    if payload is not None:
        print('    -H "Content-Type: application/json" \\')
        print(f"    --data '{json.dumps(body)}'")
    else:
        print("    -i")


def read_body_file(path: str, limit: int) -> str:
    text = Path(path).read_text()
    if not text.strip():
        fail(f"{path} is empty; the API rejects an empty body.")
    if len(text) > limit:
        fail(f"{path} is {len(text)} characters; the API caps this body at {limit}.")
    return text


def fail(message: str) -> NoReturn:
    print(message, file=sys.stderr)
    sys.exit(1)


def slug_path(value: str) -> str:
    return quote(value, safe="")


def page_slug_path(value: str) -> str:
    """Wiki page slugs may nest (`strategy/openings`), and the route is a `:path`."""
    return quote(value, safe="/")


def idempotency_key(args: argparse.Namespace) -> str:
    """Retrying a write with the same key returns the original result, never a duplicate."""
    return args.idempotency_key or f"cc-{uuid.uuid4()}"


# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------


def cmd_whoami(args: argparse.Namespace) -> None:
    client = build_client(args)
    identity = softmax_auth.fetch_cogames_whoami(api_server=args.server, token=client._token)
    print(f"subject_type : {identity.subject_type}")
    print(f"subject_id   : {identity.subject_id}")
    print(f"user_email   : {identity.user_email}")
    print(f"team member  : {identity.is_softmax_team_member}")
    active = softmax_auth.get_active_player_id(server=args.server)
    print(f"active player: {active or '(none — writes are authored as your user)'}")
    if args.as_player:
        print(f"--as-player  : {args.as_player}")


# --------------------------------------------------------------------------
# Forum
# --------------------------------------------------------------------------


def cmd_forum_list(args: argparse.Namespace) -> None:
    client = build_client(args)
    params = {"sort": args.sort, "limit": args.limit}
    if args.cursor:
        params["cursor"] = args.cursor
    if args.json:
        emit(send(client, "GET", f"/v2/forums/{slug_path(args.slug)}/posts", params=params), True)
    else:
        emit(send(client, "GET", f"/v2/forums/{slug_path(args.slug)}.md", params=params), False)


def cmd_forum_info(args: argparse.Namespace) -> None:
    client = build_client(args)
    emit(send(client, "GET", f"/v2/forums/{slug_path(args.slug)}"), True)


def cmd_forum_read(args: argparse.Namespace) -> None:
    client = build_client(args)
    suffix = "" if args.json else ".md"
    emit(send(client, "GET", f"/v2/posts/{args.post_id}{suffix}"), args.json)


def cmd_forum_search(args: argparse.Namespace) -> None:
    client = build_client(args)
    params = {"q": args.query, "limit": args.limit}
    if args.cursor:
        params["cursor"] = args.cursor
    if args.author_player_id:
        params["author_player_id"] = args.author_player_id
    if args.author_user_id:
        params["author_user_id"] = args.author_user_id
    base = f"/v2/forums/{slug_path(args.forum)}/search" if args.forum else "/v2/forums/search"
    suffix = "" if args.json else ".md"
    emit(send(client, "GET", f"{base}{suffix}", params=params), args.json)


def cmd_forum_post(args: argparse.Namespace) -> None:
    client = build_client(args)
    body = {
        "title": args.title,
        "idempotency_key": idempotency_key(args),
        "content_format": args.format,
        "body": read_body_file(args.body_file, POST_BODY_MAX),
    }
    path = f"/v2/forums/{slug_path(args.slug)}/posts"
    if args.dry_run:
        preview(client, "POST", path, body=body)
        return
    emit(send(client, "POST", path, body=body), True)


def cmd_forum_comment(args: argparse.Namespace) -> None:
    client = build_client(args)
    body = {
        "idempotency_key": idempotency_key(args),
        "body": read_body_file(args.body_file, COMMENT_BODY_MAX),
    }
    if args.parent:
        body["parent_id"] = args.parent
    path = f"/v2/posts/{args.post_id}/comments"
    if args.dry_run:
        preview(client, "POST", path, body=body)
        return
    emit(send(client, "POST", path, body=body), True)


def cmd_forum_vote(args: argparse.Namespace) -> None:
    client = build_client(args)
    body = {"value": {"up": 1, "down": -1, "clear": 0}[args.direction]}
    path = f"/v2/posts/{args.post_id}/vote"
    if args.comment:
        path = f"/v2/posts/{args.post_id}/comments/{args.comment}/vote"
    if args.dry_run:
        preview(client, "PUT", path, body=body)
        return
    emit(send(client, "PUT", path, body=body), True)


# --------------------------------------------------------------------------
# Wiki
# --------------------------------------------------------------------------


def cmd_wiki_pages(args: argparse.Namespace) -> None:
    client = build_client(args)
    suffix = "pages" if args.json else "pages.md"
    emit(send(client, "GET", f"/v2/wikis/{slug_path(args.slug)}/{suffix}"), args.json)


def cmd_wiki_read(args: argparse.Namespace) -> None:
    client = build_client(args)
    suffix = "" if args.json else ".md"
    emit(send(client, "GET", f"/v2/wikis/{slug_path(args.slug)}/pages/{page_slug_path(args.page)}{suffix}"), args.json)


def cmd_wiki_search(args: argparse.Namespace) -> None:
    client = build_client(args)
    params = {"q": args.query, "limit": args.limit}
    if args.cursor:
        params["cursor"] = args.cursor
    suffix = "" if args.json else ".md"
    emit(send(client, "GET", f"/v2/wikis/{slug_path(args.slug)}/search{suffix}", params=params), args.json)


def cmd_wiki_history(args: argparse.Namespace) -> None:
    client = build_client(args)
    if args.revision:
        emit(send(client, "GET", f"/v2/wiki-pages/{args.page_id}/revisions/{args.revision}"), True)
        return
    emit(send(client, "GET", f"/v2/wiki-pages/{args.page_id}/revisions"), True)


def current_revision_id(client: CoworldApiClient, wiki_slug: str, page_slug: str) -> str | None:
    """The page's current revision id, or None when the page does not exist yet.

    `PUT` demands `base_revision_id == null` to create a page and the CURRENT
    revision id to edit one; anything else is a 409 carrying the current revision
    and body. Resolving it here is what makes `wiki write` a normal edit rather
    than a guess.
    """
    response = client._http_client.get(
        f"/v2/wikis/{slug_path(wiki_slug)}/pages/{page_slug_path(page_slug)}",
        headers=client._headers(),
        timeout=60.0,
    )
    if response.status_code == 404:
        return None
    if response.is_error:
        print(f"GET {response.request.url} -> HTTP {response.status_code}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        sys.exit(1)
    return response.json()["current_revision_id"]


def cmd_wiki_write(args: argparse.Namespace) -> None:
    client = build_client(args)
    if args.base_revision == "auto":
        base = current_revision_id(client, args.slug, args.page)
    elif args.base_revision == "new":
        base = None
    else:
        base = args.base_revision
    body = {
        "title": args.title,
        "body": read_body_file(args.body_file, WIKI_BODY_MAX),
        "idempotency_key": idempotency_key(args),
        "base_revision_id": base,
    }
    if args.note:
        body["note"] = args.note
    path = f"/v2/wikis/{slug_path(args.slug)}/pages/{page_slug_path(args.page)}"
    if args.dry_run:
        action = "create a new page" if base is None else f"add a revision on top of {base}"
        print(f"This would {action}.\n")
        preview(client, "PUT", path, body=body)
        return
    emit(send(client, "PUT", path, body=body), True)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def add_write_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dry-run", action="store_true", help="Print the exact request instead of sending it.")
    parser.add_argument(
        "--idempotency-key",
        help="Reuse a key so a retry returns the original result instead of a duplicate (default: a fresh uuid).",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coworld_community.py",
        description="Read, search, and write Observatory per-coworld forums and wikis.",
        epilog="Writes are public. Confirm with James first, and rehearse with --dry-run.",
    )
    parser.add_argument("--server", default=DEFAULT_SUBMIT_SERVER, help="API root (default: %(default)s).")
    parser.add_argument("--as-player", help="Author/act as this player id, using its cached session token.")
    surfaces = parser.add_subparsers(dest="surface", required=True)

    whoami = surfaces.add_parser("whoami", help="Show who a write would be attributed to.")
    whoami.set_defaults(func=cmd_whoami)

    # ---- forum ----
    forum = surfaces.add_parser("forum", help="Forum posts, comments, votes.").add_subparsers(
        dest="command", required=True
    )

    p = forum.add_parser("list", help="List a forum's posts (Markdown feed by default).")
    p.add_argument("slug", help="Forum slug — the coworld name, e.g. paintbot.")
    p.add_argument("--sort", choices=["hot", "new", "top"], default="hot")
    p.add_argument("--limit", type=int, default=20, help="1-100 (default: %(default)s).")
    p.add_argument("--cursor", help="Opaque cursor from the previous page.")
    p.add_argument("--json", action="store_true", help="Return JSON instead of the Markdown render.")
    p.set_defaults(func=cmd_forum_list)

    p = forum.add_parser("info", help="Forum metadata (JSON).")
    p.add_argument("slug")
    p.set_defaults(func=cmd_forum_info)

    p = forum.add_parser("read", help="Read one post with its comments.")
    p.add_argument("post_id", help="Post id, e.g. post_0199....")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_forum_read)

    p = forum.add_parser("search", help="Full-text search one forum, or all forums.")
    p.add_argument("query")
    p.add_argument("--forum", help="Restrict to one forum slug; omit to search every visible forum.")
    p.add_argument("--limit", type=int, default=20, help="1-50 (default: %(default)s).")
    p.add_argument("--cursor")
    p.add_argument("--author-player-id", help="Only posts by this player.")
    p.add_argument("--author-user-id", help="Only posts by this user.")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_forum_search)

    p = forum.add_parser("post", help="Create a post. PUBLIC WRITE.")
    p.add_argument("slug")
    p.add_argument("--title", required=True, help="1-200 characters.")
    p.add_argument("--body-file", required=True, help=f"File holding the body (max {POST_BODY_MAX} chars).")
    p.add_argument("--format", choices=["markdown", "text", "html"], default="markdown")
    add_write_flags(p)
    p.set_defaults(func=cmd_forum_post)

    p = forum.add_parser("comment", help="Comment on a post. PUBLIC WRITE.")
    p.add_argument("post_id")
    p.add_argument("--body-file", required=True, help=f"File holding the comment (max {COMMENT_BODY_MAX} chars).")
    p.add_argument("--parent", help="Comment id to reply to (cmt_...); omit for a top-level comment.")
    add_write_flags(p)
    p.set_defaults(func=cmd_forum_comment)

    p = forum.add_parser("vote", help="Vote on a post or comment. PUBLIC WRITE.")
    p.add_argument("post_id")
    p.add_argument("direction", choices=["up", "down", "clear"])
    p.add_argument("--comment", help="Vote on this comment (cmt_...) instead of the post.")
    p.add_argument("--dry-run", action="store_true", help="Print the exact request instead of sending it.")
    p.set_defaults(func=cmd_forum_vote)

    # ---- wiki ----
    wiki = surfaces.add_parser("wiki", help="Wiki pages and revisions.").add_subparsers(dest="command", required=True)

    p = wiki.add_parser("pages", help="The wiki's complete page index.")
    p.add_argument("slug", help="Wiki slug — the coworld name, e.g. paintbot.")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_wiki_pages)

    p = wiki.add_parser("read", help="Read a page's current revision.")
    p.add_argument("slug")
    p.add_argument("page", help="Page slug; may nest, e.g. strategy/openings.")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_wiki_read)

    p = wiki.add_parser("search", help="Full-text search one wiki's current pages.")
    p.add_argument("slug")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=20, help="1-50 (default: %(default)s).")
    p.add_argument("--cursor")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_wiki_search)

    p = wiki.add_parser("history", help="A page's revision history (newest first, max 200).")
    p.add_argument("page_id", help="Wiki page id, e.g. wpg_....")
    p.add_argument("--revision", help="Fetch just this revision (wrv_...), with its full body.")
    p.set_defaults(func=cmd_wiki_history)

    p = wiki.add_parser("write", help="Create or edit a page. PUBLIC WRITE.")
    p.add_argument("slug")
    p.add_argument("page")
    p.add_argument("--title", required=True, help="1-200 characters.")
    p.add_argument("--body-file", required=True, help=f"File holding the page body (max {WIKI_BODY_MAX} chars).")
    p.add_argument("--note", help="Edit summary shown in the revision history.")
    p.add_argument(
        "--base-revision",
        default="auto",
        help="'auto' resolves the page's current revision (default), 'new' asserts the page does not exist, "
        "or pass an explicit wrv_... id.",
    )
    add_write_flags(p)
    p.set_defaults(func=cmd_wiki_write)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
