# CTF tentative lessons — session buffer

**Session started:** 2026-07-14 18:47. This is THIS SESSION's lesson buffer. Write candidate
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

### "Check the map" should always widen to "diff the whole game at the deployed ref" — a narrow question can hide a redeploy

Evidence: Asked to verify the baked map vs the latest game, the map itself was byte-identical
(arena geometry block in sim.nim unchanged 761c098→5450c64 except `*` exports) — but the
same diff surfaced a league redeploy to ctf 0.7.3 with breaking changes the narrow check
would have missed: 3x observation render scale, flag→heart label renames, grenades, no
fog-lift on death, +1/-1 scoring, and a division reset. The map was the only thing that
DIDN'T change.

### The league's deployed game version is discoverable cheaply: `coworld leagues <id>` → coworld ID → `coworld show <cow_id>`

Evidence: `coworld leagues league_3243d905…` prints the league's current coworld
(`cow_e7586b05…`), `coworld show` gives its version (0.7.3), and `coworld download`
fetches the live manifest — comparing its game description against the repo's
`coworld_manifest.json` at candidate refs pins the deployed source ref without any replay
hash-testing. The coworld ID CHANGES on redeploy (WORKING_CONTEXT had stale `cow_325613c1…`
@ 0.5.4), so a recorded cow_id going stale is itself the redeploy signal.

### A division reset (all scores 0.500, rounds 0) accompanies a game redeploy — historical rank is void

Evidence: Competition standings after the 0.7.3 redeploy show every entrant at 0.500 with
0 rounds; beacon's rank-#2/0.298 history is gone. After any redeploy, re-establish the
eval baseline before iterating on behavior — old A/B results compare against a game that
no longer exists.

### coworld-ctf archive tarballs need `gh api repos/…/tarball/<ref>` — the public codeload URL 404s

Evidence: `curl https://github.com/Metta-AI/coworld-ctf/archive/<sha>.tar.gz` returns
"Not Found" (private repo); `gh api repos/Metta-AI/coworld-ctf/tarball/<ref>` works. Same
pattern build_expand_replay.sh already uses — reuse it rather than rediscovering.

### Observation render scale (0.6.0+): wire coords are 3x map pixels; keep internals in map px and divide at the perception seam

Evidence: RULES.md "Observation render scale" — map/fog layers carry object coords and
sprite sizes at 3x; recover with `map_x = (obj.x + sprite.w/2) / 3`. The invisible
`walkability map` sprite stays unscaled (1235x659). So nav.npz, config thresholds, and all
beacon internals can stay in map pixels if perception divides once at the boundary.
Status: fix not yet implemented; beacon v5 is presumed blind on the live game until then.
