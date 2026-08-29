# CTF tentative lessons — session buffer

**Session started:** 2026-08-29 11:57. This is THIS SESSION's lesson buffer. Write candidate
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

### Version-verdict commits update WORKING_CONTEXT/VERSION_LOG but skip the README/AGENTS status blocks
Evidence: README/AGENTS said "v54 champion, verified 2026-08-07" while WORKING_CONTEXT/VERSION_LOG recorded v68 champion 2026-08-14 — five champion transitions never reached the orientation docs. The doc-maintenance rule ("update the status block only when it helps orientation") reads as optional and lost. Suggest: the submit/verdict step of coworld-policy-lifecycle should touch both status blocks.

### Machine-installed services embed absolute repo paths — a repo rename silently kills them
Evidence: renaming personal_labs_paintbot → personal_paintbot (~2026-08-26) broke the campaign-controller LaunchAgent (dead python path + dead WorkingDirectory); the surviving process logged FileNotFoundError every 5 min for 3 days with zero orders placed and nothing surfaced it. Suggest: after any repo move, re-run manage_campaign_order_launch_agent.py; consider a staleness alarm on events.jsonl.

### Re-validate documented CLI one-liners after a CLI version bump
Evidence: coworld 0.1.39 scopes `coworld list` to your own uploads, silently breaking AGENTS.md's prescribed staleness check (`coworld list | grep paintbot` now returns nothing, which reads as "no drift"). `coworld deploy-audit | grep paintbot` is the working replacement (and revealed canonical 0.7.242).

### League membership needs periodic live re-resolution — new leagues can adopt your champion with no local signal
Evidence: Elite Paintbot (league_15cf0b94, created 2026-08-19) lists stencil:v68 competing under lpm_243bbc99; nothing in the repo, WORKING_CONTEXT, or the controller state recorded it until today's audit ran `coworld memberships --mine`.

### The nav-rework kill list needs an honesty check at close-out — some kills only half-landed
Evidence: sketch §4 ordered "threat axis and everything keyed on it" removed; threatAxis/sweepTarget still drive idle aim sweep in action.nim (movement keying is gone). Appendix-B "dead code" distanceAt was instead revived by v62's defenseGate; insideBase/walkabilityDecodeMs linger uncalled. Now recorded in the sketch's close-out addendum; threat-axis removal is strategy-rework input.
