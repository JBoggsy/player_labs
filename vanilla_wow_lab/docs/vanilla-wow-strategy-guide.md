# Vanilla WoW — strategy & how-to-play guide

**A beginner's guide + pro tips + strategy for actually playing Vanilla WoW well**, written
for the player-agent lab. Where [`vanilla-wow-gameplay.md`](vanilla-wow-gameplay.md) explains
*what the game is* and [`vanilla-wow-player-contract.md`](vanilla-wow-player-contract.md)
explains *the wire contract*, this doc explains **how to be good at it** — the real WoW
knowledge a competitive policy has to encode, tied to our two scored surfaces (RFC clear +
XP) and grounded in what the `coworld-vanilla-wow` engine actually supports.

**Two source streams feed this doc**, and they're flagged throughout:
- **Real Vanilla WoW knowledge** from authoritative Classic sources (Wowhead Classic,
  Icy Veins Classic, warcraft.wiki.gg) — cited with URLs. This is *1.12-era* WoW; later
  Classic re-releases (Season of Mastery, SoD, Anniversary) changed some numbers, flagged
  where it matters.
- **Engine-grounded facts** from the game repo (`~/coding/coworlds/coworld-vanilla-wow`) —
  cited `file:line`. These tell you what a policy can lean on vs. must supply.

> **Why this matters for us.** The competition rewards *playing WoW well*: fast full RFC
> clears and high character XP. A policy that understands aggro, pulling, class rotations,
> death cost, and dungeon flow will beat one that doesn't. The bundled bots already encode a
> lot of this (see the engine citations) — this guide is the mental model behind those
> mechanics, and the map of where a purpose-built policy can push further.

---

## Part 0 — WoW in five minutes (for the never-played reader)

World of Warcraft is a **massively-multiplayer role-playing game**. You control one
**character** — a member of a **race** (Horde side here: orc, troll, tauren, undead) and a
**class** (warrior, hunter, rogue, shaman, warlock, mage, priest for us) — in a large 3D
world. The character has a **level** (1→60 in Vanilla), **health** (HP), and a **resource**
(mana, rage, or energy depending on class) that powers its abilities.

You get stronger by earning **experience points (XP)** — from killing monsters ("mobs") and
completing **quests** (tasks given by non-player characters). Enough XP → the next level →
more HP, new abilities, access to harder areas. You fight by **targeting** an enemy and using
**abilities** (melee swings, spells, shots). You **loot** corpses for money and items,
**vendor** junk for gold, **repair** damaged gear, **train** new spell ranks at class
trainers, and **recover from death** by running your ghost back to your corpse.

**A "dungeon" (or "instance")** is a private, self-contained area — you and your group get
your own copy — filled with tougher "trash" mobs and **boss** monsters. Dungeons are designed
for a **5-person group**, which is where the "holy trinity" of tank/healer/DPS comes in
(Part 3). Our scored dungeon is **Ragefire Chasm (RFC)**, the easiest low-level Horde dungeon.

That's the whole loop: **level up in the open world by killing/questing; group up to clear
dungeons.** Our two scored surfaces map directly onto those two activities.

---

## Part 1 — The two things we're scored on

Everything in this guide serves one of two goals (full detail:
[`vanilla-wow-gameplay.md`](vanilla-wow-gameplay.md#how-scoring-works) and
[`vanilla-wow-rfc-roles.md`](vanilla-wow-rfc-roles.md)):

1. **RFC clear — the competition.** One policy plays all five characters of a level-30 party
   (warrior tank, priest healer, shaman, rogue, mage) that must kill Ragefire Chasm's four
   bosses. **Round score = clear-then-speed:** a full clear scores `max(1, 1_000_000 −
   clear_seconds)`; a partial run scores `bosses_defeated / bosses_total` (< 1.0). So **every
   full clear beats every partial run, and among clears the fastest wins.** The overriding
   strategic implication: **cross the "all four bosses dead" threshold reliably first;
   optimize clear time second.** XP does not affect round ranking.
2. **XP accrual — the persistent realm.** A character's rank is its account's **highest total
   XP**. This is the leveling game: efficient questing/grinding, minimizing downtime and
   deaths. (Status: the persistent scored surface is designed but not fully live — see the
   readiness caveat in the gameplay doc.)

Two very different games. RFC is a **coordination + survival** problem over a short instance;
XP is an **efficiency + endurance** problem over many hours. The rest of this guide is
organized as: leveling fundamentals (Part 2), group/dungeon play (Part 3), the classes
(Part 4), RFC specifically (Part 5), and a synthesis of pro tips + where a policy wins
(Part 6).

---

## Part 2 — Leveling & solo survival fundamentals

The skills here drive the XP score directly, and they're also the foundation a party needs
(a party is five solo players who don't die and don't pull aggro).

### The XP math (why you fight what you fight)

Leveling 1→60 needs **~4,084,700 XP** total, and the per-level cost climbs steeply — it's a
long grind ([warcraft.wiki.gg/wiki/Experience_point](https://warcraft.wiki.gg/wiki/Experience_point)).
A same-level mob kill in Azeroth gives `XP = MobLevel × 5 + 45`
([warcraft.wiki.gg/wiki/Mob_experience](https://warcraft.wiki.gg/wiki/Mob_experience)). The
levers:

- **Higher-level mobs pay more:** `+5% XP per level above you`, up to `+20%` at 4 levels
  above — which is why players fight "yellow/orange" mobs despite the risk.
- **Lower-level mobs pay less**, dropping to **zero XP once "gray"** (the gray threshold
  widens with level: ~5 levels below you at low level, up to ~17 at 60).
- **Elite mobs give 2× XP** but hit far harder — **avoid soloing elites and group quests.**

**The "con" color system** is the mob's difficulty *and* XP signal
([warcraft.wiki.gg/wiki/Level](https://warcraft.wiki.gg/wiki/Level)): **Skull** = 10+ above
(or a boss) — deadly; **Red** = >4 above; **Orange** = 3-4 above; **Yellow** = ±2; **Green**
= a few below (safe, still XP); **Gray** = no XP. Against higher mobs your hit/crit drop and
they can crush you; against lower mobs you hit more reliably.

> **Engine grounding.** The bundled leveling policy encodes exactly this risk math: ordinary
> grind targets are capped at **player level − 1** (`OrdinaryGrindLevelMargin`), quest
> objectives may go up to your own level, and combat/object objectives only start at
> `questLevel + 2` (`QuestObjectiveSafetyMargin`) (`player/bots/leveling/planner.nim`,
> `targets_and_recovery.nim:26-149`). A candidate mob with **another live hostile within 18
> yards of it** is skipped to avoid adds (`OrdinaryPullAddRiskRadius`). So the engine already
> plays the "fight safe cons, avoid packs" game — a policy tunes the thresholds, it doesn't
> invent them.

### Rested XP — the free 2× multiplier

When you log out in an **inn or capital city**, your XP bar turns **blue** and accumulates
**rested XP**, which grants **double XP from mob kills** until spent (quest XP doesn't consume
it). Resting in an inn/city fills **4× faster** than logging out in the open world, capping at
150% of a level ([warcraft.wiki.gg/wiki/Rested](https://warcraft.wiki.gg/wiki/Rested)).
*Version note:* the wiki's "10%/16h" wording is later-expansion framing; the Vanilla-accurate
facts are the blue bar, 2× kill XP, and 4×-in-inns. **Implication:** an XP-maximizing policy
that ever logs out should do so in an inn/city, and should prefer to spend rested XP on kills.

### Downtime is the enemy (the real efficiency lever)

Time splits three ways: **combat, recovery, travel.** The best levelers crush *recovery*
([icy-veins.com/wow-classic/leveling-guide](https://www.icy-veins.com/wow-classic/leveling-guide)):

- **Always carry food** (restores HP out of combat) and **water** for mana classes. Sitting
  to eat/drink regenerates far faster than standing.
- **Mana classes fight the "five-second rule":** Spirit-based mana regen is suppressed for 5
  seconds after you spend mana
  ([warcraft.wiki.gg/wiki/Five_second_rule](https://warcraft.wiki.gg/wiki/Five_second_rule)),
  so drinking between pulls beats waiting. *Engine:* mana classes wait until power ≥ **85%**
  before a voluntary pull (`PullManaRecoveryPercent`, `routing_and_actions.nim:20-38`).
- **First Aid is near-mandatory for every class:** bandages are **mana-free** healing (heal
  over 6-8s, interrupted by any damage, ~60s per-target cooldown), made from cloth you loot
  anyway ([warcraft.wiki.gg/wiki/First_Aid](https://warcraft.wiki.gg/wiki/First_Aid)). Huge
  for warriors/rogues with no self-heal.
- **Batch quests:** grab a cluster from a hub, do them in one loop, turn them all in together
  — avoids backtracking. Skip isolated/low-value quests. Set your hearthstone to the active
  hub; use flight paths for AFK travel; **mount at level 40** (+60% speed).

> **Engine grounding.** The authored `durotar_troll_shaman.nim` profile is a master-class in
> this: it encodes farm areas with level bands + `grindCreatures` allowlists, quest chains
> with per-objective creature/item ids and `approachRoute`/`patrolRoute` corridors that skirt
> hazards, vendor/trainer stops, and a hearth anchor — with the explicit design note that it
> **"values a no-death margin over the fastest theoretical XP rate"**
> (`durotar_troll_shaman.nim:1338-1339`). The `zone_progression_policy.json` is the
> cross-zone brain (which zone to be in at each level, 1-60). This is what "an authored good
> leveling run" looks like concretely.

### Pulling & positioning (the survival core)

**Pulling** = starting a fight while peeling off **as few mobs as possible**
([warcraft.wiki.gg/wiki/Pull](https://warcraft.wiki.gg/wiki/Pull)):

- **Line-of-sight (LoS) pulling** is the key trick against **caster mobs**: aggro them, then
  duck behind terrain so they must *run to you* into melee instead of nuking from range.
- **Aggro radius** scales with the level gap — it grows when a mob out-levels you, so
  under-leveled pulling risks accidental adds
  ([warcraft.wiki.gg/wiki/Aggro](https://warcraft.wiki.gg/wiki/Aggro)).
- **Runners** (mobs that flee at low HP) **drag in more mobs** — snare them or position so
  they flee into empty space. **Patrols** can wander into a fight mid-pull — watch pathing.

**Weapon skill** is a major, easily-missed survival stat: max = **5 × level** (300 at 60);
below a mob's defense you **miss more, crit less, get dodged/parried more**. Crucially,
**equipping a new weapon *type* resets your skill to low** — a real trap when grabbing an
upgrade of an untrained type mid-grind
([warcraft.wiki.gg/wiki/Weapon_skill](https://warcraft.wiki.gg/wiki/Weapon_skill)).

### Death is expensive — avoid it, and recover cheaply when it happens

On death you become a **ghost** and run back to your **corpse** to resurrect with **no
penalty** (the "corpse run"). Resurrecting at the **Spirit Healer** instead inflicts
**resurrection sickness** + extra **durability loss** — a last resort
([warcraft.wiki.gg/wiki/Resurrection_sickness](https://warcraft.wiki.gg/wiki/Resurrection_sickness)).
*Version note:* the modern wiki lists 1-min / 50% durability (retail 10.0 values); **Vanilla
1.12 scaled the sickness up to ~10 minutes at level 60 and cost 25% durability** at the spirit
healer — use the Vanilla values. Res sickness **reduces all attributes and damage by 75%**, so
pulling while sick is a death spiral.

> **Engine grounding — the death-recovery economy is fully modeled.** The policy defaults to a
> corpse run and only escalates to the Spirit Healer (creature **6491**, 5-yd interact) after
> either: the corpse is in a known-dangerous area, **one death right after a reclaim** proves
> the corpse is lethal (`MaxUnsafeCorpseReclaimDeaths = 1`), or **5 failed reclaims**
> (`MaxCorpseReclaimFailures = 5`). Resurrection Sickness (aura **15007**) blocks voluntary
> pulls until it clears (`planner.nim:15-118`, `:264-268`; `targets_and_recovery.nim:291-375`).
> So a policy inherits sane death handling; the strategic job is *not dying in the first
> place* (level-appropriate cons, add avoidance, healing at 65% in combat / 90% out —
> `planner.nim:178-197`).

---

## Part 3 — Group play: the holy trinity, threat & coordination

This is the heart of the RFC clear. Vanilla group play is **far stricter** than modern WoW —
role confusion wipes groups.

### The trinity

- **Tank** (our **warrior**) — holds *every* enemy's attention and absorbs the damage. Wears
  plate, has the most effective HP.
- **Healer** (our **priest**) — keeps the group alive, above all the tank. Gated by mana.
- **DPS** (our **shaman / rogue / mage** — 3 slots) — deal damage, kill things. Wear
  cloth/leather/mail; die instantly if a boss turns on them.

### Threat / aggro — the single most important group mechanic

Every hostile action builds **threat** on a mob's internal list; the mob attacks whoever holds
the most. The tank's whole job is to top that list on every mob. The exact switch thresholds
([warcraft.wiki.gg/wiki/Threat](https://warcraft.wiki.gg/wiki/Threat)):

> **A mob switches target when someone exceeds the current target's threat by 10% in melee
> range, or 30% at range.**

Consequences a bot party must encode:
- **Melee DPS** (rogue, enhance shaman) can build to ~**110%** of the tank's threat before
  ripping the mob loose — a tight window.
- **Ranged DPS** (mage, and casters generally) have more room, up to ~**130%** — but lose it
  if they step into melee.
- **Healing generates threat too** (~1 threat per 2 effective healing), spread across all mobs
  in combat — an over-healing priest can pull a loose mob.

**Taunt** (warrior) *equalizes* your threat to the current top and *forces* the mob onto you
for a few seconds — a **recovery tool, not a rotation**; after it ends, whoever has the most
threat regains the mob, so the tank must keep building. At RFC's level the warrior has
**Defensive Stance** (~1.3× threat) but **not yet the Defiance talent**, and needs **rage**
(built by taking/dealing hits) — so **a warrior that opens cold has near-zero threat for the
first 1-2 seconds.** That's the exact window where eager DPS steals aggro and dies.

**The discipline:** DPS wait ~1-3 seconds ("let the tank land a Sunder or two"), then ramp;
back off if they approach the threat ceiling. Everyone **focus-fires one target** via
`/assist` on the tank (a dead mob deals zero damage — the fastest damage reduction). Mark a
**kill order** (Skull = first, X = second) and **CC targets** (Moon = sheep, Diamond = sap,
Blue = trap) that nobody damages until freed. **One puller** starts each fight; nobody else
touches a mob until the tank has threat.

**Crowd control (CC)** removes part of a pack from the fight: **Mage Polymorph/Sheep**
(humanoid/beast, breaks on damage), **Rogue Sap** (out-of-combat opener in Vanilla), **Warlock
Fear/Seduce**, **Hunter Freezing Trap**, **Priest Shackle** (undead only — irrelevant in RFC).

> **Engine grounding.** The three-lane demo prescribes exactly this shape for the level-20
> five-client RFC lane: **"tank first-contact, followers continuously converging on the moving
> tank …, DPS assisting the tank's retained target, and the healer making resource-aware
> heal/drink/potion decisions from its own party-frame/mirror truth"**
> (`docs/king-richard-three-lane-prompt.md`, Lane 2). The `RotationRoutineProfile` layer
> assigns per-role behavior (Tank/Healer/MeleeDps/RangedDps with rest/pull/combat/recover
> phases) — e.g. a `shaman-party-healer` profile and a `protection-warrior` tank profile
> (`player/bots/rotations.nim:246-266`, `:1067-1206`). The party-coordination *logic* (who
> pulls, the threat-ramp delay, focus-fire) is the thing a policy must **supply** on top.

### The failure modes that wipe low-level groups

A single-policy bot party must be engineered against each of these (all corroborated by
community sources):

| Failure | What happens | The discipline that prevents it |
|---|---|---|
| **Over-pulling** | A second (or linked) pack joins mid-fight | One puller, LoS pulls, count *linked* mobs before engaging |
| **DPS pulls aggro** | Opening before the tank has threat / crossing 110-130% | Threat-ramp delay; soft threat ceiling per DPS; melee back off harder |
| **Healer OOM** | Chain-pulled past mana → next pull wipes | Gate the next pull on healer mana; shield + efficient heals; drink when low |
| **Body-pulling** | A melee bot/pet paths into a mob's aggro radius | Strict positioning behind the tank; pets on passive/controlled |
| **Losing/killing the tank** | Healer swaps off the tank, or tank out-ranges healer | Healer prioritizes tank HP; tank stays in healer range |
| **Standing in AoE / bad position** | Cleave hits non-tanks; Fire Nova/knockback near lava | Tank faces bosses *away* from group; ranged keep max distance; avoid lava edges |
| **Breaking CC / split pulls** | An AoE/DoT frees a sheep; half the party engages early | CC-marked targets never touched until primary dead; everyone assists one target |

> **A bot party's real advantage:** perfect assist discipline and zero threat-greed are
> *achievable* in a way human pugs rarely manage — one policy controls all five, so it can
> enforce the threat ceiling and focus-fire perfectly. The genuinely hard parts are **pull
> sizing** (respecting mob links) and the **threat-ramp delay** against a rage-starved,
> Defiance-less low-level warrior tank.

---

## Part 4 — The classes (Horde, and the seven we can field)

Vanilla has nine classes; this game seeds **seven Horde classes** (no paladin — Alliance-only
and unreachable; no druid — unseeded; see
[`vanilla-wow-gameplay.md`](vanilla-wow-gameplay.md#the-nine-classes-and-why-only-seven-are-playable-today)).
Each has a signature resource and playstyle. Tight, accurate essences
([Icy Veins Classic leveling guides](https://www.icy-veins.com/wow-classic/leveling-guide)):

- **Warrior** (rage; **tank**). *Hardest/slowest to level solo*, no self-heal → heavy
  downtime; your **slow, high-damage weapon** is your most impactful gear (abilities scale off
  it). Opens fights empty on rage (Charge for a burst). But becomes **the best tank in Classic
  at 60** — and it's our RFC tank. Core: Charge → Rend → Heroic Strike, Battle Shout, Thunder
  Clap (AoE), Sunder Armor / Revenge for threat.
- **Priest** (mana; **healer**). Safe but **slow-damage early** (leans on wand + Smite/Shadow
  Word: Pain), comes online at ~40 with Shadowform. Survivable via Power Word: Shield + Renew
  + Heal. Our RFC healer — the mana-gated lifeline.
- **Shaman** (mana; **hybrid**, Horde-only). Durable, forgiving via **Healing Wave** self-heal;
  Enhancement (melee + weapon enchants Rockbiter/Windfury) is the consistent leveling spec.
  Drops **totems** for group support. Can off-heal in a pinch — a flexible RFC slot.
- **Rogue** (energy; **melee DPS**). Strong, safe, **near-zero downtime** (energy regenerates
  flat, in or out of combat). Stealth to pick fights (Sap/Ambush), Gouge/Kick control,
  Sprint/Vanish/Evasion escapes. **Swords** best solo. No self-heal (First Aid covers it).
  **Weapons are the top upgrade.**
- **Mage** (mana; **ranged DPS + AoE + CC**). Fast killer but **very fragile**. Frost spec for
  safety (Frost Nova + Blink to kite). Conjures own food/water (no vendor dependence),
  Evocation to refill. **AoE grinding** (Blizzard + Arcane Explosion) is a huge accelerator at
  higher levels. Brings **Polymorph** CC to RFC.
- **Hunter** (mana + pet focus; **ranged DPS**). *Easiest/fastest solo leveler* — the **pet
  tanks** while you shoot. **Feign Death** to drop threat/escape. Weakness: the **dead zone**
  (no ranged attack within 8 yards). Brings **Freezing Trap** CC and long-range pulling to a
  group.
- **Warlock** (mana + soul shards; **ranged DPS**). *Top-tier solo, extremely durable* —
  **Voidwalker pet tanks**, DoTs + wand kill, **Life Tap / Drain Life** for near-zero
  downtime, **Fear** for control (dangerous indoors — can pull extra packs). **Free mount at
  40.**

**Solo-XP tier (community consensus):** Hunter & Warlock top (pet tank + sustain); Mage fast
but squishy; Rogue & Shaman solid/durable; Priest safe-but-slow until 40; Warrior hardest.

> **Engine grounding.** `player/bots/rotations.nim` ships data-driven `ClassRotation` tables
> for exactly these seven (paladin/druid fall through empty, `:1208-1224`). A rotation
> prioritizes abilities by **role → priority → resource affordability → range**, with a **5-yd
> melee band**, a **`meleeWeave`** flag for instant casts that ride the auto-attack swing
> (Shaman Earth Shock is the canonical one), and a **`castWithoutTarget`** flag for area buffs
> (Battle Shout, Lightning Shield) whose empty target mask the server would otherwise reject.
> Each ability rank carries its **train level + cost**, so the trainer-visit logic can gate on
> both level and gold (`rotations.nim:167-266`, Shaman `:279-449`, Warrior `:451-489`). The
> combat competence is largely there; a policy tunes priorities and supplies party
> coordination.

---

## Part 5 — Ragefire Chasm, specifically

RFC is **the easiest dungeon in the game** and our scored target. Real-WoW orientation first,
then how the engine treats it.

### Real-WoW layout (orientation — not a hardcoded path; see the caveat below)

- **Location:** Orgrimmar, in the **Cleft of Shadow**, next to Neeru Fireblade's tent. Horde
  walk right in ([warcraft.wiki.gg](https://warcraft.wiki.gg/wiki/Ragefire_Chasm_(Classic)),
  [icy-veins.com/wow-classic/ragefire-chasm-dungeon-guide](https://www.icy-veins.com/wow-classic/ragefire-chasm-dungeon-guide)).
- **Level range:** ~**13-18** (guides vary 13-21; min entry level 10). Our seeded party is
  **level 30**, comfortably over-leveled — which should make the clear forgiving.
- **Layout:** very short, linear, a single connected cavern of **lava channels**. One of the
  shortest instances in the game; a normal group clears in ~30-60 min, a tight one in ~15-25.
- **Trash:** **Ragefire Troggs** and **Ragefire Shamans** (the shamans heal/cast — kill or
  interrupt first); **Molten Elementals / Earthborers** near the lava; and the trickiest —
  **Searing Blade Warlocks** (~13-15) that **always spawn with a linked Voidwalker minion**,
  usually near Cultists/Enforcers. Those caster+demon packs are where LoS pulls and CC pay off.

**The four bosses** (all ~level 16 elites; abilities are stable across Classic versions):

1. **Oggleflint** (trogg chieftain) — **Cleave** (frontal splash). Comes with **two troggs**;
   CC one add, burn the free add, then Oggleflint. **Tank faces him away from the group** so
   Cleave doesn't hit non-tanks.
2. **Taragaman the Hungerer** (demon) — **stands on/in the lava lake**; **Fire Nova** (AoE
   fire) + **Uppercut** (knockback). **The most dangerous boss for a bot:** position the tank
   **away from ledges/lava** so the knockback doesn't fling anyone into the lava; ranged stay
   at max range to dodge Fire Nova.
3. **Jergosh the Invoker** (orc warlock) — **Immolate** (fire DoT) + **Curse of Weakness**;
   has a companion add. Sustained DoT damage = healing pressure. CC the add, focus Jergosh.
4. **Bazzalan** (satyr) — **Sinister Strike** + **Deadly Poison** (rogue-style, hard
   single-target); flanked by Cultists. Jergosh and Bazzalan are **close together at the
   back** — pull carefully to avoid taking both boss packs at once. CC/split a Cultist, then
   burn Bazzalan.

### ⚠️ How the engine actually treats RFC (read this — it overrides "follow the map")

The repo's dungeon definition (`dungeons/example-ragefire.dungeon.json`) declares the four
bosses as **kill objectives** at internal 3D coordinates (Oggleflint `(-147.5, 38.7, -38.8)`,
Taragaman `(-244.7, 150.1, -18.7)`, Jergosh `(-376.8, 209.2, -21.8)`, Bazzalan `(-384.9,
146.0, +7.8)`), plus a final **reach** objective at Bazzalan's spot (radius 20)
(`example-ragefire.dungeon.json:64-152`). **But the docs are emphatic:**

> **"Boss entry ids define completion and discovery order only. They do not select authored
> boss coordinates"** (`docs/bot-world-state.md:124-126`). The player must **discover** the
> bosses by **Detour navmesh graph exploration** (mark current polygon visited → prefer
> adjacent unvisited → route through the visited component to the nearest unvisited → preempt
> for combat/death/boss sightings → resume) and route to newly-observed hostiles; **boss ids
> verify a kill, they don't hand you a path** (`docs/bot-world-state.md:59-68`; three-lane
> prompt Lane 1).

So a competitive RFC policy **cannot** hardcode "walk to (-244.7, 150.1)." It must explore the
instance legally, fight what engages it, and use the boss list only to know *when it's done*.
The internal coordinates ≠ the Wowhead map coordinates (different systems) — treat the
real-WoW layout above as **orientation for what you'll encounter**, and the graph-exploration
loop as **how you actually traverse**.

### The RFC clear plan (synthesizing both streams)

1. **Enter and form up.** Five characters at the entrance; establish tank as main-assist,
   healer glued to tank. (The three-lane Lane 2 forms the party via real invite/accept.)
2. **Explore forward** via graph frontier, tank first-contact. Because we're **level 30 vs.
   ~16 content**, most trash is trivial — but the **Searing Blade Warlock + Voidwalker** packs
   still warrant LoS pulls / focus-fire to avoid a loose caster on the healer.
3. **Clear-then-speed.** The priority is **all four bosses dead** (partial < 1.0 no matter
   what); only once clears are reliable does shaving `clear_seconds` (chain-pulling, skipping
   non-blocking trash, minimal drinking) pay off.
4. **Boss discipline** as above — face bosses away from the group, keep ranged out of Fire
   Nova, keep the tank off lava edges on Taragaman, don't accidentally chain Jergosh+Bazzalan.
5. **Wipe recovery without cheating.** A death means release → ghost run → re-enter → re-form
   → reclaim → resume — **no DB repair, no instance reset** (three-lane Lane 2; the
   client-honesty contract). The episode budget is `max_ticks/tick_rate` (10000/0.1), **not**
   the 7200s respawn timer (that just keeps a killed boss readable as dead — see the gameplay
   doc).

---

## Part 6 — Pro tips & where a policy wins

**Universal pro tips** (real-WoW, apply to the XP game and the party's solo competence):

- **First Aid on everyone** — mana-free healing, the biggest downtime cut for warriors/rogues.
- **Log out in an inn/city** to bank 4×-rate rested XP (2× kill XP when spent).
- **Fight yellow/orange when safe** (+up to 20% XP); **never solo elites/group quests** (2× XP
  for far more risk).
- **Weapon-skill discipline** — don't equip an upgrade of an *untrained* weapon type mid-grind
  (you'll miss constantly until skill catches up).
- **Batch quests + turn-ins; skip isolated/low-value quests;** hearth to the active hub.
- **Bag/vendor/repair discipline** — biggest bags, vendor grays, keep durability out of the
  red (a red weapon does reduced damage), repair every town visit.
- **Train ranks promptly** — skipping upgrades to save gold usually costs more in
  efficiency/downtime than the trainer fee.
- **Use terrain/LoS** to neutralize casters and split packs; **snare runners** so they don't
  drag in adds.

**Where a purpose-built policy beats the bundled bots:**

- **RFC party coordination.** The engine gives per-role rotations and navigation, but the
  *coordination policy* — pull sizing that respects mob links, the threat-ramp delay against a
  rage-starved warrior, focus-fire order, healer mana-gating the pace, boss positioning — is
  where a policy adds the most. A single brain controlling all five can enforce **perfect
  assist discipline and zero threat-greed**, which is the biggest edge over human pugs.
- **Exploration efficiency for the clear.** Faster, safer graph-frontier routing to the four
  bosses (and skipping non-blocking trash once clears are reliable) directly shaves
  `clear_seconds`, the round-score tiebreaker.
- **Leveling route + downtime tuning** for the XP game — better zone/farm selection, tighter
  drink/heal thresholds, fewer deaths (each death is XP loss + a corpse run + risk of the
  res-sickness spiral).

**The build philosophy to respect** (from King Nimrod's plan,
`player/king_nimrod/plan.md:483-487`): **"Do not add higher-level intelligence until the
lower-level loop is boring."** Perception → walk → reach melee → fight → loot → recover, made
*boring* (reliable), before layering party coordination and dungeon tactics on top. RFC clears
fail on the boring stuff (a caster loose on the healer, a knockback into lava, a rage-starved
tank losing a mob) far more than on clever tactics — so **reliability first, speed second**,
which is also exactly what the clear-then-speed score rewards.

---

## Sources

**Real Vanilla WoW (web):**
- Experience / mob XP / con colors: [warcraft.wiki.gg/wiki/Experience_point](https://warcraft.wiki.gg/wiki/Experience_point),
  [/wiki/Mob_experience](https://warcraft.wiki.gg/wiki/Mob_experience), [/wiki/Level](https://warcraft.wiki.gg/wiki/Level)
- Rested / rules: [/wiki/Rested](https://warcraft.wiki.gg/wiki/Rested),
  [/wiki/Weapon_skill](https://warcraft.wiki.gg/wiki/Weapon_skill), [/wiki/Pull](https://warcraft.wiki.gg/wiki/Pull),
  [/wiki/Aggro](https://warcraft.wiki.gg/wiki/Aggro), [/wiki/First_Aid](https://warcraft.wiki.gg/wiki/First_Aid),
  [/wiki/Five_second_rule](https://warcraft.wiki.gg/wiki/Five_second_rule),
  [/wiki/Resurrection_sickness](https://warcraft.wiki.gg/wiki/Resurrection_sickness),
  [/wiki/Threat](https://warcraft.wiki.gg/wiki/Threat)
- Leveling + class guides: [icy-veins.com/wow-classic/leveling-guide](https://www.icy-veins.com/wow-classic/leveling-guide)
  and the per-class Classic leveling guides (hunter/warlock/mage/rogue/shaman/priest/warrior)
- RFC: [icy-veins.com/wow-classic/ragefire-chasm-dungeon-guide](https://www.icy-veins.com/wow-classic/ragefire-chasm-dungeon-guide),
  [wowhead.com/classic/zone=2437/ragefire-chasm](https://www.wowhead.com/classic/zone=2437/ragefire-chasm),
  [warcraft.wiki.gg/wiki/Ragefire_Chasm_(Classic)](https://warcraft.wiki.gg/wiki/Ragefire_Chasm_(Classic)),
  [wowisclassic.com/en/dungeon-guide/ragefire-chasm](https://www.wowisclassic.com/en/dungeon-guide/ragefire-chasm/)
- *Version-sensitivity:* Season of Mastery raised leveling XP rates ([/wiki/Season_of_Mastery](https://warcraft.wiki.gg/wiki/Season_of_Mastery));
  res-sickness wiki values are retail (1min/50%), not 1.12 (~10min/25%); RFC was rebuilt in Cataclysm — ignore retail RFC.

**Engine (repo, `~/coding/coworlds/coworld-vanilla-wow`):**
`player/bots/leveling/planner.nim`, `targets_and_recovery.nim`, `routing_and_actions.nim`,
`model.nim`; `player/bots/leveling_profiles/*.json` + `player/bots/leveling/profiles/durotar_troll_shaman.nim`;
`player/bots/rotations.nim`; `dungeons/example-ragefire.dungeon.json`; `docs/bot-world-state.md`;
`docs/king-richard-three-lane-prompt.md`; `player/king_nimrod/plan.md`. (These are cross-checked
against the reference docs in this same `docs/` directory — start with
[`vanilla-wow-gameplay.md`](vanilla-wow-gameplay.md).)
