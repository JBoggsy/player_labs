# Design: the strategy file format

> **Status:** accepted 2026-09-30 (James). Not implemented yet: `strategy/STRATEGY.md`, telemetry
> v2, and the `pw.py strategy` commands do not exist. The implementation plan is in
> [the compilation design](2026-09-30-strategy-compilation.md) §11. Rendered, commentable copy:
> [2026-09-30-strategy-file-format.html](2026-09-30-strategy-file-format.html) (may lag this file;
> this Markdown file is authoritative).
>
> **Companion:** [2026-09-30-strategy-compilation.md](2026-09-30-strategy-compilation.md) defines
> the compile process (driver, agent, build layout, versioning, report, gates). Where the two
> documents overlap, the compilation design is authoritative for the process and this document
> for the source format.

## For agents: read this first

- **What this defines:** the format of the policy source, `strategy/STRATEGY.md` (plus
  `strategy/skills/` and `strategy/comms.md`), the five-level checks every component carries, and
  telemetry v2, the logs those checks read.
- **Read it when:** you write or edit `STRATEGY.md`, write a compiler, linter, or auditor for it,
  or add telemetry.
- **Words:** MUST and MUST NOT are requirements. "Can" is a permission. Everything else describes.
- **The invariants** (each is explained in the section named):
  1. `STRATEGY.md`, `skills/*/skill.bas`, `comms.md`, and `compiler/runtime/` are the source.
     Compiled output MUST NOT be edited by hand (§1).
  2. The compiler MUST NOT edit the source. Its guesses go into its report (§1).
  3. A component MUST refer only to layers below it, except the stated side-section
     exceptions (§3).
  4. Every component MUST have `Summary`, `Spec`, `Checks` (except Primitives), and `Status` (§4.3).
  5. The compiler implements `Spec` and nothing else. `Rationale` is never compiled (§4.3).
  6. Learned numbers MUST live in the owning component's `Params`, with the reason for the value
     (§4.3).
  7. Prose in `STRATEGY.md` and `skill.md` MUST be ASD-STE100 Simplified Technical English (§4.8).
  8. A check that the logs cannot compute reports `unmeasurable`. It never passes by default (§5).
  9. Every per-tick print MUST stay at or below half of the engine's print limits (§6).

## Glossary

| Term | Meaning |
| --- | --- |
| cog, seat | One player body; seats 0-15, even seats are team 0 (Red), odd seats team 1 (Blue). |
| tick | One engine step; 24 ticks = 1 second. The script runs once per tick per living cog. |
| WU | Work units, the engine's per-tick cost budget (125,000), separate from instructions (50,000). |
| component | One `###` entry in `STRATEGY.md` with an ID such as `K.enemy_contacts`. |
| unit | The BASIC file compiled from one component (compilation design §5). |
| build | One compiled output directory with its `version.json` and report. |
| edit loop | People and an LLM changing the source. |
| compile loop | The driver and compiler agent that turn the source into a build. |

## 1. The load-bearing rule

**The strategy file is the source of truth for our Paintbot PW policy. The compiled BASIC
script is a build product.**

- We design, discuss, and change the policy by editing the strategy file.
- A separate compile step (an LLM agent) turns the strategy file into a `.bas` script.
- Nobody edits the compiled `.bas` by hand. To change behavior, change the source and
  recompile.
- **The compiler never edits the strategy file.** Every guess it makes and every gap it fills
  goes into a separate, versioned compile report that is linked to the policy version. The edit
  loop reads the report and decides whether to promote a guess into the strategy file.
- Every compiled script is traceable to the exact source that produced it (section 8).
- Two other kinds of authored source are copied into builds unchanged: `strategy/comms.md`
  defines the comms policy, and `strategy/compiler/runtime/` holds the hand-written runtime
  library (the per-tick skeleton, telemetry print routines, and comms codec; compilation design
  §4.1).

There is one kind of authored BASIC: **skill code** (section 4.1). Each Skill has a
`skill.bas` file that we write and improve directly, because improving mechanics is more
productive in code than in prose. `skill.bas` is source, not output: the compiler copies it into
the build unchanged and never regenerates it. The rule above still holds without exception for
the compiled `.bas`.

This rule must be visible at every level: a banner at the top of the strategy file, a
"generated, do not edit" header in every compiled `.bas`, a line in the lab `AGENTS.md`, and the
lab `WORKING_CONTEXT.md`.

We use plain BASIC. The neural lane and the `jev.bas` oracle lane are out of scope.

## 2. Goals and non-goals

Goals:

- **One readable specification** that says what our agent knows, what situations it
  recognizes, what it can do, how it chooses, how it adapts, and what it tells teammates.
- **Machine-usable.** A compiler agent can find every component, resolve every reference, and
  report what it could not compile. A script can lint it.
- **Modular.** One component maps to one named unit of BASIC. When a component changes, the
  compiler knows which unit to change, and nothing else changes. A Skill or Capability can be
  practiced and improved on its own, touching other code only where the improvement needs it.
- **Checkable against replays** at five levels (section 5): was it true, did the agent believe
  it, did the agent act, did it act properly, and was the result what we expected.
- **Traceable** both ways: from a component to its BASIC, and from a replay (via telemetry) back
  to the component, rule, and beliefs that were active.

Non-goals:

- A general behavior-tree or planning language. The file describes one policy for one game.
- Exact executable semantics. Components are precise technical prose, not code. Precision comes
  from numbers in `Spec` and `Params`, and from the compiler reporting what was unclear.

## 3. Structure: six layers and two side sections

The file has six layers, bottom to top, and two side sections after them. A layer can refer only
to layers below it. The side sections have the specific exceptions stated in their rows.

| Section | Prefix | What it is | Can refer to | Paintbot PW examples |
| --- | --- | --- | --- | --- |
| Primitives | `P.` | What the engine already does. **Listed, not authored.** | — | `walkTo`, `lookAt`, `shootAt`, `chargeGrenade`, `sneak`, `shout` ([policy-surface §5.6-5.7](../policy-surface.md)) |
| Knowledge | `K.` | What the agent knows at runtime: direct reads from the host, plus beliefs and memory built from them. | `P.`, and `COM.` messages as a source | visible enemies and their motion; remembered pickups; heart ownership; team lives lead; last-heard gunfire sector |
| Situations | `S.` | Named states of the world, defined over Knowledge. | `K.` | outnumbered near our heart; enemy capturing a heart we own; ahead on lives late in the match |
| Skills | `SK.` | Motor skills: parameterized chains of primitives that we must execute better than other bots. No goals of their own. | `P.`, `K.`, `S.` | move-and-shoot (strafe legs timed to gun windup); lead aim; grenade throw at range; dry routing around water |
| Capabilities | `C.` | Tactical sub-objectives, built from Skills, each with success and abort conditions. | `K.`, `S.`, `SK.` | push to heart, hold heart, attack heart, retreat to heart, grab supply, snatch glory heart |
| Strategy | `ST.` / `R.` | Roles, the prioritized rules (`R.`) from Situation to Capability, and commitment. | all layers above | "two cogs per squad capture, two cover"; "when ahead on lives after 5:00, hunt instead of capture" |
| Adaptations | `A.` | Rules that change rule priorities during a match. | `K.`, `S.`, and `R.` rules (priorities only) | "if our pushes to the far heart fail 3 times, lower `R.push_far` by 20" |
| Communication | `COM.` | Messages we send and understand: content, encoding, when sent, and which Knowledge a heard message updates. A parallel track to the main decision. | everything (the send side reads this tick's decision) | "announce my target heart"; "report enemy count at my heart" |

Why Skills and Capabilities are separate: Skills hold mechanical quality (aim, footwork,
timing) and are reused by many Capabilities. Capabilities hold tactical intent. We can improve
"move and shoot" once and every fighting capability benefits, and we can A/B a tactic without
touching mechanics.

Why Situations are separate from Strategy: several rules can use the same situation, and a
situation is a claim about the world that we can check against replays. A rule is a choice that
we can A/B.

Why Adaptations and Communication are side sections, not layers: an Adaptation must name the
rules it changes, so it comes after Strategy. Communication runs on both ends of the tick: heard
messages become Knowledge before the decision, and outgoing messages report the decision after
it. Keeping both outside the stack keeps the stack's downward-only rule simple, and the linter
checks the two stated exceptions.

### Per-tick order (the compiler must follow it)

The engine runs the script from the top every tick; only globals and arrays persist
([policy-surface §3](../policy-surface.md)). Each tick:

1. Decode heard messages (`COM.` receive side) and update Knowledge (`K.`).
2. Evaluate every Situation (`S.`) once, into flags.
3. Apply Adaptations (`A.`) to rule priorities.
4. Select the rule (`R.`): highest current priority whose condition holds, subject to
   `ST.commitment`.
5. Run the selected Capability (`C.`), which calls Skills (`SK.`), which call primitives.
6. Send messages (`COM.` send side).
7. Write telemetry (section 6).

## 4. Format: structured Markdown in Simplified Technical English

**One Markdown file with a fixed heading scheme, stable IDs, and a fixed set of labeled fields
per component.** Not JSON, YAML, or XML (the comparison is in section 11).

### 4.1 File layout (source side)

```text
paintbot_pw_lab/strategy/
  STRATEGY.md                  # the source of truth (this format)
  comms.md                     # comms policy: message types, wire format, send rules
  skills/<skill_name>/
    skill.md                   # optional: the full Skill spec, linked from STRATEGY.md
    skill.bas                  # authored skill code (source, not output)
  compiler/                    # compiler instructions, lessons, runtime library (compilation design §5)
  compiled/<build-id>/         # build output, never hand-edited (compilation design §5)
```

One `STRATEGY.md` for now. Any section can link out to a per-section file when it grows.
Every Skill has a directory from the start, because every Skill has its own code.

### 4.2 Headings and IDs

```markdown
# Strategy: <policy name>
<load-bearing banner, thesis, version>

## Primitives
## Knowledge
### K.enemy_contacts
## Situations
### S.outnumbered
## Skills
### SK.move_and_shoot
## Capabilities
### C.hold_heart
## Strategy
### ST.roles
### ST.rules
### ST.commitment
## Adaptations
### A.demote_failed_push
## Communication
### COM.target_heart
## Open questions
```

- Every component is a level-3 heading whose text is its ID: prefix plus `snake_case` name.
- Rules inside `ST.rules` have their own IDs (`R.<name>`), so logs, checks, and Adaptations can
  name them.
- IDs are stable. Renaming an ID is a deliberate change that the linter reports.
- A reference is the bare ID in backticks (`` `S.outnumbered` ``). The linter resolves it.

### 4.3 Fields

Each component is a heading, then a bullet list of labeled fields, then optional prose. Fields
marked * are required.

| Field | Used by | Meaning |
| --- | --- | --- |
| `Summary`* | all | One sentence. |
| `Spec`* | all | What the compiler must implement. Precise: distances, ticks, order. |
| `Sources` | K | Host reads it uses (`playerX`, `controlOwner`, `heardX` ...) and `COM.` messages that update it. |
| `Memory` | K | What persists across ticks and for how long. |
| `Log` | K | The belief values telemetry records, and how often (section 6). Required if the component has a `Believed` check. |
| `Uses` | S, SK, C, R, A, COM | IDs of components it depends on. |
| `Params` | S, SK, C, R, A | Named numbers: value, units, range `[min, max, step]` if tunable, and **why this value** (hand-set, or tuned, with a link to the tune run). |
| `Code` | SK | Path to `skill.bas`. |
| `Done when` / `Abort when` | C | Success condition; conditions that give control back to Strategy. Each has a stable name, so telemetry can say which one fired. |
| `Checks`* | all but P | The five-level checks (section 5). |
| `Evidence` | all | Links: TENTATIVE_LESSONS, reports, A/B results, tune runs. |
| `Status`* | all | `idea`, `specified`, `compiled`, `tested`, or `proven`, with date. |
| `Rationale` | all | Why. For people and the edit loop. **The compiler does not implement rationale.** |

**Learned constants live in `Params`** of the component that uses them ("lead a moving target
by `lead_ticks` = 6"), not in Knowledge. Knowledge is what the agent learns about the world while
it plays. When the tuning loop finds a better value, the edit loop writes the new value into
`Params` with an `Evidence` link to the tune run; otherwise the next recompile loses it.

### 4.4 Strategy: rules with priorities

`ST.rules` is a list of rules. Each rule has an ID and a default priority (0-1000). Each tick
the rule with the **highest current priority whose condition holds** wins. File order breaks
ties.

```markdown
### ST.rules
- `R.dump_grenade` [900]: WHEN `S.about_to_die_with_charge` DO `C.dump_grenade`
- `R.retreat` [700]: WHEN `S.outnumbered` AND NOT `S.on_owned_heart` DO `C.retreat_to_heart`(toward=nearest_friend)
- `R.defend` [600]: WHEN `S.enemy_capturing_our_heart` DO `C.attack_heart`(heart=that_heart) FOR role=cover
- `R.hunt` [400]: WHEN `S.ahead_on_lives` AND `S.late_match` DO `C.hunt`
- `R.push` [100]: ALWAYS DO `C.push_to_heart`(heart=squad_target)
```

`ST.roles` says how the eight cogs on a team split up. All eight run the same file, so roles are
a function of `selfId`, as `base.bas` squads are. `ST.commitment` says when a running capability
may be interrupted: minimum hold times, the priority margin a new rule needs to preempt, and
hysteresis, so the agent does not switch capability every tick.

### 4.5 Adaptations

An Adaptation changes rule priorities during a match. This is the first, deliberately small form
of the policy changing its own structure.

```markdown
### A.demote_failed_push
- Summary: Stop pushing a heart that keeps failing.
- Spec: When `K.push_history` shows `fail_limit` failed pushes to one heart within
  `window` ticks, lower `R.push` priority for that heart by `step`. Restore it after `window`.
- Uses: `K.push_history`, `R.push`
- Params: fail_limit = 3; window = 1440 ticks [480, 2880, 240]; step = 50 [10, 100, 10]
```

Limits: globals reset every episode, so an Adaptation lasts only within one match. Every
priority change is logged (section 6); otherwise the "acted properly" check cannot be computed.

### 4.6 Communication

A Communication component defines one message type:

- `Content`: the beliefs or intentions it carries (for example, my target heart; enemies I see).
- `Encoding`: the exact text or numeric format. Keep it short: `shout` costs 68 work units.
- `Send when`: the condition, which can refer to this tick's selected rule and capability.
- `On receipt`: which `K.` component it updates, and how much to trust it.
- `Checks`: sent when it should be; decoded correctly by teammates; did it change the result.

Engine constraints ([policy-surface §5.7](../policy-surface.md)): every living cog within
12.8 m hears a shout, **enemies included**; at most 4 shouts per cog per tick; delivery is on the
next tick; a heard message gives the speaker's observed seat and exact position. The current
message set, wire format, and send rules are in [strategy/comms.md](../../strategy/comms.md);
each message type there becomes one `COM.` component.

### 4.7 A worked component

```markdown
### C.hold_heart
- Summary: Keep a heart that we own from capture.
- Spec: Stand inside the capture ring of `heart`. Stay off the line between the ring center
  and the nearest remembered enemy. Face the most recent threat direction. Fight with
  `SK.move_and_shoot`. Do not go more than `leash` outside the ring.
- Uses: `K.enemy_contacts`, `K.threat_direction`, `SK.move_and_shoot`, `SK.lead_aim`
- Params: heart (heart index); leash = 300 cm [100, 800, 50], hand-set, no tune run yet
- Done when: never (runs until Strategy selects a different rule)
- Abort when: `outnumbered_hold` = `S.outnumbered` true for 24 ticks; `heart_lost` = the heart
  is not ours
- Checks:
  - Acted properly: while active, the cog is within ring + `leash` in >= 95% of ticks. (script:
    `pw.py strategy audit --check C.hold_heart.leash`)
  - Result: the heart stays ours for the whole activation in >= 60% of activations. (replay stat)
- Status: idea (2026-09-30)
- Rationale: base.bas has no hold behavior. It moves on when a heart is ours ...
```

### 4.8 Prose style

All prose in `STRATEGY.md` and `skill.md` is **ASD-STE100 Simplified Technical English**: short
sentences, one meaning per word, active voice, no hedging. It is a technical specification for a
compiler agent, not a guide for people. Precision and no ambiguity come first. `Rationale` uses
the same style. The linter flags the mechanical violations (semicolons, "may/should/would",
sentences over 25 words).

## 5. Checks: five levels

Every component carries checks that we can compute from replays and telemetry. There are five
levels. Each builds on the one before it:

| Level | Question | Data needed |
| --- | --- | --- |
| **True** | Was the thing actually true or applicable? | The replay (ground truth). |
| **Believed** | Did the agent believe it was true? | Telemetry: logged beliefs and situation flags. |
| **Acted** | If it believed it, did it act on the belief? | Telemetry: the rule and capability selected. |
| **Acted properly** | If it acted, did it act as the strategy says? | Telemetry: the decision inputs (flags, priorities, commitment state), capability events; replay for the executed commands. |
| **Result** | If it acted properly and the belief was correct, was the result what we expected? | Replay outcomes over the capability's activation window. |

Levels by section:

| Section | Checks that apply |
| --- | --- |
| Knowledge | True vs Believed = **belief accuracy** (for example, logged enemy positions against replay positions; error in cm, false and missed contacts). |
| Situations | True, Believed, and their agreement (precision and recall of the flag). |
| Rules | Acted (the rule fired when its condition held and it was the top priority), Acted properly (the audit re-runs the selection from logged inputs and gets the same rule). |
| Capabilities | Acted properly (Spec, Done/Abort), Result. |
| Skills | Acted properly (execution: for example, shots fired only after windup), Result (for example, hit rate at range). |
| Adaptations | Acted (fired when its condition held), Result (did the new priorities help). |
| Communication | Sent correctly, decoded correctly by teammates, Result. |

Each check has one or more of: a semantic description, a script to run, a replay statistic. At
least one is required. A check that the logs cannot compute reports **unmeasurable**; it never
passes by default.

Belief building (Knowledge) is imperfect by nature: data is fogged. Belief-accuracy checks let us
optimize belief building from replays like any other component.

## 6. Telemetry v2

v1 (`reference/intent_telemetry.bas`, parsed by `pw.py intent`) prints one `PWI` line with a
mode code, target, and reason. v2 must provide **every value that a Believed, Acted, or Acted
properly check needs**. The replay already contains every position and every executed command,
so telemetry logs only what is in the agent's head: beliefs and decisions.

Line kinds (all integer fields; `map.json` decodes every code to its ID):

| Line | When | Fields | Serves |
| --- | --- | --- | --- |
| `PWD` decision | on any change, and every 24 ticks | tick; rule code; capability code; capability params (up to 3); situation flag words (31 flags per word); `held` (1 = kept by commitment, 0 = new selection); priority-set version | Situations Believed; Rules Acted and Acted properly; Capabilities Acted |
| `PWP` priorities | at start, and when an Adaptation changes one | tick; adaptation code; rule code; old priority; new priority; priority-set version | re-running the selection; Adaptations Acted |
| `PWE` capability event | on start, done, abort | tick; capability code; event; condition code (which Done/Abort condition) | Capabilities Acted properly and Result (activation windows) |
| `PWB` belief | per the `K.` component's `Log` field | tick; knowledge code; the logged values (for example seat, x, y, age for each believed enemy) | Knowledge belief accuracy; Situations Believed |
| `PWC` communication | on send and on decode | tick; send or receive; message code; speaker seat; decoded values | Communication checks |

Rules:

- **Alignment.** `tick` is `worldTick` at decision time. It equals the replay table tick of the
  world the agent decided from; the command appears at tick + 1 (as in v1).
- **Coverage is checked, not assumed.** `map.json` lists, for each check, the log fields it
  reads. The linter fails a check whose fields no component logs.
- **Budget.** Each tick the engine allows 1,024 printed bytes and 128 print events; exceeding
  either is a runtime error that disables the seat for the rest of the episode. The compiler
  reports the worst-case per-tick total and keeps it at or below half of each limit. Large belief
  lists are split across ticks (for example, 4 enemies per tick). The seat log is cut at 10 MiB
  per episode; target at most 2 MiB for a 14,400-tick match.
- **Kill switch.** `telemetryOff = 1` turns all lines off.
- **Tooling.** `pw_intent.py` gains a v2 parser and the five-level audit (section 10).
- **Hosted logs: available, with two caveats.** Our XP episodes return a seat log per seat
  (`logs/policy_agent_<seat>.log`, confirmed in the 2026-09-30 seed pilot,
  [field.md](../field.md#seeds-what-actually-reaches-the-engine)), and the engine writes PRINT
  output into that file. Caveat 1: no hosted policy of ours has printed anything yet (`base.bas`
  prints nothing), so the first telemetry v2 upload must confirm that the lines arrive complete.
  Caveat 2: some logs are missing for minutes after an episode ends (5 of 32 of our seat logs in
  the pilot's first fetch); refetch with `--force`, and the audit reports a seat with no log as
  unmeasurable. Logs come back only for our own seats (the pilot returned none for the opponent's),
  so belief checks apply only to our own seats.

## 7. The two loops

**Edit loop** (people and an LLM, working on `STRATEGY.md` and `skills/`): read evidence (field
reports, replays, check results, A/B results, compile reports); change components; practice
skills by improving `skill.bas` against the skill's checks; keep `Status`, `Params` values, and
`Evidence` current. It never edits compiled output.

**Compile loop** (the Python driver `pw.py strategy compile` plus one LLM compiler agent, Claude
Code or Codex; compilation design §4 and §9): input is the source, the lab's
[policy-surface.md](../policy-surface.md), and the `reference/` starters as a library of proven
BASIC. Output is one `compiled/<build-id>/` directory. Its contract:

1. **Never edit the source.** No writes to `STRATEGY.md`, `comms.md`, `skills/`, or
   `compiler/`. The driver enforces this with a git check.
2. **Compile only committed source.** Refuse to build if the source has uncommitted changes, so
   the commit SHA in `version.json` identifies the input exactly.
3. **Structure and modularity.** Follow the per-tick order (section 3). One `SUB` (or one
   delimited block) per component, named from its ID, with the ID in a comment. Each component's
   globals share a prefix derived from its ID. `map.json` records every unit, so a later build can
   change only the units whose components changed.
4. **Skills verbatim.** Copy each `skill.bas` unchanged. If a skill's code does not fit (a
   missing global, a budget problem), report it; do not rewrite it.
5. **Parameters** become constants in one init block. Tunable ones carry `' @tune min max step`,
   so [paintbot-pw-tune](../../.claude/skills/paintbot-pw-tune/SKILL.md) can search them without
   a recompile.
6. **Telemetry v2** as specified in section 6, with the budget report.
7. **Report every guess.** Where `Spec` is ambiguous or impossible, choose the most conservative
   reading, implement it, and record it in `report.md` with the component ID. Unresolved guesses
   block `Status: tested`.
8. **Safety and budget.** The build MUST pass the local gates (compilation design §8): lint,
   compile in all 16 seats, budget peaks, local screen, telemetry. A compile error or a rejected
   upload fails the whole hosted episode, so nothing uploads without passing them. The local
   screen never vetoes an intended behavior change (compilation design §8.2).
9. **Header.** `policy.bas` starts with a banner: the build ID from `version.json`, and "generated,
   do not edit".

Compile incrementally: only components whose compiler-read text changed are recompiled; all other
units are copied from the previous build (compilation design §10). A full recompile stays
available.

## 8. Versioning

A build MUST identify exactly what it came from. The compiler builds only from committed source
(contract item 2). Each build's `version.json` records the source commit, the source hashes, the
compiler agent, model, and instruction hashes, the engine, and the gate results. Uploads are
recorded in the append-only `compiled/uploads.jsonl`, so a build directory never changes after it
is written. Field list and details: compilation design §6.

## 9. What this does not solve

- **Natural language is ambiguous.** The same `Spec` can compile to different BASIC in two
  runs. Accepted. Mitigations: STE prose, numbers in `Spec` and `Params`, the incremental
  compile, and the compile report.
- **Beliefs can be wrong.** Knowledge is built from fogged data. Belief-accuracy checks measure
  this, and we optimize it like any other component.
- **Hosted telemetry is not yet seen end to end** (section 6): retrieval works, but no hosted
  episode has carried our telemetry lines yet.

## 10. Tooling (not yet built)

The compilation design adds `prepare`, `assemble`, `verify`, and `compile` (its §4). This
document needs three more:

- `pw.py strategy lint STRATEGY.md --json`: IDs unique and well formed; references resolve and
  obey the section rules (section 3); required fields present; every Situation, Capability, and
  rule is used; every check's data is logged; `Params` ranges well formed; mechanical STE
  violations. Nonzero exit on errors, so a loop can gate on it.
- `pw.py strategy trace <build>`: compare `version.json` with the current source and list the
  components changed since that build.
- `pw.py strategy audit <episodes> --json`: parse telemetry v2, join it to the hash-checked
  replay, and compute every check at all five levels. Extends `pw_intent.py`.

No new dependency.

## 11. Alternatives considered

| Option | For | Against |
| --- | --- | --- |
| **Structured Markdown** (chosen) | The content is precise prose, which LLM editors write well. Readable and diffable. Headings give structure a linter can parse. | Structure is by convention, so it needs a linter. |
| JSON / YAML | Exact structure, trivial to parse. | Long prose inside strings is hard to write and review; escaping and indentation errors; LLM edits churn whole blocks. |
| XML | LLMs handle tags well; exact structure. | Noisy for people to read; no gain over Markdown headings at this depth. |
| Ordered rules, first match wins | Simplest to read and check. | Priorities cannot change during a match. Replaced by numeric priorities (section 4.4). |
| Skills as prose only, compiled like everything else | One rule, no authored BASIC. | Mechanics improve faster in code than in prose, and a recompile would discard tuned skill code. Replaced by authored `skill.bas`. |

Prior art: situations plus prioritized rules is utility-based selection (a behavior tree's
priority selector with numeric scores); commitment is BDI-style intention (belief-desire-intention:
keep a chosen plan until there is a reason to drop it); Skills and Capabilities form a
hierarchical state machine. We borrow the concepts, not a runtime or file format: there is no
behavior-tree runtime in BASIC, and the consumer is an LLM compiler.

## 12. Decisions and open questions

Decided (2026-09-30):

- One `STRATEGY.md`, with optional links to per-section files. Skills are directories.
- `TENTATIVE_LESSONS.md` stays the evidence log. `STRATEGY.md` links to it through `Evidence`. A
  lesson becomes policy only when it goes into a component.
- **Starting point:** the first `STRATEGY.md` is a faithful description of `base.bas` in this
  format. Its compiled output must play like `base.bas` in a local screen before we change any
  behavior. This tests the compiler before we test strategy.

Open:

1. **Communication design.** Drafted as comms v1 (not yet verified against the engine; its §11) in [strategy/comms.md](../../strategy/comms.md):
   policy content that changes often, so it lives outside this format document. The field already
   has public shout protocols (Aaron's `FIRE22`/`ITEM23`,
   [field analysis](../reports/2026-09-29-league-field-analysis.md)).
2. **First hosted telemetry run.** Retrieval is confirmed; confirm that telemetry v2 lines arrive
   complete in hosted seat logs (section 6).
3. ~~Compile process design~~ Done: [2026-09-30-strategy-compilation.md](2026-09-30-strategy-compilation.md).
