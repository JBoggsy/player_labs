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

### pytest `norecursedirs` REPLACES the defaults — restate them or lose `.*`
Excluding `paintbot_lab/paintbot/rl/data` (game worktrees with duplicate test
basenames) dropped pytest's default `.*` pattern, which instantly exposed every
lab's `.cache/coworld-ctf/<sha>/tools/ci/` checkout and turned 5 collection
errors into 10. Evidence: root `pytest --collect-only` went 5 → 10 → 6 errors
across the three edits; the final `pyproject.toml` restates all nine defaults
alongside the addition. Status: any future norecursedirs edit must keep them.

### `rotate_lessons.sh` archives every lab's buffer but commits only paintbot's
The 2026-08-04 SessionStart commit (6fbb099) is titled "rotate ctf session
buffer" yet its diff touches only `paintbot_lab/TENTATIVE_LESSONS.md` and
`paintbot_lab/lessons_archive/`. `ctf_lab/lessons_archive/TENTATIVE_LESSONS-
20260804-103458.md` — three real beacon/mirroring lessons — sat untracked for
three days until this cleanup found it. Status: symptom committed (3997b0a),
hook root cause UNFIXED; the next rotation will orphan another lab's archive.

### Untracked scratch that shadows the repo's own toolchain is the expensive kind
`rl/data/` is gitignored and correctly so, but it holds full game-repo
worktrees, so it broke repo-wide `pytest` collection from a directory nobody
would think to look in. Evidence: the collection error named
`rl/data/worktrees/gv35/tools/ci/test_next_coworld_version.py`. Status: worth a
habit — when a tool writes checkouts under the repo, exclude them from test
discovery in the same change that creates them, not when they first bite.

### Paintbot's replay viewer lives in ctf_lab, and its build defaults to the CTF game
`viewer.html`, `viewer_bundle.py`, and `expand_replay_json.nim` are shared (paintbot
is a second manifest over the same engine), but `ctf_lab/tools/build_expand_replay.sh`
defaults to `CTF_REF=beae1614` — a CTF commit. The re-sim validates a per-tick hash,
so the README's bare invocation would hash-fail on every Paintbot replay and yield no
events. Evidence: the ctf script's line 42 default vs `PAINTBOT_GAME_REF=9dedac0`.
Status: fixed by `paintbot_lab/tools/build_expand_replay.sh`, which sources this lab's
versions.env. Verified end-to-end — it built the GV41 reader at 9dedac0.

### Paintbot work lands in ctf_lab whenever it touches the shared viewer — say so
The generated-map walls, four-team FFA colors, and Stencil belief overlays are all
paintbot features, but they were implemented in `ctf_lab/tools/` because that is
where the tool lives, which reads as focus drift in `git status` and in commit
subjects (`ctf: …`). Status: ctf_lab/AGENTS.md now carries a SHARED-with-paintbot
warning so a future CTF session does not regress generated-map support. Open
question for James: this tool and `rotate_lessons.sh` are both multi-lab
infrastructure living in ctf_lab; the root README says root `tools/` is the
game-agnostic home. Relocating them is unresolved.

### Red/blue binary assumptions are the recurring CTF→Paintbot porting hazard
Third instance now: the viewer defaulted ground-truth colors to `slot % 2` (invisible
in 2-team CTF, wrong for four-color FFA); TODO carries the same bug in
`event_warehouse.py`, which labels green/yellow wins as red/blue. Status: this has
recurred across independent sessions and tools — a graduation candidate for
`best_practices.md` rather than a one-off note.

### Both labs share ONE `expand_replay_json` symlink, so build order decides ownership
Binaries are per-ref (`expand_replay_json-<sha>`), so alternating labs costs no
rebuild, but `link_stable()` repoints the shared stable symlink each time. A paintbot
bundle run after a CTF build silently uses the CTF binary. Status: `viewer_bundle.py`
accepts `--expand-replay`, and the paintbot wrapper now prints the exact per-ref path
to pass; prefer that over trusting the symlink.
