# CTF tentative lessons — session buffer

**Session started:** 2026-08-03 12:35. This is THIS SESSION's lesson buffer. Write candidate
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

### beacon:v67 is auto-mirrored into the Paintbot league and scores 0 there
Entrant mirroring (metta seed.py, ("paintbot","ctf")) auto-submits CTF
champions into Paintbot, where beacon's offline arena bake is blind on
generated maps ("James Botts", active, 0.0 pts vs daveey's 84). CTF-side
implication: a beacon submission now competes in TWO venues; if the mirrored
seat matters, either retire it or expect its Paintbot losses to be visible
under the same player. (Found 2026-08-03 while bootstrapping paintbot_lab.)

### beacon's mapdata.py seam made the paintbot fork cheap — protect it
The whole stencil port hinged on every map consumer going through mapdata's
eight functions; ~5k lines of nav/fight/belief/action moved nearly unchanged
once that seam was rebuilt online. When editing beacon, keep new map facts
behind mapdata (or config) rather than inlining geometry into consumers — the
seam is what keeps the lineage portable.

### beacon's three lru_cache map loaders are a latent trap if CTF ever varies maps
mapdata._load, poi._load, nav._route_distances are process-lifetime caches —
correct only because the CTF league runs one fixed arena with maxGames=1. If
the league ever adopts paintbot-style variants (the manifest schema already
supports it upstream), these silently serve episode-1 geometry to episode 2.
stencil's fix (episode-scoped WorldMap owned by Belief) is the reference.
