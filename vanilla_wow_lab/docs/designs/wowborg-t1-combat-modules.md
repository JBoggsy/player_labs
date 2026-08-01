# Design: T1 combat — the capability modules

**Date:** 2026-07-22. **Status:** decomposition proposal for review — *what* to build as
atomic units, not yet *how*. **Evidence:** the strategy guide
([`../vanilla-wow-strategy-guide.md`](../vanilla-wow-strategy-guide.md)), a deep sweep of
the authored bots' combat stack at 0.1.31 vs HEAD (division-of-labor report, session 6),
and the codex nav audit
([`../recon/nav-audit-codex-2026-07-22.md`](../recon/nav-audit-codex-2026-07-22.md)).

## Framing: what "combat" means for us, and where the seam sits

The 0.1.31 contract already does enormous work. The **action mask** computes legality —
trained rank, cooldown, resource affordability, range, line of sight, target
hostile/alive, interrupt-only-while-casting, heal-only-when-wounded, loot-only-lootable
(verified at the frozen 0.1.31 commit). The **executor** handles facing, stand-up,
auto-attack/auto-repeat upkeep, and navmesh routing for any move. And every frame carries
the authored planner's **`recommended_action`** — the entire authored combat stack as a
per-step oracle we can defer to selectively.

So our modules are **decision** modules, not mechanics modules. The policy's job per
frame: choose among legal actions. Everything below decomposes *that* choice. What the
mask does NOT do for us (= exactly our surface): which legal target/spell to pick,
rotation ordering, pull sizing/add-risk, flee decisions, eat/drink timing, movement
destinations, and — at 0.1.31 specifically — combo-point finishers, threat
summarization, and disengage logic (those observation fields/reducers only exist at
HEAD; we must derive them from visible units' `target_guid`s ourselves).

## The kinds of combat (what situations exist)

1. **Solo grind kill** — the T1 core. Pick a safe con, pull it clean, kill it, loot it.
   Repeat. This is the XP engine for `custom-fresh-start` scoring.
2. **Defensive/forced combat** — you got adds, a patrol walked in, you're body-pulled.
   Not chosen; must be survived (fight, control, or flee).
3. **Multi-mob pulls** — 2+ linked mobs; needs kill ordering, maybe CC, and honest
   accounting that this often *shouldn't happen* (pull sizing failed).
4. **Caster-mob combat** — ranged enemies don't come to you; LoS pulling and interrupt
   decisions matter (RFC's Ragefire Shamans / Searing Blade Warlocks).
5. **Group/instance combat** — the trinity: tank holds threat (110%/130% switch rule),
   healer triages, DPS ride the threat ceiling and focus-fire. The RFC benchmark. T2 for
   the party coordination, but the per-role decision modules are T1 designs.
6. **Boss mechanics** — positional rules per encounter (Cleave facing, Taragaman's
   knockback-near-lava, DoT healing pressure). Data, not code: encounter annotations
   consumed by the group modules.

## The playstyles (how the 7 classes map onto decision shapes)

Rather than 7 class modules, classes decompose into **5 playstyles** — each a
configuration of the same modules with different priorities and one or two
style-specific behaviors:

| Playstyle | Classes | Distinct decisions |
|---|---|---|
| **Melee sustain** | warrior, rogue, enh. shaman | stay in melee band, builder/finisher or rage dump, weapon-skill awareness |
| **Caster nuke** | mage, elem. shaman, priest (smite) | open at max range, cast-time management, mana gates the pull |
| **DoT/drain** | warlock, shadow priest | apply-once DoTs, wand weave, health-as-resource (Life Tap) |
| **Pet split** | hunter, warlock | pet holds the mob, owner at range; pet health/happiness upkeep; dead-zone (hunter 8yd min) |
| **Support/heal** | priest, resto shaman | triage ladder, shield/HoT usage, mana as the party's fuel gauge |

Class specialization = a **class profile** (data): rotation priority table, resource
thresholds, buff list, playstyle assignment per role. The authored `rotations.nim`
proves this works — all 9 classes are pure data over shared selectors. We mirror that
shape in Python and can bootstrap priorities from theirs.

## The capability modules (atomic units)

Eleven modules in four layers. Each is independently testable against a fake bridge,
has a crisp input/output contract at the frame level, and fails safe (defer to
`recommended_action`).

### Layer A — perception (derived state the frame doesn't hand us)

- **A1. `threat_model`** — who is attacking whom, derived from visible units'
  `target_guid`s: my attackers, their count/level deltas, incoming-pressure estimate,
  time-to-death. (HEAD gets `BotThreatObservation` for free; at 0.1.31 we build it —
  and ours must also serve the party case: who is attacking the *healer*.)
- **A2. `combat_state`** — a small state machine over frames: `idle → pulling → engaged
  → recovering(post-kill) | fleeing | dead`. Everything downstream branches on this,
  and the nav layer needs it too (audit findings #3/#4: navigation must know it's in
  combat and must pause budgets during death recovery).

### Layer B — the fight itself

- **B1. `target_selector`** — which mob to fight *next*: level-margin safety (≤ level−1
  grind / ≤ level quest), objective priority, proximity, moving-vs-stationary. Mirrors
  the authored `safeTarget` rules.
- **B2. `pull_planner`** — is this pull *clean*: add-risk radius (level-scaled aggro
  model), bystander/patrol corridor check, mana gate (≥85% for casters), position to
  open from (range vs melee, LoS for caster mobs). Owns "one puller" discipline later.
- **B3. `rotation_engine`** — the in-combat action chooser: a priority list interpreter
  over the class profile (builder/finisher, DoT-once, cadence weaves, interrupt
  opportunities, defensive triggers), always intersected with the frame's mask. The
  authored tables are the starting data.
- **B4. `survival_monitor`** — continuous veto power above the rotation: emergency
  potion (≤35% or predicted death), bandage/self-heal windows, **flee decision**
  (attacker count × TTD thresholds) and disengage route. The audit's "combat-aware
  navigation" lives at this boundary.

### Layer C — between fights (the downtime economy)

- **C1. `recovery_manager`** — eat/drink to profile thresholds, five-second-rule
  awareness, rest-vs-next-pull timing. Downtime is the real XP lever.
- **C2. `readiness_manager`** — buff upkeep (self-buffs, weapon buffs), pet
  summon/mend/feed, ammo/reagent checks, trainer-visit signaling. Mostly
  mask-legality + timing.
- **C3. `loot_and_field`** — post-kill loot (mask-gated), bag-space awareness,
  vendor-trip signaling. Bridges to the existing quest/economy actions.

### Layer D — group play (designed now, built for RFC)

- **D1. `role_conduct`** — per-role behavior contracts: tank (first contact, threat
  ramp, face-away positioning), healer (triage ladder, tank-priority, mana gate on the
  *party's* next pull), DPS (assist target, threat ceiling ~110/130%, ramp delay).
- **D2. `party_coordinator`** — the cross-character brain: pull ordering, focus-fire
  target designation, CC assignments, encounter annotations (boss data). This is the
  part the engine explicitly does NOT supply ("the party-coordination logic is the
  thing a policy must supply"). Five instances coordinate only through the game
  (chat/observed behavior) — the deepest open design question, deliberately deferred.

### The spine that composes them

A per-frame **arbiter** replaces the race loop's inline logic: modules propose
`(action, priority, reason)`; the arbiter takes the highest-priority mask-admitted
proposal, else `recommended_action` as fallback; every choice traces. The authored
planner's own combat ordering (disengage > emergency potion > defensive > interrupt >
heal > rotation) is the priority skeleton.

## Build order (each step measurable hosted)

1. **A2 + B1 + B3-minimal + C3** — "kill safe things near the grind spot, loot them":
   first nonzero XP in `results.json`. Warrior or shaman first (melee sustain is the
   simplest loop; shaman adds the self-heal safety valve).
2. **B4 + C1** — survival + downtime: deaths/hour down, XP/hour up. Add A1 properly.
3. **B2 + C2** — clean pulls + upkeep: fewer multi-mob fights; measurable via
   adds-per-fight from traces.
4. **Second playstyle** (caster nuke: mage or priest) to prove the profile abstraction —
   the moment class specialization becomes data, not code.
5. **D1/D2** against RFC — gated on the nav rework the audit prescribes (map-aware
   waypoints, combat/death-aware nav states, route graphs instead of radial tiers).

## Measurement

The race harness pattern carries over: per-fight trace events (`fight_start`,
`fight_end{kills, adds, hp_low_water, potions, flee}`, `death`), `race_report.py`-style
per-batch scoreboards, and `results.json` XP as the headline metric. The authored bots
in goal mode (`bot_id=king-richard`, automatic selection) are the natural A/B baseline:
our external policy should beat the oracle it can always fall back to, or we learn why.

## Open questions for review

1. **Class order** — warrior-first (RFC tank, hardest solo) vs shaman-first (forgiving,
   self-heal) vs hunter-first (fastest XP, but pet adds a module)? Recommend shaman.
2. **How much oracle?** Deferring to `recommended_action` when our modules abstain is
   safe but can mask gaps. Trace-tag every deferral so batches show the abstention rate?
3. **Combo/finisher truth at 0.1.31** — masks for finishers are inert at the pinned
   version (no combo observation); rogue playstyle may need to wait for a pin bump or
   drive off `recommended_action` for finishers.
4. Where does the nav rework land relative to this — before D (required for RFC) but
   the solo-grind steps 1-3 need only local movement (target approach ≤ 60 yd), which
   the current bridge move already handles.
