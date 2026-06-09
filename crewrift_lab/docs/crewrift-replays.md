# Reading a Crewrift game: replays & logs

**Validated 2026-06-08** against coworld `296608a0`, crewrift `d9f6b30` (v0.1.40),
bitworld `5a4bea1`, and a real downloaded crewborg league episode. Citations are
by file + symbol (stable across line drift); re-derive from source if something
doesn't match.

A finished Crewrift game can be consumed two ways:

- **Visually** — the replay viewer re-simulates the game into a video. Great for a
  **human** watching what happened. (You can't "see" this if you're an agent.)
- **As data** — two kinds of text source an **agent** can actually read:
  1. **The replay expanded into a global event timeline** (`expand_replay`) —
     *objective ground truth*: every player, the true roles, every kill / body /
     vote / task / chat, by tick. **Game-level, policy-independent.**
  2. **A player's own per-slot logs** — *subjective*: what that one policy perceived,
     believed, and decided. The format is **policy-specific** (crewborg writes rich
     JSON traces; the Nim players write plain-text stderr).

Use the replay/timeline to find **what happened**, and a player's log to see **why
that policy did what it did**; align them by **tick**. This doc is about how to read
each — not about analyzing any particular game.

This doc is **policy-agnostic** (it's about reading any finished Crewrift game).
Related:
- To understand what the events *mean* as gameplay (roles, scoring, phases), see
  [`crewrift-gameplay.md`](crewrift-gameplay.md).
- For what a Crewrift player must *do* over the wire, see
  [`crewrift-player.md`](crewrift-player.md).
- For one policy's log format: crewborg's is documented in
  [`../crewrift/crewborg/docs/trace-logs.md`](../crewrift/crewborg/docs/trace-logs.md).

---

## Getting episode data

Download an episode's replay + logs + metadata in one pass with the lab's
**`coworld-episode-artifacts`** skill (indexed in the lab [`AGENTS.md`](../../AGENTS.md)):

```sh
cd /path/to/player_labs   # the repo root
uv run python .claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py \
  --policy crewborg -n 5 --out /tmp/eps      # add --version N to focus one upload
```

This handles the discovery a fresh agent gets wrong: **league** episodes (what a
league player like crewborg plays) are *not* in the `/v2/episode-requests` table,
so `coworld episodes -p crewborg` returns `[]`; the downloader goes via
`/stats/policy-versions` → `/episodes` instead. It writes one directory per episode:

- `episode.json` — metadata, incl. the **slot↔policy** map, in one of two shapes:
  **league** episodes carry **`policy_results[]`** = `[{position, policy:{name,version}}]`;
  **experience-request** episodes carry **`participants[]`** =
  `[{position, policy_name, version}]` (plus a computed `label` = `"<name>:v<version>"`).
- `results.json` — game outcome arrays (`win`, `kills`, `names`, `scores`, `vote_*`, …).
  **Note:** this does *not* carry the slot↔policy map — use `episode.json`.
- `replay.json` (+ raw `replay.json.z`) — the `.bitreplay` (magic `CREWRIFT`).
- `logs/policy_agent_{N}.log` — one per slot, each policy's own stderr (format varies
  by policy — see §C).

(If you instead use the raw `coworld` CLI — `episode-logs`/`replays --download-dir`
— the files come out prefixed `<episode_request_id>-policy_agent_{N}.log`; the downloader above
produces the clean `policy_agent_{N}.log` names this doc uses.) `coworld run-episode`
also writes a `replay.json` for a locally-run game.

---

## A. The visual replay (for humans)

A Crewrift replay is **not stored frames** — it's per-tick player input masks the
game **re-simulates** on playback (see "The `.bitreplay` format" below). It plays back
in the Crewrift *game image*, either Observatory-hosted (you just get a URL) or by
launching that image locally.

`coworld replay-open` takes an **`<episode_request_id>`** — the id of **one game**
(`V2EpisodeRequestRow.id`), *not* an experience-request/batch id. It resolves that
episode's `replay_url` + `coworld_id` via `GET /v2/episode-requests/{id}`. (Caveat: this
route only resolves **experience-request** episodes — the ids surfaced by `coworld
xp-request episodes`, `coworld replays`, or the `ref_id` in the artifact-download
`index.json`. Raw league `/episodes` ids are a different population and won't resolve.)

**View it — easiest (no local Docker):**

```sh
coworld replay-open <episode_request_id> --hosted   # creates a hosted Observatory replay
                                                    # session and prints a viewer URL
```

This prints (and opens) an **Observatory-served `viewer_url`** — nothing is downloaded
and no container runs locally. Hand that URL to a human and they can watch it in a
browser. This is the default way to watch an episode from an evaluation.

**View it — local (needs Docker):**

```sh
coworld replay-open <episode_request_id>   # resolve manifest+replay, launch viewer locally
# or, given a manifest + replay file you already have:
coworld download crewrift -o /tmp/crewrift
coworld replay /tmp/crewrift/coworld_manifest.json /path/to/replay.json
```

These set `COGAME_LOAD_REPLAY_URI` on a local container and open the **`/client/replay`**
page (singular). Playback is 24 fps and **loops** by default; on-canvas controls give
play/pause, speed (1/2/3/4/8/16×), loop toggle, and a scrubber. `coworld replay` does
**not** verify the replay loaded — if the viewer is empty, use "Verifying playback"
below. It also leaves a `tmp/coworld-replay-*` workspace under the **current directory**
(and a running container) — run it from a scratch dir, or clean up after
(`docker rm -f crewrift-replay`, remove the `tmp/…` dir).

**Manual launch** (what the CLI does under the hood):

```sh
GAME_IMAGE=$(python3 -c "import json;print(json.load(open('/tmp/crewrift/coworld_manifest.json'))['game']['runnable']['image'])")
docker run -d --name crewrift-replay -p 127.0.0.1:52100:8080 \
  -e COGAME_LOAD_REPLAY_URI=file:///coworld-replay/replay.json \
  -v /dir/containing/replay.json:/coworld-replay:ro \
  "$GAME_IMAGE"
open http://127.0.0.1:52100/client/replay
docker rm -f crewrift-replay
```

The `uri` is the path **inside** the container (relative to the `-v` mount).

---

## B. The replay as events: `expand_replay` (objective ground truth)

`tools/expand_replay` in the Crewrift repo (`Metta-AI/coworld-crewrift`)
parses a `.bitreplay` into a tick-by-tick **text event timeline**. Because it reads
the recorded game, it knows the **true roles** — kills are attributed to the real
imposters — so it is the fastest objective view of what actually happened. (The
repo's own `README.md §"Inspect replay timelines"` recommends it as the agent's
starting point.)

### It re-simulates, so the binary must match the recording build

`expand_replay` doesn't read pre-computed events — it **replays the recorded inputs
through its own compiled-in crewrift `sim`** and validates a per-tick hash, stopping
on the first mismatch (`hashOrder: rhoStop`, `replays.nim:52`). The `.bitreplay`'s
format and per-tick hashes are fixed by **the crewrift build that recorded the game**;
if the `expand_replay` binary was built from a *different* crewrift version, its sim
diverges within a few hundred ticks, prints `hash failed`, and emits almost nothing.
(The embedded `gameVersion` is the coarse constant `"1"` and does **not** catch this.)

So a usable binary must be built from the **same crewrift version that recorded the
replay** — matching the git ref is necessary but you really need the same build.

**The good news for league/Observatory replays:** they're recorded by the **current
crewrift upload**, which tracks our pinned `CREWRIFT_REF`. So a binary built at
`CREWRIFT_REF` expands them fully. **Build it with the lab tool:**

```sh
# builds a version-matched, host-native binary, cached under tools/bin/
crewrift_lab/tools/build_expand_replay.sh            # uses CREWRIFT_REF from versions.env
crewrift_lab/tools/bin/expand_replay <replay.json>   # then expand any replay

# one-shot: build (if needed) and expand
crewrift_lab/tools/build_expand_replay.sh --run /tmp/eps/<episode>/replay.json
# a different recording version? pass its ref:
crewrift_lab/tools/build_expand_replay.sh --ref <sha>
```

It fetches the (public) crewrift source for the ref as a tarball (no clone) and
compiles host-native — **no credentials needed**, just the host Nim toolchain. See
[`designs/building_players.md`](designs/building_players.md).

> **Verified 2026-06-09 (closed loop):** a binary built at `CREWRIFT_REF` (`d9f6b30`)
> expands freshly-downloaded crewborg **league** replays **fully** (4720 / 5004
> lines, 0 hash failures). Don't trust the bundled `tests/replays/notsus.bitreplay`
> as an oracle — it is **stale** w.r.t. the committed sim and hash-fails (~tick 36)
> under a current build; use a real downloaded replay. And don't rely on the
> `tools/expand_replay` binary sitting in a game checkout — it matches whatever it
> was last built from, not necessarily the current upload; rebuild with the tool above.

**When it still won't expand:** if a replay was recorded by a crewrift version that
isn't `CREWRIFT_REF` (an older league season, someone else's build), you need that
build — pass `--ref <that sha>` if you know it. When you can't, fall back to the
**visual viewer** (§A — it loads the replay into the *episode's own* game image, so it
always re-simulates correctly) and the **policy logs** (§C — version-independent).

**Output shape:** `tick N` lines, with indented events under the tick they occur.
Players are `color(name)` (e.g. `red(notsus2)`); rooms are named; tasks are
indexed. The full event vocabulary (real lines from the fixture):

```
phase RoleReveal | Playing | Voting | VoteResult | GameOver
  player orange(notsus1) joined
  player orange(notsus1) entered room Bridge
  player orange(notsus1) left room Bridge
  player blue(notsus7) started task 6
  player blue(notsus7) completed task 6
  player orange(notsus1) completed task 8 while dead          # dead crew still do tasks
  score player blue(notsus7) +1 (for completing task)
  player pale blue(notsus8) killed orange(notsus1)            # <- true imposter revealed
  body orange(notsus1) room Hydroponics                       # a body is now present there
  player blue(notsus7) called emergency button
  player red(notsus2) voted skip                               # or "voted <color>"
  player blue(notsus7) said "just resetting imposter cool downs"   # chat
```

**Programmatic use:** `tools/expand_replay.nim` exposes
`expandReplayTimeline(data: ReplayData): ReplayTimeline` — a `seq[ReplayEvent]` with
typed fields (`tick`, `kind` ∈ {PlayerJoined, EnteredRoom, LeftRoom, PhaseChanged,
VoteCalledBody, VoteCalledButton, Kill, BodyFound, Died, Revived, StartedTask,
CompletedTask, VoteCast, Chat, Score}, `actorSlot`/`actorLabel`,
`secondarySlot`/`secondaryLabel`, `room`, `task`, `whileDead`, `phase`, `voteSkip`,
`scoreAmount`/`scoreReason`, `chatText`). The CLI text is just a render of these,
and slots there are real (the text labels by color). Writing a small custom
extractor against this is encouraged over regex-parsing the text.

---

## C. A player's own logs (subjective)

Each player slot writes its **own stderr** to `logs/policy_agent_{N}.log` — that one
policy's subjective point of view (what it perceived, believed, and decided). Unlike
the objective replay timeline, a log:

- is **subjective** — only what that policy could see/infer, and only for its slot;
- is **version-independent** — it's the policy's own recorded output, so it reads
  regardless of the game build (no `expand_replay` hash-match needed). For
  hosted/league episodes this makes logs your **primary** data source;
- has a **policy-specific format** — there is no shared schema across policies.
  crewborg writes structured JSON traces; the Nim players write plain-text stderr.

**Find the slot you care about.** Map slot→policy from `episode.json` (**not**
`results.json`, which has no slot map) and filter by name **and version** — a single
league episode can contain *several* versions of the same policy, all logging the same
shape, so eyeballing the logs won't tell you which is which:

```bash
ep=/tmp/eps/<episode_dir>
# the slot for policy <name> (add `and .policy.version==<N>` if several versions play):
jq -r '.policy_results[] | select(.policy.name=="<name>") | .position' "$ep/episode.json"
# -> the slot number N; the log is "$ep/logs/policy_agent_N.log"
```

(For experience-request episodes the field is
`participants[] | select(.policy_name=="<name>") | .position`.) Occasionally a slot's
"log" is a Kubernetes collector error rather than the policy's output — a `grep '^{'`
(for JSON logs) or a quick glance skips those. **Hosted logs are capped (~10k lines)**
and may be missing the **start** of the game — don't assume tick 0 is present.

**Per-policy log formats:**

- **crewborg** — a per-tick **JSON-lines** trace (perception, suspicion beliefs, mode
  decisions, commands) with tunable verbosity (`CREWBORG_TRACE*`). Full format, field
  reference, and `jq` reading recipes:
  [`../crewrift/crewborg/docs/trace-logs.md`](../crewrift/crewborg/docs/trace-logs.md).
- **notsus / suspectra** — Nim players that log **plain-text stderr** (human-readable
  diagnostic lines, no structured schema); read them directly. suspectra's meeting-LLM
  helper may add its own lines. *(No dedicated format doc — the lines are self-describing.)*
- **A new player** — whatever it emits to stderr; document its format alongside the
  player if it's worth querying programmatically.

---

## D. Replay vs logs — which to reach for

- **`expand_replay` / the replay** = **objective**. Every player, true roles, the
  actual kills/bodies/votes/tasks/chat. Use it to locate the moment that matters (a
  kill, a missed body, a bad vote) and to know ground truth a policy couldn't see.
  Build a **version-matched** binary with `tools/build_expand_replay.sh` (§B) and it
  expands league/Observatory replays fully (they're recorded by the current upload =
  `CREWRIFT_REF`). It only `hash failed`s when the binary doesn't match the recording
  build — then use the viewer (§A) / logs (below).
- **A policy's log** = **subjective**, and **version-independent** — it's that
  policy's own recorded output, so it always reads regardless of game build. For
  hosted/league episodes this is your **primary** data source: at any tick, what that
  policy perceived, believed, and chose (depth depends on the policy's logging — §C).
- **For a hosted episode you can't expand:** the log alone still carries a lot — a
  rich logger like crewborg records its per-tick view of who/what was around and the
  phase/death/vote lifecycle. Use the **visual viewer** (§A) for objective ground truth.
- **Align by tick.** Find the event (timeline or log lifecycle), then read the policy's
  log at that tick (for crewborg, its `decision_snapshot` / nearest `suspicion_snapshot`
  — see [`../crewrift/crewborg/docs/trace-logs.md`](../crewrift/crewborg/docs/trace-logs.md)).

---

## E. The `.bitreplay` format (verified)

The Crewrift `.bitreplay` is the generic **bitworld replay codec** (`bitworld/replays`)
parameterized by Crewrift's spec (`src/crewrift/replays.nim:42-53`):
magic `"CREWRIFT"`, format version `3` (`CrewriftReplayFormatVersion`), the game
name/version, joins that carry name+slot+token (`rjkNameSlotToken`), chat enabled,
compression allowed.

- **Header:** magic, version, game name/version, a u64 millisecond timestamp, then
  the **config JSON** — so a replay carries its own game config.
- **Body:** typed records (in the bitworld codec) — `TickHash(0x01)`, `Input(0x02)`,
  `Join(0x03)`, `Leave(0x04)`, `Chat(0x05)`. Inputs are 8-bit key masks, per player
  per tick.
- **Playback re-runs the sim:** `stepReplay` applies a tick's joins/leaves/chats/
  inputs, calls `sim.step`, then validates `gameHash()` against that tick's
  `TickHash` record (mismatch logs and continues, or aborts under `--mismatch-quit`).
  Keyframes every `ReplayKeyframeTicks = 100` ticks support seeking
  (`replays.nim:41`). Default playback `looping = true` at speeds `[1,2,3,4,8,16]`
  (`replays.nim:40,88`).

Replay **loading** lives in bitworld's `readRuntimeConfig` (`runtime.nim`):
`COGAME_LOAD_REPLAY_URI` reads the bytes and sets `replayMode = true`; the binary
also accepts `--load-replay-uri:<uri>` / `--load-replay:<path>`. `file://` and
`http(s)://` are read directly (no allowlist; `file://` rejected only if missing).
Setting `COGAME_SAVE_REPLAY_URI` together with load is refused (*"Cannot save and
load a replay together"*).

The test files show the format in use: `tests/replays/notsus.bitreplay` is a ready
fixture; `tests/test_replay.nim` round-trips the codec; `tests/manual_replay.nim`
runs 8 bots and saves a replay; `tests/test_replay_controls.nim` exercises
play/pause/speed/loop/scrub.

---

## F. Verifying playback (when viewing, not via the CLI)

Health and "the map rendered" don't prove a replay loaded. The `/replay` stream
carries a text sprite `"replay tick <N>"` (`src/crewrift/global.nim`); confirm `<N>`
advances ~24/sec (it resets to 0 each loop):

```python
# uv run python -   (needs websockets)
import asyncio, re, time, websockets
pat = re.compile(rb"replay tick (\d+)")
async def main():
    async with websockets.connect("ws://127.0.0.1:52100/replay", max_size=None) as ws:
        t0 = time.time()
        while time.time() - t0 < 9:
            msg = await asyncio.wait_for(ws.recv(), timeout=3)
            for m in pat.finditer(bytes(msg)):
                print(round(time.time() - t0, 1), int(m.group(1)))
asyncio.run(main())
```

Advancing `N` = genuine playback; no `replay tick` label = a live game, not a replay.

## G. Gotchas

- **One replay per process.** `replayLoaded` is a single exclusive switch.
- **Use `/client/replay` (singular).**
- **Platform warning** (`linux/amd64` on `arm64`) is harmless; runs under emulation.
- **Don't set save + load together** — the server refuses to start.

---

## See also

- [`crewrift-gameplay.md`](crewrift-gameplay.md) — what the events *mean* as gameplay
  (roles, phases, scoring); read this to interpret a timeline or log.
- [`crewrift-player.md`](crewrift-player.md) — what a player must *do* over the wire.
- [`../crewrift/crewborg/docs/trace-logs.md`](../crewrift/crewborg/docs/trace-logs.md) —
  crewborg's per-slot JSON trace format + `jq` recipes (the §C "crewborg" pointer).
- The `coworld-episode-artifacts` skill (lab [`AGENTS.md`](../../AGENTS.md)) — the
  downloader used in "Getting episode data".
