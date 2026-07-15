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
Status: DONE in v6 — one-line change in `_center` + `config.RENDER_SCALE`; nothing else
in the pipeline needed touching. Seam design validated.

### A wire-format port is ONE build-upload-eval iteration; a full-field head-to-head battery (6x10 eps) turns around in ~15 min

Evidence: v6 = 3 small perception edits, tests, build, upload, then 6 parallel 10-episode
8v8 xreqs vs every division entrant — all posted at once, all complete inside ~15 minutes,
fetched in parallel with `--elevated`. Faster and far more informative than the old
one-opponent-at-a-time evals; make "vs the whole field" the default eval shape.

### Post-redeploy, re-verify WHO the wall is — the champion bot gets replaced too

Evidence: after the 0.7.4 redeploy the old ctf-baseline-16 is gone from the field; daveey's
new `ctf-focusfire:v5` is the new #1 and beats v6 0-9 (out-kills ~2:1) while v6 sweeps the
other five entrants 50-0 (49 of 50 by capture). An eval battery vs a stale field answers
last week's question.

### Copying the champion's mechanism isn't enough — verify the mechanism FIRES before crediting/blaming it

Evidence: v7 ported the baseline's peek-fire-duck cycle faithfully (same constants, same
cell search, pre-laid aim) and changed NOTHING vs focusfire: v6 0-9/128 kills/23.9 deaths
→ v7 0-9/127/24.0 — numbers this identical suggest the override rarely activates, not
that cover micro is worthless. Should have shipped activation counters in the same
iteration (one trace field) — a behavior A/B without mechanism instrumentation can't
distinguish "didn't fire" from "fired and didn't help", which decide opposite next steps.

### Policy-artifact zips come back EMPTY from the fetcher; stderr traces are the reliable channel

Evidence: two fetch attempts (incl. --force, --elevated) on a fresh v8 xreq returned
`policy_artifacts: []` for every episode — the `jsonl@artifact` trace member never
materialized. Re-uploading the same image with `--secret-env
BEACON_TRACE_OUTPUTS=jsonl@stderr` (v9) put full trace jsonl in the ordinary
policy_agent_N.log files on the first try. Until the artifact path is debugged, run
diagnostics with stderr traces. (Also: logs are stored as a Python bytes-repr string —
`ast.literal_eval` before splitlines.)

### The activation diagnostic worked exactly as intended — and refuted the comfortable hypotheses in one 3-episode run

Evidence: v7's flat A/B had three candidate explanations; one cheap instrumented run
(v8/v9, 3 eps) measured duck=14.0%/peek=3.7% of alive time (421+219 engagements across
24 agents) with kills/deaths unchanged — killing "never fires" and "no cover nearby"
and leaving "cover micro isn't the binding constraint". The next iteration now targets
the right layer (target selection / velocity lead / focus fire) instead of tuning duck
knobs blind. Pattern to keep: null A/B -> activation-instrumented micro-run -> THEN
choose the next lever.

### All-±1-scores with 0 kills/0 captures/0 deaths = opponent never actually played; discount the sweep

Evidence: v6 "10-0" vs daf-actinf-ctf-v4:v1 had zero kills, zero captures, zero deaths on
both sides — every red seat +1, every blue -1. That's a disconnect/abandon walkover
(0.7.4 even added a disconnected-losers fix upstream), not gameplay signal. Check the
kills/captures columns before counting a win streak as evidence.
