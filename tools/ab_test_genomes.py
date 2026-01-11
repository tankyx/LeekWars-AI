#!/usr/bin/env python3
"""
A/B test multiple genome configurations

Usage:
  python3 ab_test_genomes.py --fights 50 --configs baseline ensemble_top5 best
"""

import argparse
import subprocess
import json
import time
from pathlib import Path


def run_ab_test(configs, fights_per_config=50, opponent='domingo'):
    """Test multiple genome configurations"""

    results = []
    scorer_path = Path('V8_modules/scenario_scorer.lk')
    backup_path = scorer_path.with_suffix('.lk.ab_backup')

    # Backup baseline
    import shutil
    shutil.copy2(scorer_path, backup_path)
    print(f"💾 Baseline backed up to {backup_path}\n")

    for config_name in configs:
        print(f"\n{'='*60}")
        print(f"Testing: {config_name}")
        print(f"{'='*60}")

        # Apply configuration
        if config_name == 'baseline':
            # Restore baseline
            shutil.copy2(backup_path, scorer_path)
            print("✅ Using baseline weights")
        else:
            # Find checkpoint file
            if config_name == 'ensemble_top5':
                checkpoint = 'ga_checkpoint_gen9_ensemble_top5.json'
            elif config_name == 'best':
                checkpoint = 'ga_checkpoint_gen9.json'
            else:
                # Assume it's a checkpoint filename
                checkpoint = config_name

            if not Path(checkpoint).exists():
                print(f"❌ Checkpoint not found: {checkpoint}")
                continue

            # Apply genome
            apply_script = Path('tools/apply_best_genome.py')
            result = subprocess.run(
                ['python3', str(apply_script), checkpoint, '--no-backup'],
                capture_output=True, text=True
            )

            if result.returncode != 0:
                print(f"❌ Failed to apply genome: {result.stderr}")
                continue

            print(result.stdout)

        # Upload V8
        print(f"\n📤 Uploading V8 with {config_name} weights...")
        upload_script = Path('tools/upload_v8.py')
        result = subprocess.run(['python3', str(upload_script)],
                              capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Upload failed: {result.stderr}")
            continue

        # Extract script ID
        import re
        match = re.search(r'Script ID: (\d+)', result.stdout)
        script_id = int(match.group(1)) if match else 447626
        print(f"✅ Uploaded as script {script_id}")

        # Run test fights
        print(f"\n🎮 Running {fights_per_config} fights vs {opponent}...")
        test_script = Path('tools/lw_test_script.py')
        result = subprocess.run(
            ['python3', str(test_script), str(fights_per_config), str(script_id), opponent],
            capture_output=True, text=True
        )

        # Parse win rate
        match = re.search(r'Win Rate: ([\d.]+)%', result.stdout)
        if match:
            win_rate = float(match.group(1)) / 100

            # Parse wins/losses
            wins_match = re.search(r'Wins: (\d+)', result.stdout)
            losses_match = re.search(r'Losses: (\d+)', result.stdout)

            wins = int(wins_match.group(1)) if wins_match else 0
            losses = int(losses_match.group(1)) if losses_match else 0

            results.append({
                'config': config_name,
                'win_rate': win_rate,
                'wins': wins,
                'losses': losses,
                'total': wins + losses
            })

            print(f"✅ {config_name}: {win_rate:.1%} ({wins}/{wins+losses} wins)")
        else:
            print(f"⚠️ Could not parse results")

        time.sleep(2.0)  # Cooldown between tests

    # Restore baseline
    shutil.copy2(backup_path, scorer_path)
    print(f"\n♻️ Baseline weights restored")

    return results


def print_results_table(results):
    """Print formatted comparison table"""

    print(f"\n{'='*60}")
    print("A/B TEST RESULTS")
    print(f"{'='*60}\n")

    # Sort by win rate
    results.sort(key=lambda x: x['win_rate'], reverse=True)

    print(f"{'Config':<25} {'Win Rate':<12} {'Record':<15} {'Improvement'}")
    print(f"{'-'*60}")

    baseline_wr = next((r['win_rate'] for r in results if r['config'] == 'baseline'), 0.80)

    for r in results:
        improvement = (r['win_rate'] - baseline_wr) * 100
        improvement_str = f"{improvement:+.1f}pp" if r['config'] != 'baseline' else "-"

        print(f"{r['config']:<25} {r['win_rate']:.1%} ({r['win_rate']*100:.1f}%)  "
              f"{r['wins']}-{r['losses']:<10} {improvement_str}")

    # Statistical significance check
    print(f"\n{'='*60}")
    print("STATISTICAL NOTES")
    print(f"{'='*60}")

    for r in results:
        n = r['total']
        p = r['win_rate']
        stderr = (p * (1 - p) / n) ** 0.5
        ci_95 = 1.96 * stderr

        print(f"{r['config']}: {p:.1%} ± {ci_95:.1%} (95% CI)")

    # Winner
    if len(results) > 1:
        winner = results[0]
        print(f"\n🏆 Winner: {winner['config']} ({winner['win_rate']:.1%})")


def main():
    parser = argparse.ArgumentParser(description='A/B test genome configurations')
    parser.add_argument('--fights', type=int, default=50, help='Fights per config')
    parser.add_argument('--opponent', default='domingo', help='Test opponent')
    parser.add_argument('--configs', nargs='+',
                       default=['baseline', 'ensemble_top5', 'best'],
                       help='Configurations to test')

    args = parser.parse_args()

    print(f"🧪 A/B Testing Genome Configurations")
    print(f"   Fights per config: {args.fights}")
    print(f"   Opponent: {args.opponent}")
    print(f"   Configs: {', '.join(args.configs)}")

    results = run_ab_test(args.configs, args.fights, args.opponent)

    if results:
        print_results_table(results)

        # Save results
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        results_file = f"ab_test_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved: {results_file}")

    return 0


if __name__ == '__main__':
    exit(main())
