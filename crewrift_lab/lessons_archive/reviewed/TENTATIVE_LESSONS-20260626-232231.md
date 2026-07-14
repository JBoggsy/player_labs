# Crewrift tentative lessons — session buffer

**Session started:** 2026-06-26 17:44. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`crewrift_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Crewrift-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### coworld-crewrift already has a direct analog to crewrift_lab: `players/crewborg-aaln/optimizer/`
Evidence: It's a self-contained optimization workspace shipped *beside the player* — `AGENTS.md` + `guide/SKILL.md` + `CREWBORG_INSIGHTS.md` (≈ our best_practices/lessons) + `playbooks/` + `games/crewrift/skills/` + ~16 game-agnostic optimizer skills **copied in self-contained** (provenance noted) from `Metta-AI/optimizer-skills`. Same evaluate→mine→hypothesize→edit→gate→submit loop our AGENTS.md runs. Aaron authored it.
Status: Relevant to the player_labs→coworld-crewrift submission — packaging this lab may mean *reconciling* with Aaron's optimizer/ convention, not just landing alongside it. Decision owed before packaging.

### coworld-crewrift packaging convention: player-specific tooling lives INSIDE `players/<name>/`, only shared tools at root
Evidence: `players/notsus/tools/{run,tournament,common}.nim` (local match runner, S3 tournament reports) ship inside the player; the one shared tool, `tools/expand_replay.nim`, sits at repo root because every player needs it. A player = `players/<name>/` with a 3-file contract (`coplayer_manifest.json` {author,name,run,games}, `Dockerfile`, `README.md` with Observatory IDs + baked flags). Materially different policies get sibling dirs (sussybuster-aaln), not flag sprawl.
Status: This is the slot map for our submission — crewborg→`players/<name>/`, analysis scripts→its `tools/`, the loop→`players/<name>/optimizer/`.

### Source-ownership rule in coworld-crewrift README governs where a submission lands
Evidence: README states: game server + bundled notsus + reporter + Crewrift-specific commissioner live in *this* repo; shared reusable pieces (player SDK, ruleset_strategy commissioner) come from `Metta-AI/coworld-tools`; agnostic optimizer methodology is copied in per-player from `optimizer-skills`. Only the bundled reference player (notsus) is in `coworld_manifest.json`; league uploads (crewborg-aaln) are source mirrors, not manifest entries.

### Static-HTML deliverables: verify-by-looking needs a throwaway HTTP server, not file://
Evidence: ux.ify `shoot.mjs` timed out (60s, "load the allocator multiple times") on a `file://` page that pulls Google Fonts; the Playwright MCP also blocks `file:` outright ("Access to file: protocol is blocked"). Fix: `python3 -m http.server <port>` in the file's dir, navigate `http://localhost:<port>/...`. Note MCP screenshots write to the *caller cwd* (the repo), not an --out dir — clean up `desktop-full.png`/`mobile-full.png`/`.playwright-mcp/` after.

### James's chosen submission shape: crewborg → `players/crewborg/` in coworld-crewrift, FLATTENED (no `optimizer/` subdir)
Evidence: Decided against mirroring Aaron's nested `optimizer/`. `players/crewborg/` holds the source tree (`crewrift/crewborg/` subtree — package path preserved as `crewrift.crewborg`, zero import rewrites) AND the toolkit (docs/tools/skills/playbooks) flattened at one level, so one agent at `players/crewborg/` sees everything. Our crewborg and Aaron's `crewborg-aaln` are the same lineage but diverged — TWO distinct policies, not reconciled (Aaron renaming his frees the `crewborg` name).
Status: Package-path nesting `players/crewborg/crewrift/crewborg/` is a known wart (alt: flatten package to bare `crewborg`, but that's ~80 import rewrites). Tracking HTML: scratchpad/crewborg-submission-design.html (has a §06 inventory + Shipped? column).

### Doc-pass standard that works for "agent can hack on it immediately": module docstring + a `Collaborators` block
Evidence: `Collaborators` = `Relies on:` / `Used by:` / `Emits/touches:` + a "Modifying this file:" invariant note, calibrated on one exemplar (`modes/hunt.py`) then fanned out to 8 parallel general-purpose agents over disjoint subtrees (docstrings-only, never logic). 63 source + 39 test files in one pass, all still compile. Telling each agent to fix stale refs in passing swept the lingering retired-`Pretend` mentions for free.

### `coworld episodes -p <league-player>` returns `[]` — league & xp episodes are DISJOINT populations (live-verified)
Evidence: `uv run coworld episodes --policy crewborg --json` → `[]` against the live API for the champion league player; the CLI only queries `/v2/episode-requests` (ad-hoc/commissioner episodes). League round games live under `/stats/policy-versions?name_exact=` → `/episodes?policy_version_id=` — the `coworld-episode-artifacts` fetch_artifacts.py found v1–v71 and downloaded a real v70 league episode from the same run. So `[]` ≠ "no episodes." Confirmed both against the skill's `endpoint-map.md` AND the actual API.

### expand_replay: USE it (objective ground truth) — version-matched binary is the whole game; here's the hash-failure recovery
Evidence: it re-sims recorded inputs through a compiled-in crewrift `sim` + validates a per-tick hash → `hash failed` when the binary ≠ the recording build. Fix: build a version-matched binary (`build_expand_replay.sh`, tarball fetch, host-native, no creds; `--ref <sha>` for other versions; cache one per ref, point via `CREWRIFT_EXPAND_REPLAY`). League replays expand FULLY at `CREWRIFT_REF` (recorded by the current upload; verified 4720/5004 lines, 0 failures). On unavailable build → viewer (episode's own image) + version-independent policy logs. Bad oracles: the bundled fixture + stale checkout binaries. Synopsis saved to scratchpad for the ported tool docs.
Status: best_practices.md reframed from "don't use it / prefer logs" → "use it, here's how + failure recovery" per James. THEN trimmed hard (see next lesson) — the how-to belongs in tool docs, not best_practices.

### Doc-altitude discipline: best_practices = concise principle + WHICH tool; how-to-use/build/works = the tool's own docs + a tool library
Evidence: James caught the "Reading games" section ballooning into a tool manual (how to build expand_replay, warehouse internals) — wrong altitude, inconsistent with the doc's short-bullet style. Fix: best_practices says "investigate replays, batch-first then drill, use your tools (named, one-line when-to-use)"; the how-to moved to a saved tool-library seed (scratchpad). PRINCIPLE: a separate **tool library** doc catalogs *when to use each tool + what it does*; each tool's *own* doc carries *how to run it*. Keep principles docs concise and link out.

### Reading-games tooling is a LADDER; expand_replay is the bottom rung, not the go-to for "all the data"
Evidence: `crewrift-event-warehouse build` (a real CLI) ingests MANY episodes' replays (via expand_replay) + results → queryable parquet event store (DuckDB), re-keyed actor+target→policy/role, with DERIVED behavioral events (following_interval/chase_interval/near-crew/kill-cd→kill latency; `--snapshot-every 1` = per-tick positions). The loose scripts (aaron_compare/kill_latency/suss_rate/visibility_at_ready) + positioning_viz all query it. The `crewrift-report` skill is the triage layer above (Tier1 results/episode stats → Tier2 profile_replay=expand_replay on flagged eps → Tier3 logs). So: batch triage→report skill; deep cross-episode "all data"→warehouse; one game→expand_replay (the primitive both are built on, so the version-matched/hash discipline still applies once per batch). James's call: warehouse is the better go-to for batch data.

### Transcript mining works well: scope by cwd (SQL on sessions.cwd), then content-search; cross-check against authoritative source
Evidence: `SELECT ... FROM messages JOIN sessions WHERE s.cwd LIKE '%personal_labs%'` scoped 42 sessions; per-term LIKE counts confirmed which mechanics are real (build_expand_replay 96×, CREWRIFT_EXPAND_REPLAY 86×, expand-043 97×). Don't synthesize from raw transcript prose alone — the lab's own `tools/build_expand_replay.sh` + `docs/crewrift-replays.md §B` were the authoritative procedure; transcripts confirmed real-world usage + version nuances.

### Bedrock-in-pod THE ONE RULE (from metta PR #16867): route every call to AWS_ENDPOINT_URL_BEDROCK_RUNTIME, InvokeModel not Converse
Evidence: metta PR #16867 (docs(coworld): make the Bedrock sidecar runtime contract discoverable, OPEN) adds the player runtime contract to BEDROCK.md: hosted pod gets `AWS_ENDPOINT_URL_BEDROCK_RUNTIME` (loopback sidecar); hit real AWS instead → placeholder creds → HTTP 403 → SILENT non-LLM fallback (no score error). Corollaries: use `bedrock:InvokeModel` only (runner identity lacks Converse → AccessDenied); don't supply real creds (sidecar re-signs); **gate on the ENDPOINT var's presence, NOT USE_BEDROCK** (sidecar doesn't set it). Standard SDKs (boto3/AnthropicBedrock/@cogweb/llm) read the endpoint var automatically; only raw HTTP must. Debug: log the response BODY not just status; check `/healthz`; check crewborg telemetry (`domain.meeting_llm_decision` vs `_fallback`, `commander_started.env_seen`). Complex: strip/inject lives in runner code (`bedrock_sidecar_wiring.py`/`kubernetes_runner.py`), not BEDROCK.md. Folded into docs/reference/coworld-platform.md (made prominent: top callout + ONE RULE box + 403 table).

### Crewrift game constants DRIFTED + the emergency button no longer resets kill cooldowns (verified @a3e2859)
Evidence: current `src/crewrift/sim.nim` (master a3e2859) vs the lab docs (verified at older d9f6b30): `KillCooldownTicks` 500→**800**, `VoteTimerTicks` 240→**1200** (50s). And `voteResultResetsKillCooldowns()` → body/unknown meetings ALWAYS reset imposter cooldowns, but a BUTTON meeting resets only if `config.buttonResetsKillCooldowns`, which is **false** in the deployed `coworld_manifest.json` variants. So the emergency button NO LONGER resets cooldowns (James flagged this). crewborg's own `types.py` already encodes it (`ended_meeting_kind != "button"`); best_practices.md was wrong ("report/button resets cooldowns") — fixed.

### Crewrift constants are VARIANT- + VERSION-specific AND config-overridable → docs must cite file:Symbol + tell agents to re-derive, never hardcode
Evidence: `opportunity.py` notes "Prime league uses KillCooldown=500; regular uses 800"; the repo manifest says 800; the toolkit pins `CREWRIFT_REF=d9f6b30` (an even OLDER game). Three different values for the "same" constant depending on variant/version/episode. The reference docs handle this by citing the source proc/const NAME (not line numbers — they drift) + a grep re-check + "the authoritative value is the episode's baked game_config / the deployed ref's sim.nim const block." OPEN OPS ITEM: `versions.env` CREWRIFT_REF=d9f6b30 is stale vs the repo (a3e2859) — a build_expand_replay binary at d9f6b30 may hash-fail on current-version replays; bump when porting the toolkit.

### crewborg code findings surfaced by the doc pass (NOT bugs fixed — flagged)
Evidence: (1) commander `strength` field is consumed by modes (`"hard"` = force not bias) but **never requested from the LLM** (omitted from `llm.py` response_schema + prompts) → live LLM path is always `"soft"`; `"hard"` only reachable via `CREWBORG_COMMANDER_FORCE` test override. (2) `strategy/opportunity.py` `SEARCH_LEAD_TICKS`/`HUNT_LEAD_TICKS` are now **vestigial** (unused — Search became the unconditional fallback; Recon uses `recon_window()`). (3) cosmetic: `coworld/policy_player.py` give-up path logs `NoneType` for `last_error` when all reconnects were 0-frame. (4) `modes/search.py:_room_crew_still_around(room)` ignores its `room` param (recency-only check).
