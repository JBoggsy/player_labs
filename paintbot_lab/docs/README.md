# Paintbot documentation

This is the index and source-of-truth map for `paintbot_lab`. Start with the
current references; use dated recon/reports as historical evidence, not as live
configuration.

## Start here

| document | audience | purpose | authority / freshness |
| --- | --- | --- | --- |
| [`../README.md`](../README.md) | everyone | lab orientation, layout, commands, viewer distinction | current orientation |
| [`../AGENTS.md`](../AGENTS.md) | coding agents and maintainers | operating loop, invariants, current player | current process contract |
| [`../WORKING_CONTEXT.md`](../WORKING_CONTEXT.md) | active collaborators | current objective, live IDs, open threads | intentionally volatile; refresh during work |
| [`paintbot-gameplay.md`](paintbot-gameplay.md) | player authors and analysts | rules, variants, campaign, wire contract | current reference; verify live-version callouts |
| [`stencil-communication.md`](stencil-communication.md) | player authors and analysts | Stencil shout formats, sender priority, focus claims, squad consensus, trust model, and known limits | current through v59; v59 adds identified spray-carrier reports |
| [`tournament-like-experience-requests.md`](tournament-like-experience-requests.md) | experiment authors | normative representative-evaluation contract | current and fail-closed |
| [`../best_practices.md`](../best_practices.md) | experiment authors | durable Paintbot-specific lessons | current defaults |
| [`../user_preferences.md`](../user_preferences.md) | agents | James's durable Paintbot preferences | current user contract |

The root [`../../AGENTS.md`](../../AGENTS.md),
[`../../best_practices.md`](../../best_practices.md), and
[`../../user_preferences.md`](../../user_preferences.md) also apply.

## Player and architecture

| document | purpose | status |
| --- | --- | --- |
| [`designs/stencil-v1-design.md`](designs/stencil-v1-design.md) | Stencil architecture, online `WorldMap`, port/scrap decisions, risks | living design with post-v1 addenda |
| [`designs/stencil-nim-port.md`](designs/stencil-nim-port.md) | native-port contract, parity corpus, packaging | completed design + maintained status |
| [`designs/rl-policy.md`](designs/rl-policy.md) | Qwen policy decisions, cross-era data/training pipeline, observation representation | living design; full replay-to-checkpoint pipeline implemented |
| [`designs/spray-avoidance-v59-design.md`](designs/spray-avoidance-v59-design.md) | v59: enemy loadout belief (weapon/grenade/barrier/shield), spray-can keep-out with ally-coverage-aware flee, spray shout, spray-carrier target priority | implemented and uploaded as v59 (2026-08-08, inert); revisions 2-3 record what two adversarial review rounds corrected |
| [`../paintbot/stencil_nim/VERSION_LOG.md`](../paintbot/stencil_nim/VERSION_LOG.md) | immutable upload/version provenance | append-only; newest version first |
| [`../../player-build.md`](../../player-build.md) | game-agnostic hosted-player image contract | root reference |

The exact configuration API is the implementation in
[`config.nim`](../paintbot/stencil_nim/config.nim); prose should not duplicate
its full list.

## Evaluation and replay operations

- Representative hosted games: follow
  [`tournament-like-experience-requests.md`](tournament-like-experience-requests.md),
  then use the root `coworld-experience-requests` and
  `coworld-episode-artifacts` skills.
- Agent belief replay overlay: build the reader with
  [`../tools/build_expand_replay.sh`](../tools/build_expand_replay.sh) (defaults to
  `versions.env`'s `PAINTBOT_GAME_REF`), then bundle a fetched episode with the
  [`viewer bundler`](../tools/viewer_bundle.py) and load it in the
  [`belief viewer`](../tools/viewer.html). These moved here from ctf_lab when that
  lab was archived; commands are in [`../README.md`](../README.md). The
  version-matched replay reader supplies the episode's startup walkability mask,
  including generated Paintbot terrain. Stencil snapshots supply full enemy/teammate tracks, item
  beliefs, danger, and potential ally gun coverage clipped by terrain.
  The viewer also reports coverage/danger summary values and uses the episode's
  slot-team configuration for correct two-team and FFA ground-truth colors.
  This is the dynamic replay diagnosis tool.
- Navigation knowledge: use `../tools/render_nav.py` on a Stencil trace or
  artifact ZIP. This is a static map/flow/post viewer, not the belief replay.
- Local `../tools/self_play.py` runs are debugging only. They never replace the
  hosted verdict with the campaign's exact cell, battle kind, and roster.

Runnable examples and prerequisites are in [`../README.md`](../README.md).

## Campaign operations

The standing-order automation is implemented by
[`campaign_order_controller.py`](../tools/campaign_order_controller.py). Its
macOS LaunchAgent installation, monitoring, restart, and removal runbook is
[`infra/campaign_order_controller/README.md`](../infra/campaign_order_controller/README.md).

## Historical evidence

These documents are intentionally dated. Their measurements and IDs remain
useful, but any claim about “current,” “deployed,” variants, maps, seating, or
champions applies only to the document's cutoff.

| document | cutoff / role |
| --- | --- |
| [`recon/paintbot-2026-08-03.md`](recon/paintbot-2026-08-03.md) | founding 0.7.178 recon and source citations; explicitly superseded for live behavior |
| [`recon/paintbot-gv41-hazards-2026-08-07.md`](recon/paintbot-gv41-hazards-2026-08-07.md) | 0.7.209–0.7.211 changes: the GV41 endgame grenade barrage and paint puddles, plus a prioritized Stencil handoff; v58 implements the barrage half. Scoped to that era; the lab has since re-pinned to 0.7.215 (still GV41), which adds config-gated perks and barriers — see [`paintbot-gameplay.md`](paintbot-gameplay.md) |
| [`reports/nav-init-profile-2026-08-03.md`](reports/nav-init-profile-2026-08-03.md) | navigation startup profile |
| [`reports/stencil-navigation-deep-dive-2026-08-08.md`](reports/stencil-navigation-deep-dive-2026-08-08.md) | full navigation recon for the simplification refactor: predicate hierarchy answer, the seven reason-string lists, severity-graded debt, engine ground truth |
| [`reports/stencil-defensive-mechanics-2026-08-04.md`](reports/stencil-defensive-mechanics-2026-08-04.md) | v7-v21 defensive experiments |
| [`reports/stencil-aim-accuracy-2026-08-04.md`](reports/stencil-aim-accuracy-2026-08-04.md) | v21-v22 exact-aim A/B |
| [`reports/stencil-v54-gv40-aim-validation-2026-08-06.md`](reports/stencil-v54-gv40-aim-validation-2026-08-06.md) | v54 GV40 controller validation against v52 in both live campaign captain seatings |
| [`reports/stencil-v54-top-champions-r383-2026-08-06.md`](reports/stencil-v54-top-champions-r383-2026-08-06.md) | v54 tournament-like field test: six episodes each on current `1v1`, `2v2`, and `4ffa` cells against the round-383 territory leaders |
| [`reports/stencil-v54-large-field-r385-2026-08-06.md`](reports/stencil-v54-large-field-r385-2026-08-06.md) | v54 60-episode campaign-shaped test across all current champions: 49-3-8, with paired two-team seats and balanced FFA colors |
| [`reports/rl-observation-length-experiment.html`](reports/rl-observation-length-experiment.html) | cross-era Qwen token-length experiment: all-label grammar refuted; human-only fog isolated as the dominant cause |
| [`reports/rl-bot-semantic-length-experiment.html`](reports/rl-bot-semantic-length-experiment.html) | paired follow-up: source-derived human-visual denylist confirmed at p99 3,178 / max 4,424 tokens |
| [`reports/rl-observation-length-corpus.json`](reports/rl-observation-length-corpus.json) | exact GameVersions, Coworld IDs, source commits, policies, and episode IDs used by the length experiment |
| [`reports/rl-mettabox1-sft-2026-08-07.md`](reports/rl-mettabox1-sft-2026-08-07.md) | CUDA/BF16 canaries, LR/epoch sweep, full cross-era checkpoint, and persistence-baseline verdict |
| [`reports/rl-action-change-weighting-2026-08-07.md`](reports/rl-action-change-weighting-2026-08-07.md) | matched 1×/3×/class-balanced/16× changed-component loss sweep and held-out-era verdict |
| [`reports/rl-transition-temporal-2x2-2026-08-07.md`](reports/rl-transition-temporal-2x2-2026-08-07.md) | matched transition-sampling x four-tick-history ablation and selected-model GV40 result |
| [`reports/stencil-squad-consensus-retrospective-2026-08-06.md`](reports/stencil-squad-consensus-retrospective-2026-08-06.md) | v49-v53 leaderless-squad experiment retrospective and next-session handoff — **read this first**; it synthesizes the per-version artifacts below |
| `reports/stencil-v49…v53-*-experiment.{html,json}` | the underlying per-version squad-consensus and rejoin experiment renders + their exact request/result fixtures (v49 squad, v50 squad + live, v51 live, v52 timeout-rejoin, v53 refresh-rejoin) |
| [`reports/stencil-v55-early-defense-r399-2026-08-06.md`](reports/stencil-v55-early-defense-r399-2026-08-06.md) | v55 spawn-box opening / early-defense round-399 field test |
| [`reports/rl-initial-sft-2026-08-06.md`](reports/rl-initial-sft-2026-08-06.md) | first Mac SFT plumbing pass: 125 balanced samples, holdout barely above the majority baseline |
| [`reports/rl-action-alignment-investigation-2026-08-06.md`](reports/rl-action-alignment-investigation-2026-08-06.md) | zero-tick vs neighboring-tick action-alignment investigation that settled the corpus offset |
| [`reports/stencil-v7-top-field-4ffa-16seat-request.json`](reports/stencil-v7-top-field-4ffa-16seat-request.json) | immutable historical request fixture |
| [`reports/stencil-v9-top-field-4ffa-16seat-request.json`](reports/stencil-v9-top-field-4ffa-16seat-request.json) | immutable historical request fixture |

Session candidate lessons live in [`../TENTATIVE_LESSONS.md`](../TENTATIVE_LESSONS.md);
rotated raw records live in [`../lessons_archive/`](../lessons_archive/). Neither
is authoritative until a lesson graduates to `best_practices.md`.

## Documentation maintenance

When live state changes:

1. Update `WORKING_CONTEXT.md` for active objectives and IDs.
2. Update the small status block in `README.md`/`AGENTS.md` only when it helps
   orientation; label it with a verification date.
3. Update `paintbot-gameplay.md` when the deployed contract changes.
4. Update `tournament-like-experience-requests.md` when scheduler, seating, or
   campaign-map construction changes.
5. Preserve dated reports and recon as history; add a supersession banner
   rather than rewriting their evidence.
6. Append uploads/submissions to `VERSION_LOG.md`.

Dated audit records live in [`audits/`](audits/): the documentation audit
([`2026-08-05`](audits/2026-08-05-documentation-audit.md)) and the game-contract
audit ([`2026-08-06`](audits/2026-08-06-game-contract-audit.md)).
