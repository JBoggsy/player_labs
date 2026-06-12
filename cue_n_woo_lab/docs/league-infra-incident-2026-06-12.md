# Cue N Woo league: qualifier episodes crashed game-side (2026-06-12) — diagnosed + hotfixed

**TL;DR.** Every hosted Cue N Woo episode failed at game-container startup with
`AccessDenied` reading the tournament signing key from S3, so every submission
(kyle_policy:v1, mentalist:v1) was disqualified ("did not qualify from Qualifiers")
without playing a turn. Root cause: the episode-runner's IAM role had no S3 permission
and the key bucket had no cross-account grant. We applied a two-sided hotfix from this
session (James's credentials) and resubmitted. **The durable fix belongs in metta
Terraform — see "Reconciliation owed" below.**

## Symptom

- Membership status: `disqualified/inactive`, notes `did not qualify from Qualifiers`.
- Qualifier episode (`/v2/episode-requests?round_id=…`): `status=failed`,
  `error="Game container exited with code 1"`, `failed_policy_index: null` (not a
  player failure). Affected: ereq_90ebf51d (kyle_policy, 19:45Z), ereq_17b47669
  (mentalist, 20:22Z).

## Root cause (from `GET /jobs/{job_id}/artifacts/logs` — game container traceback)

`v2/coworld/game.py:load_signing_key` reads
`s3://observatory-private/cue-n-woo/tournament_signing_key` (manifest env
`WORKER_SIGNING_KEY_URI`) because the league variant sets `require_signing: true`.
The episode pod runs as IRSA role
`arn:aws:iam::583928386201:role/episode-runner-bedrock` (tournament account), which —
per `metta/devops/tf/tournament/irsa.tf` — only had Bedrock permissions. The bucket
lives in the primary account (751442549699), so the read needs BOTH an identity-policy
allow on the role AND a bucket-policy grant. Neither existed → AccessDenied →
`RuntimeError: require_signing is set but WORKER_SIGNING_KEY_URI is unreadable` →
exit 1 → every entrant disqualified.

## Hotfix applied (2026-06-12 ~20:35Z, by the lab session under James's credentials)

1. **Bucket policy** (account 751442549699, `aws --profile softmax`): appended statement
   `AllowTournamentEpisodeRunnerCueNWooRead` to the `observatory-private` bucket policy —
   `s3:GetObject` on `arn:aws:s3:::observatory-private/cue-n-woo/*` for principal
   `arn:aws:iam::583928386201:role/episode-runner-bedrock`. (Pattern mirrors the existing
   `AllowMettaverseTaskReadPolicies` statement. Pre-change backup:
   `/tmp/obs_private_policy_backup.json` that session; the bucket policy is hand-managed,
   not in metta TF, so no drift.)
2. **Role identity policy** (account 583928386201, reached via
   `softmax-org`-account PowerUser → `sts:AssumeRole` on `OrganizationAccountAccessRole`):
   added **inline** policy `cue-n-woo-signing-key-read-HOTFIX-20260612` to role
   `episode-runner-bedrock` — `s3:GetObject` on `arn:aws:s3:::observatory-private/cue-n-woo/*`.
   Inline (not an edit to the TF-managed `episode-runner-bedrock-access` policy) so the
   next `terraform apply` won't silently revert it.
   Verified: `iam simulate-principal-policy` → `allowed`.

## Reconciliation owed (the durable fix — metta repo)

`devops/tf/tournament/irsa.tf`, add to `aws_iam_policy.episode_runner_bedrock`'s
statement list (then delete the inline hotfix policy):

```hcl
{
  Effect   = "Allow"
  Action   = ["s3:GetObject"]
  Resource = ["arn:aws:s3:::observatory-private/cue-n-woo/*"]
}
```

Also worth upstreaming: manage the `observatory-private` bucket policy statement in TF,
and have the game fail with a *clearer* operator-facing error (it already names the URI;
the gap was that nothing surfaced it to submitters — both entrants just read
"did not qualify").

## Operational lessons

- "did not qualify" can mean *the game crashed*, not *your policy is bad*. Always pull
  the qualifier ereq and `GET /jobs/{job_id}/artifacts/logs` (serves game + worker
  container logs; the episode-artifacts skill doesn't fetch this route — worth adding).
- Hosted-vs-local config difference that bit here: local runs used
  `require_signing=false`; the league runs `true`. The signing path is exercised ONLY
  hosted, so Gate-1 can pass while every league episode crashes.
