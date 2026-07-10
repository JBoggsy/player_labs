# Bug: `POST /v2/experience-requests` returns HTTP 500 — Coworld Manifest reporter fails server-side validation (blocks ALL Heartleaf experience requests)

**Severity:** High — blocks *all* experience-request creation for the Heartleaf coworld
(and likely any coworld sharing the default reporter). Not user-recoverable; nothing in the
request body triggers it.

**Component:** Observatory backend — experience-request creation / Coworld Manifest
(Pydantic) validation, specifically the `reporter` block ("Default Reporter").

**Environment**
- Endpoint: `POST https://softmax.com/api/observatory/v2/experience-requests`
- Coworld: `heartleaf` (v0.1.10), division `div_396961a3-58af-4276-abc7-3f45fb7fe337`
- Reporter image referenced in the error: `img_a711755f-fd27-4235-8d70-634dabecb470`
  ("Default Coworld reporter … generic episode artifacts.")
- Caller: `jmsboggs@gmail.com` (user `xhkpr7aw1f0gwjvc2yl0c5sa`), authenticated; via the
  lab's `experience_request.py create` (a thin `httpx` POST — no reporter field is sent by
  the client).
- Pydantic 2.12.

## Summary

Creating an experience request against Heartleaf fails with **HTTP 500**. The response
body is a Pydantic `ValidationError` with **16 errors**, all under `reporter.0`, where the
server is validating **its own stored manifest's default reporter** against a
`CoworldReporterPlatformReference | CoworldReporterWasmReference` union — and the reporter
object matches **neither** arm. This is a **backend schema ↔ stored-manifest mismatch**, not
a bad client request:

- The reporter object has keys the reference schema now **forbids** (`extra_forbidden`):
  `id`, `name`, `type`, `image`, `env`, `run`, `description`.
- It is **missing** the field each arm now **requires**: `reporter` (PlatformReference) /
  `wasm` + `attributes` (WasmReference).

So the persisted default-reporter shape (`{id, name, type, image, env, run, description}`)
is an *older* schema than the validator the server is currently running. A deploy moved the
`CoworldReporter*Reference` models out from under the data without a migration/serializer
update.

## Reproduction

Any experience request against Heartleaf 500s — including a minimal 1-subject/1-episode
body. The client body contains **no reporter field**; the reporter comes from the server's
coworld manifest.

```json
POST /v2/experience-requests
{
  "target": {"division_id": "div_396961a3-58af-4276-abc7-3f45fb7fe337"},
  "roster": [{"player": {"policy_ref": "cady:v14"}}, {"player": {"random": true}}],
  "num_episodes": 1
}
```

Client-side schema validation of this body **passes** (keys valid); the 500 is raised
server-side while assembling/validating the Coworld Manifest.

## Exact server error (verbatim, first errors of 16)

```
HTTP 500: {"detail":"Failed to create experience request: 16 validation errors for Coworld Manifest
reporter.0.CoworldReporterPlatformReference.reporter
  Field required [type=missing, input_value={'id': 'default-reporter'...ric episode artifacts.'}, input_type=dict]
reporter.0.CoworldReporterPlatformReference.id
  Extra inputs are not permitted [type=extra_forbidden, input_value='default-reporter', input_type=str]
reporter.0.CoworldReporterPlatformReference.env
  Extra inputs are not permitted [type=extra_forbidden, input_value={}, input_type=dict]
reporter.0.CoworldReporterPlatformReference.run
  Extra inputs are not permitted [type=extra_forbidden, input_value=[], input_type=list]
reporter.0.CoworldReporterPlatformReference.name
  Extra inputs are not permitted [type=extra_forbidden, input_value='Default Reporter', input_type=str]
reporter.0.CoworldReporterPlatformReference.type
  Extra inputs are not permitted [type=extra_forbidden, input_value='reporter', input_type=str]
reporter.0.CoworldReporterPlatformReference.image
  Extra inputs are not permitted [type=extra_forbidden, input_value='img_a711755f-fd27-4235-8d70-634dabecb470', input_type=str]
reporter.0.CoworldReporterPlatformReference.description
  Extra inputs are not permitted [type=extra_forbidden, input_value='Default Coworld reporter...eric episode artifacts.', input_type=str]
reporter.0.CoworldReporterWasmReference.wasm
  Field required [type=missing, ...]
reporter.0.CoworldReporterWasmReference.attributes
  Field required [type=missing, ...]
reporter.0.CoworldReporterWasmReference.env / run / name / type / image / description
  Extra inputs are not permitted [type=extra_forbidden, ...]
```

(Both union arms are shown because the input matched neither; the full 16-error payload is
saved alongside this issue at
`/private/tmp/.../scratchpad/xreq_500_full.txt` on the reporting machine.)

## Stored reporter shape vs. what the schema now expects

Persisted default reporter (from the error's `input_value`s):
```json
{
  "id": "default-reporter",
  "name": "Default Reporter",
  "type": "reporter",
  "image": "img_a711755f-fd27-4235-8d70-634dabecb470",
  "env": {},
  "run": [],
  "description": "Default Coworld reporter ... generic episode artifacts."
}
```
Current `CoworldReporterPlatformReference` wants a `reporter` field and forbids
`id/name/type/image/env/run/description`; `CoworldReporterWasmReference` wants
`wasm` + `attributes`. Neither matches.

## Timeline (points at a recent backend deploy)

- **~11:17 local (2026-07-07):** the SAME endpoint worked — a 15-episode Heartleaf request
  (`xreq_0d8e0ab4-168b-4cc2-b068-e44888a0b81d`) created and ran to completion.
- **~1 hour later:** creation started 500ing with the above error, and the read endpoints
  (`GET /v2/experience-requests/{id}` and `/{id}/episodes`) also began returning 500 for
  an in-flight request (`xreq_25d74b9b-2dca-47f7-b375-bdea4a6ee1f4`).
- **Not client-side:** `resolve` (policy/division lookup) and `upload-policy` both work; only
  experience-request create/read for Heartleaf break. So a deploy in that window changed the
  `CoworldReporter*Reference` models (or the manifest assembler) without updating the stored
  default-reporter representation.

## Where to look

- The `CoworldReporter*Reference` Pydantic models (union member of `Coworld Manifest`'s
  `reporter` list) — recent commits that added required `reporter`/`wasm`/`attributes` and
  set `extra="forbid"`.
- The code path that **builds the Coworld Manifest for an experience request** and injects
  the **default reporter** (image `img_a711755f-…`) — it's emitting the legacy
  `{id,name,type,image,env,run,description}` shape.
- Whether the default-reporter record in the DB/registry needs a data migration to the new
  reference shape, or the assembler needs to serialize into the new schema.

## Impact / workaround

- **Impact:** no experience requests can be created for Heartleaf → no evals, no league
  qualification via this path.
- **Workaround:** none client-side (we don't control the reporter block). Do **not** hack the
  manifest around the validator — results wouldn't match production. Needs a backend fix
  (schema/serializer or a data migration of the default reporter).

## Ask

1. Fix the default-reporter serialization (or migrate the stored record) so it satisfies
   `CoworldReporterPlatformReference`/`WasmReference`.
2. Return a 4xx (not 500) when manifest assembly fails validation, so it's diagnosable.
3. Confirm the fix by creating a 1-episode Heartleaf request with the minimal body above.
