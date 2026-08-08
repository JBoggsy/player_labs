# CTF tentative lessons — session buffer

**Session started:** 2026-08-07 15:58. This is THIS SESSION's lesson buffer. Write candidate
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

### The viewer silently drew a baked arena over generated maps instead of failing
`viewer.html` + `viewer_bundle.py` were built for CTF's one fixed arena, so
reusing them on Paintbot produced a plausible-looking replay with NO walls —
wrong output, not an error. The fix made geometry come from the replay itself
(`expand_replay_json <replay> [pos_every] walkability` emitting `wall-runs-v1`)
and made the bundler raise when the map is absent. Status: general rule for
sharing ctf_lab tooling across games — assumptions inherited from the fixed
arena must fail closed, because a viewer that renders is assumed correct.

### `build_expand_replay.sh`'s fast path ignored source edits for a whole session
The cache check was `[[ -x "$out_bin" && -x "$json_bin" ]]` — existence only. So
after editing `expand_replay_json.nim`, the script printed "cached binaries up
to date" and kept running the OLD binary, which emitted no `walkability_map`.
Now it also requires `"$json_bin" -nt "$LAB_JSON_SRC"`. Status: any build-cache
fast path keyed on existence rather than source mtime is this bug waiting.

### Slot-parity color defaults silently mislabel four-team FFA
The viewer fell back to `slot % 2 === 0 ? red : blue` when a team was unknown,
which is invisible in 2-team CTF and simply wrong for Paintbot's four-color FFA
— ground truth read as red/blue with green/yellow players mislabeled. Now the
episode's authoritative slot-team config supplies colors. Status: red/blue
binary assumptions are a recurring CTF→Paintbot porting hazard (cf. TODO's
"Generalize event-warehouse outcomes beyond red/blue").

### `rotate_lessons.sh` archives every lab's buffer but commits only paintbot's
Commit 6fbb099 is titled "rotate ctf session buffer" yet its diff touches only
`paintbot_lab/` paths; `ctf_lab/lessons_archive/TENTATIVE_LESSONS-20260804-
103458.md` — three real beacon/mirroring lessons — sat untracked for three days
until a cleanup pass found it. Status: symptom committed (3997b0a), the hook
itself is UNFIXED and will orphan another lab's archive on the next rotation.
This buffer's own lifecycle text points at `ctf_lab/tools/rotate_lessons.sh`.
