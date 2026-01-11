#!/usr/bin/env python3
"""
Create ensemble genome by averaging top N genomes from GA checkpoint

Usage:
  python3 ensemble_genome.py ga_checkpoint_gen9.json --top 5
"""

import json
import argparse
from pathlib import Path


def create_ensemble(checkpoint_file, top_n=5):
    """Average parameters from top N genomes"""

    with open(checkpoint_file, 'r') as f:
        data = json.load(f)

    population = data['population'][:top_n]

    print(f"📊 Creating ensemble from top {top_n} genomes:")
    for i, g in enumerate(population):
        print(f"   {i+1}. Fitness: {g['fitness']:.3f} ({g['wins']}/{g['wins']+g['losses']} wins)")

    # Get all parameter keys from first genome
    param_keys = population[0]['genome'].keys()

    # Average each parameter
    ensemble = {}
    for key in param_keys:
        values = [g['genome'][key] for g in population]
        ensemble[key] = sum(values) / len(values)

    # Calculate ensemble fitness (weighted average)
    total_fights = sum(g['wins'] + g['losses'] for g in population)
    total_wins = sum(g['wins'] for g in population)
    ensemble_fitness = total_wins / total_fights if total_fights > 0 else 0.0

    print(f"\n✅ Ensemble fitness estimate: {ensemble_fitness:.3f} ({total_wins}/{total_fights} wins)")

    return ensemble, ensemble_fitness


def save_ensemble_checkpoint(checkpoint_file, ensemble, fitness, top_n):
    """Save ensemble as a new checkpoint"""

    output_file = checkpoint_file.replace('.json', f'_ensemble_top{top_n}.json')

    output_data = {
        'generation': 'ensemble',
        'population_size': 1,
        'population': [{
            'genome': ensemble,
            'fitness': fitness,
            'wins': 0,
            'losses': 0
        }],
        'best_genome': ensemble,
        'best_fitness': fitness,
        'history': []
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"💾 Ensemble saved: {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(description='Create ensemble genome')
    parser.add_argument('checkpoint', help='Checkpoint JSON file')
    parser.add_argument('--top', type=int, default=5, help='Number of top genomes to average')

    args = parser.parse_args()

    # Create ensemble
    ensemble, fitness = create_ensemble(args.checkpoint, args.top)

    # Save ensemble checkpoint
    output_file = save_ensemble_checkpoint(args.checkpoint, ensemble, fitness, args.top)

    print(f"\n✅ Ensemble created!")
    print(f"   Apply with: python3 tools/apply_best_genome.py {output_file}")

    return 0


if __name__ == '__main__':
    exit(main())
