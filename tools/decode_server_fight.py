#!/usr/bin/env python3
"""Decode a LeekWars server fight log into human-readable turn-by-turn output.

Uses generator's chips.json / weapons.json for accurate template ID lookup
(chip IDs and their in-fight template IDs are different namespaces).

Usage:
    python3 tools/decode_server_fight.py <fight_id>
    python3 tools/decode_server_fight.py /tmp/fight.json
"""
import json
import sys
import urllib.request

GEN_DATA = "/home/ubuntu/leek-wars-generator/data"

# LW action codes (subset; expand as needed)
CODES = {
    1: "USE_WEAPON",
    2: "USE_CHIP",
    5: "PLAYER_DEAD",
    6: "NEW_TURN",
    7: "LEEK_TURN",
    8: "FIRE_WEAPON",
    10: "MOVE",
    12: "USE_CHIP",
    13: "SET_WEAPON",
    16: "USE_WEAPON_DETAIL",
    101: "LIFE_LOST",
    102: "MAX_LIFE_LOST",
    104: "TP_LOST",
    105: "MP_LOST",
    110: "POISON_DAMAGE",
    302: "ADD_CHIP_EFFECT",
    1002: "BUG",
}

# LeekWars effect IDs (canonical)
EFFECTS = {
    1: "DAMAGE",
    2: "POISON",
    3: "HEAL",
    4: "BUFF_STR",
    5: "REL_SHIELD",
    6: "ABS_SHIELD",
    7: "BUFF_MP",
    8: "DAMAGE_RETURN",
    9: "BUFF_AGI",
    10: "TELEPORT",
    11: "VULNERABILITY",
    12: "RAW_ABS_SHIELD",
    13: "STR_DEBUFF",
    14: "AGI_DEBUFF",
    15: "RES_DEBUFF",
    16: "WIS_DEBUFF",
    17: "MP_DEBUFF",  # slow_down uses this
    18: "TP_DEBUFF",
    19: "MAG_DEBUFF",
    21: "BUFF_RES",
    22: "BUFF_MAG",
    23: "BUFF_WIS",
    24: "BUFF_SCI",
    25: "NOVA",
    31: "BUFF_MP_FLAT",
    32: "BUFF_TP",
    33: "BUFF_HP",
    38: "BUFF_STR_FLAT",
    39: "BUFF_SCI",
    40: "BUFF_WIS",
    41: "BUFF_AGI",
    42: "BUFF_RES",
    44: "BUFF_WIS",
    60: "ANTIBUFF",
    85: "STR_PCT",
    90: "POISON?",
    102: "POISON_DOT",
    107: "ABS_SHIELD",
    121: "POISON_RESIST",
    155: "POISON_DOT",
    157: "POISON_DOT",
    164: "DAMAGE_FLAT",
    165: "DAMAGE_FLAT",
    181: "POISON_DOT",
    197: "POISON_DOT",
    210: "STR_STACK",
    257: "WIS_BUFF",
    262: "WIS_BUFF",
    263: "WIS_BUFF",
    264: "POISON_RES_FLAT",
}


def load_templates():
    with open(f"{GEN_DATA}/chips.json") as f:
        chips_data = json.load(f)
    with open(f"{GEN_DATA}/weapons.json") as f:
        weapons_data = json.load(f)
    chip_tpl = {c["template"]: c["name"] for c in chips_data.values()}
    weap_tpl = {w["template"]: w["name"] for w in weapons_data.values()}
    return chip_tpl, weap_tpl


def load_fight(source):
    if source.isdigit():
        url = f"https://leekwars.com/api/fight/get/{source}"
        with urllib.request.urlopen(url) as r:
            d = json.loads(r.read())
    else:
        with open(source) as f:
            d = json.load(f)
    data = d["data"]
    if isinstance(data, str):
        data = json.loads(data)
    return d, data


def decode(source):
    fight, data = load_fight(source)
    chip_tpl, weap_tpl = load_templates()
    leeks = data["leeks"]
    actions = data["actions"]

    # Build entity ID -> name map
    names = {l["id"]: l["name"] for l in leeks}
    print(f"FIGHT {fight.get('id', '?')}  winner=team {fight.get('winner')}")
    for l in leeks:
        print(f"  e{l['id']}: {l['name']} hp={l.get('life')} tp={l.get('tp')} mp={l.get('mp')}")

    print("\n=== TURN LOG ===")
    cur_ent = None
    for a in actions:
        code = a[0]
        if code == 6:
            print(f"\n--- TURN {a[1]} ---")
        elif code == 7:
            cur_ent = a[1]
            print(f"  [{names.get(cur_ent, f'e{cur_ent}')}]")
        elif code == 12:
            chip_tpl_id = a[1]
            cn = chip_tpl.get(chip_tpl_id, f"chip-tpl#{chip_tpl_id}")
            cell = a[2] if len(a) > 2 else "?"
            print(f"    USE_CHIP {cn} -> cell {cell}")
        elif code == 13:
            wid = a[1]
            wn = weap_tpl.get(wid, f"wpn#{wid}")
            print(f"    SET_WEAPON {wn}")
        elif code == 8:
            wid = a[2] if len(a) > 2 else "?"
            wn = weap_tpl.get(wid, f"wpn#{wid}") if isinstance(wid, int) else wid
            print(f"    FIRE_WEAPON {wn}")
        elif code == 10:
            tgt = a[2] if len(a) > 2 else "?"
            print(f"    MOVE to cell {tgt}")
        elif code == 101:
            who = names.get(a[1], f"e{a[1]}")
            print(f"      ! {who} takes {a[2]} damage")
        elif code == 110:
            who = names.get(a[1], f"e{a[1]}")
            print(f"      ! POISON tick on {who}: {a[2]}")
        elif code == 104:
            who = names.get(a[1], f"e{a[1]}")
            print(f"      ! {who} loses {a[2]} TP")
        elif code == 105:
            who = names.get(a[1], f"e{a[1]}")
            print(f"      ! {who} loses {a[2]} MP")
        elif code == 302:
            chip_tpl_id = a[1]
            target = a[2] if len(a) > 2 else None
            # Format: [302, chip_tpl, target, ?, ?, effect_id, value, turns]
            eff_id = a[5] if len(a) > 5 else None
            val = a[6] if len(a) > 6 else None
            turns = a[7] if len(a) > 7 else None
            cn = chip_tpl.get(chip_tpl_id, f"chip-tpl#{chip_tpl_id}")
            en = EFFECTS.get(eff_id, f"eff#{eff_id}")
            tn = names.get(target, f"e{target}")
            print(f"      eff: {cn} -> {tn} ({en} val={val} turns={turns})")
        elif code == 5:
            who = names.get(a[1], f"e{a[1]}")
            print(f"    *** {who} DIED ***")
        elif code == 1002:
            print(f"    *** BUG/CRASH ***")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    decode(sys.argv[1])
