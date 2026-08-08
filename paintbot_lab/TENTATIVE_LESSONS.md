# CTF tentative lessons — session buffer

**Session started:** 2026-08-07 20:29. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`ctf_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (CTF-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### Stencil discards enemy-loadout intel the wire already gives it

Evidence: `identity <color> <name>[ shield][ nade] <weapon>` is emitted in the PLAYER
view for every visible player (`global.nim:5734+`, called with `viewerIndex = playerIndex`
at `global.nim:6223`), and the suffixed forms are in the golden manifest
(`tests/label_manifest.txt:40-43`) so they are contract, not chrome. Stencil's
`identityBadges` (`perception.nim:92-98`) splits off the name token and drops the rest.
`attachOverheadState` also collects `grenade carried` / `spray can carried` but only uses
them to detect SELF loadout (`perception.nim:277-279`) — enemy nade/weapon state is parsed
and thrown away.

Status: candidate improvement, not measured. Knowing a visible enemy holds a grenade or a
spray can is targeting/engagement-relevant.

### `enemy.shielded` in stencil means "SPENT shield", not "shielded"

Evidence: `global.nim:5216-5220` emits `shield carried` only when `player.shieldHp <= 0`
— the armor is gone but the 3x fire slowdown persists. An ACTIVE shield renders the bubble
instead (`"shield bubble"` / `"shield bubble hit"`, inline strings in `global.nim`, absent
from `labels.nim` AND from the golden manifest). Stencil sets `enemy.shielded` from
`shield carried` (`perception.nim:281-286`) and then treats it as a hardened/avoid signal
in `fight.nim:133` and `action.nim:336`.

Status: semantics look inverted from intent; needs a read of what those weights encode
before calling it a bug. The identity badge's `shield` token is the reliable
"has a shield at all" channel.

### The label manifest beats RULES.md when they disagree — RULES.md says so itself

Evidence: `docs/RULES.md:138-142` documents the badge as `identity <color> <name>` with no
loadout suffixes; `tests/label_manifest.txt` carries `identity <color> <name> shield gun`
etc. RULES.md line ~970 states outright that the manifest is authoritative and the prose
is the stale surface ("that is exactly how the `heart`/`flag` claim above went wrong").
Reading only RULES.md would have produced a wrong answer about what a policy can observe.

Status: check `tests/label_manifest.txt` + `src/ctf/labels.nim` before trusting RULES prose
on any observation question.

### Some readable player-view labels are NOT in the contract vocabulary

Evidence: `"shield bubble"` / `"shield bubble hit"` are emitted inline in `global.nim`
under the same per-viewer visibility gate as contract labels, but appear in neither
`labels.nim` nor `tests/label_manifest.txt`. `labels.nim`'s header explains the split
deliberately: contract labels are hoisted, chrome is not, because "the broadcast view is
free to re-cut its chrome any week."

Status: a policy CAN read these, but doing so takes an unpinned dependency on a label the
engine owes no stability promise for.

### The lab's game pin went stale in under a day — deployed paintbot is 0.7.215, pinned is 0.7.211

Evidence: `tools/versions.env` pins `PAINTBOT_GAME_VERSION=0.7.211` "verified 2026-08-07";
`uv run coworld list` today shows `paintbot 0.7.215 canonical yes` with 212/213/214 in between.
Upstream PR #256 explains why: manifest merges **auto-upload the next paintbot version**, so the
deployed version advances without anyone in this lab acting. Four versions in ~a day.

Status: the gameplay doc already says "re-resolve the canonical game before relying on these live
values" — that instruction is load-bearing, not boilerplate. Run `uv run coworld list | grep paintbot`
at the START of any game-mechanics work.

### Two new config-gated items landed upstream that the lab has no model for: perks and cardboard barriers

Evidence: PR #252 (team perks: armor/scope/grenade/thruster/luck) and PR #255 (cardboard barriers —
placeable half-hex cover that BLOCKS PAINT but not sight, 10 hits to shred). Both are in deployed
0.7.215's `config_schema` (verified by downloading the canonical manifest), both default OFF, and no
deployed variant config sets them. Campaign cells CAN override (that is exactly why #256 declared
`barrierPickups` in the schema — metta's `_cell_overrides` silently drops undeclared keys).

Status: `armor` (+1 max hp) is the one that would change spray-avoidance math — 4 hp survives a
3-damage spray. Not urgent while default-off, but it is a live tripwire.

### Stencil computes a `danger` grid every tick that NOTHING reads

Evidence: `belief_update.nim:225-293` builds, decays, dilates and stamps `belief.danger`; the only
other references anywhere are `trace.nim:519-532` (dump it). `nav.nim`'s A* costs are pure distance —
`astar` never looks at danger. So the whole danger pipeline is compute + telemetry, zero behavior.

Status: either wire it into pathing or delete it. Do NOT quietly fold it into an unrelated behavior
change — global path-cost changes are unvalidatable inside a single-behavior A/B.

### `iHaveShield` is sourced from `shield carried`, which the engine emits only when the shield is SPENT

Evidence: `perception.nim:337` sets `iHaveShield` from the `shield carried` overhead marker;
`global.nim:5216` emits that marker only when `player.shieldHp <= 0`. An ACTIVE shield draws the
bubble instead. So `iHaveShield` is true exactly when the shield no longer protects.
Consequence at `items.nim:70-72` (the "already have one, don't fetch" gate): stencil declines to
refill a shield precisely when it is spent, and wastes detours fetching one while its bubble is up.

Status: the own `identity` badge's `shield` token (and `lives <hp>hp x<lives>`, which reads past the
base cap) are the correct channels. Stencil parses neither.

### A spray-can carrier cannot fire the gun at all — the counter to a sprayer is range, not force

Evidence: `sim.nim:699` — `canFire` requires `not shooter.hasPlasmaArc`. Combined with
`PlasmaArcReach + PlasmaArcBodyRadius = 187px` (`sim_types.nim:505,517`) versus `gunRange 1300`, a
spray carrier is completely harmless outside 187px and outranged 7:1 inside it.

Status: makes "keep out of spray range" a strictly dominant policy against that enemy — there is no
punish for retreating. Worth checking whether the same asymmetry holds for other loadouts.

### Equal top speed means a keep-out radius must be PREVENTIVE, not reactive

Evidence: `MaxSpeed = 704` is per-player with no per-weapon modifier (`sim_types.nim:320`), i.e.
2.75 px/tick for both sides (`MaxSpeedPxTick` in stencil's config.nim agrees). A committed chaser
therefore never loses ground to radial flight — escape only comes from the 20-tick recharge window
(`PlasmaArcResetTicks`) or an LOS break. Carriers are worse off still at `carrierSpeedPct 70`.

Status: any "flee the threat" rung has to trigger outside the lethal radius with hysteresis, or it
degenerates into orbiting the boundary.

### Stencil's ally-coverage map has the same fate as the danger grid: computed for the trace, read by nothing

Evidence: `trace.nim:95` `coveredGrid` builds conservative instantaneous ally vision (observable
16-step heading, narrowest deployed 45-degree cone, exact pixel-wall LoS) — and is referenced
only at `trace.nim:533`, to dump it. Two separate world-model products in this policy exist purely
as telemetry.

Status: this is a PATTERN worth naming, not two coincidences. When adding a belief product, decide
up front whether a behavior consumes it; a rich trace makes an unused computation look load-bearing
in the viewer. v59 promotes coverage to a real `coverageAt()` primitive; danger is still orphaned.

### I built a finding on a stale engine COMMENT instead of tracing the state transition — and it was wrong

Evidence: `global.nim` says, at the `shield carried` emit site, "once it is spent the bubble pops
and the marker takes over, because the shield's fire slowdown is still in effect." I took that as
the engine's behavior and wrote a whole design section around "`shield carried` means SPENT shield".
`absorbDamage` (`sim.nim:802-818` at 6c7a4c0e, identical at 9dedac0e) actually does the opposite:
when the layer breaks it sets `hasShield = false` and re-clamps the cooldown — "A broken shield is
GONE: the carry icon, the ' shield' label, and the fire slowdown all end with the bubble."

Status: the comment contradicts the code sitting ~4000 lines away in the same repo. CLAUDE.md's rule
("when documentation and code disagree, determine which source is stale before relying on either")
applies to *engine comments*, not just prose docs. For a state-machine question, trace the writes to
the field. Grepping `hasShield = ` would have taken 10 seconds and settled it.

### `shield carried` is unreachable — so stencil's shield awareness is silently dead, not inverted

Evidence: the emit site guards `if not player.hasShield: continue`, then only emits the marker when
`player.shieldHp <= 0`. Since `absorbDamage` clears `hasShield` exactly when `shieldHp` hits 0, and
pickup sets both together (`sim.nim:1865`), `hasShield` implies `shieldHp > 0` — the branch cannot
fire. Stencil sources `enemy.shielded` and `iHaveShield` from that marker alone
(`perception.nim:281-286,337`), so both are permanently false. The shield weight in
`fight.nim:133` and the gate at `action.nim:336` are dead code, and `items.nim:71` never skips a
shield it already holds.

Status: a "dead observable" fails in the quietest possible way — the weight exists, the trace field
exists, the value is just always false. When adopting a label, verify the producer can actually reach
its emit branch, not merely that the label is in the vocabulary.

### Citations pinned to the wrong ref: I verified against 0.7.211 and cited 0.7.215

Evidence: the v59 spec opens "Every engine citation below is `file:line` in that ref [6c7a4c0e]",
but most were read from the cached 9dedac0e tree before the re-pin. PRs 252/255 inserted code into
`sim.nim` and `labels.nim`, shifting nearly every line number (`labelIdentity` 406 -> 477;
`canFire` 699 -> 820; shield pickup 1632 -> 1850).

Status: re-pinning the game invalidates every line citation written before it. Either re-verify
citations after a re-pin, or cite by symbol name rather than line.
