# player_labs — deferred tasks

Tasks we've intentionally parked to handle later. Add items here when we defer
something mid-session; check it back at the start of focused work.

## Open

- [ ] **Reconsider the crewborg `crewrift.crewborg` → `players.crewborg` rename.**
  Goal was to have the fork sit at `players.crewborg` (matching upstream). The
  previously-approved mechanism (symlink the SDK from a `~/coding/players` sibling) is
  now **obsolete** — as of 2026-06-09 the SDK is **git-installed** from the public
  players repo, with **no sibling checkout**. A local `players.crewborg` would still
  collide with that installed `players` package (one regular package can't span two
  locations), so the rename is *harder* now, not easier, and arguably not worth it —
  `crewrift.crewborg` works cleanly and reads fine. Decide whether to drop this task
  or find a new mechanism (e.g. a namespace-package split) before doing anything.

- [ ] **Fix the crewborg bridge to read the canonical WS env var.**
  `crewrift_lab/crewrift/crewborg/coworld/policy_player.py` reads
  `COGAMES_ENGINE_WS_URL` (a legacy alias). The runner sets both, but the canonical
  player-contract var is **`COWORLD_PLAYER_WS_URL`** (see metta `docs/roles/PLAYER.md`).
  Switch it to read `COWORLD_PLAYER_WS_URL` (optionally falling back to the alias).
  This is a player-code change — run it through the loop, not as a drive-by.

- [ ] **Link the starting policies in `crewrift-player.md` §8.** All three are now
  vendored under `crewrift_lab/crewrift/`; wire up concrete pointers so a new author
  can clone one, and describe what each demonstrates:
  - **notsus** *(Nim)* — `crewrift_lab/crewrift/notsus/`; the minimal Sprite-v1
    reference (public image `…/players/notsus:latest`).
  - **crewborg** *(Python)* — `crewrift_lab/crewrift/crewborg/`; the full worked
    player (perception/strategy/modes/bridge).
  - **suspectra** *(Nim + Python LLM hook)* — `crewrift_lab/crewrift/suspectra/`; a
    notsus fork adding evidence voting + a bounded meeting LLM.
  The §8 doc currently leans on notsus + crewborg; add suspectra and align the paths
  to the vendored copies. (See the [Player policies] index in
  `crewrift_lab/AGENTS.md` for the per-policy summary to draw from.)

- [ ] **Mint + wire a GitHub PAT for the Nim player builds (notsus, suspectra).**
  Their images clone the **private** `Metta-AI/coworld-crewrift` (+ its private
  `bitworld` dep), so `tools/build_player.sh notsus|suspectra` needs a GitHub token
  with read access to those repos. The build code is done — it passes the token as a
  BuildKit secret and fails fast with guidance if it's missing/invalid. Remaining:
  - Mint a PAT (fine-grained: Metta-AI org, `coworld-crewrift` + `bitworld`,
    Contents: Read-only; or classic `repo` scope).
  - Provide it via `export GITHUB_PAT=…` or `gh auth login`, then run a real Nim
    build once to confirm the clone + `nimby sync` + `nim c` path works end-to-end
    (only crewborg has been built so far). See
    `crewrift_lab/docs/designs/building_players.md` §Credentials.

## Done

- **Write a real `AGENTS.md`** — done; root `AGENTS.md` has the skills index, this
  TODO pointer, and the game/world-agnostic-root rule.
- **Rewrite the lab READMEs** — done; `player_labs/README.md` and
  `crewrift_lab/README.md` rewritten (human + agent oriented, current state). The
  three crewborg → `../../README.md` links now resolve; old-README content worth
  keeping (external-checkouts table, never-write-to-metta, the player contract) was
  re-homed and brought up to date.
