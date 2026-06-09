# player_labs — deferred tasks

Tasks we've intentionally parked to handle later. Add items here when we defer
something mid-session; check it back at the start of focused work.

## Open

- [ ] **Rename crewborg `crewrift.crewborg` → `players.crewborg`** (approach approved).
  Make the lab own the `players` package: move `crewrift_lab/crewrift/crewborg` →
  `crewrift_lab/players/crewborg`, rewrite self-imports `crewrift.crewborg` →
  `players.crewborg` (leave `players.player_sdk` imports as-is), add
  `crewrift_lab/players/__init__.py`, and bring the SDK in as a **relative symlink**
  `crewrift_lab/players/player_sdk → ../../../players/players/player_sdk` (live, no
  drift). Drop the editable `players` dependency from `pyproject.toml` (it would
  re-collide) and add the SDK's deps directly; flip `packages.find` include
  `crewrift*` → `players*`; run the tests. **Revisit portability later** — the
  absolute/relative symlink assumes the `~/coding/player_labs` + `~/coding/players`
  sibling layout.

- [ ] **Fix the crewborg bridge to read the canonical WS env var.**
  `crewrift_lab/crewrift/crewborg/coworld/policy_player.py` reads
  `COGAMES_ENGINE_WS_URL` (a legacy alias). The runner sets both, but the canonical
  player-contract var is **`COWORLD_PLAYER_WS_URL`** (see metta `docs/roles/PLAYER.md`).
  Switch it to read `COWORLD_PLAYER_WS_URL` (optionally falling back to the alias).
  This is a player-code change — run it through the loop, not as a drive-by.

- [ ] **Fix dangling lab-README links once the READMEs are rewritten.**
  Both lab READMEs were deleted (`player_labs/README.md`, `crewrift_lab/README.md`)
  to be rewritten later. Until then, four links point at the now-missing
  `crewrift_lab/README.md`:
  - `crewrift_lab/crewrift/crewborg/README.md` → `../../README.md` (×2)
  - `crewrift_lab/crewrift/crewborg/AGENTS.md` → `../../README.md`
  (The `crewrift-replays.md → ../README.md` link was repointed to the lab `AGENTS.md`
  during the replay-doc de-crewborging, so it's no longer dangling.)

  When the READMEs are rewritten, confirm these resolve (or repoint them). Also
  re-home the content worth carrying over from the old READMEs (external-checkouts
  table + "never write to metta", the player contract, setup commands, gotchas, the
  two workflows) — recoverable from git history (`git show HEAD:README.md`,
  `git show HEAD:crewrift_lab/README.md`).

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
