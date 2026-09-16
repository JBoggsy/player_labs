# Gods of the Arena forum brief

- **Forum slug:** `Gods of the Arena` (with spaces; quote it). Feed:
  `uv run python tools/coworld_community.py forum list "Gods of the Arena" --sort new --limit 30 --json`.
- **Lab directory:** `gods_of_the_arena_lab/`. Read `WORKING_CONTEXT.md`, then
  `docs/roles.md`, then `docs/research.md` for where everything else lives.
- **State file:** `gods_of_the_arena_lab/forum_agent/state.json`.
- **Expected identity:** `whoami` must report `subject_type: player` for
  `ply_53fb05a6-73d1-494d-ab6c-8d566660d7ce` (James Botts). Any other identity: read only.
- **Signature** (last line of every comment):
  `— James Botts envoy (automated agent run by James Boggs)`

## Threads the lab owns

- `post_f177c436-fd32-4923-bac9-56595a5142f9` "Proposed hero roles and farm priority, for
  teammates who read this". Our proposal of four jobs (burst killer, duelist, siege front,
  healer), a per-hero primary/secondary assignment, and a farm priority. We asked for
  pushback on four questions: whether funneling is right, lane assignment, a job for
  Warlock, and what other files' per-class branches do. **Commitment:** once the thread
  reaches rough agreement, post the agreed table as a comment. Record every amendment
  proposed by another entrant in `docs/roles.md` under "Public discussion", marked as
  theirs and unverified; if the lab adopts it, change the mapping table itself.
- `post_4e87805e-532c-419e-9818-1ac49d2b885f` James's earlier field note (posted by the
  "bismarck" agent under the James Boggs user identity). Dave's Codex asked there about a
  "no indefinite escort wait" convention. We may answer as the James Botts envoy if the
  lab's documents support an answer; otherwise leave it.

## Embargoed: never post

- The spell-scaling finding and everything derived from it: that abilities, items,
  footmen, towers, and rewards do not scale with level; the burst/transition/attrition
  phases; ultimates falling from a third to a tenth of an enemy; "spells fade". The
  public wiki's per-hero base and growth numbers and the kit tables are fine to cite;
  the lab's phase interpretation is not. The roles post was written to stay within
  public numbers; keep replies there too.
- Anything from `docs/scaling.md` or `docs/leveling-economy.md` beyond what the public
  wiki pages under `docs/wiki/` already state.
- The lab's policy source, its planned behaviors beyond what `docs/roles.md` publicly
  commits to, and any experience-request results James has not cleared.

## Where to record what the forum says

| Topic | Document |
| --- | --- |
| Role assignments, farm priority, lane conventions, coordination proposals | `docs/roles.md` ("Public discussion" section; the mapping table if adopted) |
| Claims about mechanics, numbers, or engine behavior | `TENTATIVE_LESSONS.md` as an entry marked "(forum claim)" with the post id, unless it contradicts a source-verified document, in which case add it to `state.json` `attention` for James rather than editing the document |
| Claims about the platform (team mode, credits, league rules) | `WORKING_CONTEXT.md` "Unresolved constraints" if it bears on the current objective; otherwise `attention` |
| Pact or alliance offers | `attention` only. Never accept or decline; James decides. |

## New posts

None authorized. Comments only.
