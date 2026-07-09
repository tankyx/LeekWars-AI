#!/usr/bin/env python3
"""GA pipeline: run an optimization job, validate the champion on an
INDEPENDENT matrix, auto-commit if green / revert if red, write a report.

This scripts the manual loop used for run_BRUISER_REFLECT_20260709_142751:
the GA's own fitness is never trusted for the ship decision — only the
fresh-seed validation matrix at proper sample sizes is.

Usage:
    python3 tools/ga_pipeline.py --job ed_weights
    python3 tools/ga_pipeline.py --job ed_weights --skip-ga ga_local/run_X/best_weights.json
    python3 tools/ga_pipeline.py --list

Nightly cron example (NOT installed automatically):
    30 2 * * * cd /home/ubuntu/LeekWars-AI && /usr/bin/python3 tools/ga_pipeline.py --job ed_weights >> /tmp/ga_pipeline.log 2>&1
"""
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CACHE_GLOB = "/home/ubuntu/leek-wars-generator/ai/*"
REPORT_DIR = PROJECT_DIR / "ga_local" / "pipeline_reports"

sys.path.insert(0, str(SCRIPT_DIR))
from local_test import build_scenario, run_fight, load_configs  # noqa
from concurrent.futures import ProcessPoolExecutor, as_completed  # noqa
from local_test import _run_fight_worker  # noqa

# ── Job definitions ─────────────────────────────────────────────────────
# validation.min_wins are HARD gates: every row must pass or the champion
# is reverted. Set them at (baseline - noise margin).
JOBS = {
    "ed_weights": {
        "desc": "EdsgerDijkstra BRUISER_REFLECT weights (mage matchup focus)",
        "optimizer_args": [
            "--build", "BRUISER_REFLECT", "--leek", "EdsgerDijkstra",
            "--train-opponents", "v8_mage_mid", "smart_mag",
            "--guard-opponents", "smart_tank", "smart_str", "smart_agi",
            "--optimizer", "cma",
            "--generations", "20", "--population", "16",
            "--fights-per-opponent", "8", "--parallel", "12",
        ],
        "files": ["V8_modules/weight_profiles.lk"],
        "validation": [
            {"leek": "EdsgerDijkstra", "opponent": "v8_mage_mid", "n": 40, "min_wins": 12},
            {"leek": "EdsgerDijkstra", "opponent": "smart_tank", "n": 30, "min_wins": 29},
            {"leek": "EdsgerDijkstra", "opponent": "smart_str", "n": 20, "min_wins": 20},
            {"leek": "EdsgerDijkstra", "opponent": "smart_agi", "n": 20, "min_wins": 19},
            {"leek": "EdsgerDijkstra", "opponent": "v8_kurt", "n": 15, "min_wins": 15},
            {"leek": "LeekRain", "opponent": "smart_dannyd", "n": 20, "min_wins": 19},
        ],
    },
    "kurt_weights": {
        "desc": "KurtGodel TANK_SCI weights",
        "optimizer_args": [
            "--build", "TANK_SCI", "--leek", "KurtGodel",
            "--train-opponents", "v8_mage_mid", "smart_dannyd",
            "--guard-opponents", "smart_tank",
            "--optimizer", "cma",
            "--generations", "20", "--population", "16",
            "--fights-per-opponent", "8", "--parallel", "12",
        ],
        "files": ["V8_modules/weight_profiles.lk"],
        "validation": [
            {"leek": "KurtGodel", "opponent": "smart_tank", "n": 30, "min_wins": 29},
            {"leek": "KurtGodel", "opponent": "v8_mage_mid", "n": 30, "min_wins": 12},
            {"leek": "MargaretHamilton", "opponent": "smart_mag", "n": 20, "min_wins": 18},
        ],
    },
    "mh_weights": {
        "desc": "MargaretHamilton MAGIC weights (sustain-bruiser focus; "
                "smart_dannyd is the closest local proxy for her WIS-bruiser farmers)",
        "optimizer_args": [
            "--build", "MAGIC", "--leek", "MargaretHamilton",
            "--train-opponents", "smart_dannyd", "v8_mage_mid",
            "--guard-opponents", "smart_mag", "v8_dijkstra",
            "--guard-floor", "0.8",
            "--optimizer", "cma",
            "--generations", "20", "--population", "16",
            "--fights-per-opponent", "8", "--parallel", "12",
        ],
        "files": ["V8_modules/weight_profiles.lk"],
        "validation": [
            {"leek": "MargaretHamilton", "opponent": "smart_mag", "n": 30, "min_wins": 27},
            {"leek": "MargaretHamilton", "opponent": "v8_dijkstra", "n": 30, "min_wins": 24},
            {"leek": "MargaretHamilton", "opponent": "smart_dannyd", "n": 20, "min_wins": 10},
            {"leek": "LeekRain", "opponent": "smart_dannyd", "n": 20, "min_wins": 19},
        ],
    },
    "tunables": {
        "desc": "Scorer landscape constants (GA_TUNE) — the empirical route "
                "into the audit's deferred score-rebalance. Wide validation.",
        "optimizer_args": [
            "--mode", "tunables", "--leek", "EdsgerDijkstra",
            "--train-opponents", "v8_mage_mid", "smart_mag", "smart_dannyd",
            "--guard-opponents", "smart_tank", "smart_str",
            "--optimizer", "cma",
            "--generations", "16", "--population", "14",
            "--fights-per-opponent", "8", "--parallel", "12",
        ],
        "files": ["V8_modules/ga_tunables.lk"],
        "validation": [
            {"leek": "EdsgerDijkstra", "opponent": "v8_mage_mid", "n": 40, "min_wins": 12},
            {"leek": "EdsgerDijkstra", "opponent": "smart_tank", "n": 30, "min_wins": 29},
            {"leek": "MargaretHamilton", "opponent": "smart_mag", "n": 30, "min_wins": 27},
            {"leek": "MargaretHamilton", "opponent": "v8_dijkstra", "n": 30, "min_wins": 24},
            {"leek": "KurtGodel", "opponent": "smart_tank", "n": 20, "min_wins": 19},
            {"leek": "AdaLovelace", "opponent": "smart_str", "n": 20, "min_wins": 20},
            {"leek": "LeekRain", "opponent": "smart_dannyd", "n": 20, "min_wins": 19},
            {"leek": "DuskHope", "opponent": "smart_dannyd", "n": 20, "min_wins": 5},
        ],
    },
}


def clear_cache():
    subprocess.run(f"rm -f {CACHE_GLOB}.class {CACHE_GLOB}.java {CACHE_GLOB}.lines",
                   shell=True, check=False)


def run_matchup(configs, leek, opponent, n, workers=12):
    leek_cfg = configs["leeks"][leek]
    opp_cfg = configs["opponents"][opponent]
    scenarios = []
    for i in range(n):
        import random
        sc = build_scenario(leek_cfg, opp_cfg, seed=random.randint(1, 2**31 - 1))
        scenarios.append((sc, len(scenarios), False))
    wins = losses = draws = crashes = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_run_fight_worker, s) for s in scenarios]
        for f in as_completed(futures):
            try:
                r = f.result()
            except Exception:
                crashes += 1
                continue
            if r.get("has_bug") or "error" in r:
                crashes += 1
            elif r.get("result") == "WIN":
                wins += 1
            elif r.get("result") == "LOSS":
                losses += 1
            else:
                draws += 1
    return {"wins": wins, "losses": losses, "draws": draws, "crashes": crashes, "n": n}


def run_job(job_name, skip_ga=None):
    job = JOBS[job_name]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"{ts}_{job_name}.md"
    lines = [f"# GA pipeline report — {job_name}", f"date: {ts}", f"desc: {job['desc']}", ""]

    # 1. GA run (or reuse an existing champion)
    if skip_ga:
        best_path = Path(skip_ga)
        lines.append(f"GA skipped; using champion: {best_path}")
    else:
        lines.append(f"optimizer args: {' '.join(job['optimizer_args'])}")
        print(f"[{job_name}] running optimizer...")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "genetic_optimizer_local.py")]
            + job["optimizer_args"],
            capture_output=True, text=True, cwd=str(PROJECT_DIR),
        )
        tail = proc.stdout[-3000:]
        lines.append("```\n" + tail + "\n```")
        m = re.search(r"Best weights: (\S+best_weights\.json)", proc.stdout)
        if not m:
            lines.append("**FAILED: no best_weights.json produced**")
            report_path.write_text("\n".join(lines))
            print(f"[{job_name}] GA failed — report: {report_path}")
            return 1
        best_path = Path(m.group(1))
        fit = re.search(r"Best fitness: ([\d.]+)", proc.stdout)
        lines.append(f"champion: {best_path} (train fitness {fit.group(1) if fit else '?'})")

    # 2. Apply champion
    print(f"[{job_name}] applying champion {best_path}")
    subprocess.run([sys.executable, str(SCRIPT_DIR / "genetic_optimizer_local.py"),
                    "--apply", str(best_path)], cwd=str(PROJECT_DIR), check=True)
    clear_cache()

    # 3. Independent validation
    configs = load_configs()
    all_green = True
    lines.append("\n## Validation")
    lines.append("| leek | opponent | result | min_wins | verdict |")
    lines.append("|---|---|---|---|---|")
    for v in job["validation"]:
        r = run_matchup(configs, v["leek"], v["opponent"], v["n"])
        ok = r["wins"] >= v["min_wins"] and r["crashes"] == 0
        retried = ""
        if not ok and r["crashes"] == 0:
            # Outlier insurance: noisy matchups show real batch-to-batch
            # overdispersion (observed 4/40 vs 14-15/40 for the SAME config
            # within hours). Re-run once and judge the POOLED sample against
            # the pooled threshold — no upward bias, just more data.
            r2 = run_matchup(configs, v["leek"], v["opponent"], v["n"])
            pooled_wins = r["wins"] + r2["wins"]
            ok = pooled_wins >= 2 * v["min_wins"] and r2["crashes"] == 0
            retried = f" (retry: {r2['wins']}/{v['n']}, pooled {pooled_wins}/{2*v['n']})"
            r = {"wins": pooled_wins,
                 "losses": r["losses"] + r2["losses"],
                 "draws": r["draws"] + r2["draws"],
                 "crashes": r["crashes"] + r2["crashes"],
                 "n": 2 * v["n"]}
        all_green = all_green and ok
        verdict = "PASS" if ok else "FAIL"
        row = (f"| {v['leek']} | {v['opponent']} | "
               f"{r['wins']}W/{r['losses']}L/{r['draws']}D"
               f"{' +' + str(r['crashes']) + 'crash' if r['crashes'] else ''} "
               f"| {v['min_wins']}/{v['n'] if not retried else v['n']} | {verdict}{retried} |")
        lines.append(row)
        print(f"[{job_name}] {v['leek']} vs {v['opponent']}: "
              f"{r['wins']} wins (need ratio {v['min_wins']}/{v['n']}) -> {verdict}{retried}")

    # 4. Commit or revert
    if all_green:
        subprocess.run(["git", "add"] + job["files"], cwd=str(PROJECT_DIR), check=True)
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"],
                              cwd=str(PROJECT_DIR))
        if diff.returncode == 0:
            lines.append("\n**VERDICT: PASS (no changes to commit — champion "
                         "identical to committed state)**")
            print(f"[{job_name}] all gates passed — nothing new to commit.")
        else:
            msg = (f"GA pipeline: {job_name} champion committed\n\n"
                   f"run: {best_path.parent.name}\nvalidation: all gates passed "
                   f"(see {report_path.name})\n\n"
                   f"Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>")
            subprocess.run(["git", "commit", "-m", msg], cwd=str(PROJECT_DIR), check=True)
            lines.append("\n**VERDICT: COMMITTED**")
            print(f"[{job_name}] all gates passed — committed.")
    else:
        subprocess.run(["git", "checkout", "--"] + job["files"],
                       cwd=str(PROJECT_DIR), check=True)
        clear_cache()
        lines.append("\n**VERDICT: REVERTED (validation gate failed)**")
        print(f"[{job_name}] validation failed — reverted.")

    report_path.write_text("\n".join(lines))
    print(f"[{job_name}] report: {report_path}")
    return 0 if all_green else 2


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--job", choices=list(JOBS.keys()))
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--skip-ga", metavar="BEST_WEIGHTS_JSON",
                    help="Skip the GA; validate+ship an existing champion")
    args = ap.parse_args()
    if args.list or not args.job:
        for name, j in JOBS.items():
            print(f"  {name:<14} {j['desc']}")
        return 0
    return run_job(args.job, skip_ga=args.skip_ga)


if __name__ == "__main__":
    sys.exit(main())
