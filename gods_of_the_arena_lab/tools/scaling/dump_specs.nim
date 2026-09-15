import std/[json, strutils]
import content

var root = newJObject()
var heroes = newJArray()
for class in HeroClass:
  let s = class.heroSpec
  var abils = newJArray()
  for slot in HeroAbilitySlot:
    let ab = heroAbility(class, slot)
    let a = ab.abilitySpec
    abils.add %*{
      "slot": slot.ord, "id": ab.ord, "name": a.name, "kind": $a.kind, "casting": $a.casting,
      "charges": a.charges, "rechargeTicks": a.rechargeTicks, "castTicks": a.castTicks,
      "projectileSpeed": a.projectileSpeed, "cooldownTicks": a.cooldownTicks, "manaCost": a.manaCost,
      "range": a.range, "damage": a.damage, "heal": a.heal, "restore": a.restore,
      "fromCaster": a.fromCaster, "areaShape": $a.area.shape, "areaRadius": a.area.radius,
      "areaInnerRadius": a.area.innerRadius, "areaWidth": a.area.width, "areaLength": a.area.length, "areaAngle": a.area.angle
    }
  heroes.add %*{
    "id": class.ord, "name": s.name, "role": s.role, "attackStyle": $s.attackStyle,
    "baseHp": s.baseHitPoints, "hpPerLevel": s.hitPointsPerLevel, "baseMana": s.baseMana, "manaPerLevel": s.manaPerLevel,
    "baseDamage": s.baseDamage, "damagePerLevel": s.damagePerLevel, "baseMove": s.baseMovePerTick, "movePerLevel": s.movePerLevel,
    "attackRange": s.attackRange, "attackTicks": s.attackTicks, "abilities": abils
  }
root["heroes"] = heroes
var items = newJArray()
for it in Item:
  if it == NoItem: continue
  let sp = it.itemSpec
  items.add %*{"id": it.ord, "name": sp.name, "kind": $sp.kind, "cost": sp.cost, "maxHp": sp.maxHp, "maxMana": sp.maxMana, "damage": sp.damage, "movePerTick": sp.movePerTick, "heal": sp.heal, "restore": sp.restore, "strike": sp.strike}
root["items"] = items
root["tickRate"] = %TickRate
root["maxItemStack"] = %MaxItemStack
echo root.pretty
