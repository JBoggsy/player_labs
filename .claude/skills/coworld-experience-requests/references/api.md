# Experience-request API reference

Schema snapshot checked 2026-09-14 against the [Observatory OpenAPI](https://softmax.com/api/observatory/openapi.json). Recheck current schema and CLI help before creating a request; this reference does not override game configuration validation.

## Workflow and authorization

Use the [skill](../SKILL.md) to resolve → compose → validate → create → stream. `create --check-schema` is read-only validation. Actual request creation can incur costs; stay within the current task scope. League submission and public community writes are separate actions.

```bash
uv run coworld xp-request --help
uv run python .claude/skills/coworld-experience-requests/scripts/experience_request.py create /tmp/request.json --check-schema
uv run python .claude/skills/coworld-experience-requests/scripts/experience_request.py create /tmp/request.json
```

Target a game/league/division using the fields below. Supply one roster selector per intended seat; explicit policy references pin versions for controlled comparisons. Game-specific role/team overrides come from that game's schema and evaluation guide. Inspect resolved participants and counts after creation.

## Routes

- Create/list: `/v2/experience-requests` (POST/GET).
- Detail: `/v2/experience-requests/{id}`.
- Child episode rows: `/v2/experience-requests/{id}/episodes`.
- Cancel: `/v2/experience-requests/{id}/cancel` (POST; stops execution).
- Division roster: `/v2/divisions/{id}/leaderboard?include_recent_rounds=false`; the flag is boolean. Exact `policy_label` is resolved through `/stats/policy-versions?name_exact=…&version=N`. No separate membership join. Undersized/unresolved rosters fail explicitly.

Auth uses the project-local Softmax login. Do not elevate access for competitive intelligence. Artifact paths and completion semantics are in the [artifact reference](../../coworld-episode-artifacts/references/endpoint-map.md).

## V2CreateExperienceRequestRequest



| Field | Type | Required | Default / bounds | Meaning |
| --- | --- | --- | --- | --- |
| `idempotency_key` | string or null | no | {} | Key that makes repeated create requests return the same experience request. |
| `private` | boolean | no | {"default": false} | Limit the request, episodes, and artifacts to the requester. |
| `llm_routing_override` | string or null | no | {} | Language-model provider override for this request. |
| `coworld_id` | string or null | no | {} | Coworld to run directly. |
| `variant_id` | string or null | no | {} | Variant to run within the direct Coworld. |
| `target` | V2ExperienceRequestTarget or null | no | {} | Coworld, league, or division to resolve as the run target. |
| `game_config_overrides` | object or null | no | {} | Top-level game configuration values validated against the Coworld schema. |
| `game_config_overlay_secret` | string or null | no | {} | Private Coworld configuration secret merged before public overrides. |
| `state` | V2CoworldState or null | no | {} | Game state to load. Omit it to start with new state. |
| `roster` | array of V2RosterParticipant | yes | {} | Policy selector for each game seat. |
| `included_players` | array of string | no | {} | Limit champion selection to these player IDs or names. Explicit policy seats are unaffected. |
| `excluded_players` | array of string | no | {} | Exclude these player IDs or names from champion selection. Exclusions take precedence. |
| `num_episodes` | integer | no | {"default": 1, "minimum": 1.0, "maximum": 100.0} | Number of episodes to create. |
| `notes` | string or null | no | {} | Note explaining the request's purpose. |
| `execution_backend` | string | no | {"default": "k8s", "const": "k8s"} | Execution system used for the episodes. |
| `reporters` | array of ReporterBindingSpec | no | {"maxItems": 10} | Reporters to run after completion, including optional dependencies. Runs are billed to the requester. |

Additional properties: False.

## V2ExperienceRequestTarget



| Field | Type | Required | Default / bounds | Meaning |
| --- | --- | --- | --- | --- |
| `coworld_id` | string or null | no | {} | Coworld to run directly. |
| `variant_id` | string or null | no | {} | Variant to run within the selected Coworld. |
| `league_id` | string or null | no | {} | League whose canonical Coworld to run. |
| `league_name` | string or null | no | {} | League name to resolve when no league ID is provided. |
| `division_id` | string or null | no | {} | Division whose league and canonical Coworld to run. |
| `division_name` | string or null | no | {} | Division name to resolve within the selected league. |

Additional properties: False.

## V2CoworldState



| Field | Type | Required | Default / bounds | Meaning |
| --- | --- | --- | --- | --- |
| `mode` | string | yes | {"enum": ["head", "snapshot"]} | State version to load: live head state or an immutable snapshot. |
| `scope` | string | no | {"default": "player", "enum": ["player", "world"]} | Whether the state belongs to selected players or the shared world. |
| `participants` | array of V2CoworldStateParticipant | no | {} | Players whose state to load, in roster order. |

Additional properties: False.

## V2RosterParticipant



| Field | Type | Required | Default / bounds | Meaning |
| --- | --- | --- | --- | --- |
| `player` | V2RosterPlayer | yes | {} | Policy selector for this roster entry. |
| `slot` | integer | no | {"default": -1, "minimum": -1.0} | Seat index, or -1 to rotate through open seats. |

Additional properties: False.

## ReporterBindingSpec



| Field | Type | Required | Default / bounds | Meaning |
| --- | --- | --- | --- | --- |
| `reporter` | PinnedReporterRef-Input or LatestReporterRef-Input | yes | {} | Reporter version to run. |
| `params` | object or null | no | {} | Parameters passed to the reporter. |
| `limits` | ReporterLimitsOverride or null | no | {} | Run-limit overrides. |
| `dependencies` | array of ReporterDependencySpec-Input | no | {} | Reporter runs that must complete before this run. |

Additional properties: False.

## V2CoworldStateParticipant



| Field | Type | Required | Default / bounds | Meaning |
| --- | --- | --- | --- | --- |
| `player_id` | string | yes | {"minLength": 1} | Player whose game state to load. |

Additional properties: False.

## V2RosterPlayer

Exactly one roster player selector must be set.

| Field | Type | Required | Default / bounds | Meaning |
| --- | --- | --- | --- | --- |
| `policy_ref` | string or null | no | {} | Policy label such as `name:v3`, or a policy-version UUID. |
| `top_n` | integer or null | no | {} | Select from the top N champions in the target league or division. |
| `random` | boolean or null | no | {} | Select a random champion from the target league for each episode. |

Additional properties: False.

## PinnedReporterRef-Input



| Field | Type | Required | Default / bounds | Meaning |
| --- | --- | --- | --- | --- |
| `kind` | string | no | {"default": "version", "const": "version"} | Selects a specific reporter version. |
| `reporter_version_id` | string | yes | {} | Reporter version to run. |

Additional properties: False.

## LatestReporterRef-Input



| Field | Type | Required | Default / bounds | Meaning |
| --- | --- | --- | --- | --- |
| `kind` | string | no | {"default": "latest", "const": "latest"} | Selects the latest reporter version. |
| `reporter_id` | string | yes | {} | Reporter whose latest version will run. |

Additional properties: False.

## ReporterLimitsOverride



| Field | Type | Required | Default / bounds | Meaning |
| --- | --- | --- | --- | --- |
| `memory_mib` | integer or null | no | {} | Maximum guest memory in mebibytes. |
| `guest_cpu_seconds` | integer or null | no | {} | Maximum CPU time available to the guest, in seconds. |
| `wall_clock_seconds` | integer or null | no | {} | Maximum elapsed run time, in seconds. |
| `scratch_mib` | integer or null | no | {} | Maximum scratch storage in mebibytes. |
| `tool_calls` | integer or null | no | {} | Maximum number of tool calls. |
| `llm_usd` | number or null | no | {} | Maximum language-model spend in US dollars. |
| `artifact_read_mib` | integer or null | no | {} | Maximum artifact data the run may read, in mebibytes. |
| `output_mib` | integer or null | no | {} | Maximum size of each output part, in mebibytes. |

Additional properties: False.

## ReporterDependencySpec-Input



| Field | Type | Required | Default / bounds | Meaning |
| --- | --- | --- | --- | --- |
| `reporter` | PinnedReporterRef-Input or LatestReporterRef-Input | yes | {} | Reporter version used for this dependency. |
| `params` | object or null | no | {} | Parameters passed to the dependency reporter. |
| `limits` | ReporterLimitsOverride or null | no | {} | Run-limit overrides for this dependency. |
| `reuse` | ReporterDependencyReuse | no | {} | Rules for reusing an existing matching dependency run. |
| `dependencies` | array of object | no | {} | Nested prerequisites using this same ReporterDependencySpec shape. |

Additional properties: False.

## ReporterDependencyReuse



| Field | Type | Required | Default / bounds | Meaning |
| --- | --- | --- | --- | --- |
| `completed` | boolean | no | {"default": true} | Allow reuse of a matching completed run. |
| `max_age_seconds` | integer or null | no | {} | Maximum age of a reusable completed run, in seconds. Null allows any age. |
| `in_flight` | boolean | no | {"default": true} | Allow reuse of a matching queued or running run. |

Additional properties: False.
