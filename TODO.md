# player_labs — deferred tasks

Tasks we've intentionally parked to handle later. Add items here when we defer
something mid-session; check it back at the start of focused work.

## Open

- [ ] **Quickstart: point, don't write (Pile 1).** The README quickstart should *route*
  to the durable docs, not restate them — and an agent not on its first run should
  reach this knowledge without the quickstart. Wire each step to its home: step 1→2 to
  the `crewrift-diagnose` skill + crewrift-report; step 3 ("change crewborg") to
  crewborg `design.md` (esp. §12 tuning parameters, the first-change surface) +
  crewborg `AGENTS.md`; the re-measure to the `crewrift-ab` skill (+ its setup via
  coworld-experience-requests). The skills it pointed to all exist now, so it's unblocked.

- [ ] **Minor: a version-log convention.** best_practices says "keep a version log"
  (version → the change it carries) but there's no file/template/home for it. Add a
  simple convention (e.g. a `versions/` log or template) so the discipline has a place.

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

- **Direction / hypothesis guide → `crewrift-diagnose` skill** — done (draft, will
  iterate). Signals → evidence-grounded mechanistic improvement hypotheses → presented
  to the human as options. Distilled from prior player-improvement work (alpha_cog/
  bulbacog notebooks + the agent-transcript corpus); the genuinely-new game-agnostic
  lessons folded into `best_practices.md`, which is positioned as the cross-cutting
  *checklist* while the skills are the authoritative how-to.
- **A/B re-measure capability (`crewrift-ab` skill)** — done; its own skill, fresh +
  matched + head-to-head: `scripts/compare.py` (role-split metric deltas with
  normal-approx significance + a regression scan, led by `--target`) for the hard
  metrics, plus a SKILL.md that walks the matched-request setup and a context-driven
  (dimension / opponent / fault) **qualitative** investigation of the two sides'
  logs/replays. Validated: null test (same version → all "noise") + significance/
  direction unit checks. Wired into AGENTS + linked from crewrift-report.
- **Write a real `AGENTS.md`** — done; root `AGENTS.md` has the skills index, this
  TODO pointer, and the game/world-agnostic-root rule.
- **Rewrite the lab READMEs** — done; `player_labs/README.md` and
  `crewrift_lab/README.md` rewritten (human + agent oriented, current state). The
  three crewborg → `../../README.md` links now resolve; old-README content worth
  keeping (external-checkouts table, never-write-to-metta, the player contract) was
  re-homed and brought up to date.
