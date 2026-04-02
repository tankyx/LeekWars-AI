#!/usr/bin/env python3
"""
Local LeekWars Fight Test Runner

Runs fights locally using the leek-wars-generator Java engine, eliminating
the need for network uploads and API calls. Supports parallel execution
and deterministic replay via seeds.

Usage:
    python3 tools/local_test.py <num_fights> <opponent> [--leek <name>] [--parallel N] [--seed N] [--verbose]

Examples:
    python3 tools/local_test.py 1 dummy_str --leek MargaretHamilton --verbose
    python3 tools/local_test.py 10 dummy_str --leek KurtGodel --parallel 4
    python3 tools/local_test.py 1 mirror --leek MargaretHamilton --seed 42

Available opponents:
    dummy_str    600 STR, 300 WIS (simple AI, move+attack)
    dummy_mag    600 MAG, 300 WIS (simple AI)
    dummy_tank   8000 HP, 200 STR, 400 RES (simple AI)
    dummy_agi    600 AGI, 300 WIS (simple AI)
    smart_str    600 STR, 300 WIS (buffs, heals, weapon swaps)
    smart_mag    600 MAG, 300 WIS (poison, denial, kiting)
    smart_tank   8000 HP, 200 STR, 400 RES, 400 WIS (shields, heals, cleanses)
    smart_agi    600 AGI, 300 WIS (kiting, long-range attacks)
    mirror       AI fights a copy of itself
    boss_fennel  Fennel King boss fight (4 leeks vs graal + crystals)
"""

import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
GENERATOR_DIR = Path("/home/ubuntu/leek-wars-generator")
GENERATOR_JAR = GENERATOR_DIR / "generator.jar"
LEEK_CONFIGS = SCRIPT_DIR / "leek_configs.json"
# AI path relative to GENERATOR_DIR (via symlink: leek-wars-generator/V8_modules -> our V8_modules)
AI_PATH = "V8_modules/main.lk"
DO_NOTHING_AI = "test/ai/do_nothing.lk"
BOSS_TEMPLATE = SCRIPT_DIR / "boss_scenario_template.json"
BOSS_MAP_DATA = SCRIPT_DIR / "boss_map_data.json"
JAVA_HOME = "/usr/lib/jvm/java-24-openjdk-amd64"

# Puzzle chips that must be equipped for boss fights
CHIP_GRAPPLE_ID = 162
CHIP_BOXING_GLOVE_ID = 163

# Add tools dir to path for FightActionParser import
sys.path.insert(0, str(SCRIPT_DIR))
from lw_test_script import FightActionParser, WEAPONS, CHIPS

# ── Action constants (match lw_test_script.py) ──
ACTION_PLAYER_DEAD = 5
ACTION_NEW_TURN = 6
ACTION_LEEK_TURN = 7
ACTION_BUG = 1002


def load_configs():
    """Load leek and opponent configs from leek_configs.json."""
    if not LEEK_CONFIGS.exists():
        print(f"ERROR: {LEEK_CONFIGS} not found. Run fetch_leek_configs.py first.")
        sys.exit(1)
    with open(LEEK_CONFIGS) as f:
        return json.load(f)


def build_scenario(leek_cfg, opponent_cfg, seed=None, opponent_ai=None):
    """Build a scenario JSON dict matching the generator's expected format.

    Args:
        leek_cfg: Our leek's config dict
        opponent_cfg: Opponent config dict
        seed: Random seed (None = random)
        opponent_ai: Override AI path for opponent (for mirror mode)
    """
    if seed is None:
        seed = random.randint(1, 2**31 - 1)

    # Resolve AI paths
    our_ai = AI_PATH
    opp_ai = opponent_ai or opponent_cfg.get("ai_relative", "test/ai/basic.leek")

    # Build entity configs
    def make_entity(cfg, entity_id, farmer_id, team_id, ai_path):
        e = {
            "id": entity_id,
            "ai": ai_path,
            "name": cfg["name"],
            "type": cfg.get("type", 1),
            "farmer": farmer_id,
            "team": team_id,
            "level": cfg.get("level", 301),
            "life": cfg.get("life", 5000),
            "cores": cfg.get("cores", 14),
            "ram": cfg.get("ram", 50),
            "tp": cfg.get("tp", 20),
            "mp": cfg.get("mp", 6),
            "strength": cfg.get("strength", 0),
            "magic": cfg.get("magic", 0),
            "agility": cfg.get("agility", 0),
            "wisdom": cfg.get("wisdom", 0),
            "resistance": cfg.get("resistance", 0),
            "science": cfg.get("science", 0),
            "frequency": cfg.get("frequency", 100),
            "weapons": cfg.get("weapons", []),
            "chips": cfg.get("chips", []),
        }
        # Cell positions: place on opposite sides of a 17x17 map
        if team_id == 1:
            e["cell"] = 50   # top-left area
        else:
            e["cell"] = 240  # bottom-right area
        return e

    our_entity = make_entity(leek_cfg, 1, 1, 1, our_ai)
    opp_entity = make_entity(opponent_cfg, 2, 2, 2, opp_ai)

    # Set max_operations based on cores (1M per core)
    cores = leek_cfg.get("cores", 14)
    max_ops = max(cores * 1_000_000, 20_000_000)

    scenario = {
        "farmers": [
            {"id": 1, "name": "Player", "country": "fr"},
            {"id": 2, "name": "Opponent", "country": "fr"},
        ],
        "teams": [
            {"id": 1, "name": "PlayerTeam"},
            {"id": 2, "name": "OpponentTeam"},
        ],
        "entities": [
            [our_entity],
            [opp_entity],
        ],
        "random_seed": seed,
        "max_turns": 64,
        "max_operations_per_entity": max_ops,
    }

    return scenario


def build_boss_scenario(configs, seed=None):
    """Build a Fennel King boss fight scenario with all 4 leeks vs graal + crystals.

    Loads the boss template and map data, builds team 1 from leek configs,
    and team 2 from the template's boss entity definitions.
    """
    if seed is None:
        seed = random.randint(1, 2**31 - 1)

    # Load boss template and map data
    if not BOSS_TEMPLATE.exists():
        print(f"ERROR: {BOSS_TEMPLATE} not found.")
        sys.exit(1)
    if not BOSS_MAP_DATA.exists():
        print(f"ERROR: {BOSS_MAP_DATA} not found. Run: python3 tools/extract_boss_map.py")
        sys.exit(1)

    with open(BOSS_TEMPLATE) as f:
        template = json.load(f)
    with open(BOSS_MAP_DATA) as f:
        map_data = json.load(f)

    leek_names = template["player_leeks"]
    player_cells = template["player_cells"]
    boss_entities_cfg = template["boss_entities"]

    # Build team 1: our 4 leeks
    team1_entities = []
    farmers = []
    all_leeks = configs.get("leeks", {})

    for i, leek_name in enumerate(leek_names):
        cfg = all_leeks.get(leek_name)
        if not cfg:
            print(f"ERROR: Leek '{leek_name}' not found in leek_configs.json")
            sys.exit(1)

        farmer_id = i + 1
        entity_id = i + 1
        farmers.append({"id": farmer_id, "name": leek_name, "country": "fr"})

        # Ensure puzzle chips are equipped (only AdaLovelace has both on the real server)
        chips = list(cfg.get("chips", []))
        if leek_name == "AdaLovelace":
            if CHIP_GRAPPLE_ID not in chips:
                chips.append(CHIP_GRAPPLE_ID)
            if CHIP_BOXING_GLOVE_ID not in chips:
                chips.append(CHIP_BOXING_GLOVE_ID)

        entity = {
            "id": entity_id,
            "ai": AI_PATH,
            "name": cfg["name"],
            "type": cfg.get("type", 0),
            "farmer": farmer_id,
            "team": 1,
            "level": cfg.get("level", 301),
            "life": cfg.get("life", 5000),
            "cores": cfg.get("cores", 14),
            "ram": cfg.get("ram", 50),
            "tp": cfg.get("tp", 20),
            "mp": cfg.get("mp", 6),
            "strength": cfg.get("strength", 0),
            "magic": cfg.get("magic", 0),
            "agility": cfg.get("agility", 0),
            "wisdom": cfg.get("wisdom", 0),
            "resistance": cfg.get("resistance", 0),
            "science": cfg.get("science", 0),
            "frequency": cfg.get("frequency", 100),
            "weapons": cfg.get("weapons", []),
            "chips": chips,
            "cell": player_cells[i] if i < len(player_cells) else 50 + i * 35,
        }
        team1_entities.append(entity)

    # Build team 2: graal + 4 crystals (passive, do_nothing AI)
    boss_farmer_id = len(leek_names) + 1
    farmers.append({"id": boss_farmer_id, "name": "BossTeam", "country": "fr"})

    team2_entities = []
    for j, bcfg in enumerate(boss_entities_cfg):
        entity_id = len(leek_names) + 1 + j
        entity = {
            "id": entity_id,
            "ai": DO_NOTHING_AI,
            "name": bcfg["name"],
            "type": 0,
            "farmer": boss_farmer_id,
            "team": 2,
            "level": bcfg.get("level", 301),
            "life": bcfg.get("life", 10000),
            "cores": bcfg.get("cores", 1),
            "ram": bcfg.get("ram", 1),
            "tp": bcfg.get("tp", 0),
            "mp": bcfg.get("mp", 0),
            "strength": bcfg.get("strength", 0),
            "magic": bcfg.get("magic", 0),
            "agility": bcfg.get("agility", 0),
            "wisdom": bcfg.get("wisdom", 0),
            "resistance": bcfg.get("resistance", 500),
            "science": bcfg.get("science", 0),
            "frequency": bcfg.get("frequency", 100),
            "weapons": bcfg.get("weapons", []),
            "chips": bcfg.get("chips", []),
            "cell": bcfg["cell"],
        }
        team2_entities.append(entity)

    # Override map team positions to match entity cell assignments
    # (generator uses map team arrays for spawn positions, not entity "cell" field)
    # Also ensure required fields are present for the generator's Map parser
    boss_map = dict(map_data)
    boss_map["team1"] = [e["cell"] for e in team1_entities]
    boss_map["team2"] = [e["cell"] for e in team2_entities]
    if "pattern" not in boss_map:
        boss_map["pattern"] = []
    if "type" not in boss_map:
        boss_map["type"] = 0

    scenario = {
        "boss": template.get("boss", 2),
        "farmers": farmers,
        "teams": [
            {"id": 1, "name": "Players"},
            {"id": 2, "name": "Boss"},
        ],
        "entities": [
            team1_entities,
            team2_entities,
        ],
        "map": boss_map,
        "random_seed": seed,
        "max_turns": template.get("max_turns", 64),
        "max_operations_per_entity": 20_000_000,
    }

    return scenario


def run_fight(scenario, fight_index=0, verbose=False):
    """Run a single fight via the generator JAR.

    Returns dict with fight result or error info.
    """
    # Write scenario to temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="lw_scenario_", delete=False, dir="/tmp"
    ) as f:
        json.dump(scenario, f)
        scenario_path = f.name

    try:
        env = os.environ.copy()
        env["JAVA_HOME"] = JAVA_HOME

        java_bin = os.path.join(JAVA_HOME, "bin", "java")
        cmd = [java_bin, "-jar", str(GENERATOR_JAR), scenario_path]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(GENERATOR_DIR),
            env=env,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if not stdout:
            return {
                "error": f"No output from generator (exit code {result.returncode}). stderr: {stderr[:500] if stderr else 'none'}",
                "stderr": stderr,
                "seed": scenario.get("random_seed"),
                "fight_index": fight_index,
            }

        # Parse JSON output (use strict=False for control chars in strings)
        # Generator may print stack traces to stdout before the JSON blob
        json_start = stdout.find('{"')
        if json_start > 0:
            stdout = stdout[json_start:]
        try:
            data = json.loads(stdout, strict=False)
        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON output: {e}. stderr: {stderr[:500] if stderr else 'none'}",
                "stdout_preview": stdout[:500],
                "seed": scenario.get("random_seed"),
                "fight_index": fight_index,
            }

        fight = data.get("fight", {})
        actions = fight.get("actions", [])
        leeks = fight.get("leeks", [])
        ops = fight.get("ops", {})
        winner_raw = data.get("winner", -1)

        # Map winner to result string
        # Generator uses 0-indexed team indices: 0=team1 wins, 1=team2 wins, -1=draw
        if winner_raw == 0:
            result_str = "WIN"
        elif winner_raw == 1:
            result_str = "LOSS"
        else:
            result_str = "DRAW"

        # Check for AI crash (entity 0 has 0 ops and BUG actions)
        our_entity_id = 0  # First entity (index 0 in generator output)
        our_ops = 0
        if isinstance(ops, dict):
            our_ops = ops.get("0", ops.get(0, 0))
        has_bug = any(
            a[0] == ACTION_BUG and len(a) > 1 and a[1] == our_entity_id
            for a in actions
            if isinstance(a, list) and len(a) > 1
        )

        # Count turns
        total_turns = sum(1 for a in actions if isinstance(a, list) and a[0] == ACTION_NEW_TURN)

        return {
            "result": result_str,
            "winner": winner_raw,
            "fight_index": fight_index,
            "seed": scenario.get("random_seed"),
            "total_turns": total_turns,
            "our_ops": our_ops,
            "has_bug": has_bug,
            "duration": data.get("duration", 0),
            "compilation_time": data.get("compilation_time", 0),
            "execution_time": data.get("execution_time", 0),
            "actions": actions,
            "leeks": leeks,
            "ops": ops,
            "logs": data.get("logs", {}),
            "stderr": stderr if verbose else None,
        }

    except subprocess.TimeoutExpired:
        return {
            "error": "Fight timed out (120s)",
            "seed": scenario.get("random_seed"),
            "fight_index": fight_index,
        }
    except Exception as e:
        return {
            "error": str(e),
            "seed": scenario.get("random_seed"),
            "fight_index": fight_index,
        }
    finally:
        try:
            os.unlink(scenario_path)
        except OSError:
            pass


def _run_fight_worker(args):
    """Worker function for parallel execution."""
    scenario, fight_index, verbose = args
    return run_fight(scenario, fight_index, verbose)


def parse_fight_actions(fight_result):
    """Parse fight actions using FightActionParser.

    Adapts generator output (flat leeks list with team field) to the
    parser's expected format (leeks1/leeks2 split).
    """
    leeks = fight_result.get("leeks", [])
    actions = fight_result.get("actions", [])

    if not actions:
        return None

    # Split leeks by team for the parser
    leeks1 = [l for l in leeks if l.get("team") == 1]
    leeks2 = [l for l in leeks if l.get("team") == 2]

    # Build adapted fight data
    adapted = {
        "leeks1": leeks1,
        "leeks2": leeks2,
    }

    parser = FightActionParser()
    # Team 1 IDs are "ours"
    our_ids = [l["id"] for l in leeks1]
    parser.set_entity_names(adapted, our_ids)
    return parser.parse_actions(actions)


def print_summary(results, leek_name, opponent_name, elapsed):
    """Print aggregated test results."""
    wins = sum(1 for r in results if r.get("result") == "WIN")
    losses = sum(1 for r in results if r.get("result") == "LOSS")
    draws = sum(1 for r in results if r.get("result") == "DRAW")
    errors = sum(1 for r in results if "error" in r)
    bugs = sum(1 for r in results if r.get("has_bug"))
    total = len(results)
    valid = wins + losses + draws

    print()
    print("=" * 60)
    print("LOCAL TEST RESULTS")
    print("=" * 60)
    print(f"Leek: {leek_name} vs {opponent_name}")
    print(f"Wins: {wins}  Losses: {losses}  Draws: {draws}  Errors: {errors}")
    if valid > 0:
        print(f"Win Rate: {wins / valid * 100:.1f}%")
    if bugs > 0:
        print(f"WARNING: {bugs} fight(s) had AI crashes (action 1002)")

    # Duration stats
    durations = [r["total_turns"] for r in results if "total_turns" in r]
    if durations:
        print(f"Avg turns: {sum(durations) / len(durations):.1f}  "
              f"(min {min(durations)}, max {max(durations)})")

    ops_list = [r["our_ops"] for r in results if "our_ops" in r and r["our_ops"] > 0]
    if ops_list:
        avg_ops = sum(ops_list) / len(ops_list)
        print(f"Avg ops: {avg_ops:,.0f}  "
              f"(min {min(ops_list):,}, max {max(ops_list):,})")

    print(f"Wall time: {elapsed:.1f}s ({elapsed / max(total, 1):.1f}s/fight)")

    # Aggregate combat stats from parsed actions
    all_our_dmg = []
    all_our_heal = []
    all_enemy_dmg = []
    chip_counts = {}
    weapon_counts = {}

    for r in results:
        summary = r.get("action_summary")
        if not summary:
            continue
        our = summary.get("our_stats", {})
        enemy = summary.get("enemy_stats", {})
        all_our_dmg.append(our.get("damage_dealt", 0))
        all_our_heal.append(our.get("healing", 0))
        all_enemy_dmg.append(enemy.get("damage_dealt", 0))
        for chip, count in our.get("chips", {}).items():
            chip_counts[chip] = chip_counts.get(chip, 0) + count
        for weapon, count in our.get("weapons", {}).items():
            weapon_counts[weapon] = weapon_counts.get(weapon, 0) + count

    if all_our_dmg:
        print(f"\nAvg damage dealt: {sum(all_our_dmg) / len(all_our_dmg):.0f}  "
              f"Avg damage taken: {sum(all_enemy_dmg) / len(all_enemy_dmg):.0f}")
        print(f"Avg healing: {sum(all_our_heal) / len(all_our_heal):.0f}")

    if chip_counts:
        print(f"\nTop chips used:")
        for chip, count in sorted(chip_counts.items(), key=lambda x: -x[1])[:8]:
            print(f"  {chip}: {count}x")

    if weapon_counts:
        print(f"Weapons used:")
        for weapon, count in sorted(weapon_counts.items(), key=lambda x: -x[1]):
            print(f"  {weapon}: {count}x")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Local LeekWars fight test runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("num_fights", type=int, help="Number of fights to run")
    parser.add_argument("opponent", help="Opponent key (dummy_str, smart_str, mirror, boss_fennel, etc.)")
    parser.add_argument("--leek", default=None, help="Leek name from leek_configs.json (not required for boss_fennel)")
    parser.add_argument("--parallel", type=int, default=1, help="Number of parallel workers (default: 1)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for deterministic replay")
    parser.add_argument("--verbose", action="store_true", help="Save per-fight logs and stderr")
    parser.add_argument("--save", action="store_true", help="Save results JSON to file")

    args = parser.parse_args()

    # Validate generator
    if not GENERATOR_JAR.exists():
        print(f"ERROR: Generator JAR not found at {GENERATOR_JAR}")
        print("Build it: cd /home/ubuntu/leek-wars-generator && JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew jar")
        return 1

    # Load configs
    configs = load_configs()
    is_boss = args.opponent == "boss_fennel"

    if is_boss:
        leek_name = "AllLeeks"
        print(f"Local test: Boss Fight (Fennel King) x{args.num_fights}")
    else:
        if not args.leek:
            print("ERROR: --leek is required for non-boss opponents")
            return 1
        leek_cfg = configs.get("leeks", {}).get(args.leek)
        if not leek_cfg:
            available = list(configs.get("leeks", {}).keys())
            print(f"ERROR: Leek '{args.leek}' not found. Available: {available}")
            return 1
        leek_name = args.leek

        # Handle mirror mode
        if args.opponent == "mirror":
            opponent_cfg = leek_cfg.copy()
            opponent_cfg["name"] = f"{leek_cfg['name']}_Mirror"
            opponent_ai = AI_PATH
        else:
            opponent_cfg = configs.get("opponents", {}).get(args.opponent)
            if not opponent_cfg:
                available = list(configs.get("opponents", {}).keys()) + ["mirror", "boss_fennel"]
                print(f"ERROR: Opponent '{args.opponent}' not found. Available: {available}")
                return 1
            opponent_ai = None

        print(f"Local test: {args.leek} vs {args.opponent} x{args.num_fights}")

    if args.parallel > 1:
        print(f"Parallel workers: {args.parallel}")
    if args.seed is not None:
        print(f"Fixed seed: {args.seed}")

    # Build scenarios
    scenarios = []
    for i in range(args.num_fights):
        seed = args.seed if args.seed is not None else random.randint(1, 2**31 - 1)
        # If using fixed seed with multiple fights, increment to get different fights
        if args.seed is not None and args.num_fights > 1:
            seed = args.seed + i
        if is_boss:
            scenario = build_boss_scenario(configs, seed=seed)
        else:
            scenario = build_scenario(leek_cfg, opponent_cfg, seed=seed, opponent_ai=opponent_ai)
        scenarios.append((scenario, i, args.verbose))

    # Run fights
    t0 = time.time()
    results = []

    if args.parallel > 1 and args.num_fights > 1:
        print(f"Running {args.num_fights} fights with {args.parallel} workers...")
        with ProcessPoolExecutor(max_workers=args.parallel) as executor:
            futures = {executor.submit(_run_fight_worker, s): s[1] for s in scenarios}
            for future in as_completed(futures):
                fight_idx = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = {"error": str(e), "fight_index": fight_idx}
                results.append(result)

                # Progress
                r = result.get("result", "ERR")
                indicator = {"WIN": "W", "LOSS": "L", "DRAW": "D"}.get(r, "!")
                print(indicator, end="", flush=True)
        print()
    else:
        print(f"Running {args.num_fights} fight(s)...")
        for scenario, idx, verbose in scenarios:
            result = run_fight(scenario, idx, verbose)
            results.append(result)

            r = result.get("result", "ERR")
            indicator = {"WIN": "W", "LOSS": "L", "DRAW": "D"}.get(r, "!")
            print(indicator, end="", flush=True)
        print()

    elapsed = time.time() - t0

    # Sort by fight index
    results.sort(key=lambda x: x.get("fight_index", 0))

    # Parse actions for each successful fight
    for r in results:
        if "error" not in r and "actions" in r:
            r["action_summary"] = parse_fight_actions(r)

    # Print summary
    print_summary(results, leek_name, args.opponent, elapsed)

    # Verbose: print per-fight details
    if args.verbose:
        print("\n--- Per-fight details ---")
        for r in results:
            idx = r.get("fight_index", "?")
            if "error" in r:
                print(f"  Fight {idx}: ERROR - {r['error']}")
                continue
            result = r.get("result", "?")
            turns = r.get("total_turns", "?")
            ops = r.get("our_ops", 0)
            bug = " [BUG]" if r.get("has_bug") else ""
            print(f"  Fight {idx}: {result} in {turns} turns, {ops:,} ops, seed={r.get('seed')}{bug}")

            if r.get("stderr"):
                # Show only first few lines of stderr
                lines = r["stderr"].split("\n")[:3]
                for line in lines:
                    if line.strip():
                        print(f"    stderr: {line}")

    # Save results
    if args.save or args.verbose:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"test_results_local_{leek_name}_{args.opponent}_{timestamp}.json"

        save_data = {
            "timestamp": timestamp,
            "leek": leek_name,
            "opponent": args.opponent,
            "num_fights": args.num_fights,
            "parallel": args.parallel,
            "seed": args.seed,
            "results": {
                "wins": sum(1 for r in results if r.get("result") == "WIN"),
                "losses": sum(1 for r in results if r.get("result") == "LOSS"),
                "draws": sum(1 for r in results if r.get("result") == "DRAW"),
                "errors": sum(1 for r in results if "error" in r),
            },
            "fights": [
                {
                    "fight_index": r.get("fight_index"),
                    "result": r.get("result", "ERROR"),
                    "seed": r.get("seed"),
                    "total_turns": r.get("total_turns"),
                    "our_ops": r.get("our_ops"),
                    "has_bug": r.get("has_bug"),
                    "error": r.get("error"),
                    "action_summary": r.get("action_summary"),
                }
                for r in results
            ],
            "wall_time_s": elapsed,
        }

        with open(results_file, "w") as f:
            json.dump(save_data, f, indent=2)
        print(f"\nResults saved to: {results_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
