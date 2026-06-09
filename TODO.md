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

- **Fixed the crewborg bridge WS env var** — `policy_player.py` now reads the canonical
  `COWORLD_PLAYER_WS_URL`, falling back to the legacy `COGAMES_ENGINE_WS_URL` alias;
  crewborg docs updated to match. 263 tests pass.
- **Linked the starting policies in `crewrift-player.md` §8** — notsus / crewborg /
  suspectra, pointed at their vendored paths with what each demonstrates (minimal
  baseline / full worked player / LLM-meeting wiring).

- **DROPPED the `crewrift.crewborg` → `players.crewborg` rename.** Not worth it, and
  the git-installed SDK makes it impossible cleanly: the installed `players` is a
  *regular* package (can't be split across locations) and already ships
  `players.crewrift.crewborg` (the upstream fork). A local `players.crewborg` would
  shadow the whole installed `players` (breaking `players.player_sdk`) or be
  unreachable — the only alternative being to re-vendor the SDK (drift). `crewrift.crewborg`
  is the *correct* name: it cleanly separates our drifting fork from upstream-as-installed.
  (No symlink ever existed — that was part of the never-executed editable-sibling plan.)
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
