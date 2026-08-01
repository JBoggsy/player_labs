# wowborg version log

## v60 - accelerated-wow 0.1.127 SDK rebuild (2026-07-31)

- Version UUID: `99a2c257-bbad-4bb2-9eb5-1eefa8920f06`
  (`wowborg:v60`, uploaded inert; not submitted to a league).
- Behavior is unchanged from v59 (`6df4d2d`). The `linux/amd64` image was rebuilt
  against accelerated-wow 0.1.127's exact game-image SDK
  (`sha256:7262b629ce02ac230ffa3a375c7e1ba8307293a5c94258b87412153cb5d9a5ba`)
  so its strict `AgentFrame` model accepts the release's added observation fields.
- Local image manifest:
  `sha256:25a675ecab81416f781679dd89f3cacf69a1f66df608a4c7ccaad1435c9b8a63`.
- Hosted movement-continuity retest:
  `xreq_d2255259-ee1b-4647-bc71-2ea93133ab54` on accelerated-wow 0.1.127 /
  `custom-fresh-start-10x`. It did not dispatch: 0.1.127 certification failed its
  smoke episode after 3,600 seconds, so the request remained pending without a
  job ID, replay, or results. Retest v60 against the corrected successor release.
- Full exact-image local `custom-fresh-start-10x` episode completed cleanly with
  score 1.0, 312 observations, 311 intents, a replay, and 1,391.080 yards of replay
  trajectory. Versus the hosted v59 baseline, movement packets fell 4,097 -> 1,376
  (-66.4%): forward starts 239 -> 22 (-90.8%), forward stops 243 -> 25 (-89.7%),
  heartbeats 2,907 -> 600 (-79.4%), turn starts 326 -> 347 (+6.4%), and turn stops
  356 -> 357 (+0.3%). The environment-owned forward continuation is therefore
  working locally; hosted confirmation still waits for a certifiable release.

## v59 - behavior-neutral `/player` progress observer (2026-07-30)

- Version UUID: `fc660a1d-2ec2-45d2-bf9a-e7725d8be246`
  (`wowborg:v59`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `6df4d2d`. `/env` remains the sole
  gameplay owner with its original policy budget. A read-only `/player` socket
  reports canonical level/XP/displacement samples and sends `done` at the
  owner-standard handoff deadline minus 35 seconds.
- Local image manifest:
  `sha256:7bb7e532a112c2cad42da37719ce9e2ef97df6564f6ef681ff85ade97f052349`.
- Hosted request:
  `xreq_50048077-8098-4ece-a725-460866e70ed4` on certified accelerated-wow
  0.1.124 / `custom-fresh-start-10x`.
- Verdict: 2/2 completed with score 1.0, retained replay, no retry or error.
  The observer emitted 248 / 247 progress reports, ended both sessions with
  `player_session_done`, and reported 1,314.4 / 1,309.9 yards. The replays
  contain 4,115 / 4,097 movement packets.
- Episodes: `ereq_292052b7-c092-404b-91de-c55d29b180dc`
  ([replay](https://softmax-public.s3.amazonaws.com/replays/249d8681-6c05-4fdb-ae14-ae6070d42506.replay))
  and `ereq_422085f1-9ec7-4554-b2ba-9942947e5dc2`
  ([replay](https://softmax-public.s3.amazonaws.com/replays/22800b03-b0b6-4e97-ae71-57a596a48680.replay)).
- Solo overworld replay intentionally has no Godview sidecar; the packaged
  viewer reconstructs movement from the selected POV's recorded client packets.

## v58 - exact policy-budget cap (superseded, 2026-07-30)

- Version UUID: `d21a35e7-f4e6-4247-a658-9df91c900c46`
  (`wowborg:v58`, uploaded inert; not submitted to a league).
- Built from source commit `2f9e751`, image manifest
  `sha256:948568fb2b063886a182d118826c98932cdc496c97497d3cf5a50c12036703b0`.
- Correctly measured the teardown margin from the `/player` handoff, but still
  capped the policy's own budget and therefore changed station selection. Its
  request `xreq_b56f2696-860e-4614-9057-140e55edf5f4` was cancelled before
  evaluation; v59 removes the behavioral confound.

## v57 - `/player` teardown margin (superseded, 2026-07-30)

- Version UUID: `1c645f35-0d52-4fdc-89d3-47f0f921b9d4`
  (`wowborg:v57`, uploaded inert; not submitted to a league).
- Built from source commit `3722172`, image manifest
  `sha256:6f5f99f21b3bd58196c83e6e92cee7a06bf970fb5a4daf7fa11da4c50b7f2dd7`.
- Request `xreq_cef1458f-ad8d-4b00-82d9-ed3debf65aa1` completed 2/2 with score
  1.0 and replay. One episode emitted 153 progress reports, reported 738.4
  yards, retained 2,451 movement packets, and sent clean `done`.
- Superseded because its policy-duration cap changed World Race's time-share
  calculation; v59 moves deadline ownership entirely into the observer.

## v56 - first `/player` progress observer (failed, 2026-07-30)

- Version UUID: `84b7a8c2-fe4e-4013-95a8-cc1375b4727b`
  (`wowborg:v56`, uploaded inert; not submitted to a league).
- Built from source commit `ad891af`, image manifest
  `sha256:db32ed339b6795c82ce666f7f3d3886a4bd6f8ee4b2b9b4b005c5170961ae438`.
- The observer connected and emitted real progress, but wowborg sent no `done`
  before the `/player` deadline. Both jobs failed as `session deadline reached`;
  retry request `xreq_573bf3a4-8983-41ba-a4b4-4eb6ea28d7a7` was cancelled.

## v55 - final 0.1.124 default-catalog artifact (2026-07-30)

- Version UUID: `94c46921-5c5d-4486-b780-1d1d31f43591`
  (`wowborg:v55`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from the same source commit `4d6b434` proven by v54, with
  the normal station catalog restored for future evaluation or submission review.
- Local image manifest:
  `sha256:22b7fe797abb62aecd709a3a076604436ab808c28af48b300fa7ff039953dd4e`.
- Evidence is compositional: v52 proved default-catalog known navigation, while
  v54 proved this exact final runtime code on the held-out course.

## v54 - held-out course with queued-error drain (2026-07-30)

- Version UUID: `d7ffc80c-8c73-468f-9a17-62f8f42d2f54`
  (`wowborg:v54`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `4d6b434`; the runtime drains consecutive
  typed request errors before accepting the host's newer pushed frame.
- Local image manifest:
  `sha256:4a1247ae9ef4948092a6b169df16d02aea157b6b219105b022aab0f597276e1e`.
- Hosted held-out request:
  `xreq_c0d63be1-8ef3-4192-825a-380e84843f0c` on certified accelerated-wow
  0.1.124 / `custom-fresh-start-10x`.
- Verdict: held-out navigation confirmed in two independent episodes. Both
  completed with score 1.0 and replay, reached `novel-east-rise` in 332.9 /
  341.8 seconds, correctly classified `novel-high-air` as unreachable, and had
  five advancing frame refreshes.
- Episodes: `ereq_ae6a184a-741d-4125-ab8f-e681189f97d1`
  ([replay](https://softmax-public.s3.amazonaws.com/replays/01f12e1a-232f-4908-a12a-7bfcd598071b.replay))
  and `ereq_c47138c9-e9e3-42b7-b4fe-c30725ba21ca`
  ([replay](https://softmax-public.s3.amazonaws.com/replays/26c188cd-6d7b-4969-a579-4777e59e3b21.replay)).

## v53 - held-out course with transient retry (2026-07-30)

- Version UUID: `c210ad97-fc1b-486a-ba5a-6f1f7d4d0d3a`
  (`wowborg:v53`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `a2636f1` with the preregistered
  held-out Durotar course and v52's single transient no-progress retry.
- Local image manifest:
  `sha256:41102802debe3637f90c70137c9ad58da16536a2c209dbc96d47f2a1fbd12ef7`.
- Hosted request:
  `xreq_62bf9b89-e840-4637-a64a-29c55b143d23` on certified accelerated-wow
  0.1.124 / `custom-fresh-start-10x`.
- Verdict: operational failure. Both episodes exited when a second queued stale
  request error arrived while the runtime was waiting for the current frame.

## v52 - transient no-progress retry (2026-07-30)

- Version UUID: `9d876528-9dba-4945-9498-6bdff9a3625f`
  (`wowborg:v52`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `a2636f1`; World Race retries a station
  once when its first journey ends specifically as `no_progress`.
- Local image manifest:
  `sha256:80f2a8a759bfa5af04b4ad48a472a2edc64298e1ff644f0e1086e77a7664a8a4`.
- Hosted request:
  `xreq_62dd5b9b-3b83-4950-a9ec-a3ca902d179d` on certified accelerated-wow
  0.1.124 / `custom-fresh-start-10x`.
- Verdict: known challenge completion demonstrated. Both episodes completed with
  score 1.0 and replay; one reached `valley-gate` in 207.7 seconds. The other
  activated `nav_station_retry` on Sarkoth but did not finish before teardown.
- Episodes: `ereq_da240441-192c-4e29-9059-0683d8ca680b`
  ([replay](https://softmax-public.s3.amazonaws.com/replays/6f88d2db-2807-4e26-9551-b204642323d1.replay))
  and `ereq_07a29d3a-afe6-48a4-b605-854e4235f160`
  ([replay](https://softmax-public.s3.amazonaws.com/replays/5b0db2c0-6259-4303-a2b4-707d6a537eae.replay)).

## v51 - held-out course with current-socket refresh (2026-07-30)

- Version UUID: `221a8b82-09f7-4424-9316-caeb20282cbd`
  (`wowborg:v51`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `15e6a13` with the same untouched
  Durotar course prepared in v49 and v50's current-socket frame recovery.
- Local image manifest:
  `sha256:f3f1bc089da5d0175c67ce26ccf18ad0413aef7356a8a97e2a10648016587256`.
- Purpose: hosted held-out navigation evaluation after v50 clears the recovery
  mechanism gate.

## v50 - current-socket AgentFrame recovery (2026-07-30)

- Version UUID: `04a59594-63fa-477e-86d2-e897917e07ef`
  (`wowborg:v50`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `15e6a13`; after a stale/deadline
  rejection, the hosted runtime consumes the next pushed frame on the existing
  `/env` connection instead of resetting the Gym lifecycle.
- Local image manifest:
  `sha256:6060e515d0354b9621d24ad7cddadae9d9af6067a710fb31bb4d7ffa4c00ad73`.
- Hosted experiment:
  `xreq_92f74d1c-5a12-49a9-8579-36d435e3d6c2` on certified accelerated-wow
  0.1.124 / `custom-fresh-start-10x`.
- Verdict: frame recovery confirmed, station completion not yet confirmed. Both
  episodes completed with score 1.0 and replay; every refresh advanced, stale
  runs capped at one, and positions changed 264/337 times. Both first reachable
  stations exhausted their no-progress replans during the startup movement stall.

## v49 - held-out Durotar navigation course (2026-07-30)

- Version UUID: `821fe38c-ac0c-4852-ad77-493797f6ad40`
  (`wowborg:v49`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `34ba007` with a data-only course that
  had never appeared in wowborg code or documentation: east rise, north basin,
  canyon approach, and an intentionally unreachable high-air target.
- Local image manifest:
  `sha256:34288844bb4b36403e51e51d2ab9936c538781d18a67b6468e273127827fdecb`.
- Purpose: held-out hosted evaluation after frame-refresh is established
  independently. This build retains v48's unsuccessful reset-based recovery and
  is superseded before evaluation.

## v48 - stale AgentFrame recovery (2026-07-30)

- Version UUID: `5ef2cfc8-054f-4721-9cdd-503a16d78922`
  (`wowborg:v48`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `34ba007`; this candidate attempted to
  refresh a stale `AgentFrame` with `VanillaWowEnv.reset()`.
- Local image manifest:
  `sha256:4ddb52f05715c6da3d6268caffaef14f7c3c3c6aa25b85af919704fec645f3c7`.
- Hosted experiment:
  `xreq_2b5eabc9-9a92-4c0a-8055-63f1b77b4796` on certified accelerated-wow
  0.1.124 / `custom-fresh-start-10x`.
- Verdict: rejected. Both episodes ended as `player_error`; reset opened a new
  Gym lifecycle instead of reattaching to the retained session.

## v47 - accelerated-wow 0.1.124 compatibility baseline (2026-07-30)

- Version UUID: `57583ca8-476e-430a-ad3b-bc7c33ce40d0`
  (`wowborg:v47`, uploaded inert; not submitted to a league).
- Built `linux/amd64` from source commit `0a4bc2c` against the certified
  accelerated-wow 0.1.124 contract and deployed game image
  `sha256:ed11e79d...d173a`.
- Adopted the upstream `environment.runtime.episode` module and the consolidated
  `NavmeshRoute` shape. The route lab uses the same compatibility interpretation.
- Local image manifest:
  `sha256:fe23e6c526b05ea88ecae024622322f26bae7442281fdc0ffa54555e011af729`.
- Purpose: establish the first hosted `/env` navigation baseline after the
  game-side session startup fix; no navigation behavior change from v46.

## v46 - canonical `/env` migration (2026-07-29)

- Version UUID: `13b4b697-54d0-4cfe-941a-ed6a3e913211`
  (`wowborg:v46`, uploaded inert; not submitted to a league).
- Replaced every wowborg-owned client path and adapter with the owner-provided
  synchronous Gymnasium contract: `AgentFrame` observations and `AgentAction`
  submissions over hosted `WS /env`.
- Policy image: `linux/amd64`, local manifest
  `sha256:8c3ef0560ba95e024580b0cfe6b42696d006e5f053166d2f8b24f3edbe4cb406`;
  copies only `environment/` and `player/sdk/` from accelerated-wow 0.1.122
  (`sha256:608ac6685...e5e4`). The build rejects historical client binaries.
- Validation before upload: 62/62 wowborg tests; 13/13 declared real-navmesh
  stations; two untouched data-only sequential held-out courses passed 3/3 each:
  scorpid basin → Razor Hill vendor → Razor north field, and south-road west →
  lower canyon west → Barrens gate.
- Hosted runtime request:
  `xreq_52b27d01-17e1-4f5b-860f-cbd096e606bc`, canonical accelerated-wow
  0.1.122 / `custom-fresh-start-10x`.

## v5-v20 - waypoint races: iteration to consistency (2026-07-21/22)

- v3 (`b10f3bb0`): first 0.1.31 contract probe — seam works, no world data (all moves
  failed). v4 (`6242a51a`): VANILLA_WOW_ASSET_SERVICE_URL→--assets fix; random_walk
  102/135 legs, 1,510 yd (replay-confirmed).
- v5 (`purpose=v5-waypoint-race`) → v20 (`purpose=v20-south-rim`): the waypoint_race
  ladder. Key versions: v6 progress-based legs; v8 authored staging chains; v10
  socket-timeout resilience (reconnect + resumable loop); v13 staging hysteresis;
  v16 moving-legs-never-budget-out (zero false DNFs since); v17 course sizing
  (2 near+1 mid+1 far); v19 far-legs-DIRECT (staging retired for long hauls);
  v20 south-rim mid target.
- Endpoint (v19+v20, 8 episodes): 6/8 fully clean, ~1.9 yd/s overall, 740-yd far legs
  in 356-391 s, laps completing. Residual: rare coastal-rock wedge (~1/8); hard tier
  (east field / mesa / NW ridge) quarantined as the future-nav benchmark.


## v3 - nim_control migration (built + fake-server smoked, not yet uploaded)

- Migrated to the game's 0.1.31 policy seam: `action.json` no longer exists upstream;
  the bridge now drives `vanilla_wow.nim_control.v1` (binary-framed local TCP,
  port 41114+slot) — arm external selection via GoalRequest, read EnvironmentFrames
  (observation + dense bindings + factorized action masks), submit one mask-admitted
  FactorizedAction per offered frame, settle via typed ActionSettled. Recon:
  `docs/recon/player-contract-0131-2026-07-21.md`.
- Base image bumped to vanilla_wow 0.1.31 (digest in `tools/versions.env`); player
  images no longer bundle world data — the shim forwards the wrapper's `--assets=<url>`
  to king_richard; session budget derives from KING_NIMROD_SESSION_DEADLINE_SECONDS.
- random_walk is frame-driven now; mask-refused moves fall back to the frame's
  recommended action; death defers to recommended recovery instead of stopping.
- Evidence unchanged (trace/artifact/breadcrumbs); artifact bundle now also carries
  environment-frame.json + decision-audit/leveling-performance/decision-loop-profile
  when present. 0.1.31 caveat: /say text must be in the frame's admitted vocabulary.
- Validated: 57 unit tests (bridge tests run the real wow_sdk client from the pinned
  image's SDK snapshot against a scripted control server); image builds amd64;
  end-to-end container smoke (fake king_richard serving the control socket): goal
  armed, 5+ legs selected/settled, positions tracked, clean teardown.

## v2 - shim adoption: random-point navigator

- Version UUID: `eb6aa13e-4fcd-4037-a443-42fc7ae676d0` (uploaded 2026-07-15,
  `players-wowborg:dev` linux/amd64, tag `purpose=v2-shim-random-walk`).

- Architecture change: our policy now drives the game's bundled Nim client
  (`king_richard --scenario=nim-control`, autonomous planner off) through its file
  bridge, layered on the DEPLOYED reference player image (vanilla_wow 0.1.19 player
  image, pinned by digest in `tools/versions.env`). No Python WoW protocol code in the
  hosted path. Design: `docs/designs/wowborg-v2-shim-adoption.md`.
- New: `shim.py` (supervisor), `bridge.py` (typed seam), `types.py`,
  `policies/random_walk.py` (T0: random 10–20 yd legs with typed movement settlements).
- Observability, three redundant channels: `trace.py` (JSONL + `WOWBORG-TRACE` stdout of
  every observation/intent/typed outcome), `artifact.py` (session-end evidence zip PUT to
  `COWORLD_PLAYER_ARTIFACT_UPLOAD_URL`), and rate-limited `/say` breadcrumbs
  (`ShimBridge.say`) that land inside the CWREPLAY itself.
- Honors the duration budget (`WOWBORG_DURATION_SECONDS`, default 120 s) — the v1
  "never self-terminates" defect is gone by construction (the shim stops the Nim client
  and exits; the base wrapper sends `done`).
- Validated locally: 45 unit tests; image builds amd64; end-to-end container smoke with
  a scripted fake king_richard (12 s, 12 legs, all `reached_target`).
- v1 login-stack modules retained for debugging; no longer the image entrypoint.

## v1 - idle login skeleton

- Version UUID: `6d3b00e5-512b-4c62-95c5-2a83367867b7` (uploaded 2026-07-13, `players-wowborg:dev` linux/amd64).
- Pure Python WoW realmd/world login client.
- Enters the seeded `wow_session.character_name`.
- Idles with periodic `CMSG_PING`.
- Does not decode world state or take gameplay actions.
- Does NOT honor the session's `deadline_seconds` — never self-terminates, so hosted
  episodes always run to the full variant deadline (fix in v2).
- First hosted smoke 2026-07-14: `xreq_23feebad-…`, 4 episodes on `orc-fresh-start`
  (5× self-play), all completed, score 0.0, no crash. Policy logs not retained; login
  success not yet confirmed from artifacts.
