# Paintbot documentation audit — 2026-08-05

> **Superseded live snapshot.** This audit accurately records its 2026-08-05
> cutoff, but its 0.7.199, round-313, v47, and equal-block scheduler conclusions
> are no longer current. See
> [`2026-08-06-game-contract-audit.md`](2026-08-06-game-contract-audit.md) for
> Paintbot 0.7.206/GV40 and campaign 7+7+1+1 seating.

## Scope

Audited every repository-owned Markdown file under `paintbot_lab`, the two
checked-in experience-request JSON examples, documentation-bearing comments in
the Paintbot tools and shared belief-viewer bundler, and the lab-root entry
points that route contributors into Paintbot.

The durable inventory and navigation result is [`../README.md`](../README.md).

## Authoritative evidence

- Canonical live Coworld: `paintbot:0.7.199`,
  `cow_80409b8a-58a6-46bc-ba57-39ee4e0ab106`, source
  `2c6bec20c46a695a061b25e1bb11a158a5e0e1f4`.
- Live manifest variant configs and config schema from `coworld show`.
- Paintbot league `league_b8fa9b35-ac22-48cf-a03f-07b397aff1c7`: campaign
  enabled, ladder disabled, four-entrant `team_n` scheduler metadata,
  `[[0,2],[1,3]]` 2v2 alliances, and 3:1:1 explicit variant rotation.
- Campaign board round 313: 100 map tuples; 45 two-team / 55 FFA cells; map-ref
  counts 20 `2v2`, 25 `default`, 26 `4ffa`, 29 `4ffa8`.
- Current policy lifecycle readback: `stencil:v47` active champion via
  submission `sub_3767de5d-80d1-47c2-8053-a089517581d4` and membership
  `lpm_b1bfb2b5-e42b-4e9c-9463-783ef2248585`.
- Tool parsers/help for `self_play.py`, `render_nav.py`,
  `compare_stencil.py`, `build_player.sh`, Coworld XP requests, campaign, and
  policy lifecycle.
- Stencil source layout and `config.nim` (111 currently declared `STENCIL_*`
  variables).

Live facts are a verification snapshot, not constants. Current-reference docs
say to re-resolve them before operations.

## Findings and resolutions

| priority | finding | resolution |
| --- | --- | --- |
| P1 | README/AGENTS/working context still presented v21/v22 as current instead of v47 | Updated current-state entry points and version provenance. |
| P1 | Gameplay docs described Paintbot 0.7.184/0.7.190, while canonical is now 0.7.199 | Updated current references with dated live evidence and refresh warnings. |
| P1 | Current docs said `default` was a fixed classic arena; 0.7.199 sets `mapPath: gen` | Removed the fixed-arena claim from current docs; preserved it only in explicitly historical recon. |
| P1 | Current docs taught old 7+7+1+1 captain/filler seating | Replaced with the current four-entrant, full-seat tournament contract and 2v2 alliance mapping. |
| P1 | 1v1 commands were presented as evaluation/screens | Relabeled all local/1v1 examples as non-representative debug probes and linked the normative hosted-eval spec. |
| P2 | The belief replay overlay was undocumented in Paintbot and easily confused with the navigation viewer | Added an explicit two-viewer section, commands, inputs, and purpose distinction. Updated the shared bundler docstring for generated Paintbot maps. |
| P2 | No Paintbot docs index or source-of-truth map existed | Added `docs/README.md`, linked from README and AGENTS, and classified current versus historical surfaces. |
| P2 | Native-port design claimed no uploads and a permanent 91-variable config | Refreshed status; preserved the 91-variable parity boundary and documented the current 111-variable source contract. |
| P3 | Founding recon and reports used “current” language without a supersession boundary | Added historical-snapshot banners and routed readers to current references. |
| P3 | Tentative-lessons lifecycle named the CTF rotator; archived lesson link was broken | Corrected the Paintbot path and archive navigation. |
| P3 | Shared belief-viewer bundler still documented only Beacon/`nav.npz` | Updated its docstring to describe traced dynamic maps with fixed-CTF fallback. |

## Intentionally historical surfaces

`VERSION_LOG.md`, dated recon, dated reports, checked-in request JSON, and
lesson archives retain historical version IDs, opponent versions, maps, and
results. Rewriting those values would corrupt provenance. The docs index and
page banners now make their cutoff explicit.

## Resolved implementation/configuration finding

The v48 build deliberately refreshed `tools/versions.env` to Paintbot 0.7.199 /
source `2c6bec20c46a695a061b25e1bb11a158a5e0e1f4` and compiled the native image
against that revision's immutable dependency lock.

`tools/analyze_giant_carries.py` is a hard-coded one-off analysis with no CLI
interface; the README now labels it historical instead of presenting it as a
general tool.

## Validation

- Local Markdown target check over Paintbot docs and governing root docs (102
  links across 24 files; no local heading-fragment links existed).
- CLI `--help` verification for documented Paintbot tools.
- Live manifest, league, campaign, membership, and submission readback.
- Searches for stale current-version/champion/seating/fixed-map terminology,
  with dated historical records explicitly exempted.
- `git diff --check` and manual reread of modified claims.

No repository-provided Markdown linter or docs build exists. External HTTP
links were not crawled; local link integrity and authoritative live/source
claims received priority.
