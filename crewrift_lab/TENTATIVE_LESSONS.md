# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-21 13:01. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`crewrift_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Crewrift-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### fetch_artifacts.py `--round` is NOT repeatable — only the last one wins
Evidence: passed ten `--round` flags in one invocation; got exactly 20 episodes (one round). Looped per-round invocations into the same `--out` dir instead (incremental, safe). Note build_warehouse.py's `--round` IS repeatable — the two scripts differ.

### tools/bin expand_replay binaries embed a build-time absolute path that broke when the repo moved
Evidence: all `tools/bin/expand_replay-*` die with `No such file or directory: …/personal_labs/crewrift_lab/.cache/crewrift-src/<ref>` — the repo now lives at `personal_labs/personal_labs_crewrift/`. Fixed with `ln -sfn …/personal_labs_crewrift/crewrift_lab …/personal_labs/crewrift_lab`. Durable fix: rebuild the binaries.

### expand_replay-34a97a3 is still the correct expander for live league replays (crewrift 0.4.68, 2026-07-21)
Evidence: 182/199 trace-complete on the latest 10 rounds; `expand_replay-d9f6b30` (versions.env's CREWRIFT_REF) hash-fails on the same replays. versions.env is the *player-build* pin, not the replay-expander pin.

### survey.py `--reasons` keys must be the exact episode DIR names, not full ereq ids
Evidence: first reasons.json keyed by full `ereq_…` id produced sidecar `reason` count 0, silently — no warning. Keys are the truncated dirs like `20260721T193356_ereq_94c9f0fc-1b`.

### Bedrock throttling persists in LIVE league rounds — the LLM layer fires ~38%
Evidence: crewborg league telemetry over 58 episodes: 154 `meeting_llm_decision` vs 248 `meeting_llm_fallback`, 236 "Too many tokens" throttle lines, 40 `meeting_llm_budget_exhausted`. The social rework is still mostly untested in production, matching the A/B story.

### ROOT CAUSE of self-suss (and likely the whole v107 slump): the slot→color seed table is STALE — the deployed game renamed its 16 colors
Evidence: crewborg's `PLAYER_COLOR_NAMES` (perception/constants.py:86, "palette order (global.nim PlayerColorNames)") = red, orange, yellow, light blue, pink, lime, blue, pale blue… — matches crewrift `d9f6b30`/`42fed21` (0.1.x). The DEPLOYED game (34a97a3 / 0.4.68, sim.nim:145) uses red, blue, green, pink, orange, yellow, purple, cyan…. The `?slot=` seed (policy_player.py:384) is marked `self_color_from_marker=True` (authoritative, never corrected), so 6/8 seats latch a WRONG self color for the whole game: slot 1 believes "orange" while actually blue, slot 4 believes "pink" while actually orange, etc. Every downstream self-exclusion (kill pool, suspicion, top_suspect, accusation, census self-death) then guards the wrong color. Telemetry confirms: 12/58 episodes have crewborg's ACTUAL color inside its own `teammate_colors` (reveal ingest failed to drop self), and the self-accusation episodes are exactly the seats whose actual color ("orange", "green") differs from the seeded one ("pink", "yellow"). Only slot 0 (red) is accidentally correct. Fix: sync PLAYER_COLOR_NAMES with the deployed game's table (and add a runtime cross-check marker-vs-seed).

### v107 league weakness decomposes into three mechanistic signals in one warehouse pass
Evidence: (1) imposter ejected 9/17 = 53% (field median ~31%) with kills/seat 1.29 and isolated-kill conversion 19% vs 34-50% for the top; (2) crew votes-received/seat 1.37 (2nd-worst) with 6/41 crew ejections; (3) SMOKING GUN: crewborg chat literally accuses its own color — 5 messages across 2 episodes of "orange sus: … vote orange" / "green sus … vote green" (self-suss in the accusation template while `fabricate/report` pipeline picks self as target). Also opponents' detectors ("X was tailing me") fire on crewborg's tail-heavy movement in BOTH roles.
### Importing another team's methodology: filter through the operating model, not topical overlap

Evidence: Pulled from `Metta-AI/optimizer-skills` (an *autonomous*-optimizer library) into
this *human-gated, speed-first* lab. What transferred cleanly: executable engines fitting
our shared-engine + per-lab-adapter pattern (their variance miner → `coworld-hypothesis-miner`),
durable engineering doctrine (`docs/player-engineering.md`), and dense measurement heuristics
(eval sizing from variance, opponent-field-from-goal → root `best_practices.md`). What was
deliberately rejected despite topical fit: promotion-gate / continuous-optimizer /
defend-leaderboard (their replacement for our human gate — importing would fight the lab's
model), the local-sim harness (probe deltas reverse on the live field), game-strategy
snapshots (stale vs our live labs). Where an import diverges from its source's posture,
state it in the imported doc (e.g. "uploads stay ungated here") so readers don't inherit
the source repo's caution.

### The Honor Society is a metagame construct, not a game mechanic — grep the game rules first

Evidence: Asked "what honor-society infrastructure do we have," the instinct is to search the
game docs. But `crewrift-gameplay.md` and `crewrift-protocol.md` have ZERO mentions of honor/
society/reputation/trust — the game only gives generic throttled meeting chat + voting. The
Honor Society is a player-community cartel (HS1 spec authored externally by Alex Smith,
received via Discord DM) layered on the chat channel. When mapping a "feature," first
establish whether it's game-provided or player-invented — it changes what "further develop"
even means (we can't rely on the game to enforce anything; every guarantee is our own crypto).

### Honor Society tracing is per-episode only; cross-game reputation is emitted but never harvested

Evidence: `society_*` Belief fields (types.py:477-486) fully track claims/trust/liars WITHIN
a game, and `domain.honor_liar` events fire — but nothing consumes them. grep for consumers of
`honor_liar`/`honor_claim` outside honor_society.py+tests returned only the emit sites. The
liar-ledger harvest → vendored distrust list is a standing TODO (WEEKLY_CONTEXT.md:57). So
rule 4 ("track standing, punish future") has an in-game half (implemented) and a cross-game
half (aspirational). A natural "further develop" target with a clean seam already emitting data.

### Honor Society has never been measured in isolation — it shipped bundled in full-stack champions

Evidence: v91/v93/v95 each folded HS in alongside weights refits, search changes, camo, knobs
(version_log.md:21-26). No A/B ever isolated "HS on vs off." Before developing it further,
note that its live value is unproven — the veto is provably safe (skip-only, witnessed
overrides) but "does trust-based cooperation actually win more crew games" is untested. Any
new HS work should carry its own isolated A/B, not ride another full-stack ship.

### CRITICAL: our HS1 wire format DOES NOT MATCH the format actually used in live games

Evidence: Searched 11 recent crewrift_prime tournament games with both crewborg (us, "James
Boggs") and sasmith-crewborg-hs1 v15 (Alex Smith). Every HS1 line in the replays is
**2 tokens**: `HS1 <86-char base64url>` (len 90; the blob decodes to 64 bytes = a bare
Ed25519 signature). Our spec/code (honor_society.py:222) emits **5 tokens**:
`HS1 <10-digit ts> <8-char nonce> <44-char pubkey> <88-char sig>` (len 157). Confirmed
`honor_society.parse(<real 2-token line>)` returns **None** — we silently ignore every real
HS1 announcement. So even when the flag is on, we cannot verify, trust, or act on sasmith's
claims, and our own announcements (if sent) would be unparseable to them. The design doc's
"HS1 canonical spec (Alex Smith 2026-07-02)" has diverged from what Alex's bot actually
emits — or was mis-transcribed. **Any HS ecosystem work must first re-derive the real HS1
format from live replays, not the vendored doc.**

### crewborg's honor state is NOT observable from league/tournament episodes

Evidence: The honor_* trace events (honor_claim, honor_liar, meeting_vote_society_veto) go to
`jsonl@artifact` (the player-artifact zip), which is only fetchable for experience-request
episodes — league/tournament episodes 404 on the v2 policy-artifact route
(fetch_artifacts.py:31, "no v2 route for league episodes"). The stderr policy log for our
seat in league games is 44 bytes ("game over") — crewborg emits its trace to the artifact,
not stderr, when an upload URL is present. So to validate honor behavior we must fire our OWN
experience-request (crewborg + sasmith, HS flag on, trace on) and read our artifact zip —
mining existing league replays only shows the CHAT exchange (what was broadcast), never our
internal register/trust/veto decisions.

### The deployed champion may not carry CREWBORG_HONOR_SOCIETY=1 at all

Evidence: WORKING_CONTEXT.md's submit recipe (v106) has NO honor flag; only v91's recipe
explicitly lists `--secret-env CREWBORG_HONOR_SOCIETY=1 --secret-env CREWBORG_HONOR_SEED=...`.
The flag+seed are per-submission secret-env, not baked into the image, so a submission that
omits them runs with HS fully inert. Before claiming "we use HS in real games," verify the
flag is in the ACTUAL submit command of the live champion — the deployed crewborg is v107
(newer than v106 in the version_log), whose exact secret-env set isn't recorded.

### The real HS1 is the COMPACT 2-token form; verified 17/17 against sasmith's registered key

Evidence: User supplied the authoritative HS1 spec. Real wire = `HS1 <sig>` (2 tokens), sig =
Ed25519 over `HS1|<ts5>|<color>` where ts5 = (unix//5)*5 and color = observed speaker color;
unpadded base64url; verify by brute-forcing ledger keys × a small ts5 window ({now5, -5, -10,
+5}); NO first-poster-wins (one key may verify at multiple colors = one member running 2 slots);
freshness 10s. Our code emits/parses only the LEGACY 5-token form → parse() returns None on
every real line. PROVED the spec by brute-forcing 17 captured compact sigs from live replays
against sasmith's registered key WxWJy6ZO... × 16 game colors × a ±45min ts5 grid: 17/17
verified. So spec is exact AND sasmith's registered key is still current (no rotation needed).
Their seed env is `CREWBORG_HS_SECRET` (ours: `CREWBORG_HONOR_SEED`).

### crewborg's PLAYER_COLOR_NAMES is STALE — the game changed its palette 2026-06-24 (commit 1cbd4de)

Evidence: `crewrift_lab/.../perception/constants.py:86` lists `red, orange, yellow, light blue,
pink, lime, blue, pale blue, gray, white, dark brown, brown, dark teal, green, dark navy, black`.
The live game (`coworld-crewrift sim.nim:149 PlayerColorNames`, current on origin/master, changed
in commit 1cbd4de "update player colors" 2026-06-24) is `red, blue, green, pink, orange, yellow,
purple, cyan, lime, brown, beige, navy, teal, rose, maroon, gray`. My recovered sasmith palette
(slot→verified color) matches the GAME list exactly (slot 6=purple, 7=cyan). Impact on HS1: since
verification reconstructs the signed bytes from the color STRING, a wrong palette breaks it. Chat
`speaker_color` and the `vote self marker <color>` self-color both come from GAME sprite labels
(correct names), BUT `policy_player._self_color_from_url` (v106's slot→color self-ID seed) uses the
STALE constant → our OWN announce would sign a wrong color whenever self-color is seeded from slot
before the marker is seen. Also a latent bug beyond HS1 (any slot-indexed color lookup wrong for
slots ≥3). Must decide: fix the constant now (re-verify v106 self-ID holds) or scope narrowly.

### HS1 fix VERIFIED end-to-end in live games (crewborg:v109 + sasmith, xreq_25bb7e0f)

Evidence: After rewriting honor_society.py to the compact form + fixing the palette + default-on,
built players-crewborg:hs-fix (in-image checks passed: palette fixed, compact 2-token announce,
our pubkey Gq5nOr6…, sasmith real sig verifies→alex-smith), uploaded v108 (no trace env) then v109
(with CREWBORG_TRACE_GROUPS=all so the non-domain honor_* events survive the lean filter). Fired
xreq_25bb7e0f: crewborg:v109 crew@slot0 + sasmith-crewborg-hs1:v15 crew@slot1, 2 random imposters@6,7.
crewborg's OWN policy_artifact_0.zip trace shows, per completed episode: `society: crew announce`
(we send compact HS1) + `domain.honor_claim {color:blue, pub:WxWJy6ZO…, known:alex-smith}` +
`domain.honor_known_member {color:blue, label:alex-smith}` — we parse+verify sasmith's REAL compact
signature and register them trusted. This is the exact chain that returned None (100% broken) before.
Note: env vars (seed + trace groups) bake at UPLOAD via --secret-env, NOT per-xreq — an upload without
CREWBORG_TRACE_GROUPS=all silently drops honor_* from the artifact (they're non-domain. → lean-filtered).
The vote-veto/posterior-pin only *fires* when the posterior would otherwise vote a trusted member, so
it won't appear in every game (a clean crewmate never becomes a vote target).

### A worktree can be removed mid-session by another actor — commits survive only if merged/on a branch

Evidence: Mid-session, the `worktree-crewrift-honor-society` worktree dir was deleted and its branch
gone (shell cwd reset to repo root). Recovered via reflog: another session had MERGED the branch into
main (`98439ca Merge branch 'worktree-crewrift-honor-society'`) — and independently landed the same
stale-PLAYER_COLOR_NAMES root cause (`ffe9759`, a v107 10-round audit). Both my commits were reachable
from main (`git merge-base --is-ancestor <sha> HEAD`). Lesson: commit early/often on the worktree
branch (uncommitted work would have been LOST when the dir vanished), and if a worktree disappears,
check `git reflog --all | grep <branch/sha>` + `git fsck --no-reflogs | grep dangling` before assuming
loss — a parallel session may have merged it. Continue from the main checkout with absolute paths.

### "Data vanished from the platform" is a read-path hypothesis until an old object 404s directly

Evidence: the 2026-07-01 "league artifacts are ephemeral (~1 round, ~10-15 min)" scare
(TODO item; v82 6/100, v80 17/196 with artifacts, newest-round-only). Re-probed 2026-07-21:
the very same v80/v82 episodes still list has_artifact=true and download fine (HTTP 200)
via `GET /v2/episode-requests/{ereq}/policy-artifacts` — 20 days later. Nothing with a
15-minute TTL returns data at 20 days, so the original disappearance was a READ failure,
not deletion: it coincided exactly with metta's artifact-route/auth churn (v1 TEAM_AUTH
`/jobs/{id}/policy-artifact` + opt-in elevation ee7a3e27c2 #17028 landing 07-02 + the v2
migration b548b013a4/#17413, 3c3fdb4f17/#17466; v1 deleted c4ddebd857/#17603), and our
fetcher maps EVERY 4xx to "no artifacts" (`get_text_or_none` → None). Also verified in
metta: no artifact TTL exists — the only S3 lifecycle expiry is the secrets bucket
(`devops/tf/observatory/policy-secrets.tf:52`); the only backend delete is the per-job
secrets bundle (`job_runner/event_processor.py:791`). Lesson: before concluding
"retention", (1) directly re-fetch an OLD known-good object, (2) distinguish 403/404/empty
in tooling instead of collapsing them, (3) check whether the platform's auth/routes were
churning that week. Harvest tool now exists anyway: `crewrift_lab/tools/harvest_artifacts.py`
(+ `docs/telemetry-harvest.md`).
