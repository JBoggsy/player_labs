# stencil-ant version log

## v7 — 2026-08-21

- Policy version ID: `f59f2ed7-069e-43b0-a560-4c2078d94566`
- Image: `players-stencil-ant:gv57-load-aware-food`
- Game contract: Emerg-ant 0.9.1 / GameVersion 57
- Runtime: `/bin/baseline`
- Change: retain exact v6 defense and carrier behavior, but score each visible food
  patch by travel distance plus a short-range crowd penalty from recently observed
  teammates. The selected patch changes only when local colony load outweighs the
  extra travel cost; `forage_crowd_redirect` records activation.
- Local ordinary-play evidence: nominally 9–7 against exact v6 over 16 matched games,
  with a 237–220 aggregate delivery lead. However, `forage_crowd_redirect` appeared
  in zero sampled policy frames or objective transitions across both independent
  windows, so these games prove that the mechanism never changed a decision.
- Local defense evidence: 5–1 against the all-in queen-rush probe across both colors.
- Hosted evidence: paid request `xreq_29758e26-3c0f-4540-b903-5f6db6126d69`
  split 2–2 against the current #1 real opponent `emergant-colony:v1`, sweeping red
  2–0 and losing blue 0–2. V7 led aggregate deliveries 60–48 and kills 7–1; its
  losses were forage finishes at 13–16 and 15–16, not queen collapses. The crowd
  objective again appeared in zero sampled frames or transitions across all 64 v7
  artifacts. Cost: $0.064884.
- Verdict: rejected as an unvalidated/inert mechanism; source restored to exact v6.
- League submission: none.

## v6 — 2026-08-21

- Policy version ID: `3da684b3-c68a-46c7-9d3a-c25d36a60afe`
- Game contract: Emerg-ant 0.9.1 / GameVersion 57
- Runtime: `/bin/baseline`
- Change: move v5's active queen-defense post 10 px farther outward, from 58 to
  68 px, without changing alarm conditions, responder bounds, or ordinary forage
  behavior.
- Local defense evidence: 5–1 against the all-in queen-rush probe across both
  colors; the blue seat swept 3–0.
- Hosted evidence: request `xreq_71a6d38c-9128-467c-a844-543802e67ce8` beat the
  current #1 real opponent `emergant-colony:v1` 3–1 across four episodes, with two
  per color. V6 swept blue 2–0, split red 1–1, led aggregate deliveries 62–47,
  and led kills 8–4. Its only loss was a 14–16 forage finish while leading kills
  2–0, not a queen collapse. Cost: $0.062538.
- Hosted refresh: request `xreq_fbf33a18-1731-4b6f-b00d-bfaa8f83f7ab` swept the
  same immutable real opponent 4–0 across two episodes per color, with a 64–34
  delivery edge and 7–1 kill edge. All episodes completed under James Botts for
  $0.112925 total; the request contained no self-play.
- Same-window control: request `xreq_f4b199f9-a3fb-44f9-ab98-c9ec806387a7`
  tested exact v5 against the same opponent and roster shape. V5 split 2–2,
  trailed v6's delivery margin (60–55 versus 62–47), and cost $0.065360. This is
  a favorable small-sample promotion signal, not statistical proof that 68 px is
  intrinsically optimal.
- League submission: none.

## v5 — 2026-08-21

- Policy version ID: `5e179085-7c8d-4b3d-b0c4-8f0272beb219`
- Game contract: Emerg-ant 0.9.1 / GameVersion 57
- Runtime: `/bin/baseline`
- Change: retain v4's guard and seven-starting-worker response, but launch the alarm
  only from direct damage or close queen contact (25 px at the queen, 35 px for the
  guard's queen-relative threat check).
- Local defense evidence: 5–1 against the all-in queen-rush probe across both colors.
- Local ordinary-play evidence: 4–4 against v4 with 123–116 aggregate deliveries.
- Rejected alternatives: hostile-danger pheromone gating defended 5–1 but cross-
  triggered between colonies and trailed v4 115–120; an 18 px contact fallback reacted
  too late and defended only 2–4; lowering only the guard fallback from 35 to 30 px
  also fell to 2–4, exposing a sharp response-latency threshold. Letting the guard
  forage food within 100 px of the queen split ordinary play against v5 4–4 with a
  negligible 118–117 delivery edge, produced zero guard deliveries, and weakened the
  rush result from 5–1 to 4–2. Latching carried-food state with nearest-teammate
  ownership improved ordinary play to 5–3 and 122–115, but weakened rush defense to
  3–3; making latched carriers intercept alarm threats collapsed further to 1–5.
  Even a six-tick ownership-aware grace defended only 3–3, and smoothing only the
  route while retaining raw alarm eligibility collapsed to 1–5. None of these
  candidates was uploaded. A single late-brood queen raider initially went 5–3 and
  118–115, but fresh seeds reversed it to 2–6 and 109–118 (combined 7–9), so it too
  was rejected without upload. Removing carrier food-trail switching cut locomotion-
  pausing pheromone commands by roughly 94% and led v5 234–221 deliveries across two
  seed windows (9–7), but weakened queen-rush defense from 5–1 to 3–3. Retaining the
  food kind at steady rate also defended only 3–3. Restoring urgent rate inside the
  220 px nest perimeter recovered defense to 4–2 but lost ordinary play 2–6 and
  115–121. The whole pheromone-rate family was rejected without upload.
  Expanding the proven two carrier lanes to four (`-54/-18/+18/+54`) also lost
  3–5 and trailed 110–122 deliveries; narrowing the original pair from `+/-36`
  to `+/-24` likewise lost 3–5 and trailed 115–122. Both were rejected without
  upload.
  Trace mining found 1,047 target changes during continuous forage, but committing
  to a still-live patch lost 3–5 and trailed 107–118 deliveries. Allowing a switch
  only when it saved more than 50 px split 4–4 and still trailed 114–117. Food-
  target commitment was therefore rejected without upload.
  Letting every hatched worker answer v5's precise alarm matched v5's 5–1 rush
  defense but lost ordinary play 2–6 and trailed 116–124 deliveries. Brood
  activated in four of eight ordinary games, including all eight reserves in
  three, so the seven-founder cap remained and the candidate was not uploaded.
- Hosted evidence: request `xreq_5e43440e-ffd2-4e9a-b7db-aa2e40fa001d` swept the
  current champion `emergant-colony:v1` 2–0. Stencil won red 16–9 with no combat and
  blue 16–8 with two guard kills and all seven starting workers answering the alarm.
  Both episodes completed; actual cost was $0.017896.
- League submission: none.

## v4 — 2026-08-21

- Policy version ID: `0862a354-7e1e-461f-92aa-0bcc1dd96560`
- Game contract: Emerg-ant 0.9.1 / GameVersion 57
- Runtime: `/bin/baseline`
- Change: one permanent queen guard plus a danger-pheromone alarm for the seven
  starting workers; reserve brood never answer the alarm.
- Local defense evidence: 3–3 against an all-in queen-rush probe across both colors;
  v3 lost its four matched control episodes.
- Local ordinary-play evidence: 4–4 against v3 with 117–113 aggregate deliveries.
- Rejected alternatives: one defender lost 0–4 to the rush; four and six initial
  responders each went 2–4; an unbounded alarm won 5–1 but lost ordinary play 2–6
  and trailed deliveries 113–124 after recruiting brood on incidental alarms.
- Hosted evidence: none yet. Paid XP is reserved for real opponents, never self-play.
- League submission: none.

## v3 — 2026-08-21

- Policy version ID: `954d33ec-0644-4426-b4cd-b4384381fe9a`
- Game contract: Emerg-ant 0.9.1 / GameVersion 57
- Runtime: `/bin/baseline`
- Change: exact canonical GV57 baseline plus per-frame telemetry and two offset
  carrier delivery lanes.
- Local evidence: 11–5 across eight seeds in both orientations; 237 deliveries
  versus 216 for the exact canonical baseline.
- Hosted evidence: request `xreq_e5826219-351f-4b32-84da-07bab81ef8bd` against
  `emergant-colony:v1` completed 1–1. Stencil won red by 16–13 deliveries and lost
  blue by queen death at 1–3. Total request cost: $0.02558.
- League submission: none.

## v1–v2 — archived

These versions targeted the retired GameVersion 52 cache-race contract and must not
be used with GameVersion 57. v2 is `6d7c656f-8431-49ae-9925-e4ee3c2ea0a7`.
