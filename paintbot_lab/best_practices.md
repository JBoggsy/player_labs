# Paintbot best practices

Paintbot-specific practices layered on top of the root
[`../best_practices.md`](../best_practices.md) — things true of *this game's*
tooling and failure modes. Starts near-empty; fills via the lessons pipeline
(`TENTATIVE_LESSONS.md` → `lessons_archive/` → graduation).

## Seeded from the founding recon (2026-08-03)

- **Never assume the map.** Every map fact must come off the wire (walkability
  sprite, `game teams` marker, `endzone` markers, planted hearts). The seed is
  not on the wire; the fixed classic arena is just one possible map among many.
- **No module-level map caches** in the player — episode-scoped state only.
  (Beacon's `lru_cache` map loaders were a latent cross-episode bug class.)
- **Verify against the DEPLOYED game version** (`uv run coworld list`), not
  repo main — the paintbot league redeploys often and runs ahead of ctf's.
- **Check behavior per-variant.** A change can help `2v2` and hurt `4ffa8`
  (different vision cone, roster, map scale); always cut eval results by
  variant before concluding.
