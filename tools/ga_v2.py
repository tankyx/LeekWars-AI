#!/usr/bin/env python3
"""GA v2 — self-tuning loop for V9's evaluation-function weights (Phase M3).

Evolves the 16 EW_* globals consumed by V9_modules/eval.lk. Injection is
whole-file: each candidate's weight set is written to
V9_modules/ga_weights.lk (which eval.lk includes permanently), the generator
compile cache is wiped, and a fixed 12-fight corpus is run locally:

    EdsgerDijkstra   vs smart_str              x2
    MargaretHamilton vs smart_mag              x2
    AdaLovelace      vs smart_str              x2
    KurtGodel        vs smart_mag              x2
    <each leek>      vs its toughest live_*    x1   (4 fights)
    <each leek>      vs itself on baseline weights (mirror) x1   (4 fights)

"Toughest live_*" = lowest win rate in tools/fight_history_<leek_id>.db among
opponents present in leek_configs.json (ties: most fights, then lowest leek
id; falls back to a power heuristic when no DB history matches).

Why the mirror fights: the smart/live half of the corpus SATURATES — V9 at
default weights sweeps it 12/12 (measured 2026-08-13), so it can only
discriminate downward (regressions). The mirror half gives the upward
gradient: the candidate runs V9_modules/main.lk (candidate weights) against a
frozen copy of the same tree (ga_local/v2_baseline_modules, symlinked as
V9_ga_baseline in the generator dir) pinned to the pre-run active weights.
The candidate alternates sides across the four mirror slots (team 1 for two
leeks, team 2 for the other two; identical assignment for every candidate) so
the first-player edge cancels in aggregate. Total corpus: 16 fights —
matching the M3 plan's "/16". Disable with --no-mirror for the exact
12-fight plan corpus.

Fitness = points/total + 0.1 * wins/total + 0.05 * win_speed, with
points = wins + 0.5*draws (errors and AI crashes count as losses) and
win_speed = mean((64 - turns)/64) over wins. The 0.05 shaping term is the
plan's "+0.05 per win-margin" tiebreaker: capped below one fight's value,
it ranks equal W/L records by how fast they win (without it this corpus
quantizes all near-baseline candidates to identical W/L and selection has
no gradient). All candidates and all generations share one fixed seed block
derived from --seed: comparisons are paired, and elites keep their fitness
across generations without re-evaluation.

Candidates are evaluated SEQUENTIALLY (parallel GA instances OOM'd this box
before). Fights within one candidate run in parallel, after a 2-fight serial
warm-up that compiles both AI trees (V9 main + V8 opponent AI) so parallel
workers never race on compile-cache writes.

Usage:
    python3 tools/ga_v2.py                         # proof run: pop 6 x 4 gens
    python3 tools/ga_v2.py --generations 12 --population 10
    python3 tools/ga_v2.py --resume ga_local/v2_run_<ts>/checkpoint.json
    python3 tools/ga_v2.py --no-promote            # skip promotion gate
"""

import argparse
import copy
import glob as globmod
import json
import math
import os
import random
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
GENERATOR_DIR = Path("/home/ubuntu/leek-wars-generator")
CACHE_DIR = GENERATOR_DIR / "ai"
GA_WEIGHTS_PATH = PROJECT_DIR / "V9_modules" / "ga_weights.lk"
V9_AI_PATH = "V9_modules/main.lk"  # relative to GENERATOR_DIR (symlink)
# Frozen incumbent tree for mirror fights: a copy of V9_modules pinned to the
# pre-run active weights, symlinked into the generator dir.
BASELINE_TREE_LOCAL = PROJECT_DIR / "ga_local" / "v2_baseline_modules"
BASELINE_TREE_LINK = GENERATOR_DIR / "V9_ga_baseline"
BASELINE_AI_PATH = "V9_ga_baseline/main.lk"
MIRROR_TAG = "mirror"

sys.path.insert(0, str(SCRIPT_DIR))
from local_test import build_scenario, run_fight, _run_fight_worker, load_configs  # noqa: E402

# ── The 16 evolvable eval weights ──
EW_ORDER = [
    "EW_DIRECT", "EW_DOT", "EW_NOVA", "EW_SELF_HEAL", "EW_SHIELDS",
    "EW_DENIAL", "EW_TAKEN", "EW_ENEMY_HEAL", "EW_KILL", "EW_DEATH",
    "EW_DROP_PENALTY", "EW_APPROACH", "EW_BULB_TAX",
    "EW_RR_TAKEN", "EW_RR_HEAL", "EW_RR_DEATH",
]

EW_DEFAULTS = {
    "EW_DIRECT": 2.0, "EW_DOT": 1.2, "EW_NOVA": 1.5, "EW_SELF_HEAL": 1.4,
    "EW_SHIELDS": 0.6, "EW_DENIAL": 30.0, "EW_TAKEN": 1.8,
    "EW_ENEMY_HEAL": 1.2, "EW_KILL": 5000.0, "EW_DEATH": 9000.0,
    "EW_DROP_PENALTY": 400.0, "EW_APPROACH": 60.0, "EW_BULB_TAX": 0.35,
    "EW_RR_TAKEN": 1.2, "EW_RR_HEAL": 0.8, "EW_RR_DEATH": 6000.0,
}

# (lo, hi, scale): "log" = multiplicative mutation for the big spike weights,
# "lin" = additive gaussian scaled to the range for the rest.
EW_BOUNDS = {
    "EW_DIRECT":       (0.2,    6.0,    "lin"),
    "EW_DOT":          (0.0,    4.0,    "lin"),
    "EW_NOVA":         (0.0,    5.0,    "lin"),
    "EW_SELF_HEAL":    (0.0,    5.0,    "lin"),
    "EW_SHIELDS":      (0.0,    3.0,    "lin"),
    "EW_DENIAL":       (0.0,    120.0,  "lin"),
    "EW_TAKEN":        (0.0,    6.0,    "lin"),
    "EW_ENEMY_HEAL":   (0.0,    5.0,    "lin"),
    "EW_KILL":         (500.0,  20000.0, "log"),
    "EW_DEATH":        (1000.0, 40000.0, "log"),
    "EW_DROP_PENALTY": (50.0,   3000.0,  "log"),
    "EW_APPROACH":     (0.0,    300.0,  "lin"),
    "EW_BULB_TAX":     (0.0,    1.0,    "lin"),
    "EW_RR_TAKEN":     (0.0,    6.0,    "lin"),
    "EW_RR_HEAL":      (0.0,    5.0,    "lin"),
    "EW_RR_DEATH":     (1000.0, 40000.0, "log"),
}

# Fixed smart-matchup half of the corpus (leek, opponent, n_fights).
CORPUS_SMART = [
    ("EdsgerDijkstra", "smart_str", 2),
    ("MargaretHamilton", "smart_mag", 2),
    ("AdaLovelace", "smart_str", 2),
    ("KurtGodel", "smart_mag", 2),
]

# Uphill half: the smart opponents with stats scaled up — the only corpus
# segment where our leeks face real death risk, i.e. where the rollout veto
# fires and the EW weights actually change outcomes. Without these the
# fitness landscape is flat (every candidate sweeps the easy fights).
CORPUS_UPHILL_SCALE = 1.6
CORPUS_UPHILL = [
    ("EdsgerDijkstra", "smart_str", 2),
    ("MargaretHamilton", "smart_mag", 2),
    ("AdaLovelace", "smart_str", 2),
    ("KurtGodel", "smart_mag", 2),
]
UPHILL_STAT_KEYS = ("life", "strength", "magic", "agility", "wisdom",
                    "resistance", "science", "frequency", "tp", "mp")

# Leek name -> leek id, for fight-history DB lookup (toughest live_* pick).
CORPUS_LEEK_IDS = {
    "AdaLovelace": 20443,
    "EdsgerDijkstra": 129288,
    "KurtGodel": 129295,
    "MargaretHamilton": 129296,
}


# ── Weight file I/O ──

def fmt_num(v):
    """Format a weight as a clean LeekScript number literal (no sci notation)."""
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:.4f}".rstrip("0").rstrip(".")


def write_ga_weights(weights, path=GA_WEIGHTS_PATH, provenance=None):
    """Write the full ga_weights.lk for a candidate/promoted weight set."""
    lines = [
        "// GA-managed evaluation weights for V9 (Phase M3) — included by eval.lk.",
        "// Written by tools/ga_v2.py; do not hand-edit the values.",
    ]
    if provenance:
        for line in provenance.split("\n"):
            lines.append(f"// {line}")
    lines.append("")
    for k in EW_ORDER:
        comment = ""
        if k == "EW_BULB_TAX":
            comment = "    // fraction of damage that counts when it's on a bulb"
        lines.append(f"global {k} = {fmt_num(weights[k])}{comment}")
    path.write_text("\n".join(lines) + "\n")


def read_active_weights(path=GA_WEIGHTS_PATH):
    """Parse the currently active weight set from ga_weights.lk."""
    text = path.read_text()
    out = {}
    for k in EW_ORDER:
        m = re.search(rf"global\s+{k}\s*=\s*(-?[\d.]+)", text)
        if not m:
            raise ValueError(f"{k} not found in {path}")
        out[k] = float(m.group(1))
    return out


def ensure_ga_weights():
    """ga_weights.lk must always exist (eval.lk includes it permanently).
    Regenerate the default set if it is missing."""
    if not GA_WEIGHTS_PATH.exists():
        write_ga_weights(EW_DEFAULTS)
        print(f"ga_weights.lk was missing — regenerated with defaults.")


def wipe_cache():
    """Clear compiled .class/.java/.sig/.lines so the generator recompiles."""
    n = 0
    for pat in ("*.class", "*.java", "*.sig", "*.lines"):
        for f in globmod.glob(str(CACHE_DIR / pat)):
            os.unlink(f)
            n += 1
    return n


def setup_baseline_tree(baseline_weights):
    """(Re)create the frozen incumbent tree for mirror fights: a copy of
    V9_modules pinned to the pre-run active weights, symlinked into the
    generator dir as V9_ga_baseline. Rebuilt at every GA start (fresh or
    resume) — note a resume after V9 code edits re-baselines the code too."""
    if BASELINE_TREE_LOCAL.exists():
        shutil.rmtree(BASELINE_TREE_LOCAL)
    BASELINE_TREE_LOCAL.mkdir(parents=True)
    src = PROJECT_DIR / "V9_modules"
    for f in src.glob("*.lk"):
        shutil.copy2(f, BASELINE_TREE_LOCAL)
    shutil.copytree(src / "strategy", BASELINE_TREE_LOCAL / "strategy")
    write_ga_weights(baseline_weights, BASELINE_TREE_LOCAL / "ga_weights.lk",
                     provenance="Frozen GA v2 incumbent (pre-run active set). "
                                "Mirror opponents run this tree.")
    if BASELINE_TREE_LINK.is_symlink():
        BASELINE_TREE_LINK.unlink()
    elif BASELINE_TREE_LINK.exists():
        raise RuntimeError(f"{BASELINE_TREE_LINK} exists and is not a symlink")
    BASELINE_TREE_LINK.symlink_to(BASELINE_TREE_LOCAL)


# ── Genome operators ──

def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def mutate(weights, rate, strength):
    w = dict(weights)
    for k, (lo, hi, scale) in EW_BOUNDS.items():
        if random.random() >= rate:
            continue
        if scale == "log":
            w[k] = round(clamp(w[k] * math.exp(random.gauss(0, strength)), lo, hi), 2)
        else:
            w[k] = round(clamp(w[k] + random.gauss(0, strength * (hi - lo)), lo, hi), 4)
    return w


def crossover(w1, w2):
    """Uniform per-key crossover."""
    return {k: (w1[k] if random.random() < 0.5 else w2[k]) for k in EW_ORDER}


def weights_equal(w1, w2, tol=1e-9):
    return all(abs(w1[k] - w2[k]) <= tol for k in EW_ORDER)


# ── Corpus construction ──

def toughest_live_opponents(configs):
    """Pick each corpus leek's toughest live_* opponent from fight history:
    lowest recorded win rate (ties: most fights, then lowest opponent id).
    Fallback: power heuristic (life + 2*primary offensive stat)."""
    live = {}
    for k in configs["opponents"]:
        if k.startswith("live_"):
            live[int(k.split("_", 1)[1])] = k

    def power(opp_key):
        c = configs["opponents"][opp_key]
        primary = max(c.get("strength", 0), c.get("magic", 0), c.get("agility", 0))
        return c.get("life", 0) + 2 * primary

    picks = {}
    for leek_name in CORPUS_LEEK_IDS:
        choice = None
        db = SCRIPT_DIR / f"fight_history_{CORPUS_LEEK_IDS[leek_name]}.db"
        if db.exists() and live:
            con = sqlite3.connect(str(db))
            rows = con.execute(
                "SELECT opponent_id, win_rate, total_fights FROM opponent_stats"
            ).fetchall()
            con.close()
            cands = [(wr, -tot, oid) for oid, wr, tot in rows if oid in live]
            if cands:
                cands.sort()
                choice = live[cands[0][2]]
        if choice is None and live:
            choice = max(live.values(), key=power)
        picks[leek_name] = choice
    return picks


def build_corpus(configs, use_mirror=True, use_uphill=True):
    """Return the corpus as a list of (leek, opponent, n_fights).
    opponent == MIRROR_TAG means: same leek config running the frozen
    baseline tree (BASELINE_AI_PATH). Uphill opponents are stat-scaled
    clones of the smart configs, injected into configs['opponents']."""
    corpus = list(CORPUS_SMART)
    picks = toughest_live_opponents(configs)
    for leek_name in CORPUS_LEEK_IDS:
        opp = picks.get(leek_name)
        if opp:
            corpus.append((leek_name, opp, 1))
    if use_mirror:
        for leek_name in CORPUS_LEEK_IDS:
            corpus.append((leek_name, MIRROR_TAG, 1))
    if use_uphill:
        opponents = configs.get("opponents", {})
        for leek_name, opp_key, n in CORPUS_UPHILL:
            up_key = f"uphill_{opp_key}"
            if up_key not in opponents and opp_key in opponents:
                clone = dict(opponents[opp_key])
                clone["name"] = up_key
                for k in UPHILL_STAT_KEYS:
                    if isinstance(clone.get(k), (int, float)):
                        clone[k] = int(round(clone[k] * CORPUS_UPHILL_SCALE))
                opponents[up_key] = clone
            corpus.append((leek_name, up_key, n))
    return corpus


def expand_slots(corpus):
    """Flatten to per-fight (leek, opponent) slots. Smart fights come first,
    then live_* fights (warm-up relies on this ordering)."""
    slots = []
    for leek, opp, n in corpus:
        for _ in range(n):
            slots.append((leek, opp))
    return slots


# ── The GA ──

class EvalWeightGA:
    def __init__(self, population_size=6, generations=4, master_seed=20260813,
                 mutation_rate=0.3, mutation_strength=0.25, elitism=1,
                 tournament_size=3, parallel=8, use_mirror=True):
        self.population_size = population_size
        self.max_generations = generations
        self.master_seed = master_seed
        self.mutation_rate = mutation_rate
        self.mutation_strength = mutation_strength
        self.elitism = elitism
        self.tournament_size = tournament_size
        self.parallel = parallel
        self.use_mirror = use_mirror

        self.configs = load_configs()
        self.corpus = build_corpus(self.configs, use_mirror=use_mirror)
        self.slots = expand_slots(self.corpus)
        self.seeds = [random.Random(master_seed * 1000 + i).randint(1, 2**31 - 1)
                      for i in range(len(self.slots))]

        self.population = []  # [{"weights": {...}, "fitness": float|None, "detail": dict|None}]
        self.generation = 0   # completed generations
        self.baseline = None  # pre-run active weights
        self.best = None      # {"weights", "fitness", "generation"}
        self.history = []

        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = PROJECT_DIR / "ga_local" / f"v2_run_{self.run_id}"

    # ── evaluation ──

    def evaluate_candidate(self, idx, entry):
        """Inject weights, wipe cache, run the fixed-seed corpus. Sequential
        across candidates; parallel across fights within one candidate."""
        t0 = time.time()
        write_ga_weights(entry["weights"])
        wipe_cache()

        scenarios = []
        inverted = []  # per-slot: True when the candidate plays team 2
        # Alternate the candidate's side across mirror slots so the first-
        # player/position edge cancels in aggregate (same assignment for
        # every candidate — comparisons stay paired).
        mirror_t2 = {name: i % 2 == 1 for i, name in enumerate(CORPUS_LEEK_IDS)}
        for (leek_name, opp_name), seed in zip(self.slots, self.seeds):
            leek_cfg = self.configs["leeks"][leek_name]
            inv = False
            if opp_name == MIRROR_TAG:
                # Same build, frozen incumbent weights (V9_ga_baseline tree).
                opp_cfg = dict(leek_cfg)
                opp_cfg["name"] = f"{leek_cfg['name']}_Mirror"
                sc = build_scenario(leek_cfg, opp_cfg, seed=seed,
                                    opponent_ai=BASELINE_AI_PATH)
                inv = mirror_t2.get(leek_name, False)
                if inv:
                    # Team 1 = frozen baseline, team 2 = candidate.
                    sc["entities"][0][0]["ai"] = BASELINE_AI_PATH
                    sc["entities"][0][0]["name"] = f"{leek_cfg['name']}_Mirror"
                    sc["entities"][1][0]["ai"] = V9_AI_PATH
                    sc["entities"][1][0]["name"] = leek_cfg["name"]
                else:
                    sc["entities"][0][0]["ai"] = V9_AI_PATH
            else:
                opp_cfg = self.configs["opponents"][opp_name]
                sc = build_scenario(leek_cfg, opp_cfg, seed=seed)
                sc["entities"][0][0]["ai"] = V9_AI_PATH
            scenarios.append(sc)
            inverted.append(inv)

        results = [None] * len(scenarios)

        # Serial warm-up: first smart fight (compiles the V9 candidate tree),
        # first live fight (V8 opponent AI) and first mirror fight (frozen
        # baseline tree). After that the cache is hot and parallel workers
        # only read it — no concurrent compile-cache writes.
        warmup = [0]
        for pred in (lambda o: o.startswith("live_"),
                     lambda o: o == MIRROR_TAG):
            for i, (_, opp_name) in enumerate(self.slots):
                if pred(opp_name):
                    warmup.append(i)
                    break
        warmup = sorted(set(i for i in warmup if i < len(scenarios)))

        for i in warmup:
            results[i] = run_fight(scenarios[i], i, False)

        rest = [i for i in range(len(scenarios)) if i not in warmup]
        if self.parallel > 1 and len(rest) > 1:
            with ProcessPoolExecutor(max_workers=self.parallel) as ex:
                futs = {ex.submit(_run_fight_worker, (scenarios[i], i, False)): i
                        for i in rest}
                for f in as_completed(futs):
                    i = futs[f]
                    try:
                        results[i] = f.result()
                    except Exception as e:
                        results[i] = {"error": str(e), "fight_index": i}
        else:
            for i in rest:
                results[i] = run_fight(scenarios[i], i, False)

        # Aggregate: draws = 0.5 win, errors/crashes = losses. Inverted mirror
        # slots (candidate on team 2) flip the result and re-attribute bugs:
        # run_fight's has_bug only watches entity 0 (team 1).
        wins = losses = draws = errors = crashes = 0
        win_turns = []
        per_matchup = {}
        for (leek_name, opp_name), inv, r in zip(self.slots, inverted, results):
            tag = f"{leek_name[:4]}v{opp_name}" + ("_t2" if inv else "")
            m = per_matchup.setdefault(tag, {"wins": 0, "total": 0})
            m["total"] += 1
            if r is None or "error" in r:
                errors += 1
                losses += 1
                continue
            bug = r.get("has_bug")
            if inv:
                acts = r.get("actions") or []

                def _bug_at(ent):
                    return any(a[0] == 1002 and len(a) > 1 and a[1] == ent
                               for a in acts
                               if isinstance(a, list) and len(a) > 1)

                cand_bug = _bug_at(1)   # candidate = entity index 1
                base_bug = _bug_at(0)   # frozen baseline = entity index 0
                if base_bug and not cand_bug:
                    # Environment-side crash: not the candidate's fault.
                    draws += 1
                    m["wins"] += 0.5
                    continue
                bug = cand_bug
            if bug:
                crashes += 1
                losses += 1
                continue
            res = r.get("result")
            if inv:
                res = {"WIN": "LOSS", "LOSS": "WIN"}.get(res, res)
            if res == "WIN":
                wins += 1
                m["wins"] += 1
                win_turns.append(r.get("total_turns") or 64)
            elif res == "LOSS":
                losses += 1
            else:
                draws += 1
                m["wins"] += 0.5

        total = len(self.slots)
        points = wins + 0.5 * draws
        # Win-speed shaping (same idea as genetic_optimizer_local's 0.01 *
        # win_speed): mean (64 - turns)/64 over wins, coefficient 0.05 — the
        # M3 plan's "+0.05 per win-margin". Max ~0.047 < one fight's 0.0625,
        # so it breaks ties between equal W/L records without ever outvoting
        # a real win. Without it this corpus quantizes every candidate to the
        # same W/L and selection has no gradient.
        win_speed = (sum(max(0.0, (64.0 - t) / 64.0) for t in win_turns)
                     / len(win_turns)) if win_turns else 0.0
        fitness = points / total + 0.1 * (wins / total) + 0.05 * win_speed

        entry["fitness"] = fitness
        entry["detail"] = {
            "wins": wins, "losses": losses, "draws": draws,
            "errors": errors, "crashes": crashes, "points": points,
            "total": total, "win_speed": round(win_speed, 4),
            "per_matchup": per_matchup,
        }

        elapsed = time.time() - t0
        breakdown = "  ".join(f"{t}:{m['wins']:g}/{m['total']}"
                              for t, m in per_matchup.items())
        crash_str = f" [{crashes} crashes]" if crashes else ""
        err_str = f" [{errors} errors]" if errors else ""
        print(f"  [{idx + 1:2d}/{self.population_size}] fitness={fitness:.4f} "
              f"({wins}W/{losses}L/{draws}D{crash_str}{err_str}, "
              f"pts={points:g}/{total}, spd={win_speed:.3f})  "
              f"{breakdown}  ({elapsed:.1f}s)")
        return fitness

    def evaluate_population(self):
        gen_no = self.generation + 1
        print(f"\n{'=' * 70}\nGENERATION {gen_no}/{self.max_generations} — EVALUATION\n{'=' * 70}")
        t0 = time.time()
        for i, entry in enumerate(self.population):
            if entry["fitness"] is None:
                self.evaluate_candidate(i, entry)
            else:
                print(f"  [{i + 1:2d}/{self.population_size}] elite, kept "
                      f"fitness={entry['fitness']:.4f}")
        elapsed = time.time() - t0

        ranked = sorted(self.population, key=lambda e: e["fitness"], reverse=True)
        fits = [e["fitness"] for e in ranked]
        top = ranked[0]
        if self.best is None or top["fitness"] > self.best["fitness"]:
            self.best = {"weights": dict(top["weights"]),
                         "fitness": top["fitness"],
                         "generation": gen_no}
            print(f"\n*** NEW BEST: fitness={self.best['fitness']:.4f} ***")

        self.history.append({
            "generation": gen_no,
            "best": fits[0], "avg": sum(fits) / len(fits), "worst": fits[-1],
            "elapsed_s": round(elapsed, 1),
        })
        print(f"\nGen {gen_no} summary: best={fits[0]:.4f} "
              f"avg={sum(fits) / len(fits):.4f} worst={fits[-1]:.4f} "
              f"({elapsed:.1f}s)")

    # ── evolution ──

    def tournament(self):
        k = min(self.tournament_size, len(self.population))
        return max(random.sample(self.population, k),
                   key=lambda e: e["fitness"])["weights"]

    def evolve(self):
        ranked = sorted(self.population, key=lambda e: e["fitness"], reverse=True)
        new_pop = []
        for i in range(min(self.elitism, len(ranked))):
            new_pop.append(copy.deepcopy(ranked[i]))  # fitness kept (fixed seeds)
        while len(new_pop) < self.population_size:
            child = crossover(self.tournament(), self.tournament())
            child = mutate(child, self.mutation_rate, self.mutation_strength)
            new_pop.append({"weights": child, "fitness": None, "detail": None})
        self.population = new_pop

    def initialize_population(self):
        self.baseline = read_active_weights()
        self.population.append({"weights": dict(self.baseline),
                                "fitness": None, "detail": None})
        for _ in range(1, self.population_size):
            self.population.append({
                "weights": mutate(self.baseline, rate=0.6, strength=0.3),
                "fitness": None, "detail": None,
            })
        print(f"Population initialized: genome 0 = active weights, "
              f"{self.population_size - 1} mutants. {len(EW_ORDER)} evolvable keys.")

    # ── checkpointing ──

    def save_checkpoint(self):
        self.run_dir.mkdir(parents=True, exist_ok=True)
        ck = {
            "phase": "M3", "kind": "v9_eval_weights",
            "generations_completed": self.generation,
            "master_seed": self.master_seed,
            "seeds": self.seeds,
            "corpus": [list(c) for c in self.corpus],
            "baseline": self.baseline,
            "best": self.best,
            "history": self.history,
            "population": self.population,
            "config": {
                "population_size": self.population_size,
                "max_generations": self.max_generations,
                "mutation_rate": self.mutation_rate,
                "mutation_strength": self.mutation_strength,
                "elitism": self.elitism,
                "tournament_size": self.tournament_size,
                "parallel": self.parallel,
                "use_mirror": self.use_mirror,
            },
        }
        with open(self.run_dir / "checkpoint.json", "w") as f:
            json.dump(ck, f, indent=2)
        if self.best:
            with open(self.run_dir / "best_weights.json", "w") as f:
                json.dump({
                    "kind": "v9_eval_weights",
                    "fitness": self.best["fitness"],
                    "generation": self.best["generation"],
                    "weights": self.best["weights"],
                    "baseline": self.baseline,
                    "run_dir": str(self.run_dir),
                }, f, indent=2)

    def load_checkpoint(self, path):
        path = Path(path)
        if not path.is_absolute():
            path = PROJECT_DIR / path
        with open(path) as f:
            ck = json.load(f)
        self.generation = ck["generations_completed"]
        self.master_seed = ck["master_seed"]
        self.seeds = ck["seeds"]
        self.corpus = [tuple(c) for c in ck["corpus"]]
        self.slots = expand_slots(self.corpus)
        self.baseline = ck["baseline"]
        self.best = ck.get("best")
        self.history = ck.get("history", [])
        self.population = ck["population"]
        cfg = ck.get("config", {})
        self.population_size = cfg.get("population_size", self.population_size)
        self.max_generations = cfg.get("max_generations", self.max_generations)
        self.mutation_rate = cfg.get("mutation_rate", self.mutation_rate)
        self.mutation_strength = cfg.get("mutation_strength", self.mutation_strength)
        self.elitism = cfg.get("elitism", self.elitism)
        self.tournament_size = cfg.get("tournament_size", self.tournament_size)
        self.use_mirror = cfg.get("use_mirror", self.use_mirror)
        if path.parent.name.startswith("v2_run_"):
            self.run_dir = path.parent
        print(f"Resumed from {path}: {self.generation} generations done, "
              f"best={self.best['fitness']:.4f}" if self.best else
              f"Resumed from {path}: {self.generation} generations done")

    def save_run_config(self):
        self.run_dir.mkdir(parents=True, exist_ok=True)
        with open(self.run_dir / "run_config.json", "w") as f:
            json.dump({
                "run_id": self.run_id, "phase": "M3",
                "population_size": self.population_size,
                "max_generations": self.max_generations,
                "master_seed": self.master_seed,
                "mutation_rate": self.mutation_rate,
                "mutation_strength": self.mutation_strength,
                "elitism": self.elitism,
                "tournament_size": self.tournament_size,
                "parallel": self.parallel,
                "use_mirror": self.use_mirror,
                "corpus": [list(c) for c in self.corpus],
                "total_fights_per_candidate": len(self.slots),
            }, f, indent=2)

    # ── reporting ──

    def print_trajectory(self):
        print(f"\nFitness trajectory:")
        for h in self.history:
            print(f"  Gen {h['generation']:2d}: best={h['best']:.4f} "
                  f"avg={h['avg']:.4f} worst={h['worst']:.4f} ({h['elapsed_s']:.0f}s)")

    def print_best_table(self):
        print(f"\nBest weights vs pre-run active set "
              f"(fitness {self.best['fitness']:.4f}, gen {self.best['generation']}):")
        print(f"  {'weight':<16s} {'default':>10s} {'best':>10s} {'change':>9s}")
        changed = 0
        for k in EW_ORDER:
            d = self.baseline[k]
            b = self.best["weights"][k]
            pct = ((b - d) / d * 100) if d else (float("inf") if b else 0.0)
            marker = "" if abs(b - d) < 1e-9 else "*"
            if marker:
                changed += 1
            print(f"  {k:<16s} {fmt_num(d):>10s} {fmt_num(b):>10s} "
                  f"{pct:+8.1f}% {marker}")
        if changed == 0:
            print("  (best == pre-run active set: no improvement found)")


# ── promotion gate ──

def run_bot_battery(run_dir):
    """24-fight server-side bot matrix. NOTE: this exercises the CURRENTLY
    UPLOADED server AI (9.0/V9/main.lk); local weights are not uploaded here."""
    print(f"\n{'=' * 70}")
    print("PROMOTION GATE: bot battery")
    print("=" * 70)
    print("NOTE: bot_battery.py runs server-side against the uploaded "
          "9.0/V9/main.lk.\nThe promoted ga_weights.lk is LOCAL only (upload "
          "is a separate decision).")
    try:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "bot_battery.py")],
            cwd=str(PROJECT_DIR), capture_output=True, text=True, timeout=1800,
        )
        out = proc.stdout + ("\n[stderr]\n" + proc.stderr[-2000:]
                             if proc.returncode != 0 else "")
        print(out)
        if run_dir:
            (run_dir / "battery_result.txt").write_text(out)
        return proc.returncode
    except subprocess.TimeoutExpired:
        print("bot battery timed out (1800s)")
        return -1


def main():
    ap = argparse.ArgumentParser(
        description="GA v2: evolve V9 eval-function weights (Phase M3)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--generations", type=int, default=None,
                    help="Total generations (default 4; on resume overrides checkpoint)")
    ap.add_argument("--population", type=int, default=None,
                    help="Population size (default 6)")
    ap.add_argument("--parallel", type=int, default=8,
                    help="Parallel fights within one candidate (default 8; "
                         "candidates always run sequentially)")
    ap.add_argument("--mutation-rate", type=float, default=0.3)
    ap.add_argument("--mutation-strength", type=float, default=0.25)
    ap.add_argument("--elitism", type=int, default=1)
    ap.add_argument("--tournament-size", type=int, default=3)
    ap.add_argument("--seed", type=int, default=20260813,
                    help="Master seed for the fixed corpus seed block")
    ap.add_argument("--resume", type=str, metavar="CHECKPOINT_JSON",
                    help="Resume from ga_local/v2_run_<ts>/checkpoint.json")
    ap.add_argument("--no-promote", action="store_true",
                    help="Skip the promotion gate entirely (restore pre-run weights)")
    ap.add_argument("--skip-battery", action="store_true",
                    help="Promote best weights but skip the bot battery")
    ap.add_argument("--no-mirror", action="store_true",
                    help="Use the exact 12-fight plan corpus (no mirror fights). "
                         "WARNING: that corpus saturates — V9 at defaults "
                         "sweeps it 12/12, leaving no upward gradient.")
    args = ap.parse_args()

    if args.resume:
        ga = EvalWeightGA(parallel=args.parallel)
        ga.load_checkpoint(args.resume)
        if args.generations is not None:
            ga.max_generations = args.generations
        if args.population is not None:
            ga.population_size = args.population
        ga.parallel = args.parallel
    else:
        ga = EvalWeightGA(
            population_size=args.population or 6,
            generations=args.generations or 4,
            master_seed=args.seed,
            mutation_rate=args.mutation_rate,
            mutation_strength=args.mutation_strength,
            elitism=args.elitism,
            tournament_size=args.tournament_size,
            parallel=args.parallel,
            use_mirror=not args.no_mirror,
        )

    if ga.population_size < 2:
        ap.error("population must be >= 2")
    if ga.elitism >= ga.population_size:
        ap.error("elitism must be < population")

    # ga_weights.lk must exist (eval.lk includes it permanently); back up the
    # pre-run active set so a crash never leaves a random candidate live.
    ensure_ga_weights()
    backup_path = Path(str(GA_WEIGHTS_PATH) + ".ga_v2_backup")
    shutil.copy2(GA_WEIGHTS_PATH, backup_path)

    random.seed(ga.master_seed + ga.generation)

    print(f"{'=' * 70}")
    print("GA v2 — V9 EVAL WEIGHTS (Phase M3)")
    print(f"{'=' * 70}")
    print(f"Corpus ({len(ga.slots)} fights/candidate):")
    for leek, opp, n in ga.corpus:
        print(f"  {leek:<18s} vs {opp:<12s} x{n}")
    print(f"Population: {ga.population_size}, generations: {ga.max_generations}, "
          f"elitism: {ga.elitism}, parallel: {ga.parallel}")
    print(f"Master seed: {ga.master_seed} (fixed corpus seed block)")
    print(f"Output: {ga.run_dir}")
    print(f"{'=' * 70}")

    promoted = False
    t_start = time.time()
    try:
        if not ga.population:
            ga.save_run_config()
            ga.initialize_population()

        # Frozen incumbent for the mirror fights (pinned to pre-run weights).
        if ga.use_mirror:
            setup_baseline_tree(ga.baseline)
            print(f"Mirror baseline tree: {BASELINE_TREE_LOCAL} "
                  f"(pinned to pre-run active weights)")

        while ga.generation < ga.max_generations:
            ga.evaluate_population()
            ga.generation += 1
            ga.save_checkpoint()
            ga.print_trajectory()
            if ga.generation < ga.max_generations:
                ga.evolve()

        total_wall = time.time() - t_start

        print(f"\n{'=' * 70}")
        print("OPTIMIZATION COMPLETE")
        print(f"{'=' * 70}")
        ga.print_trajectory()
        ga.print_best_table()
        print(f"\nBest weights JSON: {ga.run_dir / 'best_weights.json'}")
        print(f"Total wall time: {total_wall / 60:.1f} min ({total_wall:.0f}s)")

        if weights_equal(ga.best["weights"], ga.baseline):
            print("\nNOTE: run best equals the pre-run active set — no "
                  "improvement found within this budget. The loop is "
                  "verified; gains need more generations/population.")

        # Promotion gate: best weights become the active set, then battery.
        if not args.no_promote:
            prov = (f"Promoted by ga_v2 run {ga.run_id} "
                    f"(fitness {ga.best['fitness']:.4f}, gen {ga.best['generation']}).")
            write_ga_weights(ga.best["weights"], provenance=prov)
            promoted = True
            wipe_cache()
            print(f"\nPromoted best weights into {GA_WEIGHTS_PATH}")
            if not args.skip_battery:
                run_bot_battery(ga.run_dir)
    finally:
        if not promoted:
            # Crash / interrupt / --no-promote: restore the pre-run set so
            # ga_weights.lk never carries an unvetted candidate.
            shutil.copy2(backup_path, GA_WEIGHTS_PATH)
            wipe_cache()
            print(f"\nRestored pre-run ga_weights.lk from backup.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
