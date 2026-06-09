# Getting started

A guided, one-time onboarding into the lab. **You're the coding agent, and you're
setting your user up** — work through these steps *with* them: do the mechanical parts
yourself, and for anything that needs the human (signing in, choosing a direction),
explain it in plain language and hand it over. Before each step, say what you're about
to do and why, so they stay oriented.

> **Run everything from the repo root.** All paths below are written relative to the
> project root (where you're operating) — `crewrift_lab/…`, not `../…`.

By the end your user will be authenticated, will have chosen a player policy to work on,
will have a first read on how it's doing, and will have made and measured a first
improvement to it — at which point you're in the ongoing improvement loop. The full
operating model for that loop is in `AGENTS.md`.

---

## Step 1 — Authenticate to Softmax

**Goal:** get your user signed in to the Observatory API so the lab can run evaluations
and (later) upload policies on their behalf.

**First, set up the environment** (this also makes the `softmax`/`coworld` CLIs
available — safe to run, no interaction):

```sh
uv sync
```

Optionally confirm the install is healthy: `uv run pytest crewrift_lab/crewrift/crewborg/tests`
should pass.

**Then explain the sign-in and hand it to your user.** This is a browser login — *you
can't do it for them* — so tell them what it is and let them run it. Say something like:

> This lab plays on **Softmax Observatory** — the platform that runs the Coworld
> competitive leagues (where player policies face off) and serves the replays, results,
> and standings we'll analyze. To run evaluations or upload a policy, you need to sign
> in once; it's a quick browser login and the token is cached locally. I can't do it
> for you, so could you run this — the `!` lets it run right here so I can see when it's
> done:
>
> ```
> ! uv run softmax login
> ```
>
> It'll open your browser to sign in. (On a remote/headless box with no browser, use
> `! uv run softmax login --no-browser` and open the URL it prints.)

**Then verify it yourself and confirm the account with them:**

```sh
uv run softmax status
```

Expect `Authenticated` plus a `user_email`. **Show that email to your user** and check
it's the account they meant to use — if not, they can switch with
`uv run softmax login --force`. If it says *not* authenticated, the browser step didn't
complete; walk them through it again.

*(Already authenticated from a prior session? `softmax status` will say so — confirm the
account and move on.)*

---

## Step 2 — Pick the player you'll work on

**Goal:** have your user choose which of the lab's three Crewrift policies to start
improving — then record that choice so every future session resumes on the same one.

**Present the three options and let them choose.** Relay something like:

> This lab ships three Crewrift players you can build on. Which would you like to start
> working on?
>
> - **crewborg** *(Python — recommended)* — the full, mature agent: it reads the scene,
>   tracks who it suspects, picks a behavior mode, and acts, for both crewmate and
>   imposter. It has the most to improve and the richest tracing, and the lab's analysis
>   tools (report / diagnose / A‑B) are built around it. The best default — especially
>   since it's Python with well-documented internals.
> - **notsus** *(Nim)* — the minimal reference bot: the smallest complete "decode the
>   screen, move, press A" implementation. Pick this if you'd rather understand the game
>   from the ground up or grow a simple player yourself. It's deliberately weak — the
>   baseline everyone compares against.
> - **suspectra** *(Nim + a meeting LLM)* — notsus plus a bounded LLM that does
>   evidence-based voting in meetings. Pick this if you're most drawn to the
>   social-deduction / LLM-reasoning side (prompts, vote decisions).
>
> You can switch later — this just sets where we begin.

Pose it as a real choice — use the `AskUserQuestion` tool (or just ask plainly) and wait
for their answer. If they're unsure, recommend **crewborg** (most to optimize, Python,
best tool support).

**Then record their choice so it persists across sessions.** Append it to
`crewrift_lab/user_preferences.md` under a **Working context** heading, e.g.:

```markdown
## Working context
- **Active policy under optimization: `crewborg`** (chosen <today's date>). Future
  sessions: continue improving this policy unless the user says otherwise.
```

`crewrift_lab/AGENTS.md` has every session read `crewrift_lab/user_preferences.md` on
startup (it's the Crewrift-specific preferences file), so a future agent will pick this
up and **keep working on the policy you chose together** — no re-asking.

The three players live under `crewrift_lab/crewrift/` and all build with
`crewrift_lab/tools/build_player.sh <policy>` (Docker only, no credentials). For deeper
per-policy detail, see the player-policies index in `crewrift_lab/AGENTS.md`.

---

## Step 3 — Your first evaluation

**Goal:** get a real, *current* read on how the chosen policy is doing — by building it,
uploading it, running a batch of live evaluation games, and distilling the results into
strengths, weaknesses, and hypotheses that point at your first improvement.

**Give your user the overview *before* you start anything,** so they know the shape of
what's coming. Say something like:

> Here's the plan for our first evaluation:
> 1. I'll **build `<policy>` exactly as it stands now** into an uploadable image and
>    **upload it as a new version** — but **not** submit it to a league. Uploading is
>    routine and just gives us a version we can test; submitting is the public,
>    hard-to-undo step we'll save for when it's clearly better.
> 2. I'll run an **experience request** — Softmax's feature for running a whole batch of
>    episodes in parallel, against opponents and matchups *we* design. It lets us test
>    against strong players *right now* instead of waiting for league rounds to come
>    around.
> 3. Once those games run, I'll **monitor them to completion, pull the results, and
>    distill the high-signal bits** — a role-split report plus some mechanistic
>    diagnoses — so we can see where it's strong and weak and choose our first
>    improvement together.

Then work through the three parts below. **As you do each one, tell the user what
you're doing and why** — keep them oriented rather than going quiet and reappearing with
results.

### 3a — Name it, then build and upload (not submit)
First, make it theirs — before you build, ask the user what to call their policy. Relay
something like:

> Before I build, what do you want to name your policy? This is *your* version, so pick
> whatever you like — a codename, a pun, your handle. I'll upload it under that name so
> it's easy to spot among all the stock players.

Use their answer as `<your-policy-name>`. Then build the chosen policy as it stands and
upload it as their version:

```sh
crewrift_lab/tools/build_player.sh <policy>          # → players-<policy>:dev (linux/amd64)
uv run coworld upload-policy players-<policy>:dev --name <your-policy-name>
```

This creates a **testable version that is not in any league** — distinct from the stock
policy others are running. (Upload mechanics and the upload-vs-submit gate: the
**`coworld-policy-lifecycle`** skill.)

### 3b — Run the evaluation (experience request)
Using the **`coworld-experience-requests`** skill, resolve the version you just uploaded
plus a strong opponent roster, compose the batch, and create it. Tell the user what's
being measured — relay something like:

> I'm kicking off the evaluation now: a batch of games pitting our `<policy>` version
> against a strong roster of current players, across both crewmate and imposter roles so
> we get a read on each side. Softmax runs all those episodes in parallel, so we'll have
> real results shortly instead of waiting for league rounds.

### 3c — Monitor, download, distill, and present
This is the part where **keeping the user posted matters most** — the games take a
while, so don't go silent. Walk them through it:

- **Monitor** the request to completion (the `coworld-experience-requests` skill). This
  takes a bit, so let the user know it's running and that you're watching it — they
  should never wonder whether you've stalled.
- **Announce when it finishes** and tell them you're now **downloading** the results —
  pull the finished episodes into one directory (the **`coworld-episode-artifacts`** skill).
- **Distill:** tell them you're analyzing the games, then run **`crewrift-report`** for
  the role-split strengths/weaknesses + the interesting episodes, and **`crewrift-diagnose`**
  to turn those signals into evidence-grounded, mechanistic improvement hypotheses.
- **Present it to your user:** where the policy is strong vs. weak and the candidate
  hypotheses — the raw material you'll choose a first improvement from in Step 4.
- **Show them a replay.** Watching the games is half the point and it pulls the user
  in, so make sure they know they can watch any episode themselves. Offer a few picks —
  the most interesting matches from the report (a clutch imposter round, a botched
  crewmate vote, whatever stood out) — and let them choose one of yours or name their
  own. When they pick, open it the easy way: `coworld replay-open <episode_request_id>
  --hosted` prints an **Observatory-served viewer URL** (no local Docker, no extra
  download) — **hand them that URL to watch.** The `<episode_request_id>` is each
  episode's `ref_id`, recorded in the `index.json` the artifact download wrote, so you
  can map a report finding straight to its id. (Full replay mechanics, including the
  local-Docker viewer: `crewrift_lab/docs/crewrift-replays.md`.)

---

## Step 4 — Your first improvement

**Goal:** turn that read on the policy into **one** concrete change, measure whether it
actually helped, and decide whether to submit or keep going. This is the core of the
improvement loop — by the end of it you're self-sufficient.

**Ask the user for a direction.** They've now watched a replay or two and read your
hypotheses, so put the choice to them. Relay something like:

> Okay — now that you've seen it play and read through my hypotheses, where do you want
> to take it? You can run with one of the hypotheses I flagged, or point me at something
> *you* noticed watching the replays. What should we try to improve first?

Use the `AskUserQuestion` tool — offer **your generated hypotheses as options**, plus
room for their own idea. Pick **one** change and commit to it; resist bundling several
"while we're in here" tweaks, or you won't know what moved the needle.

**Make the change.** Edit the chosen policy's code — one focused change aimed at the
hypothesis. Narrate what you're changing and why you expect it to help.

**Rebuild, then smoke-test locally (Gate 1).** First rebuild the image so your change is
actually in it — `crewrift_lab/tools/build_player.sh <policy>`. Then run the
**`coworld-local-run`** skill on that freshly built image: it's the Gate-1 smoke test —
confirm the policy still **connects → plays → exits cleanly** before you spend
evaluation budget. (The skill expects an already-built local image — it smoke-tests, it
doesn't build — and runs your image in every slot in a short local game; it's a
correctness/liveness check, not a competitive one, so a score of 0 in that fixture is
fine.) This is the *same* image you upload next, so you build once, here. If the smoke
test fails, fix the change and rebuild before going further — don't upload or spend
evaluation budget on a broken build. **First run heads-up:** the smoke test pulls the
game's Docker image, which can take a few minutes — tell the user it's downloading the
game and isn't stuck; it's cached after that.

**Upload and re-measure.** Upload the rebuilt image as a new version
(**`coworld-policy-lifecycle`**), then re-evaluate — ideally **head-to-head against the
previous version with `crewrift-ab`**, so you isolate whether *this* change is what
helped rather than roster noise.

**Back to the user — submit or iterate?** Present the result (did it help, by how much,
split by role), then hand them the decision. Relay something like:

> Here's how the change did: *[the delta]*. From here we can **submit** this version as a
> league entry — that's the public, hard-to-undo step, so it's your call — or **keep
> iterating**: pick another direction and go again. What do you want to do?

**That's the loop.** You're now self-sustaining: pick a direction → change one thing →
rebuild → smoke-test → upload → re-measure with `crewrift-ab` → submit only when it's
clearly better. The full operating model — the loop and its two gates — lives in
`AGENTS.md`; from here, work from there.
</content>
