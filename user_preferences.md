# User preferences

Durable preferences the human has expressed for working in this lab — how to
communicate, what to do or avoid, defaults to assume. `AGENTS.md` tells you to
**read this on startup**.

When the human states a preference (explicitly, or clearly through repeated
correction), **record it here** as a short, concrete entry so it persists across
sessions. Keep it tidy: one bullet per preference, drop ones that are superseded.

## Preferences

- **XP requests > 16 episodes: always bring up the dashboard** (James, 2026-07-01).
  Whenever you create an experience request with more than 16 episodes, start the
  XP dashboard for it (`.claude/skills/coworld-experience-requests/scripts/xp_dashboard.py
  --port <port> xreq_...`) and give James the `http://localhost:<port>` link in the same
  message that reports the request was created. Reuse a running dashboard's port only by
  restarting it with the new xreq id(s); don't leave it pointed at a stale request.

- **Always upload policies with ALL telemetry enabled unless told otherwise** (James, 2026-07-01).
  Every `coworld upload-policy` gets `--secret-env CREWBORG_METRICS=1 --secret-env
  CREWBORG_TRACE_GROUPS=all` (the `all` trace group exists in `trace.py`). Rationale:
  massive logs when we need them beat re-uploading the same policy and re-running XP
  requests to get telemetry (v81 had to be re-uploaded as v82 for exactly this reason).
  If telemetry volume is ever suspected of causing latency/timeouts, that's a finding to
  raise, not a reason to silently strip tracing.
</content>
