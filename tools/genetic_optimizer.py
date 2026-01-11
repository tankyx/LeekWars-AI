#!/usr/bin/env python3
"""
Genetic Algorithm Optimizer for LeekWars V8 Scenario Scoring Weights

Evolves scenario_scorer.lk weight parameters to maximize win rate.

Usage:
  python3 genetic_optimizer.py --generations 20 --population 30 --fights-per-genome 50
  python3 genetic_optimizer.py --resume checkpoint_gen15.json
"""

import json
import random
import time
import copy
from datetime import datetime
from pathlib import Path
import argparse
import subprocess
import re

# Import existing testing infrastructure
from lw_test_script import LeekWarsScriptTester, BOTS
from config_loader import load_credentials


class GenomeConfig:
    """Defines tunable parameters for V8 scenario scorer"""

    def __init__(self):
        # Category A: Weight Calculation Formulas (18 params)
        self.str_damage_base = 1.5
        self.str_damage_scale = 1000.0
        self.mag_damage_base = 0.8
        self.mag_damage_scale = 2000.0
        self.agi_damage_base = 1.3
        self.agi_damage_scale = 1500.0

        self.kill_mult_70 = 5.0
        self.kill_mult_50 = 2.5

        self.mag_dot_base = 2.0
        self.mag_dot_scale = 1000.0
        self.other_dot_weight = 0.3

        self.ehp_base = 0.5
        self.ehp_res_scale = 500.0
        self.ehp_wis_scale = 1000.0
        self.ehp_urgency_30 = 3.0
        self.ehp_urgency_50 = 2.0
        self.ehp_urgency_70 = 1.5
        self.ehp_wisdom_buff = 1.5

        self.agi_pos_base = 0.8
        self.agi_pos_scale = 1000.0
        self.mag_pos_base = 0.5
        self.mag_pos_scale = 2000.0
        self.str_pos_base = 0.2

        self.eff_long_fight = 0.3
        self.eff_med_fight = 0.15
        self.eff_short_fight = 0.05

        # Category B: Fixed Bonuses (8 params)
        self.buff_weight = 5.0
        self.otko_cell_bonus = 5000
        self.threat_penalty_mult = 0.5
        self.low_hp_threat_mult = 2.0
        self.kiting_value_mult = 10
        self.distance_score_mult = 10
        self.damage_per_tp_mult = 10
        self.damage_per_mp_mult = 5

        # Category C: Buff Values (12 key buffs, simplified)
        self.steroid_value = 200
        self.doping_value = 100
        self.warm_up_value = 150
        self.adrenaline_value = 100
        self.wall_value = 150
        self.fortress_value = 150
        self.liberation_value = 120
        self.remission_value = 100
        self.mirror_value = 180
        self.thorn_value = 180
        self.bramble_value = 100
        self.bramble_combat_mult = 2.5

    def to_dict(self):
        """Convert genome to dictionary"""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    def from_dict(self, data):
        """Load genome from dictionary"""
        for k, v in data.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def mutate(self, mutation_rate=0.15, mutation_strength=0.2):
        """Mutate genome parameters

        Args:
            mutation_rate: Probability of mutating each parameter (0-1)
            mutation_strength: Maximum % change per mutation (0-1)
        """
        # Define parameter bounds (min, max) to prevent catastrophic drift
        bounds = {
            'str_damage_base': (1.0, 3.0),
            'mag_damage_base': (0.5, 1.5),
            'agi_damage_base': (0.8, 2.0),  # Prevent AGI collapse!
            'kill_mult_70': (3.0, 7.0),
            'kill_mult_50': (1.5, 4.0),
            'mag_dot_base': (1.5, 3.0),
            'other_dot_weight': (0.1, 0.5),
            'ehp_urgency_30': (2.0, 4.0),
            'ehp_urgency_50': (1.5, 3.0),
            'ehp_urgency_70': (1.0, 2.0),
            'threat_penalty_mult': (0.2, 1.0),
            'buff_weight': (3.0, 10.0),
            'otko_cell_bonus': (3000, 7000),
        }

        for key in self.__dict__.keys():
            if key.startswith('_'):
                continue

            if random.random() < mutation_rate:
                current_value = getattr(self, key)

                # Apply Gaussian mutation
                delta = random.gauss(0, mutation_strength * current_value)
                new_value = current_value + delta

                # Clamp to reasonable bounds
                if key in bounds:
                    min_val, max_val = bounds[key]
                    new_value = max(min_val, min(max_val, new_value))
                else:
                    # General bounds
                    new_value = max(0.0, new_value)

                    # Special handling for certain params
                    if 'scale' in key:
                        new_value = max(100.0, new_value)  # Scales shouldn't be too small

                setattr(self, key, new_value)

    @staticmethod
    def crossover(parent1, parent2):
        """Create offspring via uniform crossover"""
        child = GenomeConfig()

        for key in child.__dict__.keys():
            if key.startswith('_'):
                continue

            # 50% chance to inherit from each parent
            if random.random() < 0.5:
                setattr(child, key, getattr(parent1, key))
            else:
                setattr(child, key, getattr(parent2, key))

        return child


class GeneticOptimizer:
    """Genetic algorithm for evolving V8 scoring weights"""

    def __init__(self,
                 population_size=30,
                 fights_per_genome=50,
                 mutation_rate=0.15,
                 mutation_strength=0.2,
                 elitism_count=5,
                 tournament_size=5,
                 opponents=['domingo', 'betalpha', 'rex', 'hachess'],  # 4 diverse bots
                 test_leeks=None,  # List of leek names to test with (e.g., ['WeakLeek', 'StrongLeek'])
                 account='main',
                 output_dir='ga_runs'):  # Output directory for checkpoints

        self.population_size = population_size
        self.fights_per_genome = fights_per_genome
        self.mutation_rate = mutation_rate
        self.mutation_strength = mutation_strength
        self.elitism_count = elitism_count  # Top N genomes preserved unchanged
        self.tournament_size = tournament_size
        self.opponents = opponents  # Test against multiple opponents
        self.test_leeks = test_leeks if test_leeks else [None]  # Default: use account's first leek
        self.account = account

        # Split opponents into training and validation sets
        if len(opponents) >= 4:
            mid = len(opponents) // 2
            self.train_opponents = opponents[:mid]  # First half for training
            self.val_opponents = opponents[mid:]    # Second half for validation
        else:
            self.train_opponents = opponents
            self.val_opponents = []

        self.population = []
        self.generation = 0
        self.best_genome = None
        self.best_fitness = 0.0
        self.best_val_fitness = 0.0  # Track validation performance
        self.history = []

        # Output directory structure
        self.run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = Path(__file__).parent.parent / output_dir
        self.run_dir = self.output_dir / f"run_{self.run_id}"
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # V8 script path
        self.v8_path = Path(__file__).parent.parent / "V8_modules"
        self.scorer_path = self.v8_path / "scenario_scorer.lk"
        self.scorer_backup = self.scorer_path.with_suffix('.lk.backup')

    def initialize_population(self):
        """Create initial population with random variations"""
        print(f"\n🧬 Initializing population ({self.population_size} genomes)...")

        # Genome 0: Current production weights (baseline)
        baseline = GenomeConfig()
        self.population.append({
            'genome': baseline,
            'fitness': None,
            'wins': 0,
            'losses': 0,
            'draws': 0
        })

        # Genomes 1+: Random mutations of baseline
        for i in range(1, self.population_size):
            mutant = GenomeConfig()
            mutant.mutate(mutation_rate=0.3, mutation_strength=0.3)  # Larger initial variation
            self.population.append({
                'genome': mutant,
                'fitness': None,
                'wins': 0,
                'losses': 0,
                'draws': 0
            })

        print(f"✅ Population initialized")

    def backup_scorer(self):
        """Backup current scenario_scorer.lk"""
        if not self.scorer_backup.exists():
            print(f"💾 Backing up {self.scorer_path.name}...")
            import shutil
            shutil.copy2(self.scorer_path, self.scorer_backup)

    def restore_scorer(self):
        """Restore original scenario_scorer.lk"""
        if self.scorer_backup.exists():
            print(f"♻️ Restoring original {self.scorer_path.name}...")
            import shutil
            shutil.copy2(self.scorer_backup, self.scorer_path)

    def inject_genome(self, genome):
        """Modify scenario_scorer.lk with genome weights"""
        with open(self.scorer_path, 'r') as f:
            content = f.read()

        # Inject weights via regex replacement
        replacements = {
            r'return 1\.5 \+ \(str / 1000\.0\)': f'return {genome.str_damage_base} + (str / {genome.str_damage_scale})',
            r'return 0\.8 \+ \(mag / 2000\.0\)': f'return {genome.mag_damage_base} + (mag / {genome.mag_damage_scale})',
            r'return 1\.3 \+ \(agi / 1500\.0\)': f'return {genome.agi_damage_base} + (agi / {genome.agi_damage_scale})',

            r'damageWeight \*= 5\.0': f'damageWeight *= {genome.kill_mult_70}',
            r'damageWeight \*= 2\.5': f'damageWeight *= {genome.kill_mult_50}',

            r'return 2\.0 \+ \(mag / 1000\.0\)': f'return {genome.mag_dot_base} + (mag / {genome.mag_dot_scale})',
            r'return 0\.3': f'return {genome.other_dot_weight}',  # DoT weight for non-MAG

            r'var baseWeight = 0\.5 \+ \(resistance / 500\.0\) \+ \(wisdom / 1000\.0\)':
                f'var baseWeight = {genome.ehp_base} + (resistance / {genome.ehp_res_scale}) + (wisdom / {genome.ehp_wis_scale})',

            r'if \(hpRatio < 0\.3\) urgencyMultiplier = 3\.0':
                f'if (hpRatio < 0.3) urgencyMultiplier = {genome.ehp_urgency_30}',
            r'else if \(hpRatio < 0\.5\) urgencyMultiplier = 2\.0':
                f'else if (hpRatio < 0.5) urgencyMultiplier = {genome.ehp_urgency_50}',
            r'else if \(hpRatio < 0\.7\) urgencyMultiplier = 1\.5':
                f'else if (hpRatio < 0.7) urgencyMultiplier = {genome.ehp_urgency_70}',

            r'return 0\.8 \+ \(agi / 1000\.0\)': f'return {genome.agi_pos_base} + (agi / {genome.agi_pos_scale})',
            r'return 0\.5 \+ \(mag / 2000\.0\)': f'return {genome.mag_pos_base} + (mag / {genome.mag_pos_scale})',
            r'return 0\.2': f'return {genome.str_pos_base}',

            r'return 5\.0  // Fixed weight': f'return {genome.buff_weight}  // GA optimized',
            r'otkoBonus = 5000': f'otkoBonus = {genome.otko_cell_bonus}',

            r'if \(buffChip == CHIP_STEROID\) value \+= 200': f'if (buffChip == CHIP_STEROID) value += {genome.steroid_value}',
            r'if \(buffChip == CHIP_WALL \|\| buffChip == CHIP_FORTRESS\) value \+= 150':
                f'if (buffChip == CHIP_WALL || buffChip == CHIP_FORTRESS) value += {genome.wall_value}',
        }

        for pattern, replacement in replacements.items():
            content = re.sub(pattern, replacement, content)

        with open(self.scorer_path, 'w') as f:
            f.write(content)

    def upload_v8(self):
        """Upload modified V8 to LeekWars"""
        upload_script = Path(__file__).parent / "upload_v8.py"
        result = subprocess.run(['python3', str(upload_script)],
                              capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Upload failed: {result.stderr}")
            return None

        # Extract script ID from output
        match = re.search(r'Script ID: (\d+)', result.stdout)
        if match:
            return int(match.group(1))

        # Fallback: Use hardcoded V8 production ID
        return 447626

    def evaluate_genome(self, genome_idx, genome):
        """Evaluate genome fitness via test fights"""
        print(f"\n🧪 Evaluating genome {genome_idx + 1}/{self.population_size}...")

        # Inject genome weights
        self.inject_genome(genome['genome'])

        # Upload to LeekWars
        script_id = self.upload_v8()
        if not script_id:
            print(f"❌ Failed to upload genome {genome_idx}")
            return 0.0

        time.sleep(0.5)  # Wait for upload to propagate

        # Test with multiple leek profiles if specified
        all_leek_fitness = []

        for leek_name in self.test_leeks:
            if leek_name:
                print(f"  🦗 Testing with leek: {leek_name}")

            # Run test fights against TRAINING opponents only
            leek_total_wins = 0
            leek_total_fights = 0

            for opponent_name in self.train_opponents:
                bot = BOTS[opponent_name]
                fights_per_opponent = self.fights_per_genome // (len(self.train_opponents) * len(self.test_leeks))

                print(f"  🎯 Testing vs {opponent_name} ({fights_per_opponent} fights)...")

                # Create tester instance
                tester = LeekWarsScriptTester()
                email, password = load_credentials(account=self.account)

                if not tester.login(email, password):
                    print(f"  ❌ Login failed")
                    continue

                # Setup scenario with specific leek
                scenario_id = tester.setup_test_scenario(script_id, bot, preferred_leek_name=leek_name)
                if not scenario_id:
                    print(f"  ❌ Scenario setup failed")
                    continue

                # Run fights
                wins = 0
                for fight_num in range(fights_per_opponent):
                    if fight_num > 0:
                        time.sleep(0.3)  # Rate limiting (minimum safe delay)

                    fight_id = tester.run_test(scenario_id, script_id)
                    if fight_id:
                        result = tester.get_fight_result(fight_id)
                        if result and result['result'] == 'WIN':
                            wins += 1

                    # Progress indicator
                    if fight_num % 10 == 0 and fight_num > 0:
                        print(f"    [{fight_num}/{fights_per_opponent}]", end="", flush=True)
                    else:
                        print(".", end="", flush=True)

                print()  # Newline

                leek_total_wins += wins
                leek_total_fights += fights_per_opponent

                print(f"  ✅ {opponent_name}: {wins}/{fights_per_opponent} wins ({wins/fights_per_opponent*100:.1f}%)")

                time.sleep(1.0)  # Cooldown between opponents

            # Calculate fitness for this leek
            leek_fitness = leek_total_wins / leek_total_fights if leek_total_fights > 0 else 0.0
            all_leek_fitness.append(leek_fitness)

            if leek_name:
                print(f"  📊 {leek_name} fitness: {leek_fitness:.3f} ({leek_total_wins}/{leek_total_fights} wins)")

        # Average fitness across all test leeks
        fitness = sum(all_leek_fitness) / len(all_leek_fitness) if all_leek_fitness else 0.0
        total_wins = sum([int(f * self.fights_per_genome / len(self.test_leeks)) for f in all_leek_fitness])
        total_fights = self.fights_per_genome

        genome['fitness'] = fitness
        genome['wins'] = total_wins
        genome['losses'] = total_fights - total_wins

        if len(self.test_leeks) > 1:
            print(f"  📊 Genome {genome_idx + 1} AVERAGE fitness: {fitness:.3f} (across {len(self.test_leeks)} leeks)")
        else:
            print(f"  📊 Genome {genome_idx + 1} fitness: {fitness:.3f} ({total_wins}/{total_fights} wins)")

        return fitness

    def validate_genome(self, genome):
        """Validate best genome on held-out opponents"""
        if not self.val_opponents:
            return None

        print(f"\n🔍 Validating best genome on held-out opponents...")

        # Inject and upload
        self.inject_genome(genome['genome'])
        script_id = self.upload_v8()
        if not script_id:
            return None

        time.sleep(0.5)

        total_wins = 0
        total_fights = 0

        for opponent_name in self.val_opponents:
            bot = BOTS[opponent_name]
            fights_per_opponent = 20  # Fixed validation size

            print(f"  🧪 Validation vs {opponent_name} ({fights_per_opponent} fights)...")

            tester = LeekWarsScriptTester()
            email, password = load_credentials(account=self.account)

            if not tester.login(email, password):
                continue

            scenario_id = tester.setup_test_scenario(script_id, bot)
            if not scenario_id:
                continue

            wins = 0
            for fight_num in range(fights_per_opponent):
                if fight_num > 0:
                    time.sleep(0.3)

                fight_id = tester.run_test(scenario_id, script_id)
                if fight_id:
                    result = tester.get_fight_result(fight_id)
                    if result and result['result'] == 'WIN':
                        wins += 1

                if fight_num % 5 == 0 and fight_num > 0:
                    print(f"    [{fight_num}]", end="", flush=True)
                else:
                    print(".", end="", flush=True)

            print()

            total_wins += wins
            total_fights += fights_per_opponent

            print(f"  ✅ {opponent_name}: {wins}/{fights_per_opponent} wins ({wins/fights_per_opponent*100:.1f}%)")

            time.sleep(1.0)

        val_fitness = total_wins / total_fights if total_fights > 0 else 0.0
        print(f"  📊 Validation fitness: {val_fitness:.3f} ({total_wins}/{total_fights} wins)")

        return val_fitness

    def evaluate_population(self):
        """Evaluate all genomes in population"""
        print(f"\n{'='*60}")
        print(f"GENERATION {self.generation + 1} - EVALUATION")
        print(f"{'='*60}")
        print(f"Training opponents: {', '.join(self.train_opponents)}")
        if self.val_opponents:
            print(f"Validation opponents: {', '.join(self.val_opponents)}")

        for i, genome in enumerate(self.population):
            if genome['fitness'] is None:  # Skip already-evaluated genomes (elites)
                self.evaluate_genome(i, genome)

        # Sort by fitness (descending)
        self.population.sort(key=lambda x: x['fitness'] if x['fitness'] is not None else 0.0, reverse=True)

        # Update best genome
        if self.population[0]['fitness'] > self.best_fitness:
            self.best_fitness = self.population[0]['fitness']
            self.best_genome = copy.deepcopy(self.population[0])
            print(f"\n🎉 NEW BEST GENOME! Training fitness: {self.best_fitness:.3f}")

            # Validate on held-out opponents
            if self.val_opponents:
                val_fitness = self.validate_genome(self.best_genome)
                if val_fitness is not None:
                    self.best_val_fitness = val_fitness
                    print(f"🧪 Validation fitness: {self.best_val_fitness:.3f}")

                    # Overfitting check
                    gap = self.best_fitness - self.best_val_fitness
                    if gap > 0.15:  # >15% gap = overfitting
                        print(f"⚠️ OVERFITTING DETECTED! Gap: {gap:.1%}")

    def tournament_selection(self):
        """Select parent via tournament selection"""
        tournament = random.sample(self.population, self.tournament_size)
        tournament.sort(key=lambda x: x['fitness'], reverse=True)
        return tournament[0]['genome']

    def evolve(self):
        """Create next generation via selection, crossover, mutation"""
        print(f"\n🧬 Evolving generation {self.generation + 1} → {self.generation + 2}...")

        new_population = []

        # Elitism: Preserve top N genomes
        for i in range(self.elitism_count):
            new_population.append(copy.deepcopy(self.population[i]))
            print(f"  Elite {i + 1}: Fitness {self.population[i]['fitness']:.3f}")

        # Fill rest via crossover + mutation
        while len(new_population) < self.population_size:
            parent1 = self.tournament_selection()
            parent2 = self.tournament_selection()

            child_genome = GenomeConfig.crossover(parent1, parent2)
            child_genome.mutate(self.mutation_rate, self.mutation_strength)

            new_population.append({
                'genome': child_genome,
                'fitness': None,
                'wins': 0,
                'losses': 0,
                'draws': 0
            })

        self.population = new_population
        self.generation += 1

    def save_checkpoint(self):
        """Save generation checkpoint"""
        checkpoint = {
            'generation': self.generation,
            'population_size': self.population_size,
            'run_id': self.run_id,
            'population': [
                {
                    'genome': g['genome'].to_dict(),
                    'fitness': g['fitness'],
                    'wins': g['wins'],
                    'losses': g['losses']
                }
                for g in self.population
            ],
            'best_genome': self.best_genome['genome'].to_dict() if self.best_genome else None,
            'best_fitness': self.best_fitness,
            'history': self.history
        }

        filename = self.run_dir / f"ga_checkpoint_gen{self.generation}.json"
        with open(filename, 'w') as f:
            json.dump(checkpoint, f, indent=2)

        print(f"\n💾 Checkpoint saved: {filename}")

    def load_checkpoint(self, filename):
        """Resume from checkpoint"""
        print(f"\n📂 Loading checkpoint: {filename}...")

        # Convert to Path and handle both absolute and relative paths
        checkpoint_path = Path(filename)
        if not checkpoint_path.is_absolute():
            checkpoint_path = Path(__file__).parent.parent / checkpoint_path

        with open(checkpoint_path, 'r') as f:
            checkpoint = json.load(f)

        # Update run_dir to match the checkpoint's directory
        if checkpoint_path.parent.name.startswith('run_'):
            self.run_dir = checkpoint_path.parent
            self.run_id = checkpoint_path.parent.name.replace('run_', '')
            print(f"📁 Resuming in directory: {self.run_dir}")

        self.generation = checkpoint['generation']
        self.population_size = checkpoint['population_size']
        self.best_fitness = checkpoint['best_fitness']
        self.history = checkpoint['history']

        # Restore population
        self.population = []
        for g_data in checkpoint['population']:
            genome = GenomeConfig()
            genome.from_dict(g_data['genome'])
            self.population.append({
                'genome': genome,
                'fitness': g_data['fitness'],
                'wins': g_data['wins'],
                'losses': g_data['losses'],
                'draws': 0
            })

        # Restore best genome
        if checkpoint['best_genome']:
            best_g = GenomeConfig()
            best_g.from_dict(checkpoint['best_genome'])
            self.best_genome = {
                'genome': best_g,
                'fitness': self.best_fitness,
                'wins': 0, 'losses': 0, 'draws': 0
            }

        print(f"✅ Resumed from generation {self.generation}")

    def save_run_config(self):
        """Save run configuration metadata"""
        config = {
            'run_id': self.run_id,
            'started_at': self.run_id,
            'population_size': self.population_size,
            'fights_per_genome': self.fights_per_genome,
            'mutation_rate': self.mutation_rate,
            'mutation_strength': self.mutation_strength,
            'elitism_count': self.elitism_count,
            'tournament_size': self.tournament_size,
            'opponents': self.opponents,
            'train_opponents': self.train_opponents,
            'val_opponents': self.val_opponents,
            'test_leeks': self.test_leeks,
            'account': self.account
        }

        config_file = self.run_dir / "run_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"📄 Run config saved: {config_file}")

    def run(self, generations):
        """Run genetic algorithm for N generations"""
        print(f"\n{'='*60}")
        print("GENETIC ALGORITHM - V8 WEIGHT OPTIMIZATION")
        print(f"{'='*60}")
        print(f"Run ID: {self.run_id}")
        print(f"Output directory: {self.run_dir}")
        print(f"Population: {self.population_size}")
        print(f"Generations: {generations}")
        print(f"Fights/genome: {self.fights_per_genome}")
        print(f"Opponents: {', '.join(self.opponents)}")
        print(f"Mutation rate: {self.mutation_rate}")
        print(f"{'='*60}\n")

        # Backup original scorer
        self.backup_scorer()

        try:
            # Initialize if not resuming
            if not self.population:
                self.save_run_config()
                self.initialize_population()

            for gen in range(generations):
                # Evaluate
                self.evaluate_population()

                # Record history
                avg_fitness = sum(g['fitness'] for g in self.population) / len(self.population)
                history_entry = {
                    'generation': self.generation,
                    'best_fitness': self.population[0]['fitness'],
                    'avg_fitness': avg_fitness,
                    'worst_fitness': self.population[-1]['fitness']
                }
                if self.val_opponents:
                    history_entry['best_val_fitness'] = self.best_val_fitness
                    history_entry['overfitting_gap'] = self.best_fitness - self.best_val_fitness

                self.history.append(history_entry)

                print(f"\n📊 Generation {self.generation + 1} Summary:")
                print(f"  Training Best:    {self.population[0]['fitness']:.3f}")
                print(f"  Training Average: {avg_fitness:.3f}")
                print(f"  Training Worst:   {self.population[-1]['fitness']:.3f}")
                if self.val_opponents and self.best_val_fitness > 0:
                    print(f"  Validation Best:  {self.best_val_fitness:.3f}")
                    gap = self.best_fitness - self.best_val_fitness
                    status = "✅" if gap < 0.10 else "⚠️" if gap < 0.15 else "❌"
                    print(f"  Overfitting Gap:  {gap:.1%} {status}")

                # Save checkpoint
                self.save_checkpoint()

                # Evolve (unless final generation)
                if gen < generations - 1:
                    self.evolve()

        finally:
            # Restore original scorer
            self.restore_scorer()

        print(f"\n{'='*60}")
        print("OPTIMIZATION COMPLETE")
        print(f"{'='*60}")
        print(f"Best fitness: {self.best_fitness:.3f}")
        print(f"Best genome saved in checkpoint file")


def main():
    parser = argparse.ArgumentParser(description='Genetic optimizer for V8 weights')
    parser.add_argument('--generations', type=int, default=20, help='Number of generations')
    parser.add_argument('--population', type=int, default=30, help='Population size')
    parser.add_argument('--fights-per-genome', type=int, default=50, help='Test fights per genome')
    parser.add_argument('--mutation-rate', type=float, default=0.15, help='Mutation probability')
    parser.add_argument('--mutation-strength', type=float, default=0.2, help='Mutation magnitude')
    parser.add_argument('--elitism', type=int, default=5, help='Elite genomes preserved')
    parser.add_argument('--account', type=str, default='main', help='LeekWars account')
    parser.add_argument('--opponents', type=str, nargs='+', default=['domingo', 'betalpha', 'rex', 'hachess'],
                       help='Test opponents')
    parser.add_argument('--test-leeks', type=str, nargs='+', default=None,
                       help='Test with multiple leek profiles (e.g., --test-leeks WeakLeek StrongLeek)')
    parser.add_argument('--output-dir', type=str, default='ga_runs',
                       help='Output directory for checkpoints (default: ga_runs)')
    parser.add_argument('--resume', type=str, help='Resume from checkpoint file')

    args = parser.parse_args()

    optimizer = GeneticOptimizer(
        population_size=args.population,
        fights_per_genome=args.fights_per_genome,
        mutation_rate=args.mutation_rate,
        mutation_strength=args.mutation_strength,
        elitism_count=args.elitism,
        opponents=args.opponents,
        test_leeks=args.test_leeks,
        account=args.account,
        output_dir=args.output_dir
    )

    if args.resume:
        optimizer.load_checkpoint(args.resume)

    optimizer.run(args.generations)


if __name__ == '__main__':
    main()
