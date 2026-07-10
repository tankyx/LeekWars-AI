#!/usr/bin/env python3
"""2v2 behavioral test for DuskHope's BUILD_SUPPORT mode.

Team 1: DuskHope (support) + ProdigalSon (STR attacker), both on V8.
Team 2: two smart_dannyd bruisers (scripted AI).

Verifies DuskHope casts chips ON ITS ALLY (heal/shield/buff with the ally as
target) by decoding USE_CHIP actions from the fight log.
"""
import json
import subprocess
import sys
import os
import tempfile
from pathlib import Path

TOOLS = Path(__file__).parent
sys.path.insert(0, str(TOOLS))
from local_test import load_configs, AI_PATH, GENERATOR_JAR, GENERATOR_DIR, JAVA_HOME  # noqa

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 42


def make_entity(cfg, entity_id, farmer_id, team_id, ai_path, cell):
    return {
        "id": entity_id, "ai": ai_path, "name": cfg["name"],
        "type": cfg.get("type", 1), "farmer": farmer_id, "team": team_id,
        "level": cfg.get("level", 150), "life": cfg.get("life", 2000),
        "cores": cfg.get("cores", 8), "ram": cfg.get("ram", 16),
        "tp": cfg.get("tp", 12), "mp": cfg.get("mp", 5),
        "strength": cfg.get("strength", 0), "magic": cfg.get("magic", 0),
        "agility": cfg.get("agility", 0), "wisdom": cfg.get("wisdom", 0),
        "resistance": cfg.get("resistance", 0), "science": cfg.get("science", 0),
        "frequency": cfg.get("frequency", 100),
        "weapons": cfg.get("weapons", []), "chips": cfg.get("chips", []),
        "cell": cell,
    }


def main():
    configs = load_configs()
    dusk = configs["leeks"]["DuskHope"]
    prodigal = {
        "name": "ProdigalSon", "type": 1, "level": 150, "life": 1717,
        "cores": 8, "ram": 13, "tp": 14, "mp": 4, "strength": 480,
        "agility": 60, "wisdom": 260, "resistance": 280, "science": 20,
        "frequency": 120, "weapons": [182, 42, 43],
        "chips": [8, 15, 23, 30, 67, 22, 32, 11, 276, 110, 35, 13, 5],
    }
    dannyd = configs["opponents"]["smart_dannyd"]

    team1 = [
        make_entity(dusk, 1, 1, 1, AI_PATH, 47),
        make_entity(prodigal, 2, 1, 1, AI_PATH, 52),
    ]
    team2 = [
        make_entity(dict(dannyd, name="DannyD_A"), 3, 2, 2, dannyd.get("ai_relative"), 245),
        make_entity(dict(dannyd, name="DannyD_B"), 4, 2, 2, dannyd.get("ai_relative"), 250),
    ]

    scenario = {
        "farmers": [{"id": 1, "name": "P", "country": "fr"}, {"id": 2, "name": "O", "country": "fr"}],
        "teams": [{"id": 1, "name": "T1"}, {"id": 2, "name": "T2"}],
        "entities": [team1, team2],
        "random_seed": SEED,
        "max_turns": 64,
        "max_operations_per_entity": 20_000_000,
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", prefix="lw_2v2_", delete=False, dir="/tmp") as f:
        json.dump(scenario, f)
        path = f.name

    env = os.environ.copy()
    env["JAVA_HOME"] = JAVA_HOME
    java = os.path.join(JAVA_HOME, "bin", "java")
    r = subprocess.run([java, "-jar", str(GENERATOR_JAR), path],
                       capture_output=True, text=True, timeout=180,
                       cwd=str(GENERATOR_DIR), env=env)
    out = r.stdout
    start = out.find('{"')
    if start < 0:
        print("NO JSON OUTPUT")
        print(out[-3000:])
        print(r.stderr[-2000:])
        sys.exit(1)
    data = json.loads(out[start:], strict=False)
    fight = data.get("fight", data)

    actions = fight.get("actions", [])
    names = {1: "DuskHope", 2: "ProdigalSon", 3: "DannyD_A", 4: "DannyD_B"}
    cur = None
    ally_casts = []
    self_casts = 0
    turn = 0
    for a in actions:
        if not isinstance(a, list):
            continue
        if a[0] == 6:
            turn += 1
        elif a[0] == 7:
            cur = a[1]
        elif a[0] == 12 and cur == 1:  # DuskHope USE_CHIP: [12, chip, cellOrTarget, ...]
            ally_casts.append((turn, a))

    print(f"winner: {data.get('winner', fight.get('winner'))}  duration: {turn} turns")
    print(f"DuskHope USE_CHIP events: {len(ally_casts)}")
    for t, a in ally_casts[:30]:
        print(f"  T{t}: {a}")
    # Effect adds show target entity: code 302 [302, chip_db_id, ..., target_entity, ...]
    cur = None
    eff_on_ally = 0
    eff_on_self = 0
    for a in actions:
        if not isinstance(a, list):
            continue
        if a[0] == 7:
            cur = a[1]
        elif a[0] == 302 and cur == 1 and len(a) > 4:
            tgt = a[4]
            if tgt == 2:
                eff_on_ally += 1
            elif tgt == 1:
                eff_on_self += 1
    print(f"DuskHope effects applied -> ally(ProdigalSon): {eff_on_ally}, self: {eff_on_self}")
    ops = fight.get("ops", {})
    print(f"ops: {ops}")


if __name__ == "__main__":
    main()
