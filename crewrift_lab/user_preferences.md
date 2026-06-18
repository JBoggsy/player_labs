# Crewrift user preferences

Durable preferences the human has expressed **specifically for Crewrift work** —
layered on top of the lab-wide [`../user_preferences.md`](../user_preferences.md)
(read that too; it holds the game-agnostic preferences). [`AGENTS.md`](AGENTS.md)
tells you to **read this on startup**.

When the human states a Crewrift-specific preference (explicitly, or clearly through
repeated correction), **record it here** as a short, concrete entry so it persists
across sessions. Keep it tidy: one bullet per preference, drop superseded ones.
General (non-Crewrift) preferences go in the lab-wide file instead.

> **Working context lives elsewhere.** The current objective and live state of work
> (including the active policy/version that signals onboarding is done) are tracked in
> [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md), not here. This file is for *durable
> preferences* only. See [`AGENTS.md`](AGENTS.md).

## Preferences

- **Always run 2-imposter evals, never 1-imposter.** When pinning roles for an imposter
  eval, use a 2-imposter config (crewborg slot 0 = imposter + one partner-imposter slot,
  the rest crew) — it matches real league games. 1-imposter games are not useful: they
  remove the partner dynamics (e.g. a partner's kill→report resetting our kill cooldown)
  that much of the imposter strategy actually targets, so they can't validate the
  behaviour being tuned.
