"""Build one arm's request: one candidate seat + the frozen press field1 (classic-press)."""
import json
import sys

FIELD = {  # frozen for the press-ab campaign; do not edit while an A/B is running
    "bismarck_press (deepseek-v4.1-flash)": "dce81640-9329-4bb7-a928-54dedd747690",
    "talleyrand_press (gpt-6-luna)": "2f036c48-7d1c-42fa-be77-7547ab77971c",
    "metternich_press (gemini-3.5-flash-lite)": "628e6390-e9af-4993-af63-e84d16d0ef34",
    "machiavelli_press (glm-5.3-flash)": "a600ad8a-49e9-4fba-a506-ea0ac0cc47e5",
    "kissinger-v2 (silent)": "580d73eb-6a20-4762-8529-eef9655bfd83",
    "calhamer (silent)": "2f27f55a-6b0e-4af5-af2b-58aee9e3c83f",
}

label, policy, episodes, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
request = {
    "private": True,
    "target": {"league_id": "league_1bccc63d-cd0a-47d7-92d7-e762797b5f1c", "variant_id": "classic-press"},
    "num_episodes": episodes,
    "episode_player_llm_spend_limit_usd": 14,
    "roster": [{"player": {"policy_ref": policy}, "slot": -1}]
    + [{"player": {"policy_ref": ref}, "slot": -1} for ref in FIELD.values()],
    "notes": f"webdip lab press-ab1 arm {label}: one candidate seat vs frozen press field1",
}
json.dump(request, open(out, "w"), indent=1)
