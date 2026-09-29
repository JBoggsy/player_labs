# deployed_ref.py — is the lab on the league's build, and do the docs still hold?

Resolves the paintbot-pw commit the league runs and compares it with the lab's two pins in
[`tools/release.env`](../../tools/release.env) ([pw_release.md](pw_release.md)):

- **Tools** (`PW_RELEASE_TAG`/`PW_RELEASE_SHA`): the build every lab tool defaults to. `--write`
  moves them to the league's release; then rebuild.
- **Docs** (`PW_DOCS_SHA`): the commit where the `file.nim:NN` citations in `docs/mechanics.md`,
  `docs/policy-surface.md` and `docs/evidence-pipeline.md` are exact. It always prints the
  diffstat of the doc-source files between `PW_DOCS_SHA` and the deployed commit, so an agent
  can judge whether a claim needs re-verification. It never moves `PW_DOCS_SHA`; a person or
  agent does that after re-verifying the docs.

Run it at the start of any loop that uses lab tools or trusts a doc claim.

File: [`tools/deployed_ref.py`](../../tools/deployed_ref.py). Tests:
[`tools/tests/test_pw_release.py`](../../tools/tests/test_pw_release.py) (offline: exit codes,
`--write`, JSON envelope, numstat parsing).

## Commands

```bash
uv run python paintbot_pw_lab/tools/deployed_ref.py              # check; exit 0 current, 1 behind
uv run python paintbot_pw_lab/tools/deployed_ref.py --write      # move release.env if the league moved
uv run python paintbot_pw_lab/tools/deployed_ref.py --json       # one JSON object on stdout
uv run python paintbot_pw_lab/tools/deployed_ref.py --docs-sha 7b2b19f5   # diffstat from another basis
```

Flags: `--json`, `--write`, `--docs-sha SHA` (default `PW_DOCS_SHA`), `--clone PATH` (source
clone for the diffstat, default `~/coding/coworlds/paintbot-pw` or `$PW_CLONE`; only fetched,
its checkout never changes).

**Agent loop preflight:**

```bash
uv run python paintbot_pw_lab/tools/deployed_ref.py --write --json > /tmp/ref.json
# exit 0: tools current. exit 1 + result.written: release.env moved -> run every command in "next".
# exit 1 + failures[0].code == "rate_limited" (HTTP 429) or "api_unavailable" (5xx): nothing is
#   missing; wait a minute and rerun (next[0]). Do NOT run softmax login for this.
# exit 3: environment (login/network/clone) -> run next[0] (also named in failures[0].message).
```

## Exit codes

| Code | Meaning | What to do |
| --- | --- | --- |
| 0 | `release.env` matches the league's tag and commit | nothing; still read the DOCS line |
| 1 | release.env is behind the league, or `--write` just moved it, or the league's version has no release tag (`failures[].code = "untagged"`) | run `next`: `--write`, then `build_tools.sh`, `build_native.sh`, the test suite |
| 1 | the Observatory API answered HTTP 429 (`failures[].code = "rate_limited"`) or 5xx (`"api_unavailable"`): the check could not run, nothing is missing | wait, then rerun (`next[0]`); `pw.py doctor --offline` skips this check |
| 2 | usage error (bad flag, unreadable release.env) | fix the command |
| 3 | environment missing: no `softmax` login token or HTTP 401/403 (`uv run softmax login`), Observatory/GitHub unreachable, no source clone | run `next[0]` (also in the message) |

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py deployed-ref [--write] --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | `--write`, `--docs-sha SHA`, `--clone DIR` |
| Outputs | `tools/release.env` (only with `--write`, only its tag/sha lines) |
| `--json` result | see Output below: `leagues`, `tracked`, `release_env` before/after, `tools_current`, `written`, `rule_diffstat`, `docs_rule_files_changed`, `docs_to_reverify` |
| Exit codes | the table above (0 current; 1 behind, just written, untagged, or rate-limited / API down; 2 usage; 3 environment) |
| Idempotence / cache | `--write` on a current pin changes nothing. Each run makes 2 API reads per league plus one `git ls-remote`: run it once per loop, not in a tight loop |
| Typical next step | on exit 1: the commands in `next[]` (rebuild, then the tests); `pw.py doctor` runs this check for you |

## Output (2026-09-29, after `--write` moved the lab to 0.3.79)

```
paintbot-pw (teams)    coworld paintbot-pw cow_4335e79a-… version 0.3.79 -> coworld-v0.3.79 d0728ab1
Heartland (ffa_kin)    coworld heartland cow_a7182349-… version 0.1.10 -> heartland-v0.1.10 d0728ab1  (reference only; not what the lab pins track)
tools pinned at: coworld-v0.3.79 d0728ab1 (tools/release.env)
TOOLS: current for the deployed build
docs verified at: 570174a2; rule-bearing engine files 570174a2..d0728ab1:
  coworld/paintbot/runtime/host.py                     +1 -1
  coworld/paintbot/runtime/neural_package.py           +132 -23
  examples/paintbot/bots.nim                           +4 -4
  examples/paintbot/mechanics.nim                      +8 -0
  examples/paintbot/neural_host.nim                    +219 -11
  examples/paintbot/sim.nim                            +2 -2
DOCS: 6 rule-bearing file(s) changed since 570174a2. Read the diff and re-verify any affected claim ...
  git -C ~/coding/coworlds/paintbot-pw diff 570174a2 d0728ab1 -- <the files below>
```

`--json` prints one object: `ok` (tools current), `tool`, `release_tag` (the pin before this
run), `inputs`, `outputs` (`[release.env]` when written), `counts` (`processed` = leagues read),
`failures`, `next`, and `result`:

| `result` key | Meaning |
| --- | --- |
| `leagues` | per league: `label`, `league_id`, `tracked`, `coworld_id`, `coworld`, `version`, `tag`, `sha` |
| `tracked` | the paintbot-pw league's `tag`, `sha` |
| `release_env` | `before` / `after` this run (differ only after `--write`) |
| `tools_current`, `written` | booleans |
| `docs_sha`, `rule_files`, `rule_diffstat` | the diff basis, the files checked, `[{path, added, deleted}]` for changed files |
| `docs_rule_files_changed`, `docs_to_reverify` | count of changed files; the docs to check when non-zero |

## Files in the diffstat

`examples/paintbot/{sim,mechanics,bots,game,match_config}.nim`, `src/polyworld/basic.nim`,
`coworld/paintbot/coworld_manifest_template.json` (rules, host API, manifest), plus the files
`docs/policy-surface.md` names as its re-verify triggers: `examples/paintbot/oracle.nim`,
`examples/paintbot/neural_host.nim`, `coworld/paintbot/runtime/host.py`,
`coworld/paintbot/runtime/neural_package.py`. A non-zero count does not by itself mean a doc is
wrong: read the diff. At 0.3.79 the BASIC teams game is unchanged (bots/sim lines are
`-d:pwTraining` array widths; mechanics adds `controlHeartCount`), while the neural lane changed.

## How it resolves

league → `game.coworld_id` → that coworld's `name` and `version` (Observatory API, needs the
`softmax` login) → release tag → commit (`git ls-remote --tags` on `Metta-AI/paintbot-pw`,
annotated tags peeled). The manifest's `source_url` carries no commit, so the tag is the only
link. The coworld id changes with every release (0.3.78 was `cow_12867c2e-…`).

| Coworld name | Tag | Tracked by the pins? |
| --- | --- | --- |
| `paintbot-pw` | `coworld-v<version>` | yes |
| `heartland` (its own coworld since 2026-09-28) | `heartland-v<version>` | no, printed for reference |

An unknown coworld name is an `untagged` failure (exit 1); add it to `TAG_PREFIX`.

Cost: two API reads per league plus one `git ls-remote`, and a `git fetch` of the clone only
when a commit is missing. Do not loop it.

## Verified

- 2026-09-29: league on `coworld-v0.3.79` = `d0728ab1`; with release.env at 0.3.78, plain run
  exit 1 (BEHIND); `--write --json` exit 1 with `outputs: [release.env]`, `after` = 0.3.79;
  the next plain run exit 0. Heartland resolves to `heartland-v0.1.10` = `d0728ab1`.
