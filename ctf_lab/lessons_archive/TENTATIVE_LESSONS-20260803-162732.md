# CTF tentative lessons — session buffer

**Session started:** 2026-08-03 13:21. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`ctf_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (CTF-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### A stale plan_server from a deleted checkout can squat port 8792 and 404 everything

Evidence: launching the PoI/plan editors found port 8792 held by a `plan_server.py`
from the removed `personal_labs_ctf` checkout (running since 2026-07-29); its LAB
directory no longer existed so every editor URL returned 404. Fix was `lsof -p <pid>`
to check the cwd, kill, relaunch from `personal_labs_main`. When an editor 404s,
check WHICH checkout owns the port before debugging the pages.

### viewer.html, viewer_bundle.py, plan_render.py, plan_server.py, fight_ab_report.py, analyze_item_usage.py are absent from the ctf_lab README layout

Evidence: enumerating tools for a show-and-tell required reading source docstrings
because `README.md`'s layout block (lines 71–82) predates these six tools. Candidate
doc fix: extend the layout list (they are the most demo-able tools in the lab).

### viewer_bundle.py silently emits a 0-tick bundle when expand_replay_json is the wrong era

Evidence: bundling a fresh 0.7.144 episode with the GV27 reader produced a "valid"
106MB bundle showing "0 ticks · 8 traced bots" in the viewer — the reader's
"Replay game version does not match" error was swallowed (exit 0, empty stdout).
Candidate tool fix: viewer_bundle.py should fail loudly when the expansion yields
zero pos rows. Diagnosis shortcut: run `tools/bin/expand_replay_json <replay> 1`
directly and read stderr.

### League redeploys show up first as version drift; resolve the new ref from any fresh episode's coworld_id

Evidence: league moved 0.7.124 (GV27) -> 0.7.144 (GV31) by 2026-08-01. The fix
recipe worked exactly as documented in build_expand_replay.sh: grep a 40-hex sha
from `coworld show <cow_id> --json` — the one inside `source_url` (github tree URL)
is the game ref; the other two hex strings are manifest/viewer-bundle hashes.
Updated both era pins (build_expand_replay.sh, versions.env); flagged the GV27->GV31
arena/nav-bake re-verify as pending in versions.env.

### Policy artifact zips (belief traces) only come back for experience-request episodes

Evidence: `fetch_artifacts.py --policy beacon` returned league episodes with replays
but "no v2 route for league episodes" for artifacts; re-pulling via the newest CTF
`--xreq` gave replay + 8 trace zips per episode. For belief-viewer bundles, always
source from an xreq. (Documented in the skill; easy to forget when league episodes
are the newest.)

### A league redeploy window can DQ a healthy champion via lobby-join infra timeouts

Evidence: v67 (2651 Elo, 655 rounds) was disqualified 2026-08-03T03:51Z for "3
consecutive competitive failures" — every beacon failure in the round was
`player_error: never joined the lobby within 2880 lobby ticks`, and the same error hit
h050, reardenr, nancy, and co-gas in the same 03:43Z round that first ran the
redeployed 0.7.174. In completed episodes of that same round v67 went 5-1. Lesson:
after any league game redeploy, check membership status promptly; a DQ near a rollout
window is probably infra, and the recovery is a fresh submission (the Elo history is
lost with the membership).

### "3 consecutive competitive failures" is a division config knob, and evidence lives on the membership events

Evidence: `division.disqualify_after_consecutive_failures: 3` in the league settings;
the DQ event on `/v2/policy-membership-events` carries reason + the evidence
`ladder_round` id + final rating/rounds. `fetch_artifacts.py --round <round_id>` then
gets the failing episodes; `episode.json.error` has the per-episode cause (episode
requests have `failed_policy_index` to attribute blame).

### The auto-entered duplicate membership does NOT keep beacon in the ladder after a DQ

Evidence: lpm_32940dab (entrants_from_coworld auto-entry of the same v67) stayed
competing/active with the champion flag after lpm_e2f2be80 was DQ'd, but ladder rounds
schedule 5 other policies and its rounds stayed 0 — the champion flag alone does not
imply scheduling. Verify participation by grepping recent division episode-requests,
not by the membership flag.

### viewer.html now auto-loads a bundle via ?bundle=<same-origin path>

Evidence: added a `?bundle=` query-param fetch this session so the agent can hand
the human a fully-loaded viewer URL (plan_server serves tools/ + tools/bundles/).
Verified via Playwright: 1789 ticks, 8 traced bots rendered.
