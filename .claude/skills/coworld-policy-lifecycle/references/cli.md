# Submit and monitor reference

## Submit

```bash
uv run coworld submit POLICY:vN --league league_... --no-open-browser \
  --player ply_... --auto-champion always
```

`--player` is optional: it must match an active player session, or be owned by the user credential. Repeatable `--preference KEY=VALUE` passes league-defined preferences, parsing JSON values. `--auto-champion` defaults to `always`; `never` disables automatic promotion, and `lineage` requires a prior lower version of the same policy under that player. An older upload does not automatically replace a newer champion under `always`.

The CLI calls `POST /v2/league-submissions` with `league_id`, `policy_version_id`, and applicable player/promotion/preferences fields. `notes` is an API field, not a current CLI option. There is no division option: placement is server-side. An already-active version cannot be submitted again. A bare policy name resolves to a mutable latest version; use `NAME:vN`.

## Qualification is league-specific

Read `/v2/participate?league_id=…`, league configuration and resulting membership. Placement may use a staging division or a competition division. Container commissioners and configured platform ladders can hold a membership as `qualifying`; a league without a qualification gate can enter `competing` directly. Platform qualification uses its own workflow and can create its own qualification XP. Do not prescribe one timing, game count, self-play rule or score threshold across leagues.

Submission statuses: `pending`, `processing`, `placed`, `rejected`, `withdrawn`.
Membership statuses: `submitted`, `qualifying`, `competing`, `disqualified`.
Champion is a separate boolean. Inspect membership-event reasons and episode failures, not an assumed cause such as LLM latency. Active-player limits can depend on user overrides and league settings; do not hardcode two.

## Read routes

| Question | Route |
| --- | --- |
| Placement | `/v2/league-submissions?policy_version_id=UUID` |
| Membership/verdict | `/v2/league-policy-memberships?policy_version_id=UUID` |
| Transition evidence | `/v2/policy-membership-events?league_policy_membership_id=lpm_…` |
| Player standings | `/v2/divisions/{division_id}/leaderboard?include_recent_rounds=false` |

Membership/submission lists return **arrays with `X-Next-Cursor` headers**. Follow pagination. Do not use `active_only` when diagnosing disqualification: it can hide the row. Match the primary leaderboard by `player_id`; other leaderboard views also exist. Progress evidence is commissioner-dependent; missing `metadata.observed` is not zero progress.

CLI reads include `coworld submissions`, `memberships`, `results`, `leagues`, and `divisions`. Our monitor follows list pagination, but is a **policy-name membership view**, not an exact-version/exact-league completion gate; inspect the chosen membership UUID directly for final verification.

## Retirement and authorization

`coworld retire-membership lpm_… --reason "…"` calls the membership retirement route. Retirement changes participation; it does not erase previous results or history. Submission/retirement/champion changes require authorization for the intended live action. Existing explicit session authorization is sufficient; do not request the same approval twice.

Authentication failures require checking identity; forbidden access requires checking permissions. Login alone does not resolve every 403. Use normal non-elevated access.
