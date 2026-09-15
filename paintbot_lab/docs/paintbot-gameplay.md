# Paintbot game reference

The public game source is [Metta-AI/coworld-ctf](https://github.com/Metta-AI/coworld-ctf).
Its [Paintbot manifest](https://github.com/Metta-AI/coworld-ctf/blob/main/coworld_manifest_paintbot.json)
defines the published `battle-royale-s2` configuration: sixteen solo seats using
the play-calling shell and WebAssembly playbooks. It has a lobby, one life per seat,
a closing zone and pact-based cooperation. Winning and Glory are separate outputs.

## Authoritative resources

- [Game wiki](https://softmax.com/paintbot/wiki): full gameplay, combat, item and scoring tables.
- [Battle royale](https://softmax.com/paintbot/wiki/battle-royale-s2): match rules.
- [Scoring](https://softmax.com/paintbot/wiki/glory-season-2): Glory factors and limits.
- [Policy contract](https://softmax.com/paintbot/wiki/policies): control modes and packaging.
- [Forum](https://softmax.com/paintbot/forum): findings to verify against the source.

Read the selected league's exact manifest and resolved match configuration. The
engine supports multiple rule and control configurations; an engine capability is
not proof that a particular league uses it. Resolve team layout, seat control,
map, feature flags and score aggregation independently.

## Stencil compatibility

The lab's Stencil player is a direct-input Sprite-v1 policy with generated-map
navigation, capture-the-heart objectives and multi-team belief. Its source and
build inputs are in `paintbot/stencil_nim/` and `tools/versions.env`. Those local
capabilities do not establish compatibility with the play-calling configuration.
Check the selected contract before any upload or evaluation. Adapting gameplay or
adding a playbook requires an agreed objective.

For replay analysis, build the decoder against the recorded game's artifact.
A successful decode does not prove that the policy interpreted every label correctly.
Use [analysis tools](analysis-tools.md) and [evaluation setup](tournament-like-experience-requests.md).
