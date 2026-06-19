---
name: cnw-league-iam-hotfix
description: "Cue N Woo league episodes crashed on S3 signing-key AccessDenied; 2026-06-12 IAM hotfix applied, metta TF reconciliation still owed"
metadata: 
  node_type: memory
  type: project
  originSessionId: 77e158b0-bd16-41f8-8473-d1b1522d451b
---

On 2026-06-12 every hosted Cue N Woo league episode crashed game-side: role
`episode-runner-bedrock` (tournament acct 583928386201) couldn't read
`s3://observatory-private/cue-n-woo/tournament_signing_key` (league sets
`require_signing: true`). Hotfixed from James's creds: bucket-policy statement
`AllowTournamentEpisodeRunnerCueNWooRead` on `observatory-private` (primary acct) +
inline role policy `cue-n-woo-signing-key-read-HOTFIX-20260612` (reached via org
mgmt acct PowerUser → `OrganizationAccountAccessRole`).

**Why:** without it no Cue N Woo submission can ever qualify — "did not qualify"
actually meant "game container crashed."

**How to apply:** the durable fix is still owed in metta
`devops/tf/tournament/irsa.tf` (add s3:GetObject on
`arn:aws:s3:::observatory-private/cue-n-woo/*` to
`aws_iam_policy.episode_runner_bedrock`, then delete the inline hotfix). Full
incident doc: `cue_n_woo_lab/docs/league-infra-incident-2026-06-12.md` in
player_labs (branch `worktree-cue-n-woo-lab`). Related: [[cue-n-woo-lab]].
Debugging trick: `GET /jobs/{job_id}/artifacts/logs` on the Observatory API serves
GAME-container logs (the episode-artifacts skill doesn't fetch it).
