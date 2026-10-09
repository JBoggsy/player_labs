"""Build one arm's request: one candidate seat + the frozen press field1 (classic-press)."""
import json
import sys

FIELD_TAG = "geo"  # evidence/press-ab1/<FIELD_TAG>/<arm>; wave 1 used the pre-geometry field (evidence/press-ab1/<arm>)
FIELD = {  # frozen for the press-ab campaign; do not edit while an A/B is running
    "bismarck_press (deepseek-v4.1-flash)": "dd532c32-040e-4ac4-b48a-5e871aa891d9",
    "talleyrand_press (gpt-6-luna)": "95702e01-2e6a-43e2-802b-228be421b283",
    "metternich_press (gemini-3.5-flash-lite)": "aed005c0-023d-4cc0-bc8a-43309c6de71a",
    "machiavelli_press (glm-5.3-flash)": "228403f2-3db0-491c-b1e7-06538ca88200",
    "kissinger-v2 (silent)": "580d73eb-6a20-4762-8529-eef9655bfd83",
    "calhamer (silent)": "2f27f55a-6b0e-4af5-af2b-58aee9e3c83f",
}

if sys.argv[1:] == ["--field-tag"]:
    sys.exit(print(FIELD_TAG))
label, policy, episodes, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
request = {
    "private": True,
    "target": {"league_id": "league_1bccc63d-cd0a-47d7-92d7-e762797b5f1c", "variant_id": "classic-press"},
    "num_episodes": episodes,
    "episode_player_llm_spend_limit_usd": 14,
    "roster": [{"player": {"policy_ref": policy}, "slot": -1}]
    + [{"player": {"policy_ref": ref}, "slot": -1} for ref in FIELD.values()],
    "notes": f"webdip lab press-ab1 arm {label}: one candidate seat vs frozen press field ({FIELD_TAG})",
}
json.dump(request, open(out, "w"), indent=1)
