#!/usr/bin/env python3
"""
Create weight_profiles.lk from multiple GA checkpoints

Usage:
  python3 create_profile_weights.py \
    --weak genome_weak_gen10.json \
    --balanced genome_balanced_gen10.json \
    --strong genome_strong_gen10.json
"""

import json
import argparse
from pathlib import Path


def load_genome(checkpoint_file):
    """Extract best genome from checkpoint"""
    with open(checkpoint_file, 'r') as f:
        data = json.load(f)

    if 'best_genome' in data and data['best_genome']:
        return data['best_genome']
    else:
        return data['population'][0]['genome']


def genome_to_leekscript_dict(genome, indent=8):
    """Convert genome dict to LeekScript map literal"""
    lines = []
    indent_str = ' ' * indent

    # Select most important parameters (20-25 key params)
    important_params = [
        'str_damage_base', 'mag_damage_base', 'agi_damage_base',
        'kill_mult_70', 'kill_mult_50',
        'mag_dot_base', 'other_dot_weight',
        'ehp_urgency_30', 'ehp_urgency_50', 'ehp_urgency_70', 'ehp_wisdom_buff',
        'threat_penalty_mult', 'low_hp_threat_mult',
        'buff_weight', 'otko_cell_bonus',
        'kiting_value_mult', 'distance_score_mult',
        'damage_per_tp_mult', 'damage_per_mp_mult',
        'steroid_value', 'wall_value', 'fortress_value', 'mirror_value'
    ]

    for param in important_params:
        if param in genome:
            value = genome[param]
            # Format value
            if isinstance(value, float):
                value_str = f"{value:.3f}" if abs(value) < 100 else f"{int(value)}"
            else:
                value_str = str(value)

            lines.append(f"{indent_str}'{param}': {value_str},")

    return '\n'.join(lines)


def generate_weight_profiles(weak_genome, balanced_genome, strong_genome, output_file):
    """Generate weight_profiles.lk with all three profiles"""

    template = '''/** Weight Profiles - Build-specific optimized weights from GA **/

class WeightProfiles {{
    // Detect which weight profile to use based on leek stats
    static function getProfile(player) {{
        var primaryStat = max(player._strength, max(player._magic, player._agility))

        // Profile selection based on stat ranges
        if (primaryStat < 500) {{
            return WeightProfiles.WEAK_BUILD
        }} else if (primaryStat >= 500 && primaryStat < 700) {{
            return WeightProfiles.BALANCED_BUILD
        }} else if (primaryStat >= 700) {{
            return WeightProfiles.STRONG_BUILD
        }}

        return WeightProfiles.BALANCED_BUILD  // Fallback
    }}

    // Get specific weight value from profile
    static function getWeight(profile, key, default_value) {{
        if (mapContainsKey(profile, key)) {{
            return profile[key]
        }}
        return default_value
    }}

    // WEAK BUILD PROFILE
    // GA-optimized for cautious play (~400 primary stat, 1800 HP, 8 TP)
    static var WEAK_BUILD = {{
{weak_weights}
    }}

    // BALANCED BUILD PROFILE
    // GA-optimized for standard play (~600 primary stat, 2500 HP, 10 TP)
    static var BALANCED_BUILD = {{
{balanced_weights}
    }}

    // STRONG BUILD PROFILE
    // GA-optimized for aggressive play (~800 primary stat, 3200 HP, 12 TP)
    static var STRONG_BUILD = {{
{strong_weights}
    }}
}}
'''

    content = template.format(
        weak_weights=genome_to_leekscript_dict(weak_genome),
        balanced_weights=genome_to_leekscript_dict(balanced_genome),
        strong_weights=genome_to_leekscript_dict(strong_genome)
    )

    with open(output_file, 'w') as f:
        f.write(content)

    print(f"✅ Generated {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Create weight_profiles.lk from GA checkpoints')
    parser.add_argument('--weak', required=True, help='Weak build checkpoint')
    parser.add_argument('--balanced', required=True, help='Balanced build checkpoint')
    parser.add_argument('--strong', required=True, help='Strong build checkpoint')
    parser.add_argument('--output', default='V8_modules/weight_profiles.lk', help='Output file')

    args = parser.parse_args()

    print("Loading genomes...")
    weak = load_genome(args.weak)
    balanced = load_genome(args.balanced)
    strong = load_genome(args.strong)

    print(f"  Weak: {args.weak}")
    print(f"  Balanced: {args.balanced}")
    print(f"  Strong: {args.strong}")

    generate_weight_profiles(weak, balanced, strong, args.output)

    print("\n✅ Weight profiles created!")
    print(f"   Next: Modify scenario_scorer.lk to use WeightProfiles.getProfile()")


if __name__ == '__main__':
    main()
