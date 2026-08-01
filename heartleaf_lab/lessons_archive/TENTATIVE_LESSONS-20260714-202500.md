# Heartleaf tentative lessons — session buffer

**Session started:** 2026-07-14 20:25. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`heartleaf_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Heartleaf-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### The heartleaf warehouse is HOSTED — a reporter run's "completed" status says nothing about data quality; read the manifest
Evidence: an episodes-subject run over a CTF xreq "completed" with 5 parts but the manifest
showed 10/10 episodes failed ("Replay magic does not match"), 0 events. Same shape would occur
on heartleaf version skew (trace_warning). Always check `episodes_ok/episodes_total` first.

### Episodes-subject (xreq) warehouse runs leave `policy_version` NULL; key on `policy_name`
Evidence: rrun_c3b887ef over xreq_faf3a2c2 (15 Heartleaf episodes) — player_stats had
policy_version NULL for all rows while policy_name ("Cady (Ivan)", "player_3 (Yura)") was
populated. Round-subject runs populate both.

### Reporter run listing endpoints cap at the latest 100 runs — older rounds need their rrun_ id saved
Evidence: GET /v2/reporters/{id}/runs returns 100 max (backend hardcodes limit(100)); at ~2
rounds/hour that is ~2 days of Heartleaf history. fetch --round in the new skill can only
resolve rounds still inside that window.

### Round-warehouse reporter v5 mis-attributes ALL per-policy data when any player crashes: replay slots are connection-order, participants[] is seat-order
Evidence: ereq_0598d340 — warehouse said cady v21 "left at tick 753, score 0" and credited its
48-pt dinner to co-gas-relhalpha. Ground truth (agent_5 log + results.json): v21 played all
23,760 ticks, hosted, scored 48. The four "leave ~tick 750" rows were the four crashed policies
(co-gas ×3 keepalive-timeout, daf ModuleNotFoundError) whose replay slots compacted. TRUE league
scores: v20 avg 0.0 (real regression!), v21 avg 17.5. Fix: reporter must key by replay
playerName→seat, not slot==position. Until then cross-check results.json before trusting the
warehouse per-policy.

### Cheap ground-truth harness: episode.json participants[] (position→policy) + results.json (names/scores by seat) beats any derived dataset
Evidence: two API artifacts resolved in minutes what the warehouse got wrong; the per-seat
"Cady (Nikita)" naming in results.json names[] makes seat identity unambiguous.
