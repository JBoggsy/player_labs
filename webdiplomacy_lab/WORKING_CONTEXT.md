# webdiplomacy_lab working context

Resolve live state (league settings, champion, policy versions) through the platform
before acting; this file holds only the active objective and next decision.

## Objective

Build a genuinely strong Diplomacy policy for the `webdiplomacy` league
(`classic-gunboat`). Step 1 was done on 2026-10-06: a quick random baseline, then a
DumbBot port as the first acceptable bot. **Next: design the proper bot (direction
chosen by James).**

## Active artifacts

- Baseline: `webdiplomacy-random:v1` (bundled random bot, James Botts, current league
  champion). Hosted: `experiments/baseline-random-v1/`.
- Candidate: `webdip-dumbbot:v1` (policy version `aabe87ad-9bdd-4ddc-bcef-8fd090bfc634`,
  James Botts). Hosted against six random fillers (`experiments/dumbbot-v1-vs-random/`,
  28 episodes, 23 with results; the 5 gaps completed but their downloads were rate-limited):
  mean score 0.91 vs field par 0.02, solo 18/23, 0 rejected orders, max 17 ms per
  decision. The 5 non-solos were England (3) and Turkey (2), corner powers that stalled
  at 10–14 centres; the bot issues no convoys. **Not submitted.** League submission needs
  James's go-ahead.

## Constraints and open questions

- The hosted field today is only the random filler (we are the league's only
  entrant), so hosted runs cannot tell strong bots apart. Screening between strong
  candidates needs a local field of DumbBot opponents.
- The player image's base is the published 0.7.7 player image, pinned by digest. A
  game release must be re-checked (`uv run coworld list`).
- AGPL: the coworld is AGPL-3.0. Whether uploading our image counts as distribution
  under the platform's terms is unresolved; assume our player source must be
  AGPL-compatible.
