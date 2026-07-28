# Battle plan schema

A battle plan is a JSON document — a sequence of **phases** drawn over the arena,
speaking the POI/area vocabulary (`ctf/beacon/mapdata/points_of_interest.json`).
Plans live in this directory, one file each, edited with
`tools/plan_editor.html` (serve `ctf_lab/`: `python3 -m http.server -d ctf_lab`,
open `/tools/plan_editor.html`). They are the co-general artifact: either party
(James or the agent) proposes, the other edits phases and annotates, converge in
the `notes` fields. Today they are human-readable documents; the schema
deliberately accumulates optional machine-readable tags for beacon's plan
interpreter (see WORKING_CONTEXT).

## Document

```jsonc
{
  "name": "staged_push_top",          // snake_case, unique in this dir
  "author": "claude | james | both",
  "status": "proposal | agreed | superseded",
  "summary": "one-paragraph intent of the whole plan",
  "team": "red",                      // plans are authored from red's POV;
                                      // blue mirrors via x -> 1234-x
  "groups": {                         // starting seat assignment (seats 0..7)
    "pushers": [3, 4, 5, 6, 7],
    "rear":    [0, 1, 2]
  },
  "phases": [ ... ]                   // ordered
}
```

## Phase

```jsonc
{
  "name": "advance_to_midfield",
  "intent": "prose: what this phase accomplishes and why",
  "entry": {                          // when the phase begins
    "prose": "when the rear group reaches the lineup",   // required
    "tag": "presence(red_rally_top)>=3"                  // optional, machine hint
  },
  "exit":  { "prose": "...", "tag": "..." },             // optional
  "splits": {                         // optional group surgery AT phase start:
    "pushers": { "flank_n": [3, 4], "flank_s": [5, 6, 7] }
  },                                  // splits replace the parent group from
                                      // this phase on; later phases may split
                                      // further or never mention a group (it
                                      // keeps its last orders)
  "orders": [                         // one per group active this phase
    { "group": "flank_n", "kind": "move",  "to": "midfield_top" },
    { "group": "flank_s", "kind": "move",  "to": {"x": 520, "y": 480} },
    { "group": "rear",    "kind": "hold",  "at": "red_rally_top",
      "facing": "top_corridor" },     // optional aim/watch direction
    { "group": "rear",    "kind": "watch", "at": "red_lineup" }  // secondary
  ],
  "enemy_belief": [                   // where we THINK they are/will be
    { "at": "blue_rally_top", "count": 3, "note": "their lane defense" },
    { "at": {"x": 900, "y": 329}, "count": 5 }
  ],
  "notes": []                         // the back-and-forth: append, don't edit
                                      // [{"who": "james", "text": "..."}]
}
```

## Conventions

- **Locations** are either a POI/area **name** (a reference — moves when the map
  is re-curated; preferred) or a raw `{x, y}` (for one-off spots not worth
  naming; if one recurs across plans, promote it to the POI map).
- **Order kinds:** `move` (arrow), `hold` (position marker; optional `facing`),
  `watch` (secondary attention marker, e.g. rear glancing at the advance).
  With `BEACON_POSTS=1`, a primary move/hold order's target becomes the centre
  of a nearby-post search after the bot enters its arrival radius. `facing`
  resolves to a point and supplies the static threat-axis prior for that search;
  fresh enemy tracks and a danger gradient can override it. `watch` remains
  descriptive rather than a primary movement order.
- **Groups** are named sets of seats. The document `groups` block is the
  starting assignment; a phase's `splits` reassigns from that phase onward.
  Names are free-form; keep them evocative (`pushers`, `flank_n`, `bait`).
- **Seats not in any group** (after a split you may drop one) default to the
  static role split — say so in the phase intent if you rely on it.
- **entry/exit tags** use the global-signal vocabulary (all fog-independent):
  `tick>=N`, `enemy_lives<=N`, `own_deaths>=N`, `presence(<poi>)>=N`,
  `flag(own|enemy)==home|taken`. Prose is authoritative today; tags are hints
  for the interpreter; currently only `tick`, `enemy_lives`, and `own_deaths`
  are machine-evaluated.
