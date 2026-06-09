# In-lab player builds (Plan A)

How we build Crewrift player images **inside this lab** — turning a vendored player
policy into a `linux/amd64` image you can upload to Coworld, with the host needing
only Docker.

This is the **build** half of the loop's Gate-1/upload step. For the runtime image
*contract* (what any Coworld player image must be, regardless of game) see the
lab-root [`player-build.md`](../../../player-build.md); for what a Crewrift player
must *do* over the wire see [`crewrift-player.md`](../crewrift-player.md). This doc
is specifically about **producing the image**.

> **Status:** Plan A, implemented. One thin wrapper
> (`crewrift_lab/tools/build_player.sh`) builds any policy; each policy carries its
> own Dockerfile; the crewrift game version is pinned centrally in
> `crewrift_lab/tools/versions.env`.
>
> **No credentials needed — the host needs only Docker.** All inputs are public:
> crewborg installs the shared SDK from the public players repo, and notsus/suspectra
> clone the public crewrift game repo (+ its bitworld dep). Validated end-to-end.

---

## The general case — building any Crewrift player in-lab

Read this section first whether or not your player is vendored here; it's the model
every player build follows. The per-player sections after it are worked instances.

### What the build must produce

Every Coworld player image obeys the same contract (full details in
[`player-build.md`](../../../player-build.md)):

- **`linux/amd64`** — hard-checked at upload; arm64 is rejected. The lab host is
  Apple Silicon, so **the shippable artifact must be built inside Docker**
  (`buildx --platform=linux/amd64`, qemu emulation). A host-native compile produces
  an arm64 binary that cannot be uploaded — this is why a stray `notsus.out` (a
  Mach-O arm64 binary) is useless for shipping.
- A baked command that **reads `COWORLD_PLAYER_WS_URL`, connects, plays one slot,
  and exits** when the episode ends.
- **No secrets baked in**, and **no behavior/experiment knobs baked in** (see the
  principle below). Lightweight (hosted default 250m CPU / 256Mi).

### The three forces a Crewrift build has to satisfy

1. **The game dependency.** A Crewrift player is written against the game's
   protocol/modules. Nim players *compile* against the crewrift game source; Python
   players *decode* the wire protocol but still must track the game's scene
   vocabulary. Either way the build is pinned to a **specific game version**.
2. **The toolchain.** Whatever compiler/runtime the player needs (Nim + nimby, or
   Python + pip) must be present **in the image build**, not on the host.
3. **Shared code.** A player may depend on shared lab/SDK code (e.g. the Python
   players' `players.player_sdk`). The build must make that code available without
   dragging in unrelated lab tooling.

### The principles (Plan A)

- **Docker on the host; everything heavy is fetched inside the build.** The Nim
  toolchain, the game repo, Python packages, and the SDK are all installed *inside*
  the image build — no host Nim, no host Python env, and **no credentials** (all
  inputs are public). The host needs only Docker.
- **Hermetic and pinned.** Heavy deps are fetched at build time, each pinned to a
  ref: the (public) game repo is cloned **at a deliberately-pinned commit**
  (`CREWRIFT_REF`) inside the Nim builds, while the shared SDK is installed from the
  **public `Metta-AI/players` repo at `PLAYERS_SDK_REF`**
  ([`tools/versions.env`](../../tools/versions.env)) — which defaults to **`main`**
  (latest SDK each build; pin to a SHA for a reproducible image). No local checkouts.
- **One central game pin.** [`tools/versions.env`](../../tools/versions.env) holds
  `CREWRIFT_REF`, passed to every Nim build as `--build-arg`. **It must match the
  game version running in the league you target** — a player compiled against a
  different game version can skew from live behavior (the same version-skew that
  breaks `expand_replay`; see [`crewrift-replays.md`](../crewrift-replays.md) §B).
  Change the pin in one place and every player rebuilds against it.
- **The image is the code; the env is the experiment.** Bake into the image only
  what's needed to *run* the policy. **Do not bake behavior/experiment knobs**
  (e.g. crewborg's `CREWBORG_BE_DUMB`, which swaps in a deliberately-reduced
  variant). Set those at **upload time** (`coworld upload-policy --secret-env …` /
  env). This keeps the image behavior-neutral and reproducible, and keeps the
  version log honest: one image = one codebase, the env records the experiment.
  (Operational config that merely wires the policy to its own files — e.g.
  suspectra's `SUSPECTRA_LLM_*` paths — is part of the policy's identity and may be
  baked.)
- **Secrets only at upload.** LLM/cloud keys attach to the policy version
  (`--secret-env`, `--use-bedrock`), never to the image.

### How to build (the wrapper)

```sh
# from anywhere; the wrapper resolves the lab paths itself
crewrift_lab/tools/build_player.sh <policy> [--tag REF] [--push REF] [--game-ref REF]
```

It produces a `linux/amd64` image (default tag `players-<policy>:dev`), then prints
the `coworld upload-policy` command to run next. `--game-ref` overrides the central
`CREWRIFT_REF` for a one-off build (e.g. to match a specific league's game version).

### Adding a new player (vendored or not)

The build only needs three things wired, so it generalizes cleanly:

1. **A Dockerfile** that produces the amd64 image for your player, following the
   matching template below:
   - **Nim player** → copy the notsus Dockerfile: clone the (public) game at
     `ARG CREWRIFT_REF`, `nimby --global sync nimby.lock`, overlay your source at
     `players/<name>`, `nim c … players/<name>/<name>.nim`, then a slim runtime stage
     that copies the binary and bakes `CMD ["/bin/<name>"]`.
   - **Python player** → copy the crewborg Dockerfile: install your deps (and the
     SDK, if used), put your package on `PYTHONPATH`, bake
     `CMD ["python","-m","<your.module>"]`.
2. **A context decision** — where does your build get its inputs?
   - **Self-contained** (like the Nim players) → context is your player directory;
     the Dockerfile clones/fetches everything else. Register in the wrapper's
     `notsus|suspectra)` branch.
   - **Needs the shared SDK** (like crewborg) → the Dockerfile `pip install`s
     `players` from the pinned public repo (`PLAYERS_SDK_REF`); the wrapper just
     stages your fork (+ any package `__init__`) onto `PYTHONPATH`. Register in the
     `crewborg)` branch. (No local checkout — the SDK comes over the network, pinned.)
3. **Nothing else if your player isn't vendored.** A non-vendored player (source
   living elsewhere, or built straight from its origin repo) uses the same
   Dockerfile patterns; point the wrapper's context at wherever the source lives.
   The pinned-game-ref and no-baked-behavior principles apply identically. Vendoring
   only changes *where the source is copied from*, not how the image is built.

---

## Per-player builds

All three are driven by `tools/build_player.sh <policy>` and produce a
`linux/amd64` image. They differ only in toolchain and how the game/SDK dependency
is satisfied.

### crewborg (Python)

```sh
crewrift_lab/tools/build_player.sh crewborg
```

- **Image:** `python:3.12-slim`. Installs the shared SDK + crewborg's runtime deps
  (numpy/pydantic/websockets/cramjam are the SDK's base deps; `[bedrock]` adds
  boto3), puts the fork on `PYTHONPATH`, runs `python -m
  crewrift.crewborg.coworld.policy_player`.
- **SDK + fork:** crewborg is re-rooted out of `players` into the top-level
  `crewrift.crewborg` package and imports only `players.player_sdk`. The Dockerfile
  (`crewborg/coworld/Dockerfile`) `pip install`s the SDK straight from the public
  players repo's source tarball at `PLAYERS_SDK_REF`
  (`players[bedrock] @ https://github.com/Metta-AI/players/archive/<ref>.tar.gz` — no
  git or local checkout needed in the build), then the wrapper-staged fork + the lab
  `crewrift/__init__.py` are copied onto `PYTHONPATH`. It deliberately does **not**
  `pip install` the lab package (that would pull lab tooling like `coworld[auth]`).
- **Behavior env is NOT baked** — `CREWBORG_BE_DUMB`, `CREWBORG_POLICY_VARIANT`,
  etc. are experiment knobs; set them at upload time. (Upstream's image baked
  `BE_DUMB=1`, a reduced variant — the lab image ships the full default behavior.)

### notsus (Nim)

```sh
crewrift_lab/tools/build_player.sh notsus
```

- **Image:** Debian + nimby 0.1.26 → Nim 2.2.4. Clones the game at `CREWRIFT_REF`,
  `nimby --global sync nimby.lock`, overlays the vendored source at
  `players/notsus`, compiles to `/bin/notsus`; slim runtime stage runs it.
- **Self-contained context:** the build context is `crewrift/notsus/`; the
  Dockerfile fetches the (public) game and toolchain itself — no credentials.

### suspectra (Nim + Python LLM hook)

```sh
crewrift_lab/tools/build_player.sh suspectra
```

- **Image:** same Nim build as notsus (compiles `suspectra.nim`), plus a runtime
  stage with `python3` + `anthropic` + `boto3` for the meeting-LLM helper
  (`llm_meeting.py`, invoked by path; prompts in `memory/`).
- **Baked env is operational, not experimental:** the `SUSPECTRA_LLM_*` vars wire
  the helper to its prompt/memory files and cap call latency — part of the policy's
  identity. The Anthropic/Bedrock **key** is still attached at upload, never baked.
  (No build-time credentials — same public clone as notsus.)

---

## Toolchain & dependency summary

| | crewborg | notsus | suspectra |
|---|---|---|---|
| Language | Python 3.12 | Nim 2.2.4 | Nim 2.2.4 + Python 3 |
| Base image | `python:3.12-slim` | `debian:bookworm-slim` | `debian:bookworm-slim` |
| Build toolchain | pip | nimby 0.1.26 / Nim | nimby 0.1.26 / Nim |
| Game dependency | scene vocab (no compile) | clone game @ `CREWRIFT_REF` | clone game @ `CREWRIFT_REF` |
| Shared code | SDK from public players repo @ `PLAYERS_SDK_REF` | — | — |
| Credentials | none | none (all repos public) | none (all repos public) |
| Runtime deps | players[bedrock] | libcurl4 | libcurl4 + anthropic + boto3 |
| Entry | `python -m …policy_player` | `/bin/notsus` | `/bin/suspectra` |
| Build context | the fork (SDK pip-installed) | the policy dir | the policy dir |

**Host requirements:** just Docker with `buildx` + amd64 emulation (qemu) — Docker
Desktop or colima both provide this; **no credentials**. Nim builds clone the public
game repo and pull Nim deps over the network at build time; crewborg pulls Python deps
from PyPI and the SDK from the public players repo.

## Known follow-ups

- **Keep `CREWRIFT_REF` matched to the deployed game.** It can't be auto-resolved
  (the platform exposes no commit; `master` runs ahead of the deployed `:latest` — a
  `master`-built `expand_replay` hash-failed on a fresh live replay 2026-06-09, while
  `d9f6b30` expands cleanly). So it's a deliberate pin; bump it when
  `build_expand_replay` starts hash-failing on *fresh* replays (the redeploy signal).
  Currently `d9f6b30`, validated against the live game 2026-06-09.
- **Optional local-checkout fast path.** A `--local-game` mode (mount
  the `Metta-AI/coworld-crewrift` repo instead of cloning) would speed iteration at
  the cost of hermeticity; not implemented — add it if cold-build time hurts.
- **Optional shared build-base image (Plan B).** If repeat Nim builds become slow,
  a `crewrift-nim-base` (game-at-ref + nimby-synced, built once) makes each player a
  thin `FROM`-based overlay. Deferred until the 3-policy build time justifies it.
