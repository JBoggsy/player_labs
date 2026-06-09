# Starter prompt

A copy-paste prompt to hand to a **new user's coding agent** so it clones this repo and
walks them through onboarding. Share it however you like (chat, docs, a webpage); the
user pastes it to their agent as their first message — they don't need the repo yet.

The prompt front-loads a plain-language description of the lab (so the agent can answer
questions *before* cloning), hands the agent the guide role, and points it at
[`getting-started.md`](getting-started.md) to follow start to finish.

---

```text
Help me get started with player_labs, a hands-on lab for improving AI agents that
compete in Coworld's game leagues. Act as my guide, not just a coding agent — this
onboarding is part of the experience, not a normal coding task. Explain what's happening
in plain prose, use what you learn about me to pitch the level of detail right, and
narrate as you go instead of working silently. Do the mechanical work yourself; whenever
you need me (signing in, making a choice), explain it and hand it over. Be especially
clear when a step sounds bigger than it is — for example, uploading my policy for
evaluation is routine and is NOT submitting it to a league.

First, so you can answer my questions before we dive in — here's what this is:
player_labs is a human-in-the-loop lab for making Coworld game-playing agents better.
Coworld (Softmax's Observatory) runs competitive AI leagues, and the loop here is
simple: evaluate a player, find where it's weak, make one focused improvement, and
measure whether it actually helped — then repeat. It currently focuses on Crewrift, a
social-deduction game (think Among Us), and ships three starter players to choose from.
You'll do the building and measuring; I set the direction. It just needs `uv` and
Docker — no accounts or extra setup before we start.

Then walk me through it:
  1. Clone it and go in:
     git clone https://github.com/Metta-AI/player_labs && cd player_labs
  2. Open docs/getting-started.md and read it — it's a step-by-step onboarding script
     written for you, the coding agent.
  3. Follow that guide with me start to finish: authenticate, help me pick a player to
     work on, run a first evaluation, and make a first improvement. Narrate as you go so
     I always know what's happening and why.

Let's start.
```
