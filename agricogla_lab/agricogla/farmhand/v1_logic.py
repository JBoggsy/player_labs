"""Vendored PURE decision logic from the ACTUAL league v1 (agricogla-boses:v1).

Extracted from the v1 DOCKER IMAGE (agricogla-boses.tar), NOT the working-copy
player.py — which I accidentally modified (PARAMS extraction) this session, causing
farmhand to vendor a DIFFERENT, worse policy. This is the real +9 league logic:
hardcoded constants, no PARAMS layer. The choices_adapter feeds it the legal-move
layer cogweb omits.
"""
"""Agricogla Coworld player — heuristic policy with planning and opponent awareness.

Connects via COWORLD_PLAYER_WS_URL, receives observations with pre-computed
legal moves, picks the best action, responds. No LLM, no API calls, no timeouts.
"""
import json
import os

HARVEST_ROUNDS = {4, 7, 9, 11, 13, 14}


def next_harvest_in(round_num):
    for h in sorted(HARVEST_ROUNDS):
        if h >= round_num:
            return h - round_num
    return 0


def count_resources(player, resource):
    return player.get("resources", {}).get(resource, 0)


def count_animals(player, animal):
    return player.get("animals", {}).get(animal, 0)


def total_food_value(player):
    """Estimate total accessible food including conversions."""
    food = count_resources(player, "food")
    food += count_resources(player, "grain")
    food += count_resources(player, "vegetable")
    # Animals need a cooker
    if has_cooker(player):
        rates = best_cook_rates(player)
        food += count_animals(player, "sheep") * rates.get("sheep", 0)
        food += count_animals(player, "boar") * rates.get("boar", 0)
        food += count_animals(player, "cattle") * rates.get("cattle", 0)
    return food


def has_cooker(player):
    majors = player.get("majors", [])
    minors = player.get("minors", [])
    cooker_ids = {"fireplace2", "fireplace3", "hearth4", "hearth5", "clay_oven", "stone_oven"}
    return bool(cooker_ids & set(majors + minors))


def best_cook_rates(player):
    majors = player.get("majors", [])
    rates = {"sheep": 0, "boar": 0, "cattle": 0, "vegetable": 0}
    if "hearth4" in majors or "hearth5" in majors:
        rates = {"sheep": 2, "boar": 3, "cattle": 4, "vegetable": 3}
    elif "fireplace2" in majors or "fireplace3" in majors:
        rates = {"sheep": 2, "boar": 2, "cattle": 3, "vegetable": 2}
    return rates


def family_size(player):
    return len(player.get("family", []))


def room_count(player):
    return sum(1 for s in player.get("spaces", []) if s.get("kind") == "room")


def field_count(player):
    return sum(1 for s in player.get("spaces", []) if s.get("kind") == "field")


def empty_space_count(player):
    spaces = player.get("spaces", [])
    fences = player.get("fences", [])
    # Count spaces that are empty and not in a pasture and without stable
    count = 0
    for s in spaces:
        if s.get("kind") == "empty" and not s.get("stable"):
            count += 1
    return count


def pasture_count(player):
    """Rough count of pastures (groups of fenced spaces)."""
    fences = player.get("fences", [])
    if not fences:
        return 0
    # Approximate: each fence plan creates at least 1 pasture
    return max(1, len(fences) // 4)


def scoring_gaps(player):
    """Return categories at -1 penalty (zero)."""
    gaps = []
    if field_count(player) < 2:
        gaps.append("fields")
    if pasture_count(player) < 1:
        gaps.append("pastures")
    if count_resources(player, "grain") + sown_count(player, "grain") < 1:
        gaps.append("grain")
    if count_resources(player, "vegetable") + sown_count(player, "vegetable") < 1:
        gaps.append("vegetables")
    if count_animals(player, "sheep") < 1:
        gaps.append("sheep")
    if count_animals(player, "boar") < 1:
        gaps.append("boar")
    if count_animals(player, "cattle") < 1:
        gaps.append("cattle")
    return gaps


def sown_count(player, crop):
    """Count crops on fields."""
    total = 0
    for s in player.get("spaces", []):
        if s.get("crop") == crop:
            total += s.get("cropCount", 0)
    return total


def food_urgency(player, round_num):
    """0=comfortable, 1-4=increasingly desperate."""
    harvest_in = next_harvest_in(round_num)
    if harvest_in > 3:
        return 0
    food_needed = family_size(player) * 2
    food_available = total_food_value(player)
    deficit = food_needed - food_available
    if deficit <= 0:
        return 0
    if harvest_in == 0:
        return 4
    return min(4, max(1, deficit // 2 + (3 - harvest_in)))


def can_afford(player, cost):
    """Check if player can afford a cost dict like {"wood": 5, "reed": 2}."""
    if not cost:
        return True
    resources = player.get("resources", {})
    for resource, amount in cost.items():
        if resources.get(resource, 0) < amount:
            return False
    return True


def evaluate_action(action_id, obs, my_player, choices, options):
    """Score an action. Higher = better."""
    round_num = obs["state"]["round"]
    urgency = food_urgency(my_player, round_num)
    fam = family_size(my_player)
    rooms = room_count(my_player)
    fields = field_count(my_player)
    has_cook = has_cooker(my_player)
    gaps = scoring_gaps(my_player)

    # Get pile size for accumulation spaces
    pile_size = 0
    for opt in options:
        if opt["id"] == action_id and opt.get("pile"):
            pile = opt["pile"]
            pile_size = sum(pile.values()) if isinstance(pile, dict) else 0
            break

    score = 0

    # --- FAMILY GROWTH (highest priority when available and safe) ---
    if action_id == "r_family_growth":
        if choices.get("familyGrowthOk"):
            if urgency <= 1:
                score = 80
            else:
                score = 40 - urgency * 8
        else:
            score = -100  # can't actually grow

    elif action_id == "r_urgent_family":
        if choices.get("urgentGrowthOk"):
            if urgency <= 2:
                score = 65
            else:
                score = 30
        else:
            score = -100

    # --- ROOMS (enable family growth) ---
    elif action_id == "farm_expansion":
        room_cost = choices.get("roomCost", {})
        can_build_room = choices.get("legalRooms") and can_afford(my_player, room_cost)
        if rooms <= fam and can_build_room:
            score = 55  # housebound — need a room before growing
        elif can_build_room and round_num <= 7:
            score = 35  # building ahead for growth
        elif choices.get("legalStables") and can_afford(my_player, {"wood": 2}):
            score = 12  # just stables
        else:
            score = 2  # can't build anything useful

    # --- FOOD/COOKING ---
    elif action_id == "r_improvement":
        if not has_cook:
            score = 50 + urgency * 5  # critical: get a cooker
        else:
            score = 15  # minor or major for VP

    elif action_id == "r_renovate_improve":
        if not has_cook:
            score = 45 + urgency * 3  # renovate + grab cooker
        elif round_num >= 9:
            score = 25  # renovation for VP
        else:
            score = 12

    elif action_id == "day_laborer":
        score = 3 + urgency * 8  # emergency food

    elif action_id == "fishing":
        score = pile_size * (1.5 + urgency * 2)

    # --- RESOURCES ---
    elif action_id == "forest":
        wood_need = 5 if (rooms <= fam and round_num <= 8) else 2
        score = pile_size * min(3.5, wood_need)

    elif action_id == "copse":
        score = pile_size * 2.5

    elif action_id == "grove":
        score = pile_size * 2.8

    elif action_id == "clay_pit" or action_id == "hollow":
        clay_need = 3 if (not has_cook and count_resources(my_player, "clay") < 3) else 1.5
        score = pile_size * clay_need

    elif action_id == "reed_bank":
        score = pile_size * 2.5

    elif action_id == "r_west_quarry" or action_id == "r_east_quarry":
        score = pile_size * 3.0

    elif action_id == "resource_market":
        score = 8 + urgency * 2  # 1 reed + 1 stone + 1 food

    elif action_id == "traveling_players":
        score = pile_size * (1.5 + urgency * 1.5)

    # --- FIELDS AND SOWING ---
    elif action_id == "farmland":
        if fields < 2:
            score = 28
        elif fields < 5 and "fields" in gaps:
            score = 20
        else:
            score = 8

    elif action_id == "grain_seeds":
        if count_resources(my_player, "grain") == 0 and "grain" in gaps:
            score = 18
        else:
            score = 9

    elif action_id == "r_vegetable":
        if "vegetables" in gaps:
            score = 22
        else:
            score = 10

    elif action_id == "r_sow_bake":
        sowable = choices.get("sowableFields", [])
        bake_opts = choices.get("bakeOptions", [])
        sow_value = len(sowable) * 6
        bake_value = sum(b.get("food", 0) for b in bake_opts) if bake_opts else 0
        score = 20 + sow_value + bake_value * (1 + urgency)

    elif action_id == "r_cultivation":
        score = 22 + len(choices.get("sowableFields", [])) * 4

    # --- ANIMALS ---
    elif action_id == "r_sheep":
        count = pile_size
        food_val = count * best_cook_rates(my_player).get("sheep", 0) if has_cook else 0
        breed_bonus = 10 if (count_animals(my_player, "sheep") >= 1 and count >= 1) else 0
        category_bonus = 8 if "sheep" in gaps else 0
        score = count * 4 + food_val * urgency * 0.5 + breed_bonus + category_bonus

    elif action_id == "r_boar":
        count = pile_size
        food_val = count * best_cook_rates(my_player).get("boar", 0) if has_cook else 0
        breed_bonus = 10 if (count_animals(my_player, "boar") >= 1 and count >= 1) else 0
        category_bonus = 8 if "boar" in gaps else 0
        score = count * 4.5 + food_val * urgency * 0.5 + breed_bonus + category_bonus

    elif action_id == "r_cattle":
        count = pile_size
        food_val = count * best_cook_rates(my_player).get("cattle", 0) if has_cook else 0
        breed_bonus = 10 if (count_animals(my_player, "cattle") >= 1 and count >= 1) else 0
        category_bonus = 8 if "cattle" in gaps else 0
        score = count * 5 + food_val * urgency * 0.5 + breed_bonus + category_bonus

    # --- FENCES ---
    elif action_id == "r_fences":
        fence_plans = choices.get("fencePlans", [])
        wood_avail = count_resources(my_player, "wood")
        affordable_plans = [p for p in fence_plans if p.get("cost", {}).get("wood", len(p.get("edges", []))) <= wood_avail]
        if affordable_plans and "pastures" in gaps:
            score = 30 + (5 if round_num >= 8 else 0)
        elif affordable_plans:
            score = 15 + min(10, empty_space_count(my_player))
        else:
            score = 2

    # --- OCCUPATIONS ---
    elif action_id in ("lessons", "lessons_b"):
        hand_occs = choices.get("handOccupations", [])
        occ_cost = choices.get("occupationCostBySpace", {}).get(action_id)
        affordable_occs = [o for o in hand_occs if isinstance(o, dict) and o.get("affordable", True)] if hand_occs else []
        if affordable_occs and round_num <= 8:
            score = 18
        elif affordable_occs:
            score = 10
        else:
            score = -10

    # --- RENOVATION ---
    elif action_id == "r_redevelop":
        if round_num >= 12 and my_player.get("houseMaterial") != "stone":
            score = 22
        else:
            score = 8

    # --- MEETING PLACE ---
    elif action_id == "meeting_place":
        score = 4 + (3 if choices.get("handMinors") else 0)

    # --- QUARRY+STABLE combo ---
    elif action_id == "quarry_stall":
        score = 7

    else:
        score = 1  # unknown action, low priority

    # Late-game fill bonus
    if round_num >= 10:
        unused = empty_space_count(my_player)
        if action_id in ("r_fences", "farm_expansion", "farmland"):
            score += min(8, unused * 1.2)

    return score


def pick_best_action(obs):
    """Given an observation, return the best placement."""
    state = obs["state"]
    slot = obs["slot"]
    my_player = state["players"][slot]
    options = obs["options"]
    choices = obs["choices"]
    round_num = state["round"]

    # Filter to available actions
    available = [opt for opt in options if opt.get("available")]
    if not available:
        # Shouldn't happen, but fallback
        return {"action": "day_laborer"}

    # Score each available action
    scored = []
    for opt in available:
        action_id = opt["id"]
        score = evaluate_action(action_id, obs, my_player, choices, options)
        scored.append((score, action_id, opt))

    scored.sort(reverse=True, key=lambda x: x[0])
    best_score, best_action, best_opt = scored[0]

    # Build the placement with required parameters
    placement = build_placement(best_action, obs, my_player, choices)
    return placement


def build_placement(action_id, obs, my_player, choices):
    """Build a complete placement dict with required params for the action."""
    placement = {"action": action_id}

    if action_id == "farm_expansion":
        legal_rooms = choices.get("legalRooms", [])
        legal_stables = choices.get("legalStables", [])
        room_cost = choices.get("roomCost", {})
        if legal_rooms and can_afford(my_player, room_cost):
            placement["rooms"] = [legal_rooms[0]]
        elif legal_stables and can_afford(my_player, {"wood": 2}):
            placement["stables"] = [legal_stables[0]]

    elif action_id == "farmland":
        legal_fields = choices.get("legalFields", [])
        if legal_fields:
            placement["spaces"] = [legal_fields[0]]

    elif action_id in ("lessons", "lessons_b"):
        hand_occs = choices.get("handOccupations", [])
        if hand_occs:
            # Pick first available occupation
            placement["occupation"] = hand_occs[0].get("id", hand_occs[0]) if isinstance(hand_occs[0], dict) else hand_occs[0]

    elif action_id == "r_improvement":
        majors = choices.get("majors", [])
        if not has_cooker(my_player):
            for m in majors:
                if m.get("affordable") and m.get("prereqOk", True) and m.get("id") in ("fireplace2", "fireplace3"):
                    placement["improvement"] = {"kind": "major", "card": m["id"]}
                    break
        if "improvement" not in placement:
            for m in majors:
                if m.get("affordable") and m.get("prereqOk", True):
                    placement["improvement"] = {"kind": "major", "card": m["id"]}
                    break
        if "improvement" not in placement:
            hand_minors = choices.get("handMinors", [])
            if hand_minors:
                for mi in hand_minors:
                    if isinstance(mi, dict) and mi.get("affordable", True):
                        placement["improvement"] = {"kind": "minor", "card": mi["id"]}
                        break

    elif action_id == "r_renovate_improve":
        # Renovate, then optionally grab an improvement
        if not has_cooker(my_player):
            majors = choices.get("majors", [])
            for m in majors:
                if m.get("affordable") and m.get("id") in ("fireplace2", "fireplace3"):
                    placement["improvement"] = {"kind": "major", "card": m["id"]}
                    break

    elif action_id == "r_family_growth":
        # Optionally play a minor
        hand_minors = choices.get("handMinors", [])
        if hand_minors:
            for mi in hand_minors:
                if isinstance(mi, dict) and mi.get("affordable", True):
                    placement["improvement"] = {"kind": "minor", "card": mi["id"]}
                    break

    elif action_id == "r_fences":
        fence_plans = choices.get("fencePlans", [])
        wood_avail = count_resources(my_player, "wood")
        affordable_plans = [p for p in fence_plans if p.get("cost", {}).get("wood", len(p.get("edges", []))) <= wood_avail]
        if affordable_plans:
            best_plan = max(affordable_plans, key=lambda p: len(p.get("cells", [])))
            placement["edges"] = best_plan["edges"]
        else:
            placement["edges"] = []

    elif action_id == "r_sow_bake":
        sowable = choices.get("sowableFields", [])
        bake_opts = choices.get("bakeOptions", [])
        sow_list = []
        grain_avail = count_resources(my_player, "grain")
        veg_avail = count_resources(my_player, "vegetable")
        for field_idx in sowable:
            if veg_avail > 0:
                sow_list.append({"space": field_idx, "crop": "vegetable"})
                veg_avail -= 1
            elif grain_avail > 0:
                sow_list.append({"space": field_idx, "crop": "grain"})
                grain_avail -= 1
        placement["sow"] = sow_list
        if bake_opts and count_resources(my_player, "grain") > len([s for s in sow_list if s["crop"] == "grain"]):
            placement["bake"] = [{"card": bake_opts[0]["card"], "grain": 1}]

    elif action_id == "r_cultivation":
        legal_fields = choices.get("legalFields", [])
        if legal_fields:
            placement["plow"] = legal_fields[0]
        sowable = choices.get("sowableFields", [])
        sow_list = []
        grain_avail = count_resources(my_player, "grain")
        veg_avail = count_resources(my_player, "vegetable")
        for field_idx in sowable:
            if veg_avail > 0:
                sow_list.append({"space": field_idx, "crop": "vegetable"})
                veg_avail -= 1
            elif grain_avail > 0:
                sow_list.append({"space": field_idx, "crop": "grain"})
                grain_avail -= 1
        placement["sow"] = sow_list

    elif action_id == "r_redevelop":
        fence_plans = choices.get("fencePlans", [])
        wood_avail = count_resources(my_player, "wood")
        affordable_plans = [p for p in fence_plans if p.get("cost", {}).get("wood", len(p.get("edges", []))) <= wood_avail]
        if affordable_plans:
            best_plan = max(affordable_plans, key=lambda p: len(p.get("cells", [])))
            placement["edges"] = best_plan["edges"]
        else:
            placement["edges"] = []

    elif action_id == "meeting_place":
        # Optionally play a minor
        hand_minors = choices.get("handMinors", [])
        if hand_minors:
            for mi in hand_minors:
                if isinstance(mi, dict) and mi.get("affordable", True):
                    placement["improvement"] = {"kind": "minor", "card": mi["id"]}
                    break

    return placement


def decide_feeding(obs):
    """Decide what to convert to food during harvest."""
    state = obs["state"]
    slot = obs["slot"]
    my_player = state["players"][slot]
    choices = obs["choices"]

    food_needed = choices.get("foodNeededNow", 0)
    food_have = count_resources(my_player, "food")

    if food_have >= food_needed:
        return {"conversions": []}

    deficit = food_needed - food_have
    conversions = []
    conv_options = choices.get("conversionOptions", [])

    # Sort by food-per-unit value (prefer cheap conversions)
    # Raw grain/veg = 1:1, animals need cooker
    # Prioritize: raw grain, raw veg, cheapest animals
    raw_convs = [c for c in conv_options if c.get("via") == "raw"]
    cooked_convs = [c for c in conv_options if c.get("via") != "raw"]
    cooked_convs.sort(key=lambda c: c.get("foodEach", 1), reverse=True)

    for conv in raw_convs + cooked_convs:
        if deficit <= 0:
            break
        food_each = conv.get("foodEach", 1)
        max_count = conv.get("max", 0)
        # Only convert what we need
        needed_count = min(max_count, -(-deficit // food_each))  # ceiling division
        if needed_count > 0:
            conversions.append({
                "via": conv["via"],
                "good": conv["good"],
                "count": needed_count
            })
            deficit -= needed_count * food_each

    return {"conversions": conversions}


