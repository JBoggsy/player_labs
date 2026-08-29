# stencil-ant

> **Archived and incompatible with the live game.** This implementation targets the
> retired Emerg-ant 0.6.1 / GameVersion 52 cache-race contract. Use
> [`../stencil_ant_gv57_nim/`](../stencil_ant_gv57_nim/) for current work.

`stencil-ant` is the native Nim Emerg-ant adaptation of Paintbot Stencil v68.

The fork retains Stencil's retained Sprite-v1 client, episode-scoped walkability and
navigation, targeting, combat, items, and trace pipeline. Its objective contract is
Emerg-ant-specific:

- parse `food <team> cache` and `food <team> carried`;
- repeatedly raid the enemy cache and return food to the home capture zone;
- never retire a cache after a delivery or team wipe;
- assign three defenders and five foragers in the fixed eight-seat colony;
- observe and trace public scout/food pheromones without following them yet;
- use GV52's five lives, 1,050px gun range, and 60-degree vision half-angle;
- leave early-defense and squad-command experiments disabled for the attributable v1.

Build from the repository root:

```sh
emergant_lab/tools/build_player.sh stencil-ant
```

The image is `players-stencil-ant:dev`, `linux/amd64`, with `/bin/stencil-ant` as
its entrypoint. Uploading creates an inert version; never submit without James's
explicit approval.
