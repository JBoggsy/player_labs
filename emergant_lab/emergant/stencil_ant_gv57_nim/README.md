# stencil-ant for Emerg-ant GameVersion 57

This is the active native Nim player. It is derived directly from the canonical
Emerg-ant 0.9.1 baseline at commit
`1e0be3f1ecabf2fc70adb8af81818a9947281cc9`, with observation telemetry and offset
carrier delivery lanes.

Build from the repository root:

```sh
emergant_lab/tools/build_player.sh stencil-ant
```

The `linux/amd64` image exposes `/bin/baseline`, matching the live Coworld manifest.
Uploading creates an inert policy version. Never submit it to a league without
James's explicit approval.
