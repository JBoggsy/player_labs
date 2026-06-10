# Experience-request API reference

This is the field-level reference for the `coworld-experience-requests` skill (see
`SKILL.md` for the workflow). An **experience request** is a hosted batch of
episodes you define and the server runs: you pick a **target** (which game / league
/ division), a **roster** (which policies play, in which seats and roles) and a
**count**, POST it, and get back an `xreq_…` handle you poll for progress and then
pull artifacts from (replays, logs, results — via the `coworld-episode-artifacts`
skill).

It explains the **API** and its options so you can compose whatever request you
need — it is not a fixed recipe book; mix the building blocks below as the question
demands. `SKILL.md` has the end-to-end loop (resolve → compose → create → monitor →
analyze) this fits into.

The API is **game-agnostic** (works for any Coworld); only `game_config_overrides`
(e.g. Crewrift's per-slot roles) is game-specific.

> **Always check the live schema first — the API drifts.** Print
> `components.schemas.V2CreateExperienceRequestRequest` from
> `<api-server>/observatory/openapi.json` before composing a body, and treat that
> as the source of truth over this doc. The field list below was read live on
> **2026-06-08**.

## The endpoint

`POST /v2/experience-requests` on the Observatory gateway
(`softmax.auth.get_api_server() + "/observatory"`, today
`https://softmax.com/api/observatory`; auth header `X-Auth-Token`). Three ways to
call it:

```sh
# CLI — body is a JSON file (or '-' for stdin)
uv run coworld xp-request create body.json
uv run coworld xp-request list --mine
uv run coworld xp-request get xreq_... --json
uv run coworld xp-request episodes xreq_...
```

```python
# Python client (handles auth + base URL)
from coworld.api_client import CoworldApiClient
with CoworldApiClient.from_login(server_url="https://softmax.com/api") as client:
    detail = client.create_experience_request(payload)   # -> ExperienceRequestDetail
    detail = client.get_experience_request(detail.id)    # readback / poll
    episodes = client.list_experience_request_episodes(detail.id)
```

```python
# Raw httpx (when you want full control / to follow drift)
import httpx, softmax.auth as auth
api = auth.get_api_server(); base = api.rstrip("/") + "/observatory"
tok = auth.load_current_token(server=api)          # NB: not load_current_cogames_token (removed)
r = httpx.post(base + "/v2/experience-requests", headers={"X-Auth-Token": tok},
               json=payload, timeout=120, follow_redirects=True)
```

## The request body — every field

`V2CreateExperienceRequestRequest` has **`additionalProperties: false`**, so an
unknown key is rejected — send only the fields below (in particular there is **no
`backfill` field**). Group them by what they decide:

### Target — *which game*

Pick one of these (a league/division resolves its canonical Coworld for you):

| field | meaning |
| --- | --- |
| `target.division_id` / `target.division_name` | target division; resolves its league + Coworld |
| `target.league_id` / `target.league_name` | target league; resolves its canonical Coworld (ambiguous names must use the id) |
| `target.coworld_id` (+ `target.variant_id`) | a direct Coworld, for ad-hoc runs off any league |
| top-level `coworld_id` / `variant_id` | shorthand for a direct Coworld target |

### Roster — *which policies play*

Two modes; pick the one that fits who you control:

**A. Requester vs league opponents** (the usual tournament A/B — opponents are *not*
yours, they're current league members):

| field | meaning |
| --- | --- |
| `requester` | your policy: `{policy_version_id}` **or** `{player_id}` / `{player_name}` (caller-owned), plus `slot` (which seat it controls). **`slot` must be ≥ 0** (`Field(ge=0)`; the seat resolver also rejects `< 0`) — there is **no `slot=-1` auto-round-robin**; the only round-robin primitive is `rotate_seats`. |
| `opponents[]` | opponent selectors resolved from **active runnable league memberships**: each `{policy_version_id}` **or** `{player_id}` / `{player_name}` |
| `player_selection` | `top_n` (highest-ranked by recent mean reward) or `random`; how `top_n` auto-picks champions. Ignored if `top_n` unset |
| `top_n` | auto-select this many opponents from the target league instead of (or in addition to) listing them |

**B. Caller-owned explicit roster** (every policy is yours):

| field | meaning |
| --- | --- |
| `policy_version_ids[]` | your runnable policy versions, as the explicit roster |
| `requester_slot` | which seat the first `policy_version_ids` entry (the agent) controls |
| `assignments[]` | explicit slot→policy assignments (arrays of integer policy indices). **Only valid with `policy_version_ids`** |

### Roles & seating

| field | meaning |
| --- | --- |
| `game_config_overrides` | shallow override of the resolved Coworld's game config — each key **replaces** that key in the game config, and the result is validated against the game's own schema. **Crewrift:** `{"slots": [{"role": "imposter"}, {"role": "crew"}, ...]}` forces per-slot roles. `slots` is an **array of objects** (`{"role": "crew"\|"imposter", "color"?, "token"?}`), **not** bare strings; supply the **full** array (the merge replaces the whole key), slot 0 = the requester. Full Crewrift schema: [`crewrift-gameplay.md` → Forcing roles](../../../../crewrift_lab/docs/crewrift-gameplay.md) |
| `rotate_seats` | `true` cyclically rotates the **whole seat-ordered roster** by `episode_index % player_count` each episode (`app_backend/v2/experience_requests.py`). The field's description says "rotates the requester," but in fact **every** player (requester *and* all opponents) visits every seat over `player_count` episodes — a *cyclic shift*, not an independent shuffle (relative order is preserved). Cancels per-seat bias. **It does NOT pin a role:** since Crewrift roles are fixed *by seat* (via `game_config_overrides.slots`), rotating the requester through all seats rotates it through all **roles** too — so you can't "force the requester's role *and* rotate" at once. |

### Volume & execution

| field | meaning |
| --- | --- |
| `num_episodes` | how many episodes (default `1`) |
| `execution_backend` | `k8s` (default) or `antfarm` |
| `notes` | free-text label, handy for finding the request later |

## Building blocks — resolving the IDs

The body needs real IDs. Resolve them live (don't hardcode — they rotate):

```sh
uv run coworld leagues --json                       # GET /v2/leagues
uv run coworld divisions --league <league_id> --json
uv run coworld results <division_id> --json         # standings (the leaderboard)
uv run coworld memberships --division <division_id> --active-only --json
```

Underlying routes (raw): `GET /v2/leagues`, `GET /v2/divisions`,
`GET /v2/divisions/{id}/leaderboard` (current champions, ranked by recent mean
reward), `GET /v2/league-policy-memberships?division_id=…&active_only=true&limit=1000`
(the active runnable opponents). Resolve a policy **name → version id** with
`GET /stats/policy-versions?name_exact=<name>` (each row has `id`, `version`).

`opponents` accept `player_name`, so you often don't need their policy_version_ids —
list names from the leaderboard/memberships and let the server resolve the active
runnable version.

## Composition — examples to adapt (not a fixed menu)

**Your policy vs the live division's top 7 champions** (auto-select; random roles):

```json
{
  "target": {"division_id": "div_…"},
  "requester": {"policy_version_id": "<your pv id>", "slot": 0},
  "player_selection": "top_n",
  "top_n": 7,
  "num_episodes": 100,
  "notes": "crewborg vs the live top-7, random roles"
}
```

**Vs explicit, named opponents** (stable, reproducible roster) — swap the
auto-select for a list:

```json
{
  "target": {"division_id": "div_…"},
  "requester": {"player_name": "Player One", "slot": 0},
  "opponents": [{"player_name": "notsus"}, {"player_name": "evidencebot"}],
  "num_episodes": 50
}
```

**Force roles (Crewrift)** — `game_config_overrides.slots` is an **array of objects**
(slot 0 = requester); supply the full array. `role` ∈ `{"crew","imposter"}`:

```json
{
  "target": {"division_id": "div_…"},
  "requester": {"policy_version_id": "<your pv id>", "slot": 0},
  "top_n": 7,
  "game_config_overrides": {"slots": [
    {"role": "imposter"}, {"role": "crew"}, {"role": "crew"}, {"role": "crew"},
    {"role": "crew"}, {"role": "crew"}, {"role": "crew"}, {"role": "imposter"}
  ]},
  "num_episodes": 50,
  "notes": "requester forced imposter"
}
```

`create` validates this `slots` shape against the live game config schema before
POSTing (see the tool's `game_config_overrides` check), so a wrong shape fails locally
with a clear message instead of as an opaque 400.

**Cancel seat bias** — add `"rotate_seats": true` to cyclically rotate the whole
roster through every seat (see the field note above — it rotates *everyone*, and
won't pin a role). **Ad-hoc, no league** — use `"target": {"coworld_id": "cow_…"}`.

**Round-robin opponents through roles while pinning the requester's role** — no single
field does this (forcing roles by seat fixes opponent seating; `rotate_seats` un-pins
the requester's role). Do it **manually**: use **explicit `opponents`** (fixed order →
fixed seats: requester at its `slot`, opponents fill the rest in list order), then issue
**one request per role-configuration**, cycling the imposter seat(s) across the opponent
seats so each opponent takes the imposter role in some episodes. E.g. for "requester
always imposter," run 7 configs with the *second* imposter at seat 1…7; for "requester
always crew," cycle the two imposter seats over the opponents. (Don't rely on `top_n`
for this — its rank-ordered seating can drift between requests; name the opponents.)
**All-owned roster with fixed seats** — use `policy_version_ids` + `requester_slot`
(+ `assignments`) instead of `requester`/`opponents`.

Mix these freely: target × roster-mode × roles × seating × count are independent
knobs.

## After you POST: readback, poll, pull

The response is `V2ExperienceRequestDetail`: `id` (`xreq_…`), `status`, and the
counts `episode_count` / `pending_count` / `running_count` / `completed_count` /
`failed_count`, plus `episodes[]`.

- **Verify** immediately: `episode_count` matches your `num_episodes`, slot 0 is the
  requester, opponents resolved to the expected names/versions.
- **Poll**: `GET /v2/experience-requests/{id}` until `completed_count + failed_count
  == episode_count`.
- **Child episodes**: `GET /v2/experience-requests/{id}/episodes` (each is an
  `ereq_…` row with participants, scores, status, `job_id`).
- **Artifacts**: pull replays / logs / results per episode with the
  `coworld-episode-artifacts` skill (key off `job_id`), then analyze the per-episode
  `scores` / `participants` (and replays/logs) however the question needs.

## Gotchas

- **`additionalProperties: false`** — no stray keys. Don't send `backfill` (gone);
  explicit `requester` + `opponents` already avoids any server backfill behavior.
- **Ownership.** `requester` and `policy_version_ids` must be **caller-owned**;
  `opponents` are resolved from the target league's active memberships. Use
  `requester` + `opponents` for non-owned tournament opponents; `policy_version_ids`
  only for rosters you fully own.
- **`assignments` only with `policy_version_ids`.** With `top_n`/league opponents,
  control roles via `game_config_overrides.slots` and (optionally) `rotate_seats`,
  not `assignments`.
- **POST-then-404 replica lag.** A freshly created request can 404 on readback for a
  beat. If the POST body contained an `xreq_…` id, retry the GET before assuming
  failure.
- **Auth drift.** Use `softmax.auth.load_current_token(server=…)`; the older
  `load_current_cogames_token(api_server=…)` was removed.
- **Schema drift.** Re-print the live `V2CreateExperienceRequestRequest` before any
  real submission; `coworld`'s create helpers validate payload keys against live
  OpenAPI (use a dry-run/`--check-schema` path when testing drift).
