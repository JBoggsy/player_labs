---
name: paintbot-pw-scout
description: "Use when someone wants to know what the Paintbot PW league field or a specific opponent is doing: 'what are the leaders doing', 'scout the field', 'who beats whom', 'profile aaron's policy', 'decode their shouts', 'which league games should I watch'. Pulls recent PUBLIC league episodes (no credits), traces them hash-exactly, and writes a policy x policy matrix, per-opponent profiles, a shout-protocol decode and flagged episodes with reasons (pw_scout.py, pw_fights.py, pw_flags.py). Agent-drivable: `pw.py scout fetch|report ... --json`."
---

# Paintbot PW scout

Turn recent public league games into opponent intelligence: who beats whom, how each
policy opens, fights, captures and scores glory, what their shouts mean, and which games to
watch. It reads public data only: no credits, no auth, no writes. Tool reference:
[docs/tools/pw_scout.md](../../../docs/tools/pw_scout.md); fights:
[pw_fights.md](../../../docs/tools/pw_fights.md); flags:
[pw_flags.md](../../../docs/tools/pw_flags.md); metrics: [pw_metrics.md](../../../docs/tools/pw_metrics.md); index:
[docs/tools/README.md](../../../docs/tools/README.md).

## Procedure

Run from the repo root (`personal_labs_paintbot_pw/`).

1. **Build tools for the league's tag** if `doctor` says they are missing or the league moved.
   The tag lives in `paintbot_pw_lab/tools/release.env`:

   ```bash
   uv run python paintbot_pw_lab/tools/pw.py doctor --json                 # 0 ready; 1 release.env behind (code stale) or league check rate-limited; 3 missing (see next[])
   uv run python paintbot_pw_lab/tools/pw.py deployed-ref --write          # 0 = current; 1 = release.env moved: rebuild
   uv run python paintbot_pw_lab/tools/pw.py build                         # builds the tag in tools/release.env
   ```

   `uv run python paintbot_pw_lab/tools/pw.py release` prints that tag and which binaries exist.

2. **Fetch gently.** The first new episode is traced before the rest are pulled (the
   field-study guard). If the guard fails, stop and build the recording's tag.

   ```bash
   uv run python paintbot_pw_lab/tools/pw.py scout fetch --max-episodes 30 --max-rounds 6 --json
   # -> paintbot_pw_lab/episode_data/scout/<UTC date>/  (gitignored)
   ```

   One round is 12 episodes. Keep to ≤ 30 per run unless James asks for more. Requests go
   through `tools/pw_public.py` (a pause before each call, back-off on 429/5xx, a fixed retry
   limit), and episodes already on disk are skipped without a request, so a rerun only pulls
   what is new. On exit 1 with code `rate_limited` (HTTP 429 after the retries) or exit 3 (the
   public API is unreachable), stop and try later; do not loop.

3. **Report**:

   ```bash
   D=paintbot_pw_lab/episode_data/scout/<date>
   uv run python paintbot_pw_lab/tools/pw.py scout report $D --title "<what this batch is>" [--ours <our policy>] --json
   ```

   Read `SANITY` lines first. Each one is a tooling bug until disproved: flat 0%/100%
   everywhere, one side winning everything, all-zero shots or pickups, mixed rules
   versions. Any `FAILED [code]` episode is not evidence.

4. **Write the reasons (your job).** Open `$D/scout.interesting.json`. For each flagged
   episode, look at the numbers:
   - `uv run python paintbot_pw_lab/tools/pw.py metrics $D/r*_<ereq>* --json`
   - and, if useful, `pw.py fights … --list` or `pw.py flags …`.

   Then write one specific sentence per episode to `$D/reasons.json`:
   `{"<ereq id>": "…"}`. Name the policy and side, what happened, and the number that
   makes it stand out. Make each sentence distinct; never write "an interesting game".
   Then run again:

   ```bash
   uv run python paintbot_pw_lab/tools/pw.py scout report $D --reasons $D/reasons.json --title "…" --json
   ```

5. **Present.** Point the human at `$D/scout.md`. Relay the headline findings:
   - standings with Wilson intervals and n;
   - the matrix cells that matter for us;
   - each leader's opening, weapon mix and glory composition;
   - any decoded shout template, with its slot hints and how often enemies can hear it;
   - the flagged episodes with links.

   State n and that one round is one seed and one time window.

6. **Go deeper on one opponent** when asked:
   - fights: `pw.py fights $D --policy <name> --vis-every 12`;
   - what goes wrong for a policy: `pw.py flags $D --policy <name>` (its losses, worst Elo
     outcome first);
   - a specific moment: the `paintbot-pw-replay` skill.

## Pitfalls

- **Episode is the unit.** One team is one policy's 8 seats. The matrix and standings
  count episodes, never seats.
- **Small n.** A policy plays 3–4 games per round. A 3–0 record has a Wilson interval of
  44–100%. Do not call a ranking from one round; pull more rounds, or say it is
  descriptive.
- **Do not pool rules versions.** The report warns when coworld versions or tape rules
  are mixed. Split the directories and report each on its own.
- **Scout score columns are historical, not the current ladder metric.** The report currently
  emits legacy `elo_outcome` with denominator2000. The verified current OpenSkill soft outcome
  uses `clamp(0.5 + (our glory - their glory)/1200, 0, 1)` for margin_scale600. Recheck live
  settings and use `score_outcome` for current A/B decisions. A zero-score result does not
  identify a draw: use the authoritative outcome. Do not infer current performance from the
  scout report's historical Elo columns.
- **Ember frame.** Heart and pickup names are mirrored for Azure sides, so `h0` = own
  home. Quote positions from the legend line and do not mix them with raw engine indices.
  Shout slot hints use **raw** indices, because that is what the policy sends.
- **Slot hints are inferences** from sampled state (tolerance 100 units). Confirm a decode
  by reading a few examples against the replay before building on it. A shout also reveals
  the speaker's position to any cog within 1,280 units; the "enemy heard" share measures
  how often that happens.
- **Public rows have no `game_config.slots`**, so the team comes from seat parity (the
  engine's rule). `episodes.notes` says `team_from_parity`. That is expected, not an
  error.
- Never upload, submit, post, or request experiences from this skill. Scouting is
  read-only.

## Autonomous use

- **Preconditions:** `uv run python paintbot_pw_lab/tools/pw.py doctor --json` exits 0 (the guard trace needs the league's build).
- **Commands:** `uv run python paintbot_pw_lab/tools/pw.py scout fetch --max-episodes 30 --json` (the directory is `result.out`),
  then `uv run python paintbot_pw_lab/tools/pw.py scout report <dir> --json`; write `reasons.json` for `result.interesting_without_reason`
  and rerun the report with `--reasons`.
- **Reading the envelopes:** fetch → `result.out`, `result.saved`, `result.already_present`,
  `result.excluded`, `result.guard` (`ok`, `not_run (nothing new)`, or `failed`; a failed guard
  returns early with `saved`, `skipped` and `guard` only, and failure code `guard_<code>`). Report → `result.standings`,
  `result.sanity` (each line is a tooling bug until disproved), `outputs[]` (scout.md, scout.json,
  scout.interesting.json), `next[]` (the reasons step).
- **Exit codes:** 0 use it. 1 the guard trace failed (fetch: build the league's tag, then rerun),
  the public API rate-limited after retries (code `rate_limited`: try later), or some episodes
  did not verify (report: list them, use the rest). 2 bad arguments, more than 100 episodes, or
  an `--ours` policy not in the batch (`result.valid`). 3 the public API is unreachable or a
  build is missing: run `next[0]` or try later; never loop on it.
- **Human gates:** none for reading: public reads are anonymous and free (keep them small).
  Posting a finding to the forum or wiki is a public write and needs James's explicit go-ahead;
  gameplay findings stay in the lab (user_preferences).

## See also

- `paintbot-pw-replay`: unpack one episode, answer "what happened at tick X".
- `coworld-community`: what other teams say they are doing. Treat it as leads, then check
  them here.
- `crewrift_lab/.claude/skills/crewrift-survey`: the pattern this skill follows.
