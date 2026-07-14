# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-01 10:05. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`crewrift_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Crewrift-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### The multi-thousand-tick imposter freeze is a RECON stall, NOT a SEARCH bug (persists across v76–v79)
Evidence: v79 (search rework) warehouse — worst idle bout = crewborg sat at EXACTLY ONE pixel (375,429)
for 9,289 ticks, kill ready (kcd 0), crew in its room only 4.6% of ticks. Mechanism: selector
`_select_imposter` rule order = evade → (kill_ready & visible victim)→hunt → (ticks_until_ready≤100 &
most_recent_victim)→RECON → else search. When the kill is ALREADY ready (ticks_until=0 ≤100) but no
victim is currently visible, rule 3 picks RECON, which `navigate_to`s the most-recently-seen crewmate's
STALE last-known position — which crewborg already walked to (they left) — with NO reached/stale escape
in `recon.py`. So it navigates onto itself → frozen. The SEARCH rework can't touch it (search isn't
selected). FIX (v80 candidate): gate RECON to the strictly-pre-ready window (`0 < ticks_until_ready ≤
100`) so a ready-but-blind imposter goes to the never-idle SEARCH to actively find a victim; and/or give
recon a "reached stale target & not visible → fall through" escape. This is likely the highest-value
idle fix — bigger than the SEARCH rework for the freezes specifically.
