# Crewrift tentative lessons — session buffer

**Session started:** 2026-06-26 23:22. This is THIS SESSION's lesson buffer. Write candidate
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

### Crewborg's imposter kill→WIN gap is post-kill, not kill-rate; locate it by conditioning win on kill count
Evidence: sweep (`/tmp/sweep_wh`). Imposter win rate conditioned on the SAME kill count: crewborg @1 kill = 0.39, @2 = 0.63; notsus @1 = 1.00, @2 = 1.00; aaln @1 = 0.64, @2 = 0.78. Kills/game are comparable (~1.5), so the win is lost AFTER the kills. Always split imposter analysis by kill count to separate "gets kills" from "converts kills to wins".

### Crewborg often does NOT know its imposter teammate (RoleReveal capture is brittle) — two independent warehouse signals
Evidence: (1) crewborg/-base imposter CAST votes hit a teammate imposter 21–23% of the time; notsus/jordan-aaln/crewborg-mv = 0%. With `teammate_colors` populated there is NO code path to vote a teammate (suspicion `_recompute` skips teammates; bandwagon filters them), so 21–23% ⇒ `teammate_colors` empty in a meaningful fraction of games. (2) crewborg follows its own teammate 46% of follow-intervals / 77% of follow-ticks vs notsus 26%/42% — Search is designed to never follow the teammate, so the high rate ⇒ the teammate filter is frequently inert. Root cause: teammate identity is learned ONLY from the one-shot RoleReveal "IMPS" interstitial (types.py:718-720), which an initial-connect race (design §3.1) can miss entirely. Fix direction: a robust teammate-inference fallback (e.g. latch any color we WITNESS killing/venting — definitional imposter, already tracked by suspicion's witnessed set — into `teammate_colors`), and/or widen the reveal capture.

### Crewborg's imposter meeting play is far more passive than notsus
Evidence: crewborg skips 39% of imposter votes (notsus 5%); notsus casts a non-teammate vote ~95% of meetings (active crew-thinning + blending). crewborg's deterministic imposter meeting path (`modes/attend_meeting.py:_decide_imposter`) only acts on a real top_suspect or an existing heat pile, else skips, and has NO self-defense when crewborg itself is the accused. A meeting that ejects a crewmate is free parity progress.

### Parallel fan-out jobs CLOBBER each other via the shared `players-crewborg:dev` docker tag + shared `--name crewborg` uploads
Evidence: while uploading my candidate, `ps` showed THREE other agents (in sibling worktrees `direction3-emergency-meetings` and `personal_labs` root) concurrently running `build_player.sh crewborg` (→ same global tag `players-crewborg:dev`) and `coworld upload-policy ... --name crewborg`. The docker image tag is host-global (not per-worktree), so a sibling's build silently overwrites the bits your `upload-policy players-crewborg:dev` then pushes — and multiple `--name crewborg` uploads interleave version numbers you can't attribute. **Fix when fanning out:** build to a UNIQUE tag (`build_player.sh crewborg --tag players-crewborg:<slug>`) and upload under a UNIQUE policy name (`--name crewborg-<slug>`). Don't trust `players-crewborg:dev` or `crewborg:vN` to be yours in a parallel session.

### Parity-push A/B (batch 1, n=240/arm): mechanism fires, win +5.9pp but underpowered
Evidence: 6 pinned-champion 1v1 blocks (both imposters=subject, 6-of-each-champion crew, 20 eps), `crewborg-paritypush:v1` vs `crewborg-base`. From results.json `vote_players`/`vote_skip` on the subject imposter slots: **skip rate 25.9%→19.8%, player-votes/slot 0.92→1.03** — the candidate skips less and votes crew more, exactly the intended mechanism (toward notsus's active-vote profile). **Imposter win 48.3%→54.2% (+5.9pp), kills flat 1.48→1.40.** compare.py verdict: noise (p≈0.20) at n=240/arm — directionally right, underpowered. SE of a 2-prop diff at n≈236 ≈ 4.6pp, so +5.9pp ⇒ z≈1.28; need ~600/arm for z≈2. Ran batch-2 (60/champ/arm) to ~960/arm for power. NB the win effect is DILUTED across all games — the push only fires in games reaching a 3crew/2imp meeting with a known live teammate; conditional effect likely larger but needs trace to isolate (upload with CREWBORG_TRACE_GROUPS next time to log `meeting_decision` path=parity_push).

### Upload the A/B candidate with trace env if you want to confirm a meeting-path change FIRED
Evidence: uploaded `crewborg-paritypush` with the plain entrypoint (no `CREWBORG_TRACE_GROUPS`/`CREWBORG_METRICS`), so the per-agent logs carried only reconnect lines — no `meeting_decision`/`parity_push` traces to confirm the new path engaged. Had to infer the mechanism indirectly from results.json `vote_players`/`vote_skip`. For a behaviour-path A/B, bake the trace env on the candidate upload so the firing is directly observable in the artifact logs.

### The sweep ran the DETERMINISTIC meeting path (LLM off)
Evidence: `meeting_llm_decision`/`meeting_llm_fallback`/`meeting_decision` counts = 0 in `/tmp/sweep_wh` (those are policy-internal emit.event traces, NOT replay events — not captured by the warehouse extractor regardless). Meeting behavior measured in the sweep = the deterministic fallback, not the LLM path.
