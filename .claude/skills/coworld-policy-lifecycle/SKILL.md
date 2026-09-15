---
name: coworld-policy-lifecycle
description: "Submit an already-uploaded policy version to a Coworld league with explicit authorization, then monitor placement, qualification and champion state."
---

# Coworld policy lifecycle

Use this skill for a specific uploaded version and league. The [build/upload skill](../build-and-upload/SKILL.md) creates the artifact; submission is a separate live action.

## Authorization and evidence

Submit only within explicit human authorization for the intended campaign/version/league and after the agreed evaluation supports it. Existing explicit authorization satisfies this gate. Otherwise present the concrete version, evidence and target for approval. Upload success alone is not evidence of gameplay improvement.

Announce the version and target, then follow the [current CLI/API reference](references/cli.md). Membership retirement is possible, but does not erase public results or prior effects; submission is consequential rather than literally irreversible.

## Submit

Read the league's live participation guide and resolve its current identity. Use an explicit version:

```bash
uv run coworld submit POLICY:vN --league league_... --no-open-browser
```

Select `--player`, `--auto-champion`, or repeatable `--preference` only as appropriate to the authorized intent. The CLI supports these fields; it does not support client-selected divisions. Do not retire an incumbent merely to work around a rejection without authorization for that change.

## Monitor

```bash
S=.claude/skills/coworld-policy-lifecycle/scripts/policy_lifecycle.py
uv run python "$S" monitor --name POLICY --watch
```

Run the watcher in the background when useful. It lists memberships by policy name; verify the **exact submitted version, league and membership** before declaring the requested action complete. Follow cursor headers when listing memberships/submissions. Keep disqualified rows visible by omitting `active_only`.

Read submission status/notes, membership status/substatus, membership-event reasons, and `is_champion` separately. Qualification rules and timing are league-specific; some leagues use platform qualification instead of a container commissioner. A failure score, failed round or timeout does not by itself establish disqualification or its cause. Pull the matching [episode evidence](../coworld-episode-artifacts/SKILL.md).

Use the exact submission/membership IDs, policy UUID and league/division when reporting the action's current outcome. Use normal participant access. Missing private data remains a coverage limitation.
