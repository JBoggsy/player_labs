# Game mechanics and resources

## References

| Resource | Use |
| --- | --- |
| [Game guide](wiki/game-guide.md) | Illustrated rules, hero kits, items and human controls |
| [Hero statistics](wiki/hero-statistics.md) | Base attributes, level scaling and attack ranges |
| [Policy host reference](wiki/policy-and-host-surface.md) | Complete host names, argument order and units |
| [Player standings](wiki/player-standings.md) | Finding and interpreting live league results |
| [Polyworld source](https://github.com/Metta-AI/polyworld) | Authoritative implementation and engine setup |
| [Polyworld Buff directory](https://metta-ai.github.io/polyworld-buff/) | Game presentations and interactive views |
| [Game wiki](https://softmax.com/gods-of-the-arena/wiki.md) | Public game reference |
| [Game forum](https://softmax.com/gods-of-the-arena/forum.md) | Community questions and strategy discussion; verify claims against code and gameplay |
| [Participation guide](https://softmax.com/api/observatory/v2/participate?league_id=league_3c60897b-25cf-4b37-9d1a-8554c1198f28) | Active league participation and runtime requirements |

## Choosing an optimization

1. Resolve the active league's game and match configuration, and select the owned
   policy to improve with the human.
2. Inspect complete games: objective progress, engagements, time-limit finishes,
   and differences between team/class assignments.
3. Join policy intent to accepted actions and actual impact. Validate replay and
   metric extraction against a complete episode before relying on an analysis adapter.
4. Agree one behavioral hypothesis with the human. Measure completed game outcomes
   separately from operational failures. Game-code inspection establishes mechanics;
   competitive improvement requires gameplay evidence.

## Documentation maintenance

Keep these pages and the public wiki as complete current references. Replace
superseded claims directly. Do not add audit reports, change narratives, version
logs, obsolete measurements or pointers to removed material. Source links should
lead readers to the implementation that defines the documented behavior.

The files in `docs/wiki/` contain the maintained wiki content. Before publishing,
read each page from the service, reconcile concurrent edits and verify the saved
body. Use the [community workflow](../../.claude/skills/coworld-community/SKILL.md)
with the session's authorization.
