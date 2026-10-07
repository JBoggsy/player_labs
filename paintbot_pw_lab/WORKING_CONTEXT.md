# Paintbot PW working context

Use the current user request to establish the objective. Resolve live league, policy and roster
state through the platform before acting; this file is not a substitute for a live query.

## Current state (2026-10-07)

The optimizer campaign of 2026-10-06/07 is **closed and stood down**. No hosted requests,
pollers or agents are running. Resuming needs fresh authorization from James.

- **Champion:** `jb-pw-opt:v29`, version `cf05fa48-71e3-408c-96cf-ed1ce74409ea`, build
  `e42b7834-1`, compiled from `strategy/STRATEGY.md`. Rank 1 in the paintbot-pw league at MMR
  64.0 (Richard 55.7, Beta/xolod 45.9) on 2026-10-07.
- **Player:** James Botts, `ply_53fb05a6-73d1-494d-ab6c-8d566660d7ce`. League
  `league_ae677105-0ab8-4561-81ec-c9cf6735821c`, division `div_63c08219-c269-4bc5-84ae-5ccfc55b0a90`.
- **Working source** is the last rejected experiment (refuse-and-counter, `593d9c1a`). Restore
  v29's source (`e42b7834`) before starting new work.
- **Uploaded but not submitted:** v30 (`1fe285df-1`) is v29 plus the exact-geometry map guard. The
  submitted v29 only checks heart count. The league plays one map, so the guard has no effect
  today; ship it with the next real improvement, or immediately if the map or variant changes.
- **Engine:** tools and native library pinned to `coworld-v0.3.124` (`7a29ed7a`), rules 49.

Supported findings, the champion lineage and refuted levers are in
[best_practices.md](best_practices.md); open ideas are in [TENTATIVE_LESSONS.md](TENTATIVE_LESSONS.md).
Campaign evidence (reports, verdicts, request manifests, results) is archived outside git at
`~/coding/personal_labs/paintbot_pw_archives/2026-10-07-optimizer-campaign.tar.zst`; hosted episode
artifacts remain under `episode_data/optimizer-*`.

## Next decision for James

1. Resume against Richard with a new structural idea from TENTATIVE_LESSONS, or hold v29 and watch.
2. If resuming: XP balance was 11,805 on 2026-10-07 (refill about 1,429/day at 00:00 UTC). Keep a
   10,000 floor and run one cohort at a time (about 400 Richard + 100 xolod games per arm).

## Loop charter

Not set. The 2026-10-06/07 campaign charter (orchestrator-delegated) ended with the stand-down;
a new campaign needs a new charter from James.

- objective:
- policy_file: `paintbot_pw_lab/strategy/STRATEGY.md` plus authored `strategy/skills/*/skill.bas`
- policy_name / player:
- baseline:
- opponents:
- allowed_changes:
- credit_budget:
- max_iterations:

## Open constraints

- Every build keeps the exact-geometry map guard.
- Local games establish runtime health, activation and mechanisms, never competitive superiority.
  No hosted self-play.
- Hosted pollers must exit on their own and poll no faster than every 2 minutes; the API budget,
  pending-request cap and XP credits are shared with every lab on the account.
- M3 communications remain inactive and unqualified on Bassy; see [comms.md](strategy/comms.md).
  Broader neural/oracle references keep `PW_DOCS_SHA=118e1619`.
