# Cue-n-Woo tentative lessons — session buffer

**Session started:** (seeded at lab setup; the SessionStart hook restamps this).
This is THIS SESSION's lesson buffer. Write candidate lessons here **as you go** —
eagerly and noisily; most will be noise and that's fine. At the next session start,
a hook archives this file automatically to [`lessons_archive/`](lessons_archive/)
and creates a fresh one — nothing you write here is lost, and nothing carries over
by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`cue_n_woo_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Cue-n-Woo-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### Bedrock is BROKEN in hosted mentalist episodes — every league game runs the deterministic fallback, never Claude.
- **Evidence:** All 5 latest league episodes (2026-06-13 18:33–19:11Z, vs kyle_policy v3)
  show `policy_agent_0.log`: `Bedrock failed (AccessDeniedException ... aws-marketplace:Subscribe ...
  Model access is denied)` on BOTH the propose and answer calls. Every secret/blind answer
  is the `fallback_answer` template `"<Stylecue> speaking, <question keywords> matters most to me"`.
  So the entire LLM-writer half of the design is dead in production — we've been evaluating
  the fallback, not the player.
- **Status:** candidate, HIGH-STAKES — #1 thing to fix; the whole design rests on Bedrock writing answers.

### The Bedrock failure is a POD-IDENTITY/account subscription gap, NOT a code bug — mentalist's calling code is byte-identical to the working baseline.
- **Evidence:** The cue-n-woo league baseline (`v2/coworld/players/baseline.py`, gh Metta-AI/cue-n-woo)
  uses the EXACT same wiring mentalist does: `DEFAULT_MODEL_ID="us.anthropic.claude-opus-4-8"`,
  `DEFAULT_REGION="us-east-1"`, `boto3.client("bedrock-runtime").converse(...)`. Live test under
  the `softmax` profile (primary acct 751442549699): `us.anthropic.claude-opus-4-8` converse
  succeeds in BOTH us-east-1 and us-west-2; the `-v1:0` suffix is INVALID for this model. So region
  and model-id form are ruled out. Decisive: `kyle_policy` (= baseline harness with NO fallback —
  it raises and crashes on a non-retryable Bedrock error) produced coherent on-topic answers
  ("soft blue","gentle piano","a brass key") and scored in the SAME episodes mentalist's call
  threw marketplace-AccessDenied. => Bedrock IS reachable for some league player pods; the gap is
  specific to the identity/account mentalist's pod runs as (incident doc: hosted runs as
  `episode-runner-bedrock` in tournament acct 583928386201; opus-4-8 is subscribed in 751442549699
  but the tournament acct's subscription is unverified — needs `tournament` SSO login to confirm).
- **Status:** candidate, HIGH-STAKES.

### SETTLED (3 wrong guesses later): NO player pod in this tournament has working Bedrock — the episode-runner role has no Anthropic marketplace access for ANY model.
- **Evidence (ground truth, not inference):** mentalist player pod 403s on BOTH opus-4-8 (v2,
  job aaeca506) AND haiku-4-5 (v3, job e942d273) — identical `aws-marketplace:Subscribe` denial,
  so it is NOT model-specific. crewrift/crewborg does NOT run an LLM in the league: its trace shows
  `meeting_llm_fallback reason=llm_disabled (CREWBORG_LLM_MEETINGS is not enabled)` in 66/66 events
  across episodes — zero successful Bedrock/Anthropic calls. kyle = 6 hardcoded fallback strings.
  => The `episode-runner` IRSA role (tournament acct 583928386201) genuinely lacks Bedrock Anthropic
  marketplace access for every model; nobody has worked around it via Bedrock — they just don't use an LLM.
- **METHODOLOGY LESSON (the real one):** I made the SAME mistake 3×: declared a "works" baseline
  (kyle's Bedrock; crewrift's Bedrock; haiku) from a *capability* or *coherent-looking output*, without
  ever grepping a SUCCESS log line. The disciplined check is: before claiming X works, find the log line
  proving a successful call (`bedrock ok`, a real usage/token count), not just code that *could* or output
  that *looks* right. A 6-value answer histogram and a `meeting_llm_fallback=llm_disabled` grep each would
  have killed a wrong hypothesis in one step. Verify success, not capability.
- **Real fix options:** (a) direct ANTHROPIC_API_KEY via `--secret-env` — bypasses Bedrock entirely, the
  only LLM path not blocked by the role (already built into the dual-backend writer; needs a key); or
  (b) get the episode-runner role Anthropic marketplace access in 583928386201 (tournament SSO + AWS/TF).
  Until one lands, mentalist runs the deterministic fallback in the league (still ~80% vs this field).
- **Evidence:** mentalist:v2 (dual-backend writer) uploaded `--use-bedrock` AFTER metta#15616 and
  submitted — its first qualifier episode (job aaeca506) STILL threw the marketplace 403
  (`PermissionDeniedError ... required AWS Marketplace actions`); writer correctly selected Bedrock
  (`LLM backend: bedrock`) but the call was denied -> fallback. So re-upload is NOT the fix.
  Then the premise behind the re-upload theory collapsed: kyle_policy:v3's answers across 40 episodes
  (120 authored rows) are exactly **6 distinct hardcoded strings** (gentle piano / warm soup / a quiet
  library / reading slowly / a brass key / soft blue) — question- and style-independent => kyle is NOT
  running an LLM. kyle:v3's tag `bedrock_fallback_fix` meant "kyle ADDED a deterministic fallback"
  (same as mentalist already had), not "kyle fixed Bedrock". So nobody in this league has working
  player-pod Bedrock. Methodology miss: I inferred "kyle's Bedrock works" from coherent-looking short
  answers without checking their distribution; a 6-value histogram would have caught it immediately.
- **Status:** CONTRADICTS the earlier "stale upload" lesson above (kept for the record). The real fix is
  the infra-independent ANTHROPIC_API_KEY path (already built) OR fixing the episode-runner IRSA role's
  Bedrock Marketplace subscription in the tournament account 583928386201 (needs `tournament` SSO login).
- **Evidence:** Player-pod Bedrock is gated in `coworld/runner/kubernetes_runner.py`: a player pod runs
  under the `episode-runner` service account (the Bedrock IRSA role) AND gets `AWS_REGION` from
  `COWORLD_BEDROCK_REGION` (us-east-1) ONLY if its stored `policy_secret_env` has `USE_BEDROCK=true`
  (`_uses_bedrock` / `_player_service_account_name`); otherwise it runs under the default SA with no
  Bedrock. metta#15616 "Add hosted Coworld secret URIs" landed (squash `cf8ddcc`) **2026-06-12T23:41Z**
  and reworked the hosted secret-env dispatch (Secrets Manager bundle -> presigned URI -> runner merges
  per-slot env). TIMELINE: mentalist:v1 uploaded **2026-06-12T20:22Z = ~3h BEFORE that fix**;
  kyle_policy:v3 uploaded **2026-06-13T02:58Z** tagged **`purpose=bedrock_fallback_fix`** = AFTER it.
  Same league, same `episode-runner` IRSA, same default model/region — kyle's Bedrock works, ours throws
  marketplace-AccessDenied — and the only material difference is kyle re-uploaded post-fix. So the fix is
  to **rebuild + re-upload mentalist** so its secret-env is re-stored under the current dispatch path.
- **Status:** candidate, HIGH-CONFIDENCE. Caveat: secret-env keys aren't exposed via API (Secrets Manager),
  so "stored USE_BEDROCK present+correct" is inferred from the timeline + kyle precedent, not read directly.
  The IAM hotfix from the earlier incident was the SIGNING-KEY S3 read (game container), a DIFFERENT axis
  from player-pod Bedrock model access — it did not cause and is unlikely to fix this.

### Lab convention for runtime LLMs is DUAL-BACKEND (Bedrock OR Anthropic API key) — mentalist only does Bedrock, so it has no escape hatch when the pod's Bedrock access fails.
- **Evidence:** suspectra (the *recommended* Crewrift LLM player, `llm_meeting.py`) uses the
  `anthropic` SDK and branches: `USE_BEDROCK` -> `AnthropicBedrock`, else `ANTHROPIC_API_KEY` ->
  `Anthropic`. Its README: "USE_BEDROCK=1 uses Bedrock via the tournament AWS env ... Without
  Bedrock, set ANTHROPIC_API_KEY for direct Anthropic." player-build.md: attach keys at upload via
  `--secret-env ANTHROPIC_API_KEY=...` (lands in the version's pod via Secrets Manager).
  mentalist's writer hardcodes raw boto3 Bedrock only. Robust infra-independent fix: add the
  Anthropic-API-key path and upload with `--secret-env` — sidesteps the pod marketplace-subscription
  problem entirely. `upload-policy --use-bedrock` only sets `USE_BEDROCK=true` (no creds/region);
  `run-episode --use-bedrock` additionally injects host creds + AWS_REGION (why Gate-1 local passed).
- **Status:** candidate.

### Even the dumb fallback beats kyle_policy ~80% — because the classifier-style-cue tilt is real and the opponent answers blind+generic.
- **Evidence:** Fallback-vs-kyle record 4/5 wins; scores like 659.7 vs 0.3, 549.9 vs 110.
  The template leads with a style-derived word (`Exaggerated`, `Zen`, `Friendly`) and the
  judge's `secret_probability` routinely hits 0.99+. Confirms probe finding 3 (style is a
  decisive tilt) AND that kyle's generic blind answers are weak. The one loss (136 vs 524)
  was a `friendly classroom teacher` style where the template's stiff phrasing lost all 6
  questions narrowly — fallback has no floor when the style cue is mild/non-distinctive.
- **Status:** candidate — implies Bedrock upside is on top of an already-winning baseline; quantify the lift once Bedrock works.

### The stub-worker cert smoke does NOT exercise the LLM writer — needs a real-config local episode to verify Claude prose.
- **Evidence:** `coworld-local-run`'s default smoke + the manifest `certification` block run with
  `stub_worker:true` and self-play, so both slots fall to identical fallbacks (duplicate-conflict 40/40)
  and the Bedrock/Anthropic path never runs — a green cert smoke says nothing about whether the writer
  works. To actually test it: build an episode_request from the default variant's `game_config` with
  `require_signing:false` + `stub_worker:false` (keep the real `llm_worker_url`), then
  `coworld run-episode <manifest> <request.json> --use-bedrock --aws-profile softmax --aws-region us-east-1`.
  Confirm the log shows `LLM backend: bedrock ... ok` + real prose, not the `"<Style> speaking, ..."` template.
  Did this for v2 (2026-06-13): pirate style classified 0.628, Claude wrote
  "Arrr, I'd weigh anchor and hunt buried treasure...", all ≤12 tokens, no rejections, scores [579.2, 80.8].
  Build the spec via `coworld.cli.load_coworld_package` + `certifier.build_manifest_episode_job_spec`
  then override `game_config` (the build helper defaults to the cert/stub config). NOTE API drift:
  `build_manifest_episode_job_spec(package, *, variant_id, player_images, player_run)` — no
  `require_signing`/`variant` kwargs the older WORKING_CONTEXT recipe implied.
- **Status:** candidate — should become the cue-n-woo Gate-1-for-LLM recipe (README updated).

### Unify Bedrock + direct-Anthropic on the `anthropic` SDK, not raw boto3 — one messages.create+tool path serves both.
- **Evidence:** `AnthropicBedrock(aws_region=..., aws_profile=...)` + `Anthropic(api_key=...)` share the
  identical `.messages.create(model, tools, tool_choice, messages)` API and tool_use response shape, so
  the dual backend is one code path with a client-construction switch (vs maintaining boto3 `converse`
  separately). Live-verified `AnthropicBedrock` works with `us.anthropic.claude-opus-4-8` in us-east-1 AND
  us-west-2; the `-v1:0` suffix is INVALID for this model; the direct API uses the bare `claude-opus-4-8`.
  `AnthropicBedrock` needs botocore present (keep boto3 in the image).
- **Status:** candidate.

### results.json `rows[]` is the per-question scoring ground truth — richer than scores[].
- **Evidence:** Each of the 6 rows carries `owner/opponent`, the literal `secret_answer` vs
  `opponent_answer`, `secret/opponent_score_points` (base+bonus), `average_secret_probability`
  (the judge's both-orderings-averaged preference), `duplicate_conflict`, and per-`orderings`
  probs. `owner==0` rows = mentalist's authored questions; `owner==1` = blind-answer rows.
  This is exactly the game referee's `score_round` output — enough to attribute every point
  without opening the replay. Opponent logs are empty (we don't own that slot).
- **Status:** candidate — basis for a future cue-n-woo report skill.
