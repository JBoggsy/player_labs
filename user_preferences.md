# User preferences

Durable preferences the human has expressed for working in this lab — how to
communicate, what to do or avoid, defaults to assume. `AGENTS.md` tells you to
**read this on startup**.

When the human states a preference (explicitly, or clearly through repeated
correction), **record it here** as a short, concrete entry so it persists across
sessions. Keep it tidy: one bullet per preference, drop ones that are superseded.

## Preferences

- **No cheating or privileged competitor intelligence**. Gameplay
  optimization must use intended, server-validated mechanics: no clipping, coordinate injection,
  unauthorized teleporting, intentional graveyard exploits, or similar bypasses. Inspect another
  player's logs or artifacts only when ordinary non-elevated access permits it; never use elevated
  permissions to retrieve competitor evidence for optimization.

- **Never spend XP requests on self-play**. Use local episodes for self-play; reserve hosted XP requests for real-opponent evaluation. XP uses a granted, replenishing credit allowance; see [credit accounting](docs/xp-credits.md).

- **Every behavior change ships with activation tracing**. Whenever
  a change gates a new behavior (or meaningfully alters when an existing one fires),
  add (possibly temporary) tracing/logging in the SAME iteration that counts how often
  it actually activates — so a null A/B can distinguish "never fired" from "fired and
  didn't help".

- **Speed over caution — iterations per day is the KPI**.
  Write code fast and get iterations out; don't spend time being careful/safe. No
  smoke tests, no pre-upload gate (Gate 1 is removed from the loop), no test-first
  discipline, no routine test-suite runs — upload straight after the rebuild and let
  the next experience request catch breakage and measure gameplay in one step. Care
  is reserved for consequential live actions and destroying data. League submission
  remains gated; retirement can end participation but does not erase prior results. Encoded in `AGENTS.md` ("Speed is the meta-priority") and
  `best_practices.md` ("Speed first").

- **Create hosted experience requests without asking first**.
  Hosted episodes are cheap and routine: whenever they would answer the current question,
  create the targeted request immediately and stream its artifacts. Do not pause merely to
  request permission for an evaluation; league submission remains separately gated.

- **XP requests > 16 episodes: always bring up the dashboard**.
  Whenever you create an experience request with more than 16 episodes, start the
  XP dashboard for it (`.claude/skills/coworld-experience-requests/scripts/xp_dashboard.py
  --port <port> xreq_...`) and give James the `http://localhost:<port>` link in the same
  message that reports the request was created. Reuse a running dashboard's port only by
  restarting it with the new xreq id(s); don't leave it pointed at a stale request.

- **Keep documentation current.** All repository documentation and game wiki pages must describe current behavior. Remove historical reports, version logs, obsolete measurements, change narratives and references to removed information. Retain supported lessons as current guidance; do not recreate archival documentation.

- **Enable available policy telemetry by default.** Include decision reasons and
  activation counts, and verify the uploaded artifact emits them. If tracing appears
  to hurt latency, report measured evidence before reducing it. Exact flags and LLM
  recipes belong in each game's preferences, not the shared upload procedure.
