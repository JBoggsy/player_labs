# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-28 10:15. This is THIS SESSION's lesson buffer. Write candidate
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

## belief-audit build (2026-07-28)

- **`build_warehouse.py --expand-replay` must be an ABSOLUTE path** — it subprocess-runs
  `crewrift-event-warehouse build` with `cwd=` the vendored package dir, so a repo-relative
  binary path fails per-episode with FileNotFoundError while the manifest still says
  "✓ no trace_warning". Failure mode looks like "0 events, 8 failed", not an error. (The
  SKILL.md examples use /tmp paths, which is why this never bit before.)
- **`--policy crewborg -n N` league episodes have NO policy artifacts** — the fetcher says
  "no v2 route for league episodes (only episode requests)". Belief-audit (any artifact-
  telemetry consumer) needs xreq/ereq episodes, not league rounds. Fetch by `--xreq`.
- **The xreq listing route is `GET <api>/observatory/v2/experience-requests` → `{entries: […]}`**;
  short ids from notes (xreq_61f440b3) must be resolved to full UUIDs before `--xreq` fetch
  (the episodes sub-route 422s on a short id).
- **`imposter_unranked` needs an alive filter** — a dead imposter legitimately drops out of
  the suspicion ranking; comparing rankings to the full-roster imposter set produced 4 false
  divergences in an 8-seat smoke (all were post-death meetings). Filter live_imposters by
  `truth_death_ts > snapshot_ts`.
- **Real-data smoke check found real signal immediately**: crewborg's belief notices deaths
  via census 300-650 ticks late (`death_belief_lag`, source=census), and `ranking_top_crew`
  at p≈0.5-0.53 barely over the current 0.5 vote bar — both plausible hypothesis fuel.

## belief-audit doc audit (2026-07-28, post-commit)

- (Note: the "belief-audit build" lesson block above was written this session and already
  committed with the skill — the stop-hook's untouched-buffer check can false-positive when
  lessons are committed mid-session.)
- **Skill-relative doc links need THREE `../` to reach crewrift_lab/** — a SKILL.md at
  `crewrift_lab/.claude/skills/<name>/` linking to `crewrift/crewborg/docs/…` is at depth 3;
  I wrote `../../` first and the audit-documentation pass caught the dead link. Check with
  `ls <skill-dir>/<relative-link>` before committing skill docs.
- **Validate SKILL.md example SQL by running it against the test fixture** — the
  belief-audit SKILL.md's example query was executed against the synthetic warehouse the
  tests build (duckdb + the fixture's `_setup`) before committing. Cheap and it makes doc
  examples load-bearing rather than aspirational.

## improvement-loop alpha, loop 1 (2026-07-28)

### Decompose a shipped lever's paths before proposing new levers — the win may hide a dead branch
Evidence: v116's retime A/B'd +21.5pp conversion as a WHOLE, but the L1 warehouse decomposed
its ballot reasons: join path 53.1% conversion vs expire path 0.8% (n=113/124 on-imposter).
The expire path (73% of ballots by volume) is near-worthless — invisible in the A/B aggregate.
`belief_meeting_vote_selected.value.reason` (belief-audit partition) made this a one-query read.

### Vote locking makes ballot timing asymmetric: early votes recruit, late votes are spent
Evidence: no re-vote in crewrift (gameplay §Voting). Field ballots land p50 dt≈312; a cast at
dt 601 faces a median 5.3 locked ballots and recruits ~0. Any coordination lever must act
BEFORE the field's vote wave — chat can, a held ballot can't.

### The miner's invariant list is as valuable as its hypotheses — it closed both smoke signals in one pass
Evidence: census death-lag (0.178/seat) and ranking_top_crew (0.186/seat) are REAL rates, but
joined as div_* features both mined invariant (r=+0.07/+0.01) — present in wins and losses
alike. Saved a loop that would have designed around a non-load-bearing divergence.

### stream_eval survives xreq stragglers badly — one stuck 'pending 1' episode holds the watcher forever
Evidence: L1 step-1: 3/400 episodes failed platform-side (player_never_started); two watchers
sat at 'fetched 99/100, drained=False' indefinitely. Kill the stream and run build_warehouse.py
--episodes once the xreqs report terminal counts; builds are incremental so this costs nothing.

### Warehouse `chat` events cap at 6 per meeting — the extractor only sees the sim's visible buffer growing
Evidence: L1 prevote-push probe "sent 76, warehouse shows 2". expand_replay printChats emits
only for chatCount..<len; sim buffer caps at VoteChatVisibleMessages=6 (delete(0)+add → len
static) → chats 7+ per meeting never become events. Warehouse per-meeting chat histogram
hard-caps at 6. Raw replay bytes carry the full chat record (delivery provable there); policy
telemetry counters are the right mechanism instrument. Any chat-volume/chat-timing analysis on
busy meetings undercounts — including some past studies.

### Raw replay bytes are NOT visibility — writeChat records dropped chats too
Evidence: L3 chatfix verdict. server.nim writeChat()s every client chat BEFORE
addVotingChat applies the MessageCooldownTicks filter, so "the text is in replay.json"
includes server-swallowed messages. Visibility instrument = re-apply the acceptance rule
(>=100t since last ACCEPTED chat) to the telemetry send stream, or use warehouse chat
events (visible-buffer-derived, but capped 6/meeting).

### The client chat cooldown must EXCEED the server's, and check EVERY chat path
Evidence: CHAT_COOLDOWN_TICKS=60 < MessageCooldownTicks=100, and the deterministic
accuse path + HS1 announce didn't cooldown-check each other → 30% of accusations
silently swallowed (98% in the 1-tick-after-HS window). Cost measured: 1.45 vs 0.63
votes-on-target. Any new chat feature must route through one cooldown gate.

### A guard tripping its point-estimate bar at p=0.10 is still a NO-SHIP — rerun powered, don't rationalize
Evidence: L3 chatfix GUARD-7 (mis-ej/cep 0.181 vs bar 0.174, fisher p=0.098). The prereg
said any guard failure disqualifies; the honest move is a fresh powered prereg (L4), not
"it's probably noise, ship it".

### coworld upload "unauthorized: authentication required" can mean THE DOCKER DAEMON IS DOWN
Evidence: L4 v118 upload. The registry-sounding error chain (denied/unauthorized) came from
assert_docker_image_reachable falling through to a remote manifest check after the local
docker.sock was gone (OrbStack quit overnight). Check `docker info` before debugging auth.
