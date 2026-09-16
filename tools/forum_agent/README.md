# Forum agent

A standing, unattended agent that keeps the lab's presence on one Coworld's forum
current: it answers and corrects in threads the lab is part of, honors public
commitments, and records what other entrants say back into the lab's documents. It is
headless Claude Code run on a timer in this repository, so it shares the interactive
sessions' CLAUDE.md, skills, memory directory, and lab documents.

It is built to be quiet. A run's default outcome is no write; the rules in
[`prompt.md`](prompt.md) list the only reasons it may comment (a direct question, a
correction, a commitment falling due, a proposal that needs an answer, new verified
evidence) and cap it at one comment per run. It never opens a new thread unless the
lab's brief authorizes that specific post.

## Pieces

| Path | What it is |
| --- | --- |
| `tools/forum_agent/prompt.md` | Game-agnostic operating rules: when to write, what never to post, the run procedure. |
| `tools/forum_agent/run.sh` | Runs one pass: `run.sh <lab brief>`. Restricts tools to the community CLI plus repository file edits. |
| `<lab>/forum_agent/brief.md` | The lab's brief: forum slug, expected identity, signature, owned threads, embargoes, which document each topic is recorded in, and any authorized new posts. |
| `<lab>/forum_agent/state.json` | The agent's memory between runs: seen post and comment ids, everything it wrote, open commitments, and an `attention` list for the human. Committed with the lab. |

The first lab using it is Gods of the Arena:
[`gods_of_the_arena_lab/forum_agent/`](../../gods_of_the_arena_lab/forum_agent/).

## Running

One pass by hand:

```sh
tools/forum_agent/run.sh gods_of_the_arena_lab/forum_agent/brief.md
```

On a timer, per lab, with a launchd agent (macOS). The Gods of the Arena one is
`~/Library/LaunchAgents/com.jamesboggs.forum-agent.gota.plist`, every 30 minutes,
logging to `~/Library/Logs/forum-agent/gota/`:

```sh
launchctl load ~/Library/LaunchAgents/com.jamesboggs.forum-agent.gota.plist    # install
launchctl start com.jamesboggs.forum-agent.gota                                 # run now
launchctl unload ~/Library/LaunchAgents/com.jamesboggs.forum-agent.gota.plist  # stop
tail -f ~/Library/Logs/forum-agent/gota/stdout.log
```

To add a lab: write its `forum_agent/brief.md` and an empty-ish `state.json`, copy the
plist with a new label, interval, brief path, and log directory, and load it.

## Operational notes

- **Identity.** The community CLI writes as the active player session
  (`uv run softmax status`). Player tokens last about a day; when the token is stale
  the agent makes no writes and adds a note to `state.json` under `attention`.
- **No commits.** The agent edits lab documents in place but never commits; review
  `git status` in the lab and commit at a normal checkpoint.
- **Embargoes.** Mechanics findings are proprietary by default (`user_preferences.md`);
  the brief lists what is cleared for public discussion.
- **Auth for Claude.** Headless runs use the same Claude Code login as the terminal.
