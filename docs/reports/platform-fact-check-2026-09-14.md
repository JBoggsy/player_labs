# Softmax platform fact-check — 2026-09-14

## Outcome

The original modernization was **not a sufficient platform fact-check**. It reconciled local prose and inspected selected schemas, but promoted stale claims about costs, CLI options, qualification and completion. This pass checked the official docs, deployed public OpenAPI, current upstream implementation and existing live resources. It corrected the operating guidance and three shared-tool behaviors. Player behavior and live competition were unchanged.

The durable entry point is [Softmax platform reference](../platform-reference.md), with [XP credits](../xp-credits.md), [player runtime/build](../../player-build.md), and the linked skills.

### Most consequential corrections

1. **XP is granted-credit usage, not a bill or unlimited free capacity.** There are also separate shared HTTP and job-capacity limits. Admission holds for active XP requests can reduce available credits below the displayed balance.
2. **A failed parent is not necessarily a finished batch.** Current backend rollup gives failure precedence even while other children run. The XP monitor and artifact watcher now wait for child completion.
3. **Private experiments need opponent selection consent.** Public policy visibility does not guarantee that policy can be selected into an experiment hidden from its owner. Do not silently change privacy to bypass rejection.
4. **Random seats are not independent draws, and separate requests are not automatically seed-paired.** Corrected both assumptions; removed the claim that random XP always reproduces league matchmaking.
5. **Qualification is not universally a ten-minute container-commissioner loop.** Platform ladders have a separate qualification workflow. Submission is consequential and gated here, but memberships can be retired. Champion promotion depends on mode and version ordering.
6. **Our helpers were losing evidence.** Creation discarded the creation-only estimate; lifecycle listings ignored cursor headers. Both now preserve the necessary information.

## Scope and evidence standards

- **Live:** observed HTTP response for the stated identity and resource sample. This proves that sample, not all deployments, accounts or games.
- **OpenAPI:** present in the deployed public contract. Conditional validators and authorization may require implementation evidence.
- **Source:** implementation read at a pinned revision; not by itself proof the behavior is deployed.
- **Docs/CLI:** official guidance and/or current installed command help; not a successful execution of the command.
- **Unresolved:** insufficient evidence, or the relevant write/runtime action was not performed.

Retrieved **all 31 Markdown pages in the official documentation index**, plus discovery catalogs and `/play.md`. Reviewed the player development/evaluation/runtime/authentication/error/rate-limit guides in detail and inspected authoring guidance where it defines the shared runtime contract. The public OpenAPI contained **237 paths / 259 operations**; catalogued every operation and checked the lab-used route families, parameters and request schemas. This is not a claim to have exercised every operation.

Recorded **36 read checks**, including successful and unsuccessful responses, with sanitized response shapes, rate headers and selected artifact hashes. Additional checks confirmed the artifact's policy belongs to the signed-in user, the public Coworld directory/index, and reporter/run listings. Authenticated probes used the saved **user** credential, without elevation; community reads were also tested anonymously. No second user's credential or player session was tested.

Source supplement: **17 files** retrieved directly from `Metta-AI/metta` at upstream main **`70bcdd00b120ae29326b6844e792c076a7b3ae54`**. No writes to the protected main checkout. Project-local **coworld 0.1.47 / softmax-cli 0.26.34** matched PyPI; checked 12 relevant CLI help surfaces. `softmax --version` is not a supported flag; package metadata supplies the version.

The lab branch started at `a3bd7e3e`, two local commits ahead of fetched `origin/main`. `origin/main` had no missing commits. The fork's separate `upstream/main` was divergent and was not merged into this documentation task. Existing credit-correction edits were retained and completed.

### Evidence files

- [Source inventory and hashes](platform-evidence-2026-09-14/sources.json): fetched docs/catalogs and pinned source URLs.
- [OpenAPI operation inventory](platform-evidence-2026-09-14/openapi-operations.json): methods, paths, query names and rate metadata.
- [Schema extract](platform-evidence-2026-09-14/schema-extract.json): relevant request/response schemas and full-spec SHA-256.
- [Sanitized live read checks](platform-evidence-2026-09-14/live-read-checks.json): statuses, shapes, limits and downloaded-byte evidence. Resource IDs/cursors are redacted; credentials, private bodies and signed URLs are excluded.

Official entry points: [docs index](https://docs.softmax.com/llms.txt), [OpenAPI](https://softmax.com/api/observatory/openapi.json), [API catalog](https://softmax.com/.well-known/api-catalog). Full raw downloads and private sample rows were used only as local scratch evidence, not added to the repository.

## Claim ledger

### Discovery, identity and permissions

| Claim checked | Resolution | Evidence level |
| --- | --- | --- |
| Observatory base includes `/api/observatory` | Confirmed; omitting the gateway segment is not an equivalent route | OpenAPI + live |
| OpenAPI lists every deployed route | False: `/whoami` and `/usage/me/credits` answered 200 but were absent from the public spec | OpenAPI + live |
| 200 from `/whoami` proves authentication | False: anonymous also receives 200; inspect `subject_type` | Docs + live |
| User/player identity is interchangeable | False: writes and private evidence have subject/ownership scopes; credit budgets still belong to the owner | Docs + source; live user only |
| Every 401/403 is solved by login | False: 403 can be authorization; read current identity and the error | Official error guide + source |
| Public evidence means anonymous access everywhere | False: supported public league/forum/wiki reads succeeded, but the sampled episode-request detail required authentication | Live, scoped to tested routes |
| Community exists per Coworld version | Corrected to per Coworld name, shared across versions | Source + live surface metadata |
| Current game is fixed by an old name/ID note | Re-resolve league and canonical version; read its participation guide and exact manifest | Docs + live |

### Costs, traffic and capacity

| Claim checked | Resolution | Evidence level |
| --- | --- | --- |
| XP requests charge users money | False: granted credits, never a user bill | Credit source |
| Credits are per player | False: shared per owning user across players/Coworlds | Source |
| Standard user allowance | 500/7 ≈ **71.43/day**, cap **1,000** | Source; not tested as a standard user |
| Softmax team allowance | 10,000/7 ≈ **1,428.57/day**, cap **20,000** | Source + live account meter |
| Refill occurs daily | Midnight UTC; 10 credits correspond to $1 of metered usage | Source + live schedule |
| Displayed balance is all available admission capacity | False: active-request estimates are held against it | Source |
| Estimate is a hard spending cap | False: actual metering can exceed it and create debt | Source; no intentional overrun |
| Cost preview can be fetched before creation | No public quote route found; `cost_preview` is creation-only | OpenAPI + source |
| `recent_requests` is full per-request cost | False: that account-meter collection attributes compute only | Source |
| XP credit allowance is the API request allowance | False: independent budgets | Docs + source + live |
| API rate limiting is merely advisory | Live headers say `enforced`; official changelog dates enforcement to September 14 | Docs + live |
| User HTTP capacities | 2,400/36,000 request and 24,000/360,000 complexity capacities for minute/hour buckets; continuous refill | Docs + live headers |
| XP parallelism is unlimited | False: 100/request schema limit; source defaults 100 outstanding jobs/user and 300 undispatched episodes/user, plus shared capacity | OpenAPI + source; not load-tested |

### Experiment construction and completion

| Claim checked | Resolution | Evidence level |
| --- | --- | --- |
| `random` seats draw independently | False: weighted selection without replacement until eligible-pool refill | Current source |
| Explicit subject can never reappear as an opponent | False: withheld initially, eligible again after pool refill; exclusions/roster design matter | Current source |
| Rotation completely cancels seat bias | Too strong: incomplete cycles and game roles need actual coverage checks | Source + experimental-design distinction |
| Random XP matches all league tournaments | Unsupported generalization; matchmaking is league-specific | Removed from shared instructions |
| Same request body means same seeds in A/B | False: unpinned seeds derive from request ID/index; explicitly pinned integer seed repeats across the batch | Source |
| Hosted/local default configs match | False: hosted first variant versus local certification fixture | Source + docs/CLI |
| Private XP may use any visible opponent | False: selection consent can filter the pool or reject explicit selection with 409 | OpenAPI + source; owned scope endpoint live |
| `state` guarantees arbitrary saved-state exploration | Unsupported: selector is passed to game config; game persistence support is still required | OpenAPI + source |
| `--check-schema` fully validates/admission-checks a request | False: helper checks keys and resolvable game overrides, not every nested constraint or credit quote | Local implementation |
| Parent `failed` means all children stopped | False; fixed helper completion logic and regression test | Current source + local tests |
| Request cancellation is only a label change | False: authorized cancellation reaches child jobs; read `can_cancel` and child states | Source; no cancellation performed |
| All failures are nonpositive-score infrastructure noise | Unsupported globally; use fault metadata and report player failures separately | Removed score-only filtering prescription |

### Upload, runtime and competition

| Claim checked | Resolution | Evidence level |
| --- | --- | --- |
| Upload enters a league | False; submission is separate | Official docs + CLI/source contract; no new upload |
| Every upload increments version | False: identical upload may reuse version | Official upload guide |
| Every player is a WebSocket container | False: platform-hosted images versus game-hosted files | Official runtime guide + CLI |
| File uploads accept container flags/secrets | False; game owns execution/model access, no player environment | Docs + CLI |
| Player resource defaults are hard limits | False: 250m CPU / 256Mi scheduling requests | Official runtime/resource guidance |
| Player ZIP is a one-time 200 MB upload | Corrected: replaceable object up to 200 MiB; finish before exit | Official protocol guide |
| Sidecar supports only InvokeModel | Obsolete: official guide includes Converse and both streaming variants | Official Bedrock guide |
| Submit cannot select player/preferences | False: `--player` and `--preference` exist | Current CLI + OpenAPI |
| All qualification runs every ten minutes in a container commissioner | False: configured platform qualification also exists; thresholds/timing are league-specific | Current source |
| `competing` guarantees champion | False: separate `is_champion` and promotion mode/version rules | OpenAPI + source + live rows |
| `always` promotes any qualifying upload | Too broad: older upload cannot displace newer champion automatically | Current source |
| `lineage` means any prior champion owned by user | Too broad: prior lower version of the same policy under that player | Current source |
| Submission cannot be changed | Membership can be retired; previous results/history remain. Human gate retained | Docs + source; no retirement performed |
| Two active players is a universal cap | False: user override and league settings can determine it | Current source |
| No XP self-play means platform qualification cannot use it | False: lab experiment preference does not describe platform-managed qualification | Current source |

### Retrieval and community

| Claim checked | Resolution | Evidence level |
| --- | --- | --- |
| All list routes paginate in JSON | False: membership/submission arrays use `X-Next-Cursor` headers; followed a live second page | OpenAPI + live |
| Recorded episodes include all attempted executions | False: request attempts and recorded episodes are separate collections | OpenAPI + live shapes |
| Current artifact routes work | Owned results, replay, log and ZIP returned 200; full replay/ZIP bytes read | Live |
| Accessible slot listing includes all competitors | False: listing is scoped to readable policies | Source; owned sample live |
| Replay URL is replay bytes | Not generally; raw artifact route is distinct from watch/viewer URL | Docs + source + live bytes |
| Replay formats/compression are universal | False: game-owned and version-sensitive | Official replay guide |
| Artifact availability proves indefinite retention | Unsupported: no platform retention SLA established | Explicitly unresolved |
| Reporter routes mean every episode has a report | False: list routes answered, sampled episode report aggregate returned 404 | OpenAPI + live |
| Public forum/wiki reads work | Anonymous metadata/feed/index/search returned 200 | Live |
| Forum/wiki write schemas and limits match our reference | Checked fields, source rate constants, concurrency/revision handling; shared API limits also apply | OpenAPI + source; no writes |

## Live sample: what was actually exercised

An existing owned XP was followed from list → detail → child rows → episode request → results/replay → accessible player diagnostics. The sampled request contained one completed episode; it was not a new competitive evaluation. A separate owned membership supplied a live division for leaderboard and exact policy-version resolution.

- Replay: **411,608 bytes**, HTTP 200, opaque binary; hash retained.
- Owned player ZIP: **115,267 bytes**, HTTP 200, ZIP signature; hash retained.
- Owned player log and results JSON: HTTP 200.
- Membership second page: HTTP 200 with cursor continuation.
- Current Coworld manifest and public league participation guide: HTTP 200.
- Anonymous forum/wiki metadata, feed/index and search: HTTP 200.
- Episode reporter aggregate using the recorded UUID: 404. A speculative `ep_` prefix returned 422; it is not the correct UUID shape and is not recommended. No claim of successful reporter rendering follows from these checks.

A downloaded replay was not played in a browser. A completed existing request cannot validate current write admission, new artifact upload, cancellation, failure propagation or live qualification transitions. The regression tests exercise local helper behavior against the verified contracts, not production mutations.

## Documentation changes and tool validation

Updated the root workflow, practices, README/onboarding, credit and runtime references, XP/local-run/lifecycle skills, artifact endpoint map, and community reference. Removed stale paid-XP claims from Emerg-ant instructions, removed Cue-n-Woo's obsolete separate job-log-fetcher recommendation, and marked Crewrift's older platform contract as historical. Game mechanics and player code were not changed.

Three behavioral fixes:

1. XP monitor and artifact watcher stop only when child rows/counts establish completion, including cancellation; a parent failure alone is insufficient.
2. XP creator preserves `cost_preview` from POST through its readback/summary, including delayed readback.
3. Lifecycle lookup follows membership/submission cursor headers rather than silently omitting older matches. Diagnostic hints no longer assert universal timeout causes or a fixed player cap.

Validation: **33 focused tests passed** across shared analysis contracts and artifact watch selection. Tests cover mixed failed/running children, cancellation, submitted work, pagination, and creation-only estimate retention. Documentation check: **507 documents, zero current or historical broken local file targets**. `git diff --check` passed. The link checker does not prove remote availability, anchor correctness or semantic accuracy.

## Remaining gaps and boundaries

These are follow-up candidates, not claims that the platform is broken:

- **Exact lifecycle monitor scope:** its CLI still selects policy-name history, not an exact league/version/membership. Verify the intended membership directly before declaring success. Add explicit scope selectors in a focused tool task.
- **Failure-complete policy discovery:** the downloader's policy selector still uses recorded episodes. For failure analysis use XP/round request rows or `/policy-versions/{id}/episode-requests`; add an explicit attempt-discovery mode if needed.
- **HTTP retry consistency:** some helpers retry using fixed intervals or fail immediately, rather than consistently honoring rate-limit headers. This pass documents the current contract; a shared transport change requires its own focused implementation/validation.
- **Standard-user/player-session isolation:** source-checked only. Do not generalize this team user's access to other accounts. No credentials were switched or minted for this audit.
- **Stateful games:** `head`/`snapshot` selectors and game-config forwarding are verified; arbitrary game state loading/mutation and persistence semantics are not. Test only within a selected game's contract.
- **Reporter execution and retention:** no new reporter run, output-rendering proof or storage-retention guarantee was obtained.
- **Write/runtime boundaries:** no XP creation, upload, submit, retire, cancel, community write, replay-session allocation, game launch, or remote Git write was performed. Those contracts remain docs/source-verified where marked.

### Upstream documentation gaps observed

The docs index has no dedicated XP-credit guide, and the public OpenAPI omits the working account credit route. Its reporter field says “billed to the requester,” while credit source says users are never charged money; do not turn internal attribution wording into a customer-billing claim. Some overview prose still describes all player programs as containers, while the specific runtime guide correctly documents file policies. These discrepancies are recorded here, not silently treated as authoritative. No upstream edits or public reports were sent.

### Learning from this correction

**Documentation consistency is not independent factual verification.** A repeated transcript claim can remain wrong, and a test can encode the same mistaken assumption—as the previous “failed parent is drained” test did. For platform facts, attach the deployed schema/live read or pinned source, the tested identity, and the boundary of what was not exercised. This is a correction to this audit's method, not a new gameplay lesson promoted from one session.
