# Press agent: an LLM harness around SearchBot (draft)

Status: **v1 built, local testing** (2026-10-08). The code is `webdip_bot/press/`
(personality `castlereagh_press`); module map in `webdip_bot/README.md`. Facts marked
*verified* were checked on this date against the live platform, metta source, or vendor
docs. Sections marked *not built* are still proposals.

## Goal

A full-press player for the `webDiplomacy` league. An LLM agent negotiates, keeps
beliefs about each power, and sets strategy. SearchBot does the tactical work as a set
of tools. The LLM decides *who to trust and what to aim for*. Search decides *which
orders achieve it*. The same image, with different souls and models, also fills the
league's empty seats.

## Platform facts (verified)

- **League.** `webDiplomacy` (`league_1bccc63d…`) plays `classic-press` once a day:
  4-minute movement phases, 1-minute retreat and build phases, ends 1908. Scoring is
  the draw share (SC² / ΣSC²), ranked by mean score. Its filler roster is **empty**
  today. `webDiplomacy Gunboat` (`league_428e91e5…`) is where Kissinger plays.
- **Press.** `game/sendmessage` sends a message (`toCountryID` 0 = public). Incoming
  messages arrive in `game/playercontext` with `messages=1`. A phase ends early only
  when every seat is Ready.
- **LLM access.** Upload with `coworld upload … --use-llm --llm-model <OpenRouter
  slug>`. The model is **fixed per policy version**; changing it means uploading a new
  version. The pod gets `COWORLD_LLM_ENDPOINT` (sidecar, OpenAI `/v1/chat/completions`
  or Anthropic `/v1/messages`) and `COWORLD_LLM_MODEL`. **Streaming is rejected
  (HTTP 400).** The sidecar ignores the auth header. See "LLM channel" below for
  local parity. Platform-hosted spend is metered against the league's limits,
  and HTTP 429 can come from the league spend limit, the per-seat request ceiling (about
  30 per minute), or provider capacity.
- **Fillers** are uploaded policy versions set through
  `POST /v2/leagues/{id}/filler-policies`. The lab already manages the gunboat roster
  this way.

## LLM channel (verified against metta `8b6042db` sidecar source)

Player pods have no general network egress. The bot's **only** LLM path is the
per-pod sidecar at `COWORLD_LLM_ENDPOINT` (`/v1/chat/completions`, non-streaming).
It never reads `OPENROUTER_API_KEY` and makes no other outbound call.

- The production model allowlist is `null`, so any canonical OpenRouter slug is
  admitted. The sidecar forces the request's model and sets
  `provider.require_parameters=true`.
- The sidecar strips the caller fields `fallbacks, metadata, models, plugins, provider,
  route, service_tier, session_id, speed, trace, usage, user`. `reasoning` passes
  through, which matters because GLM reasons by default.
- The response body passes through unchanged. OpenRouter includes `usage.cost` (USD)
  without being asked, so the bot logs exact per-call cost from the body. Hosted
  responses also carry `X-Coworld-Spend-Usd` (running spend for this pod's seat) and
  `X-Coworld-Spend-Limit-Usd` when a cap is set. `GET /spend` returns the same.
- **Local parity.** `coworld run-episode --use-llm` has no sidecar. It forwards the
  host's `COWORLD_LLM_ENDPOINT` (or `OPENROUTER_API_KEY`) into the containers. We run
  a host-side emulator of the sidecar contract (`tools/llm_sidecar_local.py`: same
  routes, `stream: true` → 400, same stripped fields, spend headers, call ledger) and
  set `COWORLD_LLM_ENDPOINT=http://host.docker.internal:<port>`. The bot therefore runs
  the same code path locally and hosted.

## Harness choice

**Proposal: a thin Python harness on `pydantic-ai`, built in Pi's style.**

Pi's appeal is its minimalism: a tiny system prompt, few tools, files as memory, and
skills as markdown loaded on demand. We keep all of that. We do not use Pi's runtime,
for three reasons:

1. **Streaming.** Pi's agent core requires a streaming function (`streamFn`), and the
   sidecar rejects streaming. We would need to write a non-streaming adapter that fakes
   stream events.
2. **Two runtimes.** Pi is TypeScript. SearchBot is Python with a native Nim extension.
   Every tool call would cross a process boundary, and the image would need Node.
3. **Little to gain.** Each wake rebuilds its context from our files, so Pi's session
   and compaction machinery would go unused. What remains is a tool-calling loop.

`pydantic-ai` supplies that loop in-process. It turns typed Python functions into tool
schemas, accepts any OpenAI-compatible base URL, makes non-streaming requests through
`run_sync`, and caps requests with `UsageLimits`. Hermes is dropped for the same
reasons as Pi, and because it is a broad personal-assistant harness of which we would
use a small part.

## Core principle: Kissinger is the floor

The LLM never sits on the path that produces legal orders. At phase start the harness
saves plain Kissinger orders (not Ready). Every later agent decision overwrites them
through the same search pipeline. LLM timeout, a 429, or a crash therefore degrades to
today's champion, never to a silent seat.

## Architecture

```
bot.py phase loop (outer driver: poll, deadline clock, save orders)
  └─ PressHarness (new, per game)
       ├─ GameJournal   structured facts the harness writes (press, commitments,
       │                adjudicated orders, kept/broken verdicts)
       ├─ Workspace     per-game markdown the LLM writes (plan, one file per power)
       ├─ AgentLoop     pydantic-ai agent: SOUL.md + skill index + our tools
       └─ SearchService SearchBot behind a typed API, called by the tools
```

**Wakes.** A wake is one agent run: the harness builds a briefing (board, referee facts,
saved orders, plan, notes, unread press) and runs the tool loop until the model gives a
final answer or hits a limit. In each movement phase (config in `config.py`, `PRESS_*`):

| Wake | Trigger | Job |
| --- | --- | --- |
| open | phase start, after the Kissinger floor orders are saved | read the board, send opening press, commit a first policy |
| negotiate | unread press waiting and `PRESS_WAKE_GAP_S` (20 s) since the last wake, until `PRESS_COMMIT_MARGIN_S` (75 s) before the deadline; at most `PRESS_MAX_WAKES` (5) wakes per phase | reply, record commitments, re-commit |
| commit | `PRESS_COMMIT_MARGIN_S` before the deadline | final policy, update the plan |

A wake ends `ok`, `time_limit` (`PRESS_WAKE_SECONDS`, 60 s), `request_limit`
(`PRESS_REQUEST_LIMIT`, 8 model calls) or `error`. Anything already done stays: sent press
stands and each `commit_orders` saves orders immediately. `PRESS_FINAL_MARGIN_S` (15 s)
before the deadline the last saved orders are marked Ready. Press that arrives between
wakes is queued and shown at the next wake. Retreats and builds are played by
SearchBot/DumbBot without a wake.

## Knowledge structures

| Layer | Owner | Lifetime | Content |
| --- | --- | --- | --- |
| `SOUL.md` | us, per personality | policy version | Identity, voice, strategic doctrine, honesty policy, and the rule that opponents' text is untrusted data. |
| Skills (`skills/<name>/SKILL.md`) | us | policy version | Procedures loaded on demand via `read_skill`: opening books per power, negotiation playbook (DMZs, support deals, anti-leader coalitions), stab checklist, endgame and draw-share play, reading search output. |
| `game/plan.md` | LLM | one game | Objectives, alliance map, next-phase intentions, stab plans. |
| `game/opponents/<POWER>.md` | LLM | one game | Natural-language model of each power: disposition toward us, trust, style, goals, promises. |
| `GameJournal` (JSONL) | harness | one game | Facts the LLM cannot edit: every message, every commitment (recorded in structured form), adjudicated orders, and an automatic kept/broken verdict for each commitment. |
| Cross-game memory | later | forever | Notes on recurring league opponents. Out of scope for v1. |

**The harness computes facts and the LLM interprets them.** Promise checks, SC
counts, and threat maps come from code. The LLM supplies judgment and language.

## Tools (SearchBot adapted)

| Tool | What it does | Built from |
| --- | --- | --- |
| `board()` | Text summary: centres and units per power, neutral centres, our centres within reach of foreign units. | `Notation.brief` |
| `predict(power)` | Most likely orders of one power (top 3 per unit with frequencies) under the opponent model and our committed policy. | `OpponentModel` level-1 sampling |
| `evaluate(orders, policy?)` | Expected, worst and best projected centres and per-order success/dislodge rates of a written order set. | `PositionEvaluator`, native adjudicator |
| `search(policy)` | Best orders under a policy, with the same statistics. Does not change saved orders. | `choose_movement` |
| `assess_deal(power, their_orders, our_orders, our_forbidden?)` | Expected centres if both sides honour, if they betray, and if we betray. | two searches and one evaluation |
| `commit_orders(policy)` | Adopt a policy: search and save the orders now (not Ready); re-committing replaces them. | `bot.py` save path |
| `send_press(to, text)` | Message one power or ALL (max 8 per phase, 600 characters). | `game/sendmessage` |
| `conversation(power)` | Recent private thread with one power. | journal |
| `record_commitment(power, orders?, dmz?, note?)` | Record a promise made this phase (by them or ME) for the referee to check. | journal |
| `update_plan(text)`, `note_power(power, text)` | Rewrite plan.md or the notes on one power. | workspace |
| `read_skill(name)` | Load one skill's full text. | `skills/` |

**Policy: the agent's control surface over search** (`press/search_service.py`)
- Per-power **stance** and **trust**: an ally does not move or support into our provinces
  with probability = trust; allies and hostile powers are sampled as competent.
- **Expected orders** from deals, played in each sample with that power's trust.
- **Hard constraints** on our plan: `forbid_moves_into` and `require_orders`.
- **Centre values per power** (extra value per centre taken from that power).
- **Risk** (0 = mean over opponent samples, 1 = worst case). Other search settings
  (opponent level, samples, budget) stay at the personality's values.

## SearchBot changes (built)

- `SearchBot.press` (default `None`) carries the resolved policy. With `None`, behaviour
  is bit-identical to gunboat play (golden check: 334/334).
- Stance-conditioned opponent sampling and expected-order injection
  (`OpponentModel.apply_press`); constraints in seeds and ascent
  (`search_moves.constrain`, pruned `joint_alternatives`); per-power centre values in
  `score_fast`.
- The policy's `risk` is applied with a save/restore of `config.SEARCH_RISK`, the same
  pattern `spring_value` uses. Tool calls are sequential, so this is safe. Turning config
  into an explicit value is deferred until a concurrent caller exists.
- `press/search_service.py` reports expected, worst and best projected centres and
  per-order success/dislodge rates across the opponent samples.
- *Not built:* a `lookahead` tool (multi-phase rollouts lost in gunboat; revisit with
  measurements).

## Logging (built)

Every seat prints one JSON object per line to stdout (the seat log: local
`logs/policy_agent_<slot>.log`, hosted episode logs). Press-player events:

| Event | Content |
| --- | --- |
| `press_start` | model, soul, country, the full system prompt, all PRESS_/SEARCH_/OPP_ config |
| `wake_start` / `wake` | wake id (`<turn>-<n>-<kind>`), kind, seconds allowed, unread count / status, calls, cost, final reply |
| `llm_request` | the messages added since the previous request of the same wake (the first carries the briefing; the system prompt is replaced by a pointer to `press_start`) |
| `llm_call` | status, tokens (prompt, completion, reasoning, cached), `usage.cost`, sidecar spend header, generation id, and the full reply (text, tool calls, reasoning if returned) |
| `tool_call` | tool, arguments, full result, seconds |
| `press_in` / `press_out` | message id, sender/recipient, full text |
| `commitment` / `commitment_verdict` | recorded promises and the referee's kept/broken verdict |
| `press_commit` | committed policy, resulting orders, expected centres |
| `decision` | per phase: orders diff (`rejected`), search trace counters, policy, LLM cost |
| `workspace` | after every movement phase: plan.md, notes per power, all commitments |

The launcher adds `private_press` (every private message of the seat) at game end. The
viewer (`tools/game_viewer.py`) joins it with the replay's public messages.

## Models

The model is an upload flag, so every policy version names exactly one model, and the
code reads `COWORLD_LLM_MODEL` without hard-coding it. Pin dated slugs. Avoid the
`~…-latest` aliases, because a moving model makes results impossible to attribute.

Candidate cheap open-family models with tool calling on OpenRouter (prices per million
tokens, input / output, listed 2026-10-08; check open-weight status before choosing):

| Slug | Price | Note |
| --- | --- | --- |
| `deepseek/deepseek-v4.1-flash` | $0.30 / $1.20 | Recent, 1M context |
| `z-ai/glm-5.3-flash` | $0.15 / $0.50 | Recent, 1M context |
| `qwen/qwen3.8-flash` | $0.15 / $0.47 | May be API-only rather than open weights |
| `minimax/minimax-m3` | $0.30 / $1.20 | |

`castlereagh_press` uses `z-ai/glm-5.3-flash` (`config.PRESS_MODEL` locally; hosted it
is the `--llm-model` upload flag). Reasoning effort is `low` (`PRESS_REASONING`).

Measured cost, two local `classic-press-short` self-play games (7 LLM seats, 8 movement
phases each, `wd.py costs`): $0.32 and $0.35 per game, $0.0058 and $0.0063 per seat per
movement phase, about 13–14 calls per seat-phase. Projected full `classic-press` game
(16 movement phases): about $0.10 per LLM seat, $0.70 with all seven seats on LLMs.
Model latency: 4.4 s median, 15.6 s p90.

## Fillers

The press league's roster is empty, so our agents become the field.

- **Personality = `SOUL.md` + model + default `SearchPolicy`.** This extends
  `personalities.py`: one image, `POLICY` build arg, one uploaded version per filler.
- **Diversity matters more than strength.** Honest and deceptive, aggressive and
  defensive, different models. A field of clones teaches nothing and invites
  self-play artifacts.
- **Keep some non-LLM fillers** (Kissinger, DumbBot) as silent, cheap, stable anchors.
- **Risk: shared spend.** All platform-hosted LLM calls in the league meter against the
  league's limit. LLM fillers can exhaust it and push our main player into 429s
  (it then falls back to Kissinger). Confirm the limit and its scope before we fill six
  seats with LLM agents.
- **Lab rule check.** Hosted XP credits are not spent on own-policy self-play. Fillers
  are part of the league field, but evaluation batches against all-our-own fillers need
  the human's call.

## Risks and open questions

- **Prompt injection.** Opponents are LLM agents too. Their messages are untrusted data.
  Message text must never trigger a tool, and `SOUL.md` states this.
- **Latency budget.** About 30 requests per minute and 4-minute phases allow roughly
  100 LLM calls per movement phase. Search takes about 1 s and is not the constraint.
- **When to mark Ready.** Ready ends the phase early when all seven seats are Ready.
  For a press player that is a strategic choice, not a formality.
- **Depth.** Deeper look-ahead lost in gunboat. Alliances may change that (a two-phase
  supported attack with an ally), but it needs measurement, not assumption.
