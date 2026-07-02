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

- **NEVER submit a policy without LLM chatting to the actual tournament** (James, 2026-07-01).
  League submissions ALWAYS carry the meeting LLM (the recipe below). Deterministic (LLM-off)
  uploads exist ONLY as A/B test arms — both arms deterministic to isolate the mechanism under
  test. The flow: A/B the change deterministically → if positive, re-upload the same image with
  the LLM recipe → verify `meeting_llm_decision` fires → submit THAT.

- **ALL uploads: meeting LLM ON, commander OFF, unless told otherwise** (James, 2026-07-01).
  Every `coworld upload-policy` gets `--use-bedrock --bedrock-model
  us.anthropic.claude-haiku-4-5-20251001-v1:0 --secret-env CREWBORG_LLM_MEETINGS=1`
  (the proven v70 recipe: NO manual USE_BEDROCK — the SDK gates on the sidecar endpoint)
  and does NOT set `CREWBORG_LLM_COMMANDER` (stays off). After upload, verify
  `domain.meeting_llm_decision` fires in an xreq probe; note league/dispatch pods
  historically lack the Bedrock sidecar (LLM falls back deterministic there) — check the
  league telemetry after any submission.

- **Always upload policies with ALL telemetry enabled unless told otherwise** (James, 2026-07-01).
  Every `coworld upload-policy` gets `--secret-env CREWBORG_METRICS=1 --secret-env
  CREWBORG_TRACE_GROUPS=all --secret-env CREWBORG_TRACE_SUSPICION_FEATURES=1` (the `all`
  trace group exists in `trace.py`; the suspicion-features flag is a SEPARATE env gate —
  `TRACE_GROUPS=all` does NOT imply it, and without it `suspicion_snapshot` lacks the
  `ranking[].features` vectors the suspicion refit needs; added 2026-07-02 per James after
  discovering no upload had ever carried it). Rationale: massive logs when we need them
  beat re-uploading the same policy and re-running XP requests to get telemetry (v81 had
  to be re-uploaded as v82 for exactly this reason). If telemetry volume is ever suspected
  of causing latency/timeouts, that's a finding to raise, not a reason to silently strip
  tracing.
</content>
