#!/usr/bin/env python3
"""
Local Genetic Optimizer for V8 Weight Profiles & Counter-Strategy Multipliers

Evolves weight profile maps in weight_profiles.lk or counter-strategy multipliers
in strategic_depth.lk using local fight testing.

Usage:
    # Optimize MargaretHamilton's MAGIC weights (weights mode)
    python3 tools/genetic_optimizer_local.py \
        --build MAGIC --leek MargaretHamilton \
        --train-opponents smart_str smart_mag smart_agi \
        --val-opponents dummy_str dummy_mag \
        --generations 30 --population 20 --fights-per-opponent 10 --parallel 12

    # Optimize counter-strategy multipliers (counter mode)
    python3 tools/genetic_optimizer_local.py \
        --mode counter \
        --leeks MargaretHamilton AdaLovelace KurtGodel EdsgerDijkstra \
        --train-opponents smart_str smart_mag smart_agi smart_tank \
        --generations 30 --population 20 --fights-per-opponent 5 --parallel 12

    # Resume from checkpoint
    python3 tools/genetic_optimizer_local.py \
        --resume ga_local/run_COUNTER_.../checkpoint_gen15.json

    # Apply best weights
    python3 tools/genetic_optimizer_local.py \
        --apply ga_local/run_COUNTER_.../best_weights.json
"""

import argparse
import copy
import glob as globmod
import json
import os
import random
import re
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
GENERATOR_DIR = Path("/home/ubuntu/leek-wars-generator")
WEIGHT_PROFILES_PATH = PROJECT_DIR / "V8_modules" / "weight_profiles.lk"
STRATEGIC_DEPTH_PATH = PROJECT_DIR / "V8_modules" / "strategic_depth.lk"
CACHE_DIR = GENERATOR_DIR / "ai"

# Import local_test infrastructure
sys.path.insert(0, str(SCRIPT_DIR))
from local_test import build_scenario, run_fight, _run_fight_worker, load_configs

# ── Build type name -> global variable name mapping ──
BUILD_NAME_TO_GLOBAL = {
    "STRENGTH": "STRENGTH_WEIGHTS",
    "MAGIC": "MAGIC_WEIGHTS",
    "AGILITY": "AGILITY_WEIGHTS",
    "STRENGTH_SCIENCE": "STRENGTH_SCIENCE_WEIGHTS",
    "TANK_SCI": "TANK_SCI_WEIGHTS",
    "HYBRID": "HYBRID_WEIGHTS",
    "BRUISER_REFLECT": "BRUISER_REFLECT_WEIGHTS",
}

# ── Evolvable keys with bounds ──
EVOLVABLE_KEYS = {
    "burstDamage":      (0, 600),
    "weaponUses":       (0, 200),
    "tpEfficiency":     (0, 100),
    "dotEffects":       (-100, 800),
    "kiteDistance":      (-100, 400),
    "damageReturn":     (0, 600),
    "poisonStacks":     (0, 600),
    "shieldValue":      (0, 600),
    "healValue":        (0, 300),
    "distanceToTarget": (-50, 50),
    "threatReduction":  (0, 400),
    "otkoBonus":        (1000, 8000),
    "checkpointBonus":  (500, 5000),
    "multiTargetBonus": (0, 1000),
    "denialValue":      (0, 600),
    "poisonLethalBonus": (0, 1200),
}

# Extra key for science builds
NOVA_KEY = {"novaEffects": (0, 800)}

# Builds that have novaEffects
NOVA_BUILDS = {"TANK_SCI", "STRENGTH_SCIENCE"}

# Frozen keys (not evolvable)
FROZEN_KEYS = {
    "bulbDamageMultiplier",
    "bulbKillBonusHealer",
    "bulbKillBonusBuffer",
    "bulbKillBonusAttacker",
}

# ── Counter-strategy multiplier keys with bounds (percentage: 100 = ×1.0) ──
COUNTER_EVOLVABLE_KEYS = {
    "vs_kiter_burst":       (80, 200),
    "vs_kiter_heal":        (80, 200),
    "vs_kiter_kite":        (30, 120),
    "vs_kiter_dist":        (80, 250),
    "vs_kiter_dot":         (80, 200),
    "vs_burst_shield":      (80, 200),
    "vs_burst_heal":        (80, 200),
    "vs_burst_threat":      (80, 200),
    "vs_burst_burst":       (80, 200),
    "vs_tank_nova":         (80, 200),
    "vs_tank_denial":       (80, 200),
    "vs_tank_dot":          (80, 200),
    "vs_reflect_on_burst":  (20, 100),
    "vs_reflect_on_shield": (80, 200),
    "vs_reflect_on_heal":   (80, 200),
    "vs_reflect_off_burst": (80, 200),
    "cd_shield_burst":      (80, 200),
    "cd_shield_otko":       (80, 150),
    "cd_heal_burst":        (80, 200),
}


class WeightGenome:
    """A single weight profile with mutation and crossover."""

    def __init__(self, build_type, weights=None):
        self.build_type = build_type
        self.weights = weights or {}

    @classmethod
    def from_baseline(cls, build_type, profiles_path=None):
        """Parse current weights from weight_profiles.lk."""
        injector = WeightProfileInjector(profiles_path or WEIGHT_PROFILES_PATH)
        weights = injector.parse_baseline(build_type)
        return cls(build_type, weights)

    def get_bounds(self):
        """Get evolvable keys and their bounds for this build type."""
        bounds = dict(EVOLVABLE_KEYS)
        if self.build_type in NOVA_BUILDS:
            bounds.update(NOVA_KEY)
        return bounds

    def get_evolvable_keys(self):
        """Return only the evolvable keys present in this genome."""
        bounds = self.get_bounds()
        return {k: v for k, v in self.weights.items() if k in bounds}

    def mutate(self, rate=0.15, strength=0.2):
        """Gaussian mutation with strength proportional to bounds range."""
        bounds = self.get_bounds()
        for key in list(self.weights.keys()):
            if key not in bounds:
                continue
            if random.random() < rate:
                lo, hi = bounds[key]
                span = hi - lo
                delta = random.gauss(0, strength * span)
                new_val = self.weights[key] + delta
                # Clamp to bounds
                new_val = max(lo, min(hi, new_val))
                # Round to int (LeekScript weights are integers)
                self.weights[key] = round(new_val)

    @staticmethod
    def crossover(parent1, parent2):
        """Uniform crossover: 50/50 per key."""
        child = WeightGenome(parent1.build_type)
        # Start with parent1's full weights (including frozen keys)
        child.weights = dict(parent1.weights)
        # For evolvable keys, randomly pick from either parent
        bounds = parent1.get_bounds()
        for key in bounds:
            if key in parent1.weights and key in parent2.weights:
                if random.random() < 0.5:
                    child.weights[key] = parent2.weights[key]
        return child

    def to_dict(self):
        return {"build_type": self.build_type, "weights": dict(self.weights)}

    @classmethod
    def from_dict(cls, data):
        return cls(data["build_type"], dict(data["weights"]))


class CounterGenome(WeightGenome):
    """A counter-strategy multiplier genome."""

    def __init__(self, weights=None):
        super().__init__("COUNTER", weights)

    @classmethod
    def from_baseline(cls, build_type=None, profiles_path=None):
        """Parse current counter multipliers from strategic_depth.lk."""
        injector = CounterWeightInjector()
        weights = injector.parse_baseline()
        return cls(weights)

    def get_bounds(self):
        return dict(COUNTER_EVOLVABLE_KEYS)

    def get_evolvable_keys(self):
        bounds = self.get_bounds()
        return {k: v for k, v in self.weights.items() if k in bounds}

    @staticmethod
    def crossover(parent1, parent2):
        child = CounterGenome()
        child.weights = dict(parent1.weights)
        bounds = COUNTER_EVOLVABLE_KEYS
        for key in bounds:
            if key in parent1.weights and key in parent2.weights:
                if random.random() < 0.5:
                    child.weights[key] = parent2.weights[key]
        return child

    def to_dict(self):
        return {"build_type": "COUNTER", "weights": dict(self.weights)}

    @classmethod
    def from_dict(cls, data):
        return cls(dict(data["weights"]))


class WeightProfileInjector:
    """Read/write weight blocks in weight_profiles.lk."""

    def __init__(self, profiles_path=None):
        self.path = Path(profiles_path or WEIGHT_PROFILES_PATH)
        self.backup_path = self.path.with_suffix(".lk.ga_backup")

    def parse_baseline(self, build_type):
        """Extract current weights for a build type."""
        global_name = BUILD_NAME_TO_GLOBAL.get(build_type)
        if not global_name:
            raise ValueError(f"Unknown build type: {build_type}. "
                             f"Available: {list(BUILD_NAME_TO_GLOBAL.keys())}")

        content = self.path.read_text()

        # Find the weight block: global MAGIC_WEIGHTS = [ ... ]
        pattern = rf"global\s+{global_name}\s*=\s*\["
        match = re.search(pattern, content)
        if not match:
            raise ValueError(f"Could not find {global_name} in {self.path}")

        # Find the matching closing bracket
        start = match.end()
        bracket_depth = 1
        pos = start
        while pos < len(content) and bracket_depth > 0:
            if content[pos] == "[":
                bracket_depth += 1
            elif content[pos] == "]":
                bracket_depth -= 1
            pos += 1

        block = content[start:pos - 1]

        # Parse key-value pairs: 'key': value
        weights = {}
        for m in re.finditer(r"'(\w+)'\s*:\s*(-?[\d.]+)", block):
            key = m.group(1)
            val_str = m.group(2)
            # Use int if no decimal, else float
            if "." in val_str:
                weights[key] = float(val_str)
            else:
                weights[key] = int(val_str)

        return weights

    def inject(self, build_type, weights):
        """Replace a weight block in weight_profiles.lk with new values."""
        global_name = BUILD_NAME_TO_GLOBAL.get(build_type)
        if not global_name:
            raise ValueError(f"Unknown build type: {build_type}")

        content = self.path.read_text()

        # Find the full weight block (from 'global X_WEIGHTS = [' to matching ']')
        pattern = rf"(global\s+{global_name}\s*=\s*\[)(.*?)(\])"
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            raise ValueError(f"Could not find {global_name} block in {self.path}")

        old_block = match.group(2)

        # Build new block preserving comment structure
        # Parse existing lines to preserve comments
        new_lines = []
        for line in old_block.split("\n"):
            stripped = line.strip()
            if not stripped:
                new_lines.append(line)
                continue

            # Match: 'key': value  // comment  OR  'key': value
            key_match = re.match(
                r"(\s*)'(\w+)'\s*:\s*(-?[\d.]+)\s*,?\s*(//.*)?$", line
            )
            if key_match:
                indent = key_match.group(1)
                key = key_match.group(2)
                comment = key_match.group(4) or ""

                if key in weights:
                    val = weights[key]
                    # Format: int for whole numbers, float for decimals
                    if isinstance(val, float) and val != int(val):
                        val_str = str(val)
                    else:
                        val_str = str(int(val))

                    # Check if this is the last key (no trailing comma needed)
                    # We'll add commas for all but we let the regex handle it
                    if comment:
                        new_line = f"{indent}'{key}': {val_str},{comment.rstrip()}"
                    else:
                        new_line = f"{indent}'{key}': {val_str},"
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        new_block = "\n".join(new_lines)

        # Replace the block
        new_content = content[:match.start(2)] + new_block + content[match.end(2):]
        self.path.write_text(new_content)

    def backup(self):
        """Create a safety backup of weight_profiles.lk."""
        if not self.backup_path.exists():
            shutil.copy2(self.path, self.backup_path)
            print(f"Backup saved: {self.backup_path}")

    def restore(self):
        """Restore weight_profiles.lk from backup."""
        if self.backup_path.exists():
            shutil.copy2(self.backup_path, self.path)
            print(f"Restored from backup: {self.backup_path}")

    @staticmethod
    def invalidate_cache():
        """Clear compiled .class/.java/.lines files so generator recompiles."""
        patterns = ["*.class", "*.java", "*.lines"]
        count = 0
        for pat in patterns:
            for f in globmod.glob(str(CACHE_DIR / pat)):
                os.unlink(f)
                count += 1
        return count


class CounterWeightInjector:
    """Read/write COUNTER_MULTS map in strategic_depth.lk."""

    def __init__(self):
        self.path = STRATEGIC_DEPTH_PATH
        self.backup_path = self.path.with_suffix(".lk.ga_backup")

    def parse_baseline(self):
        """Extract current COUNTER_MULTS values."""
        content = self.path.read_text()

        pattern = r"global\s+COUNTER_MULTS\s*=\s*\["
        match = re.search(pattern, content)
        if not match:
            raise ValueError(f"Could not find COUNTER_MULTS in {self.path}")

        # Find matching closing bracket
        start = match.end()
        bracket_depth = 1
        pos = start
        while pos < len(content) and bracket_depth > 0:
            if content[pos] == "[":
                bracket_depth += 1
            elif content[pos] == "]":
                bracket_depth -= 1
            pos += 1

        block = content[start:pos - 1]

        # Parse key-value pairs
        weights = {}
        for m in re.finditer(r"'(\w+)'\s*:\s*(-?[\d.]+)", block):
            key = m.group(1)
            val_str = m.group(2)
            if "." in val_str:
                weights[key] = float(val_str)
            else:
                weights[key] = int(val_str)

        return weights

    def inject(self, weights):
        """Replace COUNTER_MULTS values in strategic_depth.lk."""
        content = self.path.read_text()

        pattern = r"(global\s+COUNTER_MULTS\s*=\s*\[)(.*?)(\])"
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            raise ValueError(f"Could not find COUNTER_MULTS block in {self.path}")

        old_block = match.group(2)

        # Build new block preserving comments
        new_lines = []
        for line in old_block.split("\n"):
            stripped = line.strip()
            if not stripped:
                new_lines.append(line)
                continue

            key_match = re.match(
                r"(\s*)'(\w+)'\s*:\s*(-?[\d.]+)\s*,?\s*(//.*)?$", line
            )
            if key_match:
                indent = key_match.group(1)
                key = key_match.group(2)
                comment = key_match.group(4) or ""

                if key in weights:
                    val = weights[key]
                    if isinstance(val, float) and val != int(val):
                        val_str = str(val)
                    else:
                        val_str = str(int(val))

                    if comment:
                        new_line = f"{indent}'{key}': {val_str},{comment.rstrip()}"
                    else:
                        new_line = f"{indent}'{key}': {val_str},"
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        new_block = "\n".join(new_lines)
        new_content = content[:match.start(2)] + new_block + content[match.end(2):]
        self.path.write_text(new_content)

    def backup(self):
        """Create a safety backup of strategic_depth.lk."""
        if not self.backup_path.exists():
            shutil.copy2(self.path, self.backup_path)
            print(f"Backup saved: {self.backup_path}")

    def restore(self):
        """Restore strategic_depth.lk from backup."""
        if self.backup_path.exists():
            shutil.copy2(self.backup_path, self.path)
            print(f"Restored from backup: {self.backup_path}")

    @staticmethod
    def invalidate_cache():
        """Clear compiled .class/.java/.lines files so generator recompiles."""
        return WeightProfileInjector.invalidate_cache()


class MultiLeekFightRunner:
    """Evaluate a genome across multiple leeks x opponents."""

    def __init__(self, leek_names, opponents, parallel_workers=12,
                 fights_per_opponent=5):
        self.leek_names = leek_names
        self.opponents = opponents
        self.parallel_workers = parallel_workers
        self.fights_per_opponent = fights_per_opponent

        # Load configs once
        self.configs = load_configs()

        # Validate leeks
        for leek in leek_names:
            if leek not in self.configs.get("leeks", {}):
                available = list(self.configs.get("leeks", {}).keys())
                raise ValueError(f"Leek '{leek}' not found. Available: {available}")

        # Validate opponents
        for opp in opponents:
            if opp not in self.configs.get("opponents", {}):
                available = list(self.configs.get("opponents", {}).keys())
                raise ValueError(f"Opponent '{opp}' not found. Available: {available}")

    def evaluate(self):
        """Run fights for all leek×opponent combos and return aggregated results.

        Returns dict with:
            win_rate, wins, losses, draws, errors, crashes, total,
            per_leek: dict[str, dict with per_opponent breakdown]
        """
        all_scenarios = []
        scenario_meta = []  # (leek_name, opp_name) per scenario

        for leek_name in self.leek_names:
            leek_cfg = self.configs["leeks"][leek_name]
            for opp_name in self.opponents:
                opp_cfg = self.configs["opponents"][opp_name]
                for i in range(self.fights_per_opponent):
                    seed = random.randint(1, 2**31 - 1)
                    scenario = build_scenario(leek_cfg, opp_cfg, seed=seed)
                    fight_idx = len(all_scenarios)
                    all_scenarios.append((scenario, fight_idx, False))
                    scenario_meta.append((leek_name, opp_name))

        # Run all fights in parallel
        results = []
        if self.parallel_workers > 1 and len(all_scenarios) > 1:
            with ProcessPoolExecutor(max_workers=self.parallel_workers) as executor:
                futures = {
                    executor.submit(_run_fight_worker, s): s[1]
                    for s in all_scenarios
                }
                for future in as_completed(futures):
                    fight_idx = futures[future]
                    try:
                        result = future.result()
                    except Exception as e:
                        result = {"error": str(e), "fight_index": fight_idx}
                    results.append(result)
        else:
            for scenario, idx, verbose in all_scenarios:
                results.append(run_fight(scenario, idx, verbose))

        # Sort by fight index
        results.sort(key=lambda x: x.get("fight_index", 0))

        # Aggregate results
        total_wins = 0
        total_losses = 0
        total_draws = 0
        total_errors = 0
        total_crashes = 0
        per_leek = {}

        for i, result in enumerate(results):
            leek_name, opp_name = scenario_meta[i]

            if leek_name not in per_leek:
                per_leek[leek_name] = {
                    "wins": 0, "losses": 0, "draws": 0,
                    "errors": 0, "crashes": 0, "total": 0,
                    "per_opponent": {},
                }
            leek_data = per_leek[leek_name]

            if opp_name not in leek_data["per_opponent"]:
                leek_data["per_opponent"][opp_name] = {
                    "wins": 0, "losses": 0, "draws": 0,
                    "errors": 0, "crashes": 0, "total": 0,
                }
            opp_data = leek_data["per_opponent"][opp_name]

            leek_data["total"] += 1
            opp_data["total"] += 1

            if "error" in result:
                total_errors += 1
                total_losses += 1
                leek_data["errors"] += 1
                leek_data["losses"] += 1
                opp_data["errors"] += 1
                opp_data["losses"] += 1
                continue

            if result.get("has_bug"):
                total_crashes += 1
                total_losses += 1
                leek_data["crashes"] += 1
                leek_data["losses"] += 1
                opp_data["crashes"] += 1
                opp_data["losses"] += 1
                continue

            r = result.get("result")
            if r == "WIN":
                total_wins += 1
                leek_data["wins"] += 1
                opp_data["wins"] += 1
            elif r == "LOSS":
                total_losses += 1
                leek_data["losses"] += 1
                opp_data["losses"] += 1
            else:
                total_draws += 1
                leek_data["draws"] += 1
                opp_data["draws"] += 1

        total = len(results)
        win_rate = total_wins / total if total > 0 else 0.0

        # Build flat per_opponent for compatibility with progress display
        per_opponent = {}
        for leek_name, leek_data in per_leek.items():
            for opp_name, opp_data in leek_data["per_opponent"].items():
                key = f"{leek_name[:4]}v{opp_name}"
                per_opponent[key] = opp_data

        return {
            "win_rate": win_rate,
            "wins": total_wins,
            "losses": total_losses,
            "draws": total_draws,
            "errors": total_errors,
            "crashes": total_crashes,
            "total": total,
            "per_opponent": per_opponent,
            "per_leek": per_leek,
        }


class LocalFightRunner:
    """Run fights using local_test.py infrastructure."""

    def __init__(self, leek_name, opponents, parallel_workers=12,
                 fights_per_opponent=10):
        self.leek_name = leek_name
        self.opponents = opponents
        self.parallel_workers = parallel_workers
        self.fights_per_opponent = fights_per_opponent

        # Load configs once
        self.configs = load_configs()
        self.leek_cfg = self.configs.get("leeks", {}).get(leek_name)
        if not self.leek_cfg:
            available = list(self.configs.get("leeks", {}).keys())
            raise ValueError(f"Leek '{leek_name}' not found. Available: {available}")

        # Validate opponents
        for opp in opponents:
            if opp not in self.configs.get("opponents", {}):
                available = list(self.configs.get("opponents", {}).keys())
                raise ValueError(f"Opponent '{opp}' not found. Available: {available}")

    def evaluate(self):
        """Run fights against all opponents and return results.

        Returns dict with:
            win_rate: float (0-1)
            wins: int
            losses: int
            draws: int
            errors: int
            crashes: int
            total: int
            per_opponent: dict[str, dict]
        """
        all_scenarios = []
        scenario_opponents = []  # Track which opponent each scenario belongs to

        for opp_name in self.opponents:
            opp_cfg = self.configs["opponents"][opp_name]
            for i in range(self.fights_per_opponent):
                seed = random.randint(1, 2**31 - 1)
                scenario = build_scenario(self.leek_cfg, opp_cfg, seed=seed)
                fight_idx = len(all_scenarios)
                all_scenarios.append((scenario, fight_idx, False))
                scenario_opponents.append(opp_name)

        # Run all fights in parallel
        results = []
        if self.parallel_workers > 1 and len(all_scenarios) > 1:
            with ProcessPoolExecutor(max_workers=self.parallel_workers) as executor:
                futures = {
                    executor.submit(_run_fight_worker, s): s[1]
                    for s in all_scenarios
                }
                for future in as_completed(futures):
                    fight_idx = futures[future]
                    try:
                        result = future.result()
                    except Exception as e:
                        result = {"error": str(e), "fight_index": fight_idx}
                    results.append(result)
        else:
            for scenario, idx, verbose in all_scenarios:
                results.append(run_fight(scenario, idx, verbose))

        # Sort by fight index
        results.sort(key=lambda x: x.get("fight_index", 0))

        # Aggregate results
        total_wins = 0
        total_losses = 0
        total_draws = 0
        total_errors = 0
        total_crashes = 0
        per_opponent = {}

        for i, result in enumerate(results):
            opp_name = scenario_opponents[i]
            if opp_name not in per_opponent:
                per_opponent[opp_name] = {
                    "wins": 0, "losses": 0, "draws": 0,
                    "errors": 0, "crashes": 0, "total": 0,
                }

            per_opponent[opp_name]["total"] += 1

            if "error" in result:
                total_errors += 1
                total_losses += 1  # Count errors as losses
                per_opponent[opp_name]["errors"] += 1
                per_opponent[opp_name]["losses"] += 1
                continue

            if result.get("has_bug"):
                total_crashes += 1
                total_losses += 1  # Count crashes as losses
                per_opponent[opp_name]["crashes"] += 1
                per_opponent[opp_name]["losses"] += 1
                continue

            r = result.get("result")
            if r == "WIN":
                total_wins += 1
                per_opponent[opp_name]["wins"] += 1
            elif r == "LOSS":
                total_losses += 1
                per_opponent[opp_name]["losses"] += 1
            else:  # DRAW
                total_draws += 1
                per_opponent[opp_name]["draws"] += 1

        total = len(results)
        win_rate = total_wins / total if total > 0 else 0.0

        return {
            "win_rate": win_rate,
            "wins": total_wins,
            "losses": total_losses,
            "draws": total_draws,
            "errors": total_errors,
            "crashes": total_crashes,
            "total": total,
            "per_opponent": per_opponent,
        }


class LocalGeneticOptimizer:
    """Main evolution loop for local weight profile optimization."""

    def __init__(self, build_type, leek_name, train_opponents, val_opponents=None,
                 population_size=20, fights_per_opponent=10, generations=30,
                 mutation_rate=0.15, mutation_strength=0.2, elitism=3,
                 tournament_size=4, parallel_workers=12,
                 mode="weights", leek_names=None):
        self.mode = mode  # "weights" or "counter"
        self.build_type = build_type
        self.leek_name = leek_name
        self.leek_names = leek_names or ([leek_name] if leek_name else [])
        self.train_opponents = train_opponents
        self.val_opponents = val_opponents or []
        self.population_size = population_size
        self.fights_per_opponent = fights_per_opponent
        self.max_generations = generations
        self.mutation_rate = mutation_rate
        self.mutation_strength = mutation_strength
        self.elitism = elitism
        self.tournament_size = tournament_size
        self.parallel_workers = parallel_workers

        if mode == "counter":
            self.injector = CounterWeightInjector()
        else:
            self.injector = WeightProfileInjector()
        self.population = []  # List of {genome: WeightGenome, fitness: float|None}
        self.generation = 0
        self.best_genome = None
        self.best_fitness = 0.0
        self.best_val_fitness = 0.0
        self.history = []

        # Output directory
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = PROJECT_DIR / "ga_local"
        self.run_dir = self.output_dir / f"run_{build_type}_{self.run_id}"

    def _create_baseline(self):
        """Create a baseline genome for the current mode."""
        if self.mode == "counter":
            return CounterGenome.from_baseline()
        else:
            return WeightGenome.from_baseline(self.build_type)

    def _genome_from_dict(self, data):
        """Deserialize a genome dict for the current mode."""
        if self.mode == "counter" or data.get("build_type") == "COUNTER":
            return CounterGenome.from_dict(data)
        else:
            return WeightGenome.from_dict(data)

    def initialize_population(self):
        """Create initial population: baseline + mutations."""
        print(f"Initializing population ({self.population_size} genomes)...")

        # Genome 0: baseline (current production weights)
        baseline = self._create_baseline()
        self.population.append({"genome": baseline, "fitness": None})

        # Genomes 1+: mutated variants
        for _ in range(1, self.population_size):
            mutant = self._create_baseline()
            mutant.mutate(rate=0.3, strength=0.3)  # Larger initial spread
            self.population.append({"genome": mutant, "fitness": None})

        print(f"Population initialized. {len(baseline.get_evolvable_keys())} evolvable keys.")

    def evaluate_genome(self, genome_idx, genome_entry):
        """Evaluate a single genome's fitness via local fights."""
        genome = genome_entry["genome"]

        # Inject weights
        if self.mode == "counter":
            self.injector.inject(genome.weights)
        else:
            self.injector.inject(self.build_type, genome.weights)

        # Clear compilation cache
        self.injector.invalidate_cache()

        # Run fights (multi-leek for counter mode, single-leek for weights mode)
        if self.mode == "counter" and len(self.leek_names) > 1:
            runner = MultiLeekFightRunner(
                leek_names=self.leek_names,
                opponents=self.train_opponents,
                parallel_workers=self.parallel_workers,
                fights_per_opponent=self.fights_per_opponent,
            )
        else:
            runner = LocalFightRunner(
                leek_name=self.leek_names[0] if self.leek_names else self.leek_name,
                opponents=self.train_opponents,
                parallel_workers=self.parallel_workers,
                fights_per_opponent=self.fights_per_opponent,
            )
        results = runner.evaluate()

        fitness = results["win_rate"]
        genome_entry["fitness"] = fitness
        genome_entry["results"] = results

        # Progress indicator
        opp_detail = "  ".join(
            f"{opp}:{d['wins']}/{d['total']}"
            for opp, d in results["per_opponent"].items()
        )
        crashes = results["crashes"]
        crash_str = f" [{crashes} crashes]" if crashes else ""
        print(f"  [{genome_idx+1:2d}/{self.population_size}] "
              f"fitness={fitness:.3f} ({results['wins']}W/{results['losses']}L"
              f"/{results['draws']}D{crash_str})  {opp_detail}")

        return fitness

    def evaluate_population(self):
        """Evaluate all unevaluated genomes."""
        print(f"\n{'='*60}")
        print(f"GENERATION {self.generation + 1} - EVALUATION")
        print(f"{'='*60}")
        print(f"Train: {', '.join(self.train_opponents)} "
              f"({self.fights_per_opponent} fights/opponent)")

        t0 = time.time()
        for i, entry in enumerate(self.population):
            if entry["fitness"] is None:
                self.evaluate_genome(i, entry)

        elapsed = time.time() - t0

        # Sort by fitness descending
        self.population.sort(
            key=lambda x: x["fitness"] if x["fitness"] is not None else 0.0,
            reverse=True,
        )

        # Update best
        top = self.population[0]
        if top["fitness"] > self.best_fitness:
            self.best_fitness = top["fitness"]
            self.best_genome = copy.deepcopy(top["genome"])
            print(f"\n*** NEW BEST: fitness={self.best_fitness:.3f} ***")

        # Stats
        fitnesses = [e["fitness"] for e in self.population if e["fitness"] is not None]
        avg = sum(fitnesses) / len(fitnesses) if fitnesses else 0
        print(f"\nGen {self.generation + 1} summary: "
              f"best={fitnesses[0]:.3f} avg={avg:.3f} worst={fitnesses[-1]:.3f} "
              f"({elapsed:.1f}s)")

        return elapsed

    def validate_best(self):
        """Validate best genome on held-out opponents."""
        if not self.val_opponents or not self.best_genome:
            return None

        print(f"\nValidating best genome on: {', '.join(self.val_opponents)}")

        # Inject best weights
        if self.mode == "counter":
            self.injector.inject(self.best_genome.weights)
        else:
            self.injector.inject(self.build_type, self.best_genome.weights)
        self.injector.invalidate_cache()

        if self.mode == "counter" and len(self.leek_names) > 1:
            runner = MultiLeekFightRunner(
                leek_names=self.leek_names,
                opponents=self.val_opponents,
                parallel_workers=self.parallel_workers,
                fights_per_opponent=self.fights_per_opponent,
            )
        else:
            runner = LocalFightRunner(
                leek_name=self.leek_names[0] if self.leek_names else self.leek_name,
                opponents=self.val_opponents,
                parallel_workers=self.parallel_workers,
                fights_per_opponent=self.fights_per_opponent,
            )
        results = runner.evaluate()
        val_fitness = results["win_rate"]

        opp_detail = "  ".join(
            f"{opp}:{d['wins']}/{d['total']}"
            for opp, d in results["per_opponent"].items()
        )
        print(f"Validation: fitness={val_fitness:.3f} "
              f"({results['wins']}W/{results['losses']}L/{results['draws']}D)  "
              f"{opp_detail}")

        # Overfitting check
        gap = self.best_fitness - val_fitness
        if gap > 0.15:
            print(f"WARNING: Overfitting detected! "
                  f"Train={self.best_fitness:.3f} Val={val_fitness:.3f} Gap={gap:.1%}")

        self.best_val_fitness = val_fitness
        return val_fitness

    def tournament_selection(self):
        """Select a parent via tournament selection."""
        tournament = random.sample(self.population, min(self.tournament_size, len(self.population)))
        tournament.sort(key=lambda x: x["fitness"] if x["fitness"] else 0, reverse=True)
        return tournament[0]["genome"]

    def evolve(self):
        """Create next generation: elitism + tournament + crossover + mutation."""
        new_pop = []

        # Elitism: preserve top N
        for i in range(min(self.elitism, len(self.population))):
            elite = copy.deepcopy(self.population[i])
            # Keep fitness so we don't re-evaluate
            new_pop.append(elite)

        # Fill rest via crossover + mutation
        crossover_fn = CounterGenome.crossover if self.mode == "counter" else WeightGenome.crossover
        while len(new_pop) < self.population_size:
            p1 = self.tournament_selection()
            p2 = self.tournament_selection()
            child = crossover_fn(p1, p2)
            child.mutate(self.mutation_rate, self.mutation_strength)
            new_pop.append({"genome": child, "fitness": None})

        self.population = new_pop
        self.generation += 1

    def save_checkpoint(self):
        """Save current state to checkpoint file."""
        self.run_dir.mkdir(parents=True, exist_ok=True)

        checkpoint = {
            "generation": self.generation,
            "mode": self.mode,
            "build_type": self.build_type,
            "leek_name": self.leek_name,
            "leek_names": self.leek_names,
            "best_fitness": self.best_fitness,
            "best_val_fitness": self.best_val_fitness,
            "best_genome": self.best_genome.to_dict() if self.best_genome else None,
            "population": [
                {
                    "genome": e["genome"].to_dict(),
                    "fitness": e["fitness"],
                }
                for e in self.population
            ],
            "history": self.history,
            "config": {
                "population_size": self.population_size,
                "fights_per_opponent": self.fights_per_opponent,
                "mutation_rate": self.mutation_rate,
                "mutation_strength": self.mutation_strength,
                "elitism": self.elitism,
                "tournament_size": self.tournament_size,
                "train_opponents": self.train_opponents,
                "val_opponents": self.val_opponents,
            },
        }

        path = self.run_dir / f"checkpoint_gen{self.generation:02d}.json"
        with open(path, "w") as f:
            json.dump(checkpoint, f, indent=2)

        # Also save best weights as a standalone file
        if self.best_genome:
            best_path = self.run_dir / "best_weights.json"
            with open(best_path, "w") as f:
                json.dump(self.best_genome.to_dict(), f, indent=2)

    def load_checkpoint(self, checkpoint_path):
        """Resume from a checkpoint file."""
        path = Path(checkpoint_path)
        if not path.is_absolute():
            path = PROJECT_DIR / path

        with open(path) as f:
            checkpoint = json.load(f)

        self.generation = checkpoint["generation"]
        self.mode = checkpoint.get("mode", "weights")
        self.build_type = checkpoint["build_type"]
        self.leek_name = checkpoint["leek_name"]
        self.leek_names = checkpoint.get("leek_names", [self.leek_name])
        self.best_fitness = checkpoint["best_fitness"]
        self.best_val_fitness = checkpoint.get("best_val_fitness", 0.0)
        self.history = checkpoint.get("history", [])

        # Restore injector based on mode
        if self.mode == "counter":
            self.injector = CounterWeightInjector()
        else:
            self.injector = WeightProfileInjector()

        # Restore run directory
        if path.parent.name.startswith("run_"):
            self.run_dir = path.parent
            self.run_id = path.parent.name.split("_", 2)[-1]

        # Restore config if present
        cfg = checkpoint.get("config", {})
        if cfg:
            self.train_opponents = cfg.get("train_opponents", self.train_opponents)
            self.val_opponents = cfg.get("val_opponents", self.val_opponents)
            self.population_size = cfg.get("population_size", self.population_size)
            self.fights_per_opponent = cfg.get("fights_per_opponent", self.fights_per_opponent)
            self.mutation_rate = cfg.get("mutation_rate", self.mutation_rate)
            self.mutation_strength = cfg.get("mutation_strength", self.mutation_strength)
            self.elitism = cfg.get("elitism", self.elitism)
            self.tournament_size = cfg.get("tournament_size", self.tournament_size)

        # Restore best genome
        if checkpoint.get("best_genome"):
            self.best_genome = self._genome_from_dict(checkpoint["best_genome"])

        # Restore population
        self.population = []
        for entry in checkpoint["population"]:
            genome = self._genome_from_dict(entry["genome"])
            self.population.append({
                "genome": genome,
                "fitness": entry["fitness"],
            })

        print(f"Resumed from generation {self.generation} "
              f"(best={self.best_fitness:.3f})")

    def save_run_config(self):
        """Save run parameters."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        config = {
            "run_id": self.run_id,
            "mode": self.mode,
            "build_type": self.build_type,
            "leek_name": self.leek_name,
            "leek_names": self.leek_names,
            "train_opponents": self.train_opponents,
            "val_opponents": self.val_opponents,
            "population_size": self.population_size,
            "fights_per_opponent": self.fights_per_opponent,
            "max_generations": self.max_generations,
            "mutation_rate": self.mutation_rate,
            "mutation_strength": self.mutation_strength,
            "elitism": self.elitism,
            "tournament_size": self.tournament_size,
            "parallel_workers": self.parallel_workers,
        }
        path = self.run_dir / "run_config.json"
        with open(path, "w") as f:
            json.dump(config, f, indent=2)

    def run(self):
        """Run the genetic algorithm."""
        print(f"{'='*60}")
        mode_label = "COUNTER multipliers" if self.mode == "counter" else f"{self.build_type} weights"
        print(f"LOCAL GENETIC OPTIMIZER - {mode_label}")
        print(f"{'='*60}")
        if self.mode == "counter" and len(self.leek_names) > 1:
            print(f"Leeks: {', '.join(self.leek_names)}")
        else:
            print(f"Leek: {self.leek_name}")
        print(f"Train opponents: {', '.join(self.train_opponents)}")
        if self.val_opponents:
            print(f"Val opponents: {', '.join(self.val_opponents)}")
        print(f"Population: {self.population_size}, "
              f"Generations: {self.max_generations}, "
              f"Fights/opp: {self.fights_per_opponent}")
        print(f"Mutation: rate={self.mutation_rate}, strength={self.mutation_strength}")
        print(f"Elitism: {self.elitism}, Tournament: {self.tournament_size}")
        print(f"Parallel workers: {self.parallel_workers}")
        print(f"Output: {self.run_dir}")
        print(f"{'='*60}")

        # Backup original weights
        self.injector.backup()

        try:
            # Initialize if not resuming
            if not self.population:
                self.save_run_config()
                self.initialize_population()

            start_gen = self.generation
            for gen_num in range(self.max_generations):
                actual_gen = start_gen + gen_num

                # Evaluate
                elapsed = self.evaluate_population()

                # Record history
                fitnesses = [e["fitness"] for e in self.population
                             if e["fitness"] is not None]
                entry = {
                    "generation": self.generation + 1,
                    "best": max(fitnesses) if fitnesses else 0,
                    "avg": sum(fitnesses) / len(fitnesses) if fitnesses else 0,
                    "worst": min(fitnesses) if fitnesses else 0,
                    "elapsed_s": round(elapsed, 1),
                }

                # Validate every 5 generations
                if self.val_opponents and (gen_num + 1) % 5 == 0:
                    val_fitness = self.validate_best()
                    if val_fitness is not None:
                        entry["val_fitness"] = val_fitness

                self.history.append(entry)

                # Save checkpoint
                self.save_checkpoint()

                # Print progress chart
                self._print_history()

                # Evolve (unless final generation)
                if gen_num < self.max_generations - 1:
                    self.evolve()

        finally:
            # Restore original weights
            self.injector.restore()
            self.injector.invalidate_cache()

        print(f"\n{'='*60}")
        print(f"OPTIMIZATION COMPLETE")
        print(f"{'='*60}")
        print(f"Best fitness: {self.best_fitness:.3f}")
        if self.best_genome:
            print(f"Best weights: {self.run_dir / 'best_weights.json'}")
            print(f"\nTo apply: python3 tools/genetic_optimizer_local.py "
                  f"--apply {self.run_dir / 'best_weights.json'}")

    def _print_history(self):
        """Print a simple text-based fitness chart."""
        if not self.history:
            return
        print(f"\nFitness history:")
        max_fit = max(e["best"] for e in self.history)
        bar_width = 40
        for e in self.history:
            gen = e["generation"]
            best = e["best"]
            avg = e["avg"]
            bar_len = int(best / max(max_fit, 0.01) * bar_width) if max_fit > 0 else 0
            avg_pos = int(avg / max(max_fit, 0.01) * bar_width) if max_fit > 0 else 0
            bar = "#" * bar_len
            val_str = ""
            if "val_fitness" in e:
                val_str = f" val={e['val_fitness']:.3f}"
            print(f"  Gen {gen:2d}: {best:.3f} |{'#' * bar_len}{' ' * (bar_width - bar_len)}|"
                  f" avg={avg:.3f}{val_str}")


def apply_weights(weights_path):
    """Apply a best_weights.json file back to weight_profiles.lk or strategic_depth.lk."""
    path = Path(weights_path)
    if not path.is_absolute():
        path = PROJECT_DIR / path

    with open(path) as f:
        data = json.load(f)

    build_type = data["build_type"]
    weights = data["weights"]

    is_counter = (build_type == "COUNTER")

    if is_counter:
        injector = CounterWeightInjector()
        injector.backup()
        current = injector.parse_baseline()
        target_path = STRATEGIC_DEPTH_PATH
    else:
        injector = WeightProfileInjector()
        injector.backup()
        current = injector.parse_baseline(build_type)
        target_path = WEIGHT_PROFILES_PATH

    print(f"Applying {build_type} weights from {path}")
    print(f"Keys: {len(weights)}")

    # Show diff
    print(f"\nChanges:")
    changed = 0
    for key in sorted(weights.keys()):
        old = current.get(key)
        new = weights[key]
        if old != new:
            print(f"  {key}: {old} -> {new}")
            changed += 1
    if changed == 0:
        print("  (no changes)")
        return

    if is_counter:
        injector.inject(weights)
    else:
        injector.inject(build_type, weights)
    injector.invalidate_cache()
    print(f"\nApplied {changed} weight changes to {target_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Local genetic optimizer for V8 weight profiles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Mode selection
    parser.add_argument("--mode", type=str, choices=["weights", "counter"],
                        default="weights",
                        help="Optimization mode: 'weights' (base profiles) or "
                             "'counter' (counter-strategy multipliers)")
    parser.add_argument("--apply", type=str, metavar="WEIGHTS_JSON",
                        help="Apply best weights JSON to weight_profiles.lk or strategic_depth.lk")
    parser.add_argument("--resume", type=str, metavar="CHECKPOINT_JSON",
                        help="Resume from checkpoint file")

    # Build config
    parser.add_argument("--build", type=str,
                        choices=list(BUILD_NAME_TO_GLOBAL.keys()),
                        help="Build type to optimize (weights mode only)")
    parser.add_argument("--leek", type=str,
                        help="Leek name from leek_configs.json (weights mode)")
    parser.add_argument("--leeks", type=str, nargs="+",
                        help="Multiple leek names (counter mode)")

    # Opponents
    parser.add_argument("--train-opponents", type=str, nargs="+",
                        default=["smart_str", "smart_mag", "smart_agi"],
                        help="Training opponents (default: smart_str smart_mag smart_agi)")
    parser.add_argument("--val-opponents", type=str, nargs="*",
                        default=None,
                        help="Validation opponents (default: none)")

    # GA parameters
    parser.add_argument("--generations", type=int, default=30)
    parser.add_argument("--population", type=int, default=20)
    parser.add_argument("--fights-per-opponent", type=int, default=10)
    parser.add_argument("--mutation-rate", type=float, default=0.15)
    parser.add_argument("--mutation-strength", type=float, default=0.2)
    parser.add_argument("--elitism", type=int, default=3)
    parser.add_argument("--tournament-size", type=int, default=4)
    parser.add_argument("--parallel", type=int, default=12)

    args = parser.parse_args()

    # Mode: apply weights
    if args.apply:
        apply_weights(args.apply)
        return 0

    # Mode: resume
    if args.resume:
        optimizer = LocalGeneticOptimizer(
            build_type="MAGIC",  # Will be overridden by checkpoint
            leek_name="placeholder",
            train_opponents=[],
            parallel_workers=args.parallel,
        )
        optimizer.load_checkpoint(args.resume)
        # Allow overriding generations
        optimizer.max_generations = args.generations
        optimizer.parallel_workers = args.parallel
        optimizer.run()
        return 0

    # Mode: counter (new run)
    if args.mode == "counter":
        leek_names = args.leeks or ([args.leek] if args.leek else None)
        if not leek_names:
            parser.error("--leeks (or --leek) required for counter mode")

        optimizer = LocalGeneticOptimizer(
            build_type="COUNTER",
            leek_name=leek_names[0],
            train_opponents=args.train_opponents,
            val_opponents=args.val_opponents or [],
            population_size=args.population,
            fights_per_opponent=args.fights_per_opponent,
            generations=args.generations,
            mutation_rate=args.mutation_rate,
            mutation_strength=args.mutation_strength,
            elitism=args.elitism,
            tournament_size=args.tournament_size,
            parallel_workers=args.parallel,
            mode="counter",
            leek_names=leek_names,
        )
        optimizer.run()
        return 0

    # Mode: weights (new run)
    if not args.build or not args.leek:
        parser.error("--build and --leek are required for a new weights run")

    optimizer = LocalGeneticOptimizer(
        build_type=args.build,
        leek_name=args.leek,
        train_opponents=args.train_opponents,
        val_opponents=args.val_opponents or [],
        population_size=args.population,
        fights_per_opponent=args.fights_per_opponent,
        generations=args.generations,
        mutation_rate=args.mutation_rate,
        mutation_strength=args.mutation_strength,
        elitism=args.elitism,
        tournament_size=args.tournament_size,
        parallel_workers=args.parallel,
    )
    optimizer.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
