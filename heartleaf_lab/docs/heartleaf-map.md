# Heartleaf map — fixed layout reference (gardens, houses, harvest mechanic)

**The map is FIXED, not regenerated.** Verified in `coworld-heartleaf/src/heartleaf.nim`: the
world loads from static assets `data/map.aseprite` (walk/bottom/overhang layers) + the named
rectangles in `data/map.resource` (`loadWorldMap`, `loadGardens` @ src line 440). Nothing about
the layout is procedural. The league variant's `seed: 4731713` only drives **which gardens hold
food each day** and how much — **garden and house *locations never change*.** So a player can
navigate to known garden coordinates instead of waiting to *see* a garden (which it usually
can't at spawn — it starts inside/near its own house).

> **Source caveat:** these coordinates are parsed from the **0.1.0** public repo clone
> (`data/map.resource`); the deployed league game is **0.1.10**. Map layout almost never moves
> across patch versions, but **verify against 0.1.10** before trusting these as nav targets —
> decode a real replay/scene frame (we have `replay.json` per eval episode; the SDK
> `SpriteWorld.apply_frame` decodes the BitWorld sprite bytes) and confirm a few garden object
> world-positions match. This also validates the **coordinate-frame alignment**: these are
> map-asset pixel coords; cady perceives world coords as `object.screen_xy + camera` (camera =
> `(-obj1.x, -obj1.y)` from the world-map object id 1). Confirm cady's world frame == this
> map-asset frame (the `SELF_OFFSET`/camera-origin calibration) — if there's a constant offset,
> apply it once.

## Harvest mechanic (how you collect a garden)

From `heartleaf.nim` `gardenInReach`/`collectGarden`/`tryCollect` + `common.nim`:

- A garden is collectable when **all** hold: (1) the player is on the **main outdoor map**
  (`mapIndex == MainMapIndex == 0` — *not* inside a house), (2) the garden **`hasFood()`**, and
  (3) the player's **feet** are within **`InteractionRadius == 40` px** of the garden rect
  (squared distance ≤ `1600`; `feet.rectDistanceSquared(garden.rect) <= 40²`).
- **Feet** = `(spriteX + PlayerBoxOffsetX + PlayerBoxWidth/2, spriteY + PlayerBoxOffsetY +
  PlayerBoxHeight/2)` — the gnome's foot-center, not its sprite origin. So the interaction
  radius is generous: you don't have to stand *on* the 9×9 garden tile, just get your feet
  within 40 px of it, then press **A** — `collectGarden` sweeps *all* food from that garden into
  your inventory at once. `gardenInReach` returns the **nearest** in-reach garden with food.
- Food: each garden starts with `GardenStartFoodCount = 1` item (a random veggie slot); the
  seeded RNG re-seeds gardens per day. A garden shows the `"garden marker"` sprite (object base
  4000) **only while it holds food** — which is why an unfed garden is invisible to perception.

## Gardens — 39 fixed 9×9 rects (center x,y in map-asset pixels)

```
(42,377)  (69,392)  (74,715)  (87,749)  (101,408) (105,579) (127,372) (138,529)
(158,198) (196,353) (234,188) (234,847) (263,408) (268,455) (272,92)  (280,651)
(289,806) (309,905) (313,500) (388,511) (409,173) (418,145) (418,230) (428,498)
(447,814) (454,392) (465,455) (490,118) (517,819) (527,202) (527,496) (543,368)
(545,559) (590,901) (592,232) (605,401) (629,594) (671,840) (711,373)
```

(Each rect is `9×9`; center = `left + 4, top + 4`. Full rects are in `data/map.resource`
blocks named `garden`.) The map spans roughly x∈[38,711], y∈[88,905].

## Houses — 9 fixed door rects (31×24), `houseN` → seat `N-1`

Player *N* spawns at house *N* (manifest: "Player 1 spawns near house 1…"), so seat index
`s` (0-based) owns `house(s+1)`. Fixed gnome names by seat: Ivan, Anton, Yura, Sasha, Maxim,
Nikita, Vova, Dima, Egor.

| house | seat | gnome | door center (x,y) | rect (l,t,w,h) |
|---|---|---|---|---|
| house1 | 0 | Ivan   | (237,811) | (222,799,31,24) |
| house2 | 1 | Anton  | (103,548) | (88,536,31,24) |
| house3 | 2 | Yura   | (142,349) | (127,337,31,24) |
| house4 | 3 | Sasha  | (185,181) | (170,169,31,24) |
| house5 | 4 | Maxim  | (376,141) | (361,129,31,24) |
| house6 | 5 | Nikita | (572,207) | (557,195,31,24) |
| house7 | 6 | Vova   | (594,370) | (579,358,31,24) |
| house8 | 7 | Dima   | (597,578) | (582,566,31,24) |
| house9 | 8 | Egor   | (502,782) | (487,770,31,24) |

Other named regions in `map.resource`: `market`, `water`, `honey` (×3), `smoke`/`smoke stack`
(×6) — decorative/other, not gardens.

## Why this matters for cady (the v1 zero-score bug → v2 fix)

cady v1 scored 0 because it only enters Gather when a food garden is *currently perceived*, and
at spawn it sees none, so it went straight to Host and held with an empty inventory. With the
map fixed, **v2 can drive off these known coordinates**: pick the nearest garden(s) by world
position and navigate there to harvest (press A within 40 px), then go to its own `houseN` to
host — no reliance on happening to see a garden. First validate the coordinate-frame alignment
(caveat above), ideally by decoding a 0.1.10 replay frame.
