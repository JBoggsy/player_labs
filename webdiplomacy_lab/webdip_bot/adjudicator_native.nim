## Integer/boolean counterpart of fastadj.Adjudicator; keep resolution order identical.
import std/[tables, sequtils]
import nimpy

type
  Unit = tuple[country: int, province: int, kind: string]
  OrderKind = enum hold, move, supportHold, supportMove
  Order = object
    kind: OrderKind
    source, target: int
  Resolver = ref object
    units: seq[Unit]
    orders: seq[Order]
    at: Table[int, int]
    movesInto: Table[int, seq[int]]
    supportsHold, supportsMove: seq[seq[int]]
    headToHead: seq[int]
    state: seq[int]
    outcome: seq[bool]
    deps: seq[int]

const
  unresolved = 0
  guessing = 1
  resolved = 2

proc resolve(a: Resolver, nr: int): bool
proc decide(a: Resolver, nr: int): bool

proc resolve(a: Resolver, nr: int): bool =
  if a.state[nr] == resolved:
    return a.outcome[nr]
  if a.state[nr] == guessing:
    if nr notin a.deps:
      a.deps.add(nr)
    return a.outcome[nr]
  let old = a.deps.len
  a.outcome[nr] = false
  a.state[nr] = guessing
  let first = a.decide(nr)
  if a.deps.len == old:
    if a.state[nr] != resolved:
      a.outcome[nr] = first
      a.state[nr] = resolved
    return first
  if a.deps[old] != nr:
    a.deps.add(nr)
    a.outcome[nr] = first
    return first
  for d in a.deps[old ..< a.deps.len]:
    a.state[d] = unresolved
  a.deps.setLen(old)
  a.outcome[nr] = true
  a.state[nr] = guessing
  let second = a.decide(nr)
  if first == second:
    for d in a.deps[old ..< a.deps.len]:
      a.state[d] = unresolved
    a.deps.setLen(old)
    a.outcome[nr] = first
    a.state[nr] = resolved
    return first
  let cycle = a.deps[old ..< a.deps.len]
  for d in cycle:
    a.state[d] = unresolved
  a.deps.setLen(old)
  for d in @[nr] & cycle:
    if a.orders[d].kind == move:
      a.outcome[d] = true
      a.state[d] = resolved
  return a.resolve(nr)

proc supportHolds(a: Resolver, nr: int): bool =
  let country = a.units[nr].country
  let province = a.units[nr].province
  let order = a.orders[nr]
  for attacker in a.movesInto.getOrDefault(province):
    if a.units[attacker].country == country:
      continue
    if order.kind == supportMove and a.units[attacker].province == order.target:
      if a.resolve(attacker):
        return false
      continue
    return false
  return true

proc supportCount(a: Resolver, supports: seq[int], excludeCountry = -1): int =
  for supporter in supports:
    if excludeCountry != -1 and a.units[supporter].country == excludeCountry:
      continue
    if a.resolve(supporter):
      inc result

proc attackStrength(a: Resolver, nr: int): int =
  let j = a.at.getOrDefault(a.orders[nr].target, -1)
  let head = a.headToHead[nr]
  if j == -1 or (head == -1 and a.orders[j].kind == move and a.resolve(j)):
    return 1 + a.supportCount(a.supportsMove[nr])
  if a.units[j].country == a.units[nr].country:
    return 0
  return 1 + a.supportCount(a.supportsMove[nr], a.units[j].country)

proc preventStrength(a: Resolver, nr: int): int =
  let head = a.headToHead[nr]
  if head != -1 and a.resolve(head):
    return 0
  return 1 + a.supportCount(a.supportsMove[nr])

proc holdStrength(a: Resolver, province: int): int =
  let j = a.at.getOrDefault(province, -1)
  if j == -1:
    return 0
  if a.orders[j].kind == move:
    return (if a.resolve(j): 0 else: 1)
  return 1 + a.supportCount(a.supportsHold[j])

proc moveSucceeds(a: Resolver, nr: int): bool =
  let dest = a.orders[nr].target
  let attack = a.attackStrength(nr)
  let head = a.headToHead[nr]
  if head != -1:
    if attack <= 1 + a.supportCount(a.supportsMove[head]):
      return false
  elif attack <= a.holdStrength(dest):
    return false
  for other in a.movesInto.getOrDefault(dest):
    if other != nr and attack <= a.preventStrength(other):
      return false
  return true

proc decide(a: Resolver, nr: int): bool =
  case a.orders[nr].kind
  of move: return a.moveSucceeds(nr)
  of supportHold, supportMove: return a.supportHolds(nr)
  of hold: return true

proc adjudicate(units: seq[Unit], orders: PyObject): (seq[bool], seq[bool]) {.exportpy.} =
  let n = units.len
  let a = Resolver(units: units, orders: newSeq[Order](n), state: newSeq[int](n),
                   outcome: newSeq[bool](n), headToHead: newSeqWith(n, -1),
                   supportsHold: newSeq[seq[int]](n), supportsMove: newSeq[seq[int]](n))
  for i, unit in units:
    a.at[unit.province] = i
    let raw = orders[i]
    let kind = raw[0].to(string)
    case kind
    of "M": a.orders[i] = Order(kind: move, target: raw[1].to(int))
    of "SH": a.orders[i] = Order(kind: supportHold, target: raw[1].to(int))
    of "SM": a.orders[i] = Order(kind: supportMove, source: raw[1].to(int), target: raw[2].to(int))
    else: a.orders[i] = Order(kind: hold)
  for i, order in a.orders:
    if order.kind == move:
      a.movesInto.mgetOrPut(order.target, @[]).add(i)
      let j = a.at.getOrDefault(order.target, -1)
      if j != -1 and a.orders[j].kind == move and a.orders[j].target == units[i].province:
        a.headToHead[i] = j
    elif order.kind == supportHold:
      let j = a.at.getOrDefault(order.target, -1)
      if j != -1 and a.orders[j].kind != move:
        a.supportsHold[j].add(i)
    elif order.kind == supportMove:
      let j = a.at.getOrDefault(order.source, -1)
      if j != -1 and a.orders[j].kind == move and a.orders[j].target == order.target:
        a.supportsMove[j].add(i)
  var moved = newSeq[bool](n)
  var dislodged = newSeq[bool](n)
  for i in 0 ..< n:
    moved[i] = a.orders[i].kind == move and a.resolve(i)
  for i in 0 ..< n:
    if moved[i]: continue
    for attacker in a.movesInto.getOrDefault(units[i].province):
      if moved[attacker]:
        dislodged[i] = true
        break
  return (moved, dislodged)
