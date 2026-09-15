# Softmax platform: verified operating reference

This page records platform contracts, not permission to act. The lab's [workflow](../AGENTS.md) and [preferences](../user_preferences.md) control authorization.

## Find the current contract

1. Read the [official documentation index](https://docs.softmax.com/llms.txt), [API overview](https://docs.softmax.com/api-reference/overview), [rate limits](https://docs.softmax.com/guides/rate-limits).
2. Fetch the [public OpenAPI](https://softmax.com/api/observatory/openapi.json). Its server is `https://softmax.com/api/observatory`. The discovery [API catalog](https://softmax.com/.well-known/api-catalog) points to this specification.
3. Read the target league's `/v2/participate?league_id=…` guide, league settings, and exact Coworld manifest. `/play.md` follows the current Game of the Week; it is not a fixed game guide.
4. Use installed CLI help. On this check, project-local `coworld` was **0.1.47**, `softmax-cli` **0.26.34**, matching PyPI. Distribution name and command name differ: the package is `softmax-cli`, the command is `softmax`.

OpenAPI documents supported public HTTP shapes; it is **not an exhaustive route inventory**. The fetched specification omitted `/whoami`, `/usage/me/credits`, and CLI upload internals, although the first two answered live. Absence from this specification alone does not prove removal. Do not infer undocumented endpoint semantics from a successful request either.

## Identity and visibility

Use saved Softmax credentials through the CLI/client. Raw HTTP uses `Authorization: Bearer …`. `/whoami` returns 200 even anonymously: inspect `subject_type`. User credentials and player sessions are different scopes; selecting another player does not create a new user allowance. Policy upload/XP/submission support player sessions; Coworld upload requires a user credential. See [authentication](https://docs.softmax.com/guides/authentication).

Use ordinary non-elevated access. A public result does not expose every seat's logs or ZIP. `403` is an authorization problem, not automatically expired login; `404` can mean an invisible or absent resource. Some reads still require authentication even for public evidence. Never use team-only debug access to obtain competitor intelligence.

## Three separate budgets

| Budget | What it controls | Evidence |
| --- | --- | --- |
| XP credits | Compute/model allowance, shared per owning user; not a monetary bill | [Credits](xp-credits.md); live account meter |
| HTTP requests and complexity | API traffic, shared across identities owned by the same user | [Official rate-limit guide](https://docs.softmax.com/guides/rate-limits); live headers |
| Episode admission/concurrency | Queued and outstanding jobs; parallel execution is not unlimited | [Current source](https://github.com/Metta-AI/metta/blob/main/app_backend/src/metta/app_backend/job_capacity.py) |

Live user headers showed request capacities **2,400/minute, 36,000/hour**, complexity capacities **24,000/minute, 360,000/hour**, and `X-RateLimit-Mode: enforced`. These are continuously refilling bucket capacities, not fixed-window totals. An ordinary cost-10 endpoint supports 10 requests/second sustained under the hour budget. Read response headers; coordinate all workers using the account.

Source constants allow **100 episodes per XP request**, **100 outstanding XP jobs per user**, and **300 undispatched XP episodes per user**. Queue/concurrency values are source-verified defaults, not a live capacity guarantee. League/global capacity can further delay work.

Honor `Retry-After` on 429 with bounded backoff. A 402 credit denial differs from an HTTP-rate 429 and from a pending-job-cap 429. Preserve the same supported idempotency key and payload when retrying a write; inspect readback after ambiguous failures. See [error handling](https://docs.softmax.com/api-reference/error-handling).

## XP composition and comparability

- Pin Coworld version, variant, exact policy versions, role/seat treatment and seed design. An omitted hosted variant resolves to the first manifest variant in current source; a local run normally uses the certification fixture. These are different defaults.
- Supply one roster entry per intended seat. `policy_ref` fixes a version; `random` and `top_n` draw from eligible champions. Include/exclude filters affect champion selection, not explicit policy seats.
- Current sampling is rank-weighted **without replacement until the eligible pool refills**. Explicit versions are withheld in the initial cycle, but can appear after refill. Seats are not independent draws. Open seats rotate by episode index; an incomplete rotation need not balance seat counts. This is not a guarantee that an XP reproduces every league commissioner's matchmaking.
- An explicit integer `game_config_overrides.seed` pins every episode to that seed. Without it, current source derives seeds from request identity and episode index. Identical bodies in separate requests therefore do not automatically produce paired seeds. Verify actual configs and game determinism.
- `private` defaults to false. A private request can exclude opponents whose policy consent only allows requests visible to their owner. Explicit disallowed selection returns `409 policy_selection_not_allowed`; sampled pools are filtered. Do not silently publish an experiment to get around that rejection. Policy owners can read their own `/v2/policies/{policy_id}/selection-access`.
- `state` exposes `head`/`snapshot` and `player`/`world` selectors. The API forwards it through `coworld_state` game configuration; it does not establish that every game supports arbitrary saved-state exploration. Read the game's schema and persistence contract.

These details were checked in [XP implementation](https://github.com/Metta-AI/metta/blob/main/app_backend/src/metta/app_backend/v2/experience_requests.py), [creation route](https://github.com/Metta-AI/metta/blob/main/app_backend/src/metta/app_backend/v2/routes/experience_requests.py), and [policy selection](https://github.com/Metta-AI/metta/blob/main/app_backend/src/metta/app_backend/v2/policy_selection.py).

## Creation, completion and evidence

`POST /v2/experience-requests` returns before execution finishes. Save its response: `cost_preview` is creation-only and is not reconstructed by later GETs. There is no public pre-create cost-preview endpoint in the checked schema. Our `create --check-schema` checks top-level keys and resolvable game overrides; it is **not full request validation, a cost quote, or admission approval**.

Credit admission subtracts estimates held for active requests from the current balance. Estimates are not spending caps; actual usage can overrun. The account meter's `recent_requests` records **compute only**, not complete per-request model spend. See [credit source](https://github.com/Metta-AI/metta/blob/main/app_backend/src/metta/app_backend/user_credits.py).

A parent can roll up to `failed` as soon as a child fails. **Wait for every child to be terminal**, not just for the parent label. Cancellation is a separate write: the server checks authority, stops dispatch, and cancels child work; cancellation is not instantaneous proof of completed artifact collection. Inspect `can_cancel` rather than deriving authority from visibility.

Use episode requests (`ereq_…`) to account for attempts, including failures. Recorded episode UUIDs are another identity; not every failed attempt has a recorded episode. Follow each route's pagination shape:

| Collection | Continuation |
| --- | --- |
| Policy versions, XP lists, recorded episodes, paged episode-request lists | JSON `next_cursor` |
| Memberships and submissions | `X-Next-Cursor` response header |
| XP `/{id}/episodes` | All child rows; no cursor; `include_game_config` defaults true |
| XP `/{id}/episode-requests` | Paged summary alternative |

[Artifact endpoints](../.claude/skills/coworld-episode-artifacts/references/endpoint-map.md) distinguish raw results/replays, accessible seat listings, seat logs and ZIPs. Replays are optional game-owned bytes, with version-specific viewers. A watch URL is not the artifact. Missing evidence must remain in coverage accounting; the artifact contract does not guarantee a retention period.

## Upload, submission and qualification

Uploading registers a policy version and enters no league. Identical uploads **may reuse** a version: record the returned UUID/reference, not an assumed increment. Container images and game-hosted files have different contracts; see [player build](../player-build.md) and the [official upload guide](https://docs.softmax.com/coworld/build-a-player/upload-and-evaluate).

Submission requests placement. The current CLI supports `--player`, repeatable `--preference`, and `--auto-champion always|never|lineage`; it does not accept a division flag. Read the league's rules and participation guide. Qualification may use a container commissioner or a platform ladder/Temporal workflow, or may not be configured. There is no universal ten-minute qualifier cadence or universal score threshold.

`competing` and `is_champion` are separate fields. `always` does not let an older upload automatically displace a newer champion; `lineage` requires a prior lower version of the same policy under that player. These are source-verified rules, not a promise that every submission becomes champion. [Promotion source](https://github.com/Metta-AI/metta/blob/main/app_backend/src/metta/app_backend/v2/policy_membership_events.py).

Placed memberships can be retired; this does not erase earlier rounds or public history. **Submission is consequential and explicitly gated here, not literally unmodifiable.** Likewise, platform-managed qualification may create its own self-play XP; the lab's no-hosted-self-play preference governs experiments we choose, not platform internals. See [qualification placement](https://github.com/Metta-AI/metta/blob/main/app_backend/src/metta/app_backend/v2/league_policy_memberships.py).

## Community and local evidence

Forums and wikis are keyed by Coworld name, not by each Coworld version. Their public visibility depends on the game's league visibility. Read the [community reference](coworld-community.md) for schema and write limits. Public writes require authorization for the intended action.

Official guides recommend local packaging checks. This lab deliberately skips routine pre-upload gates and uses local runs for focused debugging/mechanism checks and own-policy self-play. That is a **lab preference**, not a platform prohibition on local testing. Local provider calls can use separately billed provider credentials; the “users are not billed” credit statement applies to Softmax-granted XP usage, not all local compute or external services.
