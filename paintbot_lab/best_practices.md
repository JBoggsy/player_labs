# Paintbot best practices

Paintbot-specific practices layered on top of the root
[`../best_practices.md`](../best_practices.md) — things true of *this game's*
tooling and failure modes. Starts near-empty; fills via the lessons pipeline
(`TENTATIVE_LESSONS.md` → `lessons_archive/` → graduation).

## Seeded from the founding recon (2026-08-03)

- **Only campaign-shaped episodes count as tests.** Use the live cell's full
  commissioner roster: normal two-team invasions use four policies in
  7+7+1+1 captain/ally seating; four-team FFA uses one policy per color;
  follow [`docs/tournament-like-experience-requests.md`](docs/tournament-like-experience-requests.md).
  Treat partial-seat, arbitrary-map, and local scenarios as debug probes,
  never as performance evidence. A current `1v1` map ref is valid only with
  its campaign mode and battle-kind seating reproduced.
- **Never assume the map.** Every map fact must come off the wire (walkability
  sprite, `game teams` marker, `endzone` markers, planted hearts). The seed is
  not on the wire; do not bake in historical `default` geometry.
- **No module-level map caches** in the player — episode-scoped state only.
  (Beacon's `lru_cache` map loaders were a latent cross-episode bug class.)
- **Verify against the DEPLOYED game version** (`uv run coworld list`), not
  repo main — the paintbot league redeploys often and runs ahead of ctf's.
- **Check behavior per-variant.** A change can help `2v2` and hurt `4ffa8`
  (different vision cone, roster, map scale); always cut eval results by
  variant before concluding.
- **Never infer muster from map size.** Use the cell mode and created episode
  roster. Current campaign cells leave `map_size` unset, and historical boards
  demonstrate that size and roster can vary independently.
- **Version game mechanics explicitly.** GameVersion 40 restored continuous
  integer-brad aim after GV36's discrete slot model. Re-check deployed sim code
  and tests before carrying a mechanics claim into a new controller revision.
- **Validate consensus safety across every representation of a vote.** Once an
  agent locks a vote, use that same value for local storage, quorum counting,
  and rebroadcast; a lock on only one path can still create overlapping
  conflicting commitments.
- **Measure coordination liveness only among agents that can participate.**
  Evaluate drift over concurrently alive intervals; terminal state from a dead
  member cannot distinguish a protocol failure from permanent elimination.
- **Give fixed squads an explicit reconnection mechanism when communication is
  range-limited.** Retries and epoch resynchronization cannot repair a physical
  partition by themselves; define and test how separated members rendezvous
  before treating proximity-chat consensus as complete.
