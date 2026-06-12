# mentalist — version log

Each uploaded policy version → the change it carries (lab best practice; the
canonical id is the policy-version UUID from `policy_lifecycle.py versions`).

| Version | Change | Notes |
|---|---|---|
| v1 (`9fcac03b-a8b8-4195-8402-7c887a7574c0`) | Initial player: 3 fixed private questions → TF-IDF style classifier (61 styles × 2 draws library) → Bedrock Claude (`us.anthropic.claude-opus-4-8`) writes in-style proposals + blind answers; deterministic fallbacks on Bedrock failure/low clock. | Uploaded + submitted to the Cue N Woo league 2026-06-12 (`--run python --run=-m --run mentalist --use-bedrock`). First submission disqualified by a league-side IAM bug (see `../docs/league-infra-incident-2026-06-12.md`); resubmitted after the hotfix. |
