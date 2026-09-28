# Paintbot PW lab

A lab for building and improving a BASIC policy for **paintbot-pw**, Paintbot rebuilt on
the Polyworld Nim engine. Sixteen cogs (Red = even seats, Blue = odd) fight for ten
heart towers on Heartwick island; every seat is a BASIC script the game hosts itself, so
there is no player container. Agree the policy and strategic objective with James before
implementing behavior.

**This is not [`paintbot_lab/`](../paintbot_lab/AGENTS.md).** That lab covers the older
Paintbot coworlds (Season 1 capture-the-heart shooter, Season 2 battle royale with WASM
plays and the Stencil Nim player). Different engine, rules, player format, replay format
and tools. Do not reuse its code, mechanics claims or lessons here without re-verifying
them against paintbot-pw source. The closest sibling is
[`gods_of_the_arena_lab/`](../gods_of_the_arena_lab/AGENTS.md): same engine family and
BASIC dialect, different game and host API.

## Read in this order

1. [WORKING_CONTEXT.md](WORKING_CONTEXT.md) — current objective, identity, next decision.
2. [README.md](README.md) — the knowledge map: what we know, where it is, how to check it
   is still current. Run `tools/deployed_ref.py` first.
3. [docs/mechanics.md](docs/mechanics.md) — the rules as deployed; section 1 (winning
   versus glory) sets the whole strategy.
4. [docs/policy-surface.md](docs/policy-surface.md) — the BASIC dialect, budgets, failure
   modes and every host call. Read before writing any BASIC.
5. [docs/field.md](docs/field.md) — leagues, match configuration, standings, experience
   request options and credit budget.
6. [docs/evidence-pipeline.md](docs/evidence-pipeline.md) — artifacts, hash-checked
   re-simulation, local runs, and the tools still to build.
7. [TENTATIVE_LESSONS.md](TENTATIVE_LESSONS.md) — untested hypotheses to turn into A/Bs.

## Files

| Path | Contents |
| --- | --- |
| `docs/mechanics.md` | Rules at the deployed commit: heart meter vs glory, awards, hearts, lives, combat, pickups, vision, modes, result fields, guide-vs-code mismatches. |
| `docs/policy-surface.md` | Upload formats (raw `.bas`, neural ZIP), dialect, per-tick execution, budgets, failure modes, host API, advisor oracle, starter summaries. |
| `docs/field.md` | Both leagues' configuration and ranking rule, dated standings, entrants, our account's presence, experience-request fields and credit costs. |
| `docs/community.md` | Forum/wiki digest (the forum is empty; the wiki is a stale README copy), maintainer measurements, gotchas, release cadence. |
| `docs/evidence-pipeline.md` | Artifact inventory, replay format, the verified build/replay/local-run commands, the per-seat stats probe (appendix), recommended tools. |
| `reference/*.bas` | Official starters at the deployed tag: `base.bas` (teams baseline), `jev.bas` (base + LLM advisor), `ffa.bas` / `ffa_blind.bas` (Heartland). Keep reference files distinct from candidates. |
| `reference/manifest-0.3.65.json` | The deployed coworld manifest (config schema, variants, readme). |
| `tools/deployed_ref.py` | Resolves each league's coworld release to its `coworld-v<version>` tag commit and says whether the docs are current. |
| `episode_data/` | Downloaded hosted episodes (gitignored), one directory per episode. |

## Rules specific to this lab

- **Cite the deployed commit, not `main`.** The source is `Metta-AI/paintbot-pw` (local
  clone `~/coding/coworlds/paintbot-pw`), a standalone copy of Polyworld. The manifest's
  `source_url` carries no commit; the `coworld-v<version>` tag is the only link from a
  release to source, which `tools/deployed_ref.py` resolves. Releases ship several times a
  day (40 in the first 10 days), so re-run it before trusting any mechanics claim.
- **Only a win scores.** The result `scores` are the winning team's glory; the loser and
  both sides of a draw get 0. League Elo compares the two sides' mean scores as
  win/draw/loss, so a win whose glory has decayed to 0 rates as a draw. Never read glory
  size as rank movement, and never infer a win from anything but the result.
- **A BASIC compile error fails the whole episode** (no results, no data from that
  eval slot); it shows up as failed hosted episodes, which is the signal to read. When
  the platform attributes a failure to one policy, Elo scores that side as a forfeit loss
  (`elo.py:170-175`) and 3 consecutive failures disqualify a league entry, so only submit
  a version with completed hosted episodes. A runtime error or budget overrun disables
  only that seat for the rest of the episode.
- **Budgets are 50,000 instructions and 125,000 work units per decision**
  (`bots.nim:147-148`); the guide and starter headers still say 20,000.
- **Teams-only vs FFA-only names.** Calling an FFA-kin function (`kin()`, `gene()`, …) in
  the teams game is a compile error. Keep Heartland code paths separate.
- **Replays re-simulate across versions.** The newest build replays older rules versions
  hash-exactly (verified on rules-44 replays with the 0.3.65 build). Always hash-check;
  the repo's `replay_stats.nim` does not.
- **Experience-request rosters:** pin all 8 opponent seats to one explicit policy to match
  league conditions; `top_n`/`random` draw per seat and mix opponents.
- **Identity.** Uploads bind to the active player session; confirm `softmax status` shows
  the intended player before uploading (see WORKING_CONTEXT).
- Use the shared experience-request, artifact, A/B and miner skills; this lab supplies
  the game adapters. Keep documentation as complete current references; replace
  superseded information in place.
- League submission and public community writing remain explicitly gated.
