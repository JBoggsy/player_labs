# Vanilla WoW tentative lessons — session buffer

**Session started:** 2026-08-03 12:35. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`vanilla_wow_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Vanilla-WoW-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### Diff the game image's `AgentFrame` JSON schema against the policy image's BEFORE running a hosted retest

Evidence: the retest plan said "run the same wowborg:v59". v59 physically cannot run on
accelerated-wow 0.1.146: its copied 0.1.124 contract is `extra="forbid"`, and 0.1.146 adds a
required top-level `queued_melee_spell_id` plus nested `units[].class_id` — so every frame
would be rejected, exactly as it was on 0.1.127 (128 `extra_forbidden` errors). Two hosted
episodes were already burned that way. The check is cheap and decisive: run
`AgentFrame.model_json_schema()` inside both images and `cmp` the output. It showed v60's
schema is BYTE-IDENTICAL to 0.1.146's, so v60 was runnable with no rebuild.
Status: candidate — cheap preflight that would have saved two dead hosted episodes.

### A "same policy" comparison survives an SDK rebuild; a version-number match does not

Evidence: v60 is documented as "behavior unchanged from v59", rebuilt only against a newer
game SDK. So v60-on-0.1.146 vs v59-on-0.1.124 is still a controlled comparison of the
game-side movement fix — the policy behavior is the constant, the version number isn't.
Insisting on the literal v59 would have produced no episode at all.
Status: candidate.

### Validate a new analysis metric against a known-BAD control before trusting it on new data

Evidence: `movement_report.py`'s first "boundary-only stop" definition (stop followed by a
restart within 1 s) scored the known-broken v59 baseline as 0 boundary-only stops — PASS.
Measuring the actual distributions showed why: baseline pauses last 3-91 s, so timing is not
the discriminator. Displacement is — across all 239 baseline pauses the character moved under
0.9 yd, i.e. it halted, stood still, and restarted. Redefined on displacement, the baseline
correctly scores 239/239 and FAILs. A metric that passes the case it was built to catch is
worthless, and only the negative control reveals it.
Status: candidate — generalizes well beyond this lab.

### A fix that changes the failure mode is progress — report the delta, not "still broken"

Evidence: 0.1.152 did fix the 0.1.146 fall (z holds at spawn 38.718 across all 84
observations; 0.1.146 sank to 28/18.6 with FALLING on 100% of packets). But the character
still cannot move, now blocked on a NEW gate — *"piloted movement controls settled: movement
collision readiness timed out"*, 32/36 failures, and **zero** movement packets where 0.1.146
emitted 175. Reporting this as "still broken" would have wasted Richard's time; the useful
signal is that the grounding fix landed and likely introduced a readiness wait that never
satisfies.
Status: candidate.

### An authenticated asset URL is inert until every runtime data owner installs it

Evidence: accelerated-wow 0.1.152's `/env` attach carried the correct authenticated
`/player/assets` URL and the host applied it to presentation assets, yet every wowborg move
timed out on `world collision residency pending`. The host binary is compiled with
`simulationDataHttp`; unlike the normal player runtime, `environment/host/session.nim` never
called `setSimulationDataBaseUrl`, so VMap collision fetched through an unset simulation-data
origin. Landed owner-repo PR #7809 commit `1608da7a` installs the same attach URL for simulation data
before client construction, and the complete environment-host asset proof now asserts both bases.
Status: candidate — inspect runtime initialization for every compile-time data owner before
blaming the fetcher or adding movement fallback behavior.

### `build_player.sh`'s import sanity check is the cheapest SDK-break detector in the lab

Evidence: 0.1.152 removed the re-exports from `player/sdk/navmesh/__init__.py`, so
`from player.sdk.navmesh import route_navmesh` broke. The build's post-build import check
caught it in seconds, before any episode ran — the fix was a one-line path change to
`player.sdk.navmesh.client` (matching the SDK's own `cli/commands.py`, and upstream commit
`b337a12ef "Collapse package re-export wrappers"` confirms the intent). Keep that check
current whenever wowborg adds an SDK import.
Status: candidate.

### Upload version numbers follow the last UPLOADED version, not your local tags

Evidence: the 2026-08-03 build was tagged `players-wowborg:v61` locally and documented as
"v61", but never uploaded. Uploading the next (0.1.152) build produced `wowborg:v61` —
because numbering increments from v60, the last uploaded version. Two different builds
briefly shared the name in the docs. Don't write a `vN` into VERSION_LOG until the upload
returns it.
Status: candidate.

### There is no published version -> commit map for accelerated-wow releases

Evidence: trying to align the local test SDK pin with 0.1.152, the image's
`environment/contract/agent.py` and `player/sdk/navmesh/client.py` blobs **never coexist in
any commit** of the game repo's main history — so the release wasn't built from a plain main
commit, and the image records no source SHA. Pin to the nearest commit carrying the shipped
SDK layout and say so explicitly; treat the pinned IMAGE as the authoritative contract and
the git pin as a test-only approximation.
Status: candidate — cost ~15 min of blob archaeology to establish; write it down once.

### Decode the replay's movement FLAGS, not just opcodes — they name the failure outright

Evidence: "character doesn't move" was diagnosable but vague from positions and opcode counts
alone. Decoding the `MovementInfo` flag word settled it in one query: `FALLING` (0x2000) on
**100.0%** of movement packets in both 0.1.146 episodes vs **3.8%** in the baseline. The
character was never grounded, and a falling character ignores forward input horizontally —
which explains why `MSG_MOVE_START_FORWARD` kept flowing while x/y never changed. The flags
are already in `cwreplay._movement_info`'s `move_flags`; nothing was reading them.
Status: candidate — add flag decoding to `movement_report.py`.

### Prove a data/tooling layer innocent by direct query before blaming the layer above it

Evidence: "no physically admissible source triangle" reads like a navmesh problem. Two direct
checks refuted that: the spawn-area `maps`/`vmaps`/`mmaps` tiles are byte-identical between
0.1.124 and 0.1.146 (same md5s), and running 0.1.146's own `vmangos-navmesh-helper` at the
spawn pose z=38.718 planned a 48-yard route while the same query at z=27.988 refused. The mesh
was right; the character's z was wrong. That inverted the search from "navmesh regressed" to
"character placement regressed" — the actual bug.
Status: candidate — the helper takes a JSON request on stdin and is trivially scriptable.

### "Episode completed, score 1.0" says nothing about whether the player did anything

Evidence: both 0.1.146 episodes completed with score 1.0, a retained replay, and zero errors —
and the character never moved one yard. `results.json` shows why: `score_metric` is
`level_progress`, so 1.0 is just "level 1", and `xp_gained` was 0. The baseline scored an
identical 1.0 while walking 1,315 yards. Read the behavioral metric, never the score, when the
question is whether the policy functioned.
Status: candidate — this score would have made a green-looking false pass.

### Rebuild against the exact target image to separate "our pin is stale" from "the game regressed"

Evidence: the 0.1.146 movement failure had two candidate causes — v60's 0.1.127-era SDK copy, or
a game regression. Rebuilding v61 against 0.1.146's exact image and running one local
exact-image episode settled it in ~20 minutes: v61 reproduced the failure exactly (1 distinct
x/y, 0.0 yd), so the game is at fault. Without that control the finding would have been an
unfalsifiable "something is broken".
Status: candidate — the exact-image local episode is the lab's decisive instrument.

### The game image moved its Python packages from dist-packages to `/app`

Evidence: `wowborg/Dockerfile` copied `environment/` and `player/sdk` from
`/usr/local/lib/python3.11/dist-packages`. On accelerated-wow 0.1.146 that path does not exist —
the build fails at COPY with "not found". They now live under `/app`. Releases through 0.1.127
used the old path. The `player/sdk` layout also changed (`navmesh_domain/` → `navmesh/`,
`nim_client_domain/` → `nim_client/`), though those were pure renames with no protocol change.
Status: candidate — a build-contract change with no deprecation window.

### `versions.env` can silently lag the version actually built and uploaded

Evidence: `tools/versions.env` still pins accelerated-wow 0.1.124 on a clean working tree,
but v60 was built against 0.1.127's image digest (recorded only in `VERSION_LOG.md`). The
build pin was passed via `--base` and never committed, so the repo cannot reproduce v60 from
`versions.env` alone. VERSION_LOG's per-version "Local image manifest" hash was what let me
identify the local `players-wowborg:diag-0127` image as v60.
Status: candidate — record the base digest in `versions.env` when a version ships against it.

### Active shared HTTP fetches are startup telemetry, not a safe quiescence invariant

Evidence: after the `/env` host correctly installed the authenticated simulation-data base,
world entry immediately started two legitimate collision requests and deterministically hit
`httpAssetFetchesActive() == 0`. Removing that assertion let hello complete; movement's own
collision-readiness gate then waited for the required residency, and the exact patched local
episode walked normally. A process-global fetch count cannot prove one session is ready.
Status: candidate — gate the required resource, and report unrelated in-flight work as telemetry.

### Do not classify an already-pushed frame as a failed movement settlement

Evidence: the synchronous `/env` SDK exposed three startup frames before the submitted move's
`action_state` appeared. Position was unchanged and no typed result was present, so wowborg
counted them as stalls, cast Stuck, and replanned immediately before movement began. Preserving
the typed "no action result observed" state removed the false recovery: known-course replans
fell 1 -> 0, and a novel 121.8-yard route completed as one uninterrupted forward span.
Status: candidate — action settlement must be explicit; a newer observation alone is not failure.
