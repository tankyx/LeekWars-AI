#!/usr/bin/env python3
"""
Apply best genome from genetic algorithm to scenario_scorer.lk

Usage:
  python3 apply_best_genome.py ga_checkpoint_gen9.json
  python3 apply_best_genome.py ga_checkpoint_gen9.json --validate --fights 30
"""

import json
import re
import argparse
import subprocess
from pathlib import Path


def load_best_genome(checkpoint_file):
    """Extract best genome from checkpoint"""
    with open(checkpoint_file, 'r') as f:
        data = json.load(f)

    # Best genome is stored separately, or is first in population
    if 'best_genome' in data and data['best_genome']:
        genome = data['best_genome']
        fitness = data.get('best_fitness', 0.0)
    else:
        # First genome in population (already sorted by fitness)
        genome = data['population'][0]['genome']
        fitness = data['population'][0]['fitness']

    print(f"📊 Loaded best genome:")
    print(f"   Fitness: {fitness:.3f} ({fitness*100:.1f}% win rate)")
    print(f"   Generation: {data['generation']}")

    return genome, fitness


def apply_genome_to_scorer(genome, scorer_path, backup=True):
    """Apply genome weights to scenario_scorer.lk"""

    # Backup original
    if backup:
        backup_path = scorer_path.with_suffix('.lk.ga_backup')
        if not backup_path.exists():
            import shutil
            shutil.copy2(scorer_path, backup_path)
            print(f"💾 Backup created: {backup_path}")

    # Read current file
    with open(scorer_path, 'r') as f:
        content = f.read()

    # Apply replacements (same logic as genetic_optimizer.py)
    replacements = [
        # Damage weights
        (r'return 1\.5 \+ \(str / 1000\.0\)',
         f'return {genome["str_damage_base"]:.3f} + (str / {genome["str_damage_scale"]:.1f})'),

        (r'return 0\.8 \+ \(mag / 2000\.0\)',
         f'return {genome["mag_damage_base"]:.3f} + (mag / {genome["mag_damage_scale"]:.1f})'),

        (r'return 1\.3 \+ \(agi / 1500\.0\)',
         f'return {genome["agi_damage_base"]:.3f} + (agi / {genome["agi_damage_scale"]:.1f})'),

        # Kill multipliers
        (r'damageWeight \*= 5\.0  // 5x damage weight',
         f'damageWeight *= {genome["kill_mult_70"]:.3f}  // GA optimized (70%+ kill)'),

        (r'damageWeight \*= 2\.5  // 2\.5x for near-kill',
         f'damageWeight *= {genome["kill_mult_50"]:.3f}  // GA optimized (50-70% kill)'),

        # DoT weights
        (r'return 2\.0 \+ \(mag / 1000\.0\)',
         f'return {genome["mag_dot_base"]:.3f} + (mag / {genome["mag_dot_scale"]:.1f})'),

        (r'return 0\.3  // Other builds: low weight',
         f'return {genome["other_dot_weight"]:.3f}  // GA optimized'),

        # eHP weights
        (r'var baseWeight = 0\.5 \+ \(resistance / 500\.0\) \+ \(wisdom / 1000\.0\)',
         f'var baseWeight = {genome["ehp_base"]:.3f} + (resistance / {genome["ehp_res_scale"]:.1f}) + (wisdom / {genome["ehp_wis_scale"]:.1f})'),

        (r'if \(hpRatio < 0\.3\) urgencyMultiplier = 3\.0',
         f'if (hpRatio < 0.3) urgencyMultiplier = {genome["ehp_urgency_30"]:.3f}'),

        (r'else if \(hpRatio < 0\.5\) urgencyMultiplier = 2\.0',
         f'else if (hpRatio < 0.5) urgencyMultiplier = {genome["ehp_urgency_50"]:.3f}'),

        (r'else if \(hpRatio < 0\.7\) urgencyMultiplier = 1\.5',
         f'else if (hpRatio < 0.7) urgencyMultiplier = {genome["ehp_urgency_70"]:.3f}'),

        (r'baseWeight \*= 1\.5  // 50% bonus',
         f'baseWeight *= {genome["ehp_wisdom_buff"]:.3f}  // GA optimized'),

        # Position weights
        (r'return 0\.8 \+ \(agi / 1000\.0\)  // AGI builds',
         f'return {genome["agi_pos_base"]:.3f} + (agi / {genome["agi_pos_scale"]:.1f})  // GA optimized'),

        (r'return 0\.5 \+ \(mag / 2000\.0\)  // MAG builds',
         f'return {genome["mag_pos_base"]:.3f} + (mag / {genome["mag_pos_scale"]:.1f})  // GA optimized'),

        (r'return 0\.2  // STR builds',
         f'return {genome["str_pos_base"]:.3f}  // GA optimized'),

        # Efficiency weights
        (r'if \(fightLengthEstimate > 3\) return 0\.3',
         f'if (fightLengthEstimate > 3) return {genome["eff_long_fight"]:.3f}'),

        (r'else if \(fightLengthEstimate > 1\.5\) return 0\.15',
         f'else if (fightLengthEstimate > 1.5) return {genome["eff_med_fight"]:.3f}'),

        (r'return 0\.05  // Short fight',
         f'return {genome["eff_short_fight"]:.3f}  // GA optimized'),

        # Fixed bonuses
        (r'return 5\.0  // Fixed weight for buff',
         f'return {genome["buff_weight"]:.3f}  // GA optimized'),

        (r'otkoBonus = 5000',
         f'otkoBonus = {int(genome["otko_cell_bonus"])}'),

        (r'threatPenalty = -threatAtPos \* 0\.5',
         f'threatPenalty = -threatAtPos * {genome["threat_penalty_mult"]:.3f}'),

        (r'threatPenalty \*= 2\.0  // Double penalty',
         f'threatPenalty *= {genome["low_hp_threat_mult"]:.3f}  // GA optimized'),

        (r'kitingValue = distToTarget \* 10',
         f'kitingValue = distToTarget * {genome["kiting_value_mult"]:.1f}'),

        (r'kitingValue = max\(0, \(10 - distToTarget\)\) \* 10',
         f'kitingValue = max(0, (10 - distToTarget)) * {genome["distance_score_mult"]:.1f}'),

        (r'tpEfficiency = damagePerTP \* 10',
         f'tpEfficiency = damagePerTP * {genome["damage_per_tp_mult"]:.1f}'),

        (r'mpEfficiency = damagePerMP \* 5',
         f'mpEfficiency = damagePerMP * {genome["damage_per_mp_mult"]:.3f}'),

        # Buff values
        (r'if \(buffChip == CHIP_STEROID\) value \+= 200',
         f'if (buffChip == CHIP_STEROID) value += {int(genome["steroid_value"])}'),

        (r'if \(buffChip == CHIP_DOPING\) value \+= 100',
         f'if (buffChip == CHIP_DOPING) value += {int(genome["doping_value"])}'),

        (r'if \(buffChip == CHIP_WARM_UP\) value \+= 150',
         f'if (buffChip == CHIP_WARM_UP) value += {int(genome["warm_up_value"])}'),

        (r'if \(buffChip == CHIP_ADRENALINE\) value \+= 100',
         f'if (buffChip == CHIP_ADRENALINE) value += {int(genome["adrenaline_value"])}'),

        (r'if \(buffChip == CHIP_WALL \|\| buffChip == CHIP_FORTRESS\) value \+= 150',
         f'if (buffChip == CHIP_WALL || buffChip == CHIP_FORTRESS) value += {int(genome["wall_value"])}'),

        (r'if \(buffChip == CHIP_LIBERATION\) value \+= 120',
         f'if (buffChip == CHIP_LIBERATION) value += {int(genome["liberation_value"])}'),

        (r'if \(buffChip == CHIP_REMISSION\) value \+= 100',
         f'if (buffChip == CHIP_REMISSION) value += {int(genome["remission_value"])}'),

        (r'if \(buffChip == CHIP_MIRROR \|\| buffChip == CHIP_THORN\)',
         f'if (buffChip == CHIP_MIRROR || buffChip == CHIP_THORN)'),

        (r'if \(this\._player\._agility > this\._player\._strength\) value \+= 180',
         f'if (this._player._agility > this._player._strength) value += {int(genome["mirror_value"])}'),

        (r'brambleValue = 100  // Base value',
         f'brambleValue = {int(genome["bramble_value"])}  // GA optimized'),

        (r'brambleValue \*= 2\.5  // 2\.5x value',
         f'brambleValue *= {genome["bramble_combat_mult"]:.3f}  // GA optimized'),
    ]

    changes_made = 0
    for pattern, replacement in replacements:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            changes_made += 1
            content = new_content

    # Write modified file
    with open(scorer_path, 'w') as f:
        f.write(content)

    print(f"✅ Applied {changes_made} parameter changes to {scorer_path.name}")

    return changes_made


def validate_genome(fights=30, opponent='domingo'):
    """Run validation tests with new weights"""
    print(f"\n🧪 Running validation ({fights} fights vs {opponent})...")

    # Upload V8
    upload_script = Path(__file__).parent / "upload_v8.py"
    result = subprocess.run(['python3', str(upload_script)],
                          capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Upload failed: {result.stderr}")
        return None

    # Extract script ID
    match = re.search(r'Script ID: (\d+)', result.stdout)
    script_id = int(match.group(1)) if match else 447626

    # Run tests
    test_script = Path(__file__).parent / "lw_test_script.py"
    result = subprocess.run(
        ['python3', str(test_script), str(fights), str(script_id), opponent],
        capture_output=True, text=True
    )

    # Parse win rate
    match = re.search(r'Win Rate: ([\d.]+)%', result.stdout)
    if match:
        win_rate = float(match.group(1)) / 100
        print(f"✅ Validation complete: {win_rate:.1%} win rate")
        return win_rate
    else:
        print(f"⚠️ Could not parse win rate from test output")
        print(result.stdout[-500:])  # Show last 500 chars
        return None


def main():
    parser = argparse.ArgumentParser(description='Apply best GA genome to scorer')
    parser.add_argument('checkpoint', help='Checkpoint JSON file')
    parser.add_argument('--validate', action='store_true', help='Run validation tests')
    parser.add_argument('--fights', type=int, default=30, help='Validation fights')
    parser.add_argument('--opponent', default='domingo', help='Validation opponent')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup')

    args = parser.parse_args()

    # Load best genome
    genome, fitness = load_best_genome(args.checkpoint)

    # Apply to scorer
    scorer_path = Path(__file__).parent.parent / "V8_modules" / "scenario_scorer.lk"
    changes = apply_genome_to_scorer(genome, scorer_path, backup=not args.no_backup)

    if changes == 0:
        print("⚠️ No changes made - check regex patterns")
        return 1

    # Validate if requested
    if args.validate:
        win_rate = validate_genome(args.fights, args.opponent)

        if win_rate:
            improvement = (win_rate - 0.80) * 100  # vs 80% baseline
            print(f"\n📊 Performance vs baseline:")
            print(f"   GA training: {fitness:.1%}")
            print(f"   Validation:  {win_rate:.1%}")
            print(f"   Improvement: {improvement:+.1f}pp")

    print(f"\n✅ Genome applied successfully!")
    print(f"   Upload to LeekWars: python3 tools/upload_v8.py")

    return 0


if __name__ == '__main__':
    exit(main())
