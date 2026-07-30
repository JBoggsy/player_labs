# CTF tentative lessons — session buffer

**Session started:** 2026-07-15 12:27. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`ctf_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (CTF-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### The CTF event warehouse already exists locally — check `ctf_lab/tools/` + lab skills before building "new" tooling
Evidence: Asked to "build a ctf event warehouse" for reporter work; a grep for "warehouse" found `ctf_lab/tools/event_warehouse.py` + the `ctf-event-warehouse` skill already covering the local half (DuckDB/Parquet, slot→policy re-keying, replay + beacon trace feeds). The genuinely missing piece was only the *hosted reporter* variant in reporter_lab.

### Porting a bitworld game to a reporter_lab warehouse has a twice-proven playbook — start from heartleaf's SPEC.md
Evidence: reporter_lab has crewrift + heartleaf roundwarehouse reporters; heartleaf's `SPEC.md` documents the exact recipe (path-last shims for mummy/curly/bitworld-client so the sim monolith compiles to single-threaded wasm, stage assets to /scratch, per-episode error isolation, deterministic sorted Snappy Parquet, manifest part). CTF's `tools/expand_replay.nim` already exposes the needed API (`expandReplayTimeline` + typed events), same one our local `expand_replay_json.nim` wraps.

### CTF-specific wrinkles for a hosted CTF warehouse reporter (vs crewrift/heartleaf)
Evidence: (1) coworld-ctf is PRIVATE — crewrift/heartleaf are public vendor submodules in reporter_lab, so the vendoring/pin strategy needs a decision (tarball fetch like `build_expand_replay.sh` vs submodule). (2) `sim.nim` (3.3k lines) imports bitworld/server + client + pixie and loads aseprite assets at init — the heartleaf shim class of problem, where the real port work is. (3) Beacon belief-trace events CANNOT ride along: per-seat policy logs are owner-scoped on public leagues (heartleaf spec non-goals them), so the hosted reporter carries only ground-truth replay_events/participants; the trace side stays in the local tool. Status: BUILT + deployed v1 (2026-07-15); see below.

### Hosted CTF warehouse v1 is LIVE (not subscribed) — use it via the reporters API for xreq warehouses
Evidence: `rptr_b0c0ca87…` / v1 `rv_c4113712…` in reporter_lab (`ctf/reporters/roundwarehouse/`). Trigger: `POST /v2/reporters/runs` with `{"reporter_version_id": "rv_c4113712-52e4-45bd-80a8-dae1ba56337d", "subject": {"kind": "episodes", "episode_request_ids": [...]}}`, poll the run, download `events`/`player_stats` parquet parts. Canary over 5 real episodes verified event-for-event against the local native expander. Beacon trace_events still local-only.

### Wasm32 trap in bitworld games: native `int` arithmetic overflows in wasm — CTF's procedural map broke before any replay ran
Evidence: CTF's diagonal-wall distance math (`dx*dx + dy*dy <= thickness²·len2²/4` in sim.nim) is written in native `int`; fine at 64-bit, overflows at wasm32's 32-bit during map construction. Fix shape: a guarded sed overlay at a STABLE path (reporter-sdk-nim/gen/) that widens just those expressions to int64 — never dirty the pinned submodule, and never generate into a mktemp dir (Nim embeds source paths into the binary → random path = non-reproducible component hash; three builds gave three hashes until moved to a stable path).

### Reporter platform.get allowlist has NO per-item episode-request route — episodes-subject runs can't resolve policy identity
Evidence: canary manifest recorded `path '/v2/episode-requests/{id}' is not in the platform allowlist: ['/v2/episode-requests', '/v2/leagues', '/v2/leagues/{id}', '/v2/rounds/{id}']` for every episode; the collection route ignores `episode_id`/`id` query filters (returns the same unfiltered page — verified with direct API probes). Round-subject runs resolve identity fully (participants come from the round listing). Workarounds: join identity client-side from episode.json (lab already has it), or get the item route allowlisted. Status: FIXED — metta PR #18129 merged + deployed; verified 2026-07-21 that episodes-subject run `rrun_0adf507f…` on the UNCHANGED v1 resolved policy names (beacon/ctf-focusfire/ctf-flankfire/Picasso, 171/185 event rows named — the unnamed 15 are global rows: phase/game_over/flag_return_home) with ZERO manifest warnings. No re-upload was needed, exactly as predicted.

### Adversarial review earns its keep: Codex found a real security bypass in a "one-line" allowlist add — verify the finding, then fix the general class
Evidence: adding `/v2/episode-requests/` to the reporter platform.get allowlist looked trivial, but Codex flagged that the segment matcher (rpartition on the raw string) accepts `%2F`-encoded nested paths — httpx sends `%2F` literally, server decodes it into a deeper artifact/replay route, AND platform.get isn't byte-budgeted so it also dodges artifact-read accounting. Verified both claims empirically before fixing (matcher accepts it; httpx raw_path preserves %2F). First fix (reject `%`) was incomplete — Codex re-review caught `/v2/rounds/.` normalizing to the non-allowlisted collection. General fix that closes the whole class: check the allowlist against `client.build_request(...).url.path` (what actually goes on the wire) and require it to equal the input. Lesson: on a security-adjacent surface, match against the effective request, not the raw string; and a second adversarial pass after the first fix is worth it.

### CTF slot attribution is trustworthy where heartleaf's wasn't: joinOrder == requested slot survives crashes
Evidence: heartleaf replay slots are connection-order and compact around crashes (ISSUE-slot-attribution, high-severity mis-attribution). CTF's `addPlayer` assigns `joinOrder = requested slot` from the join URL and untrusted joins must arrive in order, so replay slot == participants[].position even with dropouts — verified on fixtures by diffing per-slot event-derived kills/deaths/captures against results.json arrays (exact match). BUT the sim's `removePlayerAt` compacts `sim.players`, so any expansion loop must key tracking state by joinOrder, never players index. Also: results `scores` can include out-of-band bookkeeping (disconnect/abandoned-win) with NO replay score events — only assert score parity for slots that have score events.

### Reporter runs pending a long time is usually BACKLOG, not a stuck reporter — check runner health + queue depth before touching anything
Evidence: both a manual canary and the first subscription-fired CTF run sat `pending` ~30+ min. Looked like a stall; wasn't. The `observatory-backend-reporter-runner` pod (namespace `observatory`, NOT orchestrator) was healthy and continuously claiming/completing OTHER reporters' runs. Real cause: platform-wide queue of 258 pending runs, drained oldest-first (`ORDER BY created_at LIMIT concurrency` in reporter_runner/worker.py `claim_pending_reporter_runs`) at ~5 runs/min → ~0.9 h ETA. Diagnostic recipe: `GET /v2/reporters/runs?limit=100&offset=…` bucket by status to get queue depth + oldest pending + completion rate; `kubectl --context softmax-main -n observatory logs deploy/observatory-backend-reporter-runner --tail=80` to confirm the runner is claiming/publishing. Do NOT restart the runner — it's working; you're just behind other tenants.

### Reporter backlog is DRAINING, not building — but barely; the bottleneck is the runner's memory budget, not replicas
Evidence (2026-07-21, ~19:40): two snapshots 6 min apart showed the head-of-queue advancing FASTER than wall time (oldest visible pending 18:54→19:04 in 6 real min; oldest-pending age 45.6→41.5 min) and newest completion tracking "now" — so it drains. But arrival ≈ completion (~0.98/min vs ~0.92/min in the last ~100 runs), leaving a persistent ~40-min-deep standing queue. Root bottleneck, from `job_runner/config.py`: REPORTER_RUNNER_CONCURRENCY=4 but MEMORY_LIMIT_MIB=2048 − HOST_RESERVE=1024 = **1024 MiB guest budget**, and each CTF-warehouse run requests memory_mib=1024 → it eats the WHOLE budget, so heavy reporters run strictly ONE-AT-A-TIME (deployment is 1 replica; logs literally say "Claimed 1 run using 1024/1024 MiB"). Levers to raise throughput (owner of `observatory-backend-reporter-runner` deployment): bump the memory limit, add replicas, or lower the CTF reporter's requested memory_mib in a v2 (1024 is generous — the canary used ~248 KB bytes_read / 5s; could likely drop to 256–512). Measuring drain-vs-growth without admin: page `GET /v2/reporters/runs?limit=100` (max 100, newest-first, no offset; `status`/`scope=all` need admin — 403 otherwise) and watch the oldest-pending timestamp move across two readings.

### The CTF round_closed subscription works — it fired on the next closed round immediately
Evidence: created `rsub_59b9e3e3…` (v1 `rv_c4113712`, league `league_3243d905…` "Ctf", publish_posts=false); within ~15 min a subscription-triggered run (`rrun_79d59d74…`) appeared for the version without any manual trigger. Confirms the trigger binding + scope are correct even though it queued behind the backlog.

### Wasmtime-py + pyarrow host tests can deadlock at interpreter teardown — end with os._exit(0)
Evidence: the CTF host test printed its OK verdict then hung indefinitely in `__cxa_finalize_ranges` (native static destructors from 3 Wasmtime engines + pyarrow), stalling check.sh twice (>20 min). Sibling tests never hit it (fewer engines). Fix: flush stdout and `os._exit(0)` after the verdict.

### Live reporter versions can be AHEAD of reporter_lab source — never assume a rebuild reproduces production
Evidence: reporter_lab's provenance ledger (audited 2026-07-14): Crewrift Warehouse live v9 vs checked-in v8, Heartleaf Warehouse live v5 vs checked-in v1 — live source not in the checkout. Deployment guide: re-query the registry immediately before any deploy; registration/upload/subscription are separately authorized live mutations, never done from a green local build alone.
