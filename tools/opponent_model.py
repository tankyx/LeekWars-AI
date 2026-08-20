#!/usr/bin/env python3
"""Model-driven opponent selection for solo ladder fights.

Builds, per leek, a win-probability model from that leek's fight history
(tools/fight_history_<leek_id>.db) joined with the enemy behavioral model
(data/enemy_model_main.json, keyed by opponent name, carries an archetype).

Score(opponent) is a shrinkage blend of the per-opponent empirical win rate
and the archetype-level win rate for this leek:

    wr_blend = (wins + K * archetype_wr) / (total + K)      K = 4

Unknown opponent -> archetype prior; unknown archetype -> leek global prior.
A small level-diff term (+-0.03 max) is added when the garden listing
provides the opponent's level. Ties are broken on opponent talent (higher
talent = more talent gain), handled by the caller.

Usage:
    python3 tools/opponent_model.py            # rebuild + save cache
    python3 tools/opponent_model.py --report   # rebuild, save, print report
"""
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ENEMY_MODEL_PATH = os.path.join(ROOT, "data", "enemy_model_main.json")
CACHE_PATH = os.path.join(ROOT, "data", "opponent_model.json")

K_SHRINK = 4
LEVEL_COEF = 0.002   # per level of (my_level - opp_level)
LEVEL_CAP = 0.03

# Talent economics, fit from 15,418 cached fight reports (2026-08-18):
# gain_win(diff)  ~= 14.9 + 0.030 * diff
# gain_loss(diff) ~= -14.0 + 0.026 * diff      diff = opp_talent - our_talent
# EV(fight) = p * gain_win + (1-p) * gain_loss. Key insight: at even odds,
# fighting UP is +EV (+15.6/-12.1 at +100) — max-P is not the right pick.
GAIN_WIN_BASE, GAIN_WIN_PER = 14.9, 0.030
GAIN_LOSS_BASE, GAIN_LOSS_PER = -14.0, 0.026
TALENT_LOG = os.path.join(ROOT, "data", "talent_log.jsonl")

# Our four main-account leeks (all currently level 301 — the leek_info table
# in the history DBs is stale, so the level is maintained here).
LEEKS = {
    20443: ("AdaLovelace", 301),
    129295: ("KurtGodel", 301),
    129296: ("MargaretHamilton", 301),
    129288: ("EdsgerDijkstra", 301),
}


def load_enemy_archetypes():
    """opponent_id -> archetype (fallback: name -> archetype)."""
    with open(ENEMY_MODEL_PATH) as f:
        em = json.load(f)
    em.pop("_meta", None)
    by_id, by_name = {}, {}
    for name, v in em.items():
        if not isinstance(v, dict):
            continue
        arch = v.get("archetype")
        if not arch:
            continue
        if v.get("opponent_id") is not None:
            by_id[v["opponent_id"]] = arch
        by_name[name] = arch
    return by_id, by_name


def load_enemy_top_weapons():
    """opponent name/id -> top-1 weapon name (by usage), from the enemy model."""
    with open(ENEMY_MODEL_PATH) as f:
        em = json.load(f)
    by_id, by_name = {}, {}
    for name, v in em.items():
        if not isinstance(v, dict):
            continue
        wu = v.get("weapon_usage") or {}
        if not wu:
            continue
        top = max(wu.items(), key=lambda kv: kv[1])[0]
        if v.get("opponent_id") is not None:
            by_id[v["opponent_id"]] = top
        by_name[name] = top
    return by_id, by_name


def load_latest_talents():
    """leek name -> latest talent from data/talent_log.jsonl."""
    talents = {}
    try:
        with open(TALENT_LOG) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("leek") and r.get("talent"):
                    talents[r["leek"]] = r["talent"]
    except OSError:
        pass
    return talents


def build_leek(leek_id, by_id, by_name, weap_by_id=None, weap_by_name=None):
    """Build the model entry for one leek from its fight history DB."""
    db_path = os.path.join(TOOLS_DIR, f"fight_history_{leek_id}.db")
    if not os.path.exists(db_path):
        return None
    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT opponent_id, opponent_name, opponent_level, "
        "SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END), COUNT(*) "
        "FROM fight_history GROUP BY opponent_id").fetchall()
    con.close()
    my_level = LEEKS.get(leek_id, (None, 301))[1]

    opponents = {}
    arch_wins, arch_tot = {}, {}
    weap_wins, weap_tot = {}, {}
    g_wins = g_tot = 0
    matched_fights = 0
    for oid, name, olevel, wins, total in rows:
        arch = by_id.get(oid) or by_name.get(name)
        weap = (weap_by_id or {}).get(oid) or (weap_by_name or {}).get(name)
        opponents[str(oid)] = {
            "name": name, "level": olevel, "wins": wins, "total": total,
            "archetype": arch, "weapon": weap,
        }
        g_wins += wins
        g_tot += total
        if arch:
            matched_fights += total
            arch_wins[arch] = arch_wins.get(arch, 0) + wins
            arch_tot[arch] = arch_tot.get(arch, 0) + total
        if weap:
            weap_wins[weap] = weap_wins.get(weap, 0) + wins
            weap_tot[weap] = weap_tot.get(weap, 0) + total

    archetypes = {
        a: {"wins": arch_wins[a], "total": arch_tot[a],
            "wr": arch_wins[a] / arch_tot[a]}
        for a in sorted(arch_tot)
    }
    weapons = {
        w: {"wins": weap_wins[w], "total": weap_tot[w],
            "wr": weap_wins[w] / weap_tot[w]}
        for w in sorted(weap_tot)
    }
    return {
        "name": LEEKS.get(leek_id, (f"leek_{leek_id}", 301))[0],
        "level": my_level,
        "global_wr": g_wins / g_tot if g_tot else 0.5,
        "global_fights": g_tot,
        "archetype_coverage": matched_fights / g_tot if g_tot else 0.0,
        "archetypes": archetypes,
        "weapons": weapons,
        # opponent_id -> archetype/weapon for every enemy-model entry, so an
        # opponent this leek never fought still gets its priors (not global).
        "enemy_archetype_by_id": {str(oid): a for oid, a in by_id.items()},
        "enemy_weapon_by_id": {str(oid): w for oid, w in (weap_by_id or {}).items()},
        "opponents": opponents,
    }


def build_all():
    by_id, by_name = load_enemy_archetypes()
    weap_by_id, weap_by_name = load_enemy_top_weapons()
    talents = load_latest_talents()
    cache = {
        "_meta": {
            "built": datetime.now(timezone.utc).isoformat(),
            "k_shrink": K_SHRINK,
            "level_coef": LEVEL_COEF,
            "level_cap": LEVEL_CAP,
            "gain_win": [GAIN_WIN_BASE, GAIN_WIN_PER],
            "gain_loss": [GAIN_LOSS_BASE, GAIN_LOSS_PER],
            "talents": talents,
            "source": "tools/opponent_model.py",
        },
        "leeks": {},
    }
    for leek_id in LEEKS:
        entry = build_leek(leek_id, by_id, by_name, weap_by_id, weap_by_name)
        if entry:
            entry["talent"] = talents.get(entry["name"])
            cache["leeks"][str(leek_id)] = entry
    return cache


def save_cache(cache):
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f)


def load_cache():
    with open(CACHE_PATH) as f:
        return json.load(f)


def get_leek_entry(leek_id, cache=None):
    """Cache entry for a leek; rebuild just this leek if the cache is stale/missing."""
    try:
        cache = cache or load_cache()
        entry = cache.get("leeks", {}).get(str(leek_id))
        if entry:
            return entry
    except (OSError, json.JSONDecodeError):
        pass
    by_id, by_name = load_enemy_archetypes()
    weap_by_id, weap_by_name = load_enemy_top_weapons()
    entry = build_leek(leek_id, by_id, by_name, weap_by_id, weap_by_name)
    if entry:
        entry["talent"] = load_latest_talents().get(entry["name"])
    return entry


def score_opponent(leek_entry, opponent_id, opp_level=None, opp_talent=None):
    """Blended win probability for one opponent (id from the garden listing)."""
    k = K_SHRINK
    global_wr = leek_entry.get("global_wr", 0.5)
    o = leek_entry.get("opponents", {}).get(str(opponent_id))
    if o:
        arch = o.get("archetype")
        weap = o.get("weapon")
    else:
        # never fought by this leek — still use the enemy model's priors
        arch = leek_entry.get("enemy_archetype_by_id", {}).get(str(opponent_id))
        weap = leek_entry.get("enemy_weapon_by_id", {}).get(str(opponent_id))
    # prior: weighted blend of archetype WR and top-weapon WR by sample sizes
    arch_stats = leek_entry.get("archetypes", {}).get(arch) if arch else None
    weap_stats = leek_entry.get("weapons", {}).get(weap) if weap else None
    pnum, pden = 0.0, 0
    if arch_stats and arch_stats["total"] > 0:
        pnum += arch_stats["wr"] * arch_stats["total"]
        pden += arch_stats["total"]
    if weap_stats and weap_stats["total"] > 0:
        pnum += weap_stats["wr"] * weap_stats["total"]
        pden += weap_stats["total"]
    prior = pnum / pden if pden > 0 else global_wr
    if o and o["total"] > 0:
        score = (o["wins"] + k * prior) / (o["total"] + k)
    else:
        score = prior
    if opp_level is not None:
        diff = leek_entry.get("level", 301) - opp_level
        score += max(-LEVEL_CAP, min(LEVEL_CAP, LEVEL_COEF * diff))
    if opp_talent is not None and leek_entry.get("talent") is not None:
        # ELO correction (v2.1): the nominal score is at diff 0; a +100-talent
        # opponent is genuinely harder, not just worth more. v2.0 skipped this
        # and fed our leeks overpriced fights (A/B 2026-08-18: v2 lost to v1
        # on its own objective, +0.45 vs +1.98 mean talent gain).
        diff = opp_talent - leek_entry["talent"]
        p = min(0.98, max(0.02, score))
        score = 1.0 / (1.0 + (10.0 ** (diff / 400.0)) * (1.0 - p) / p)
    return score


def ev_opponent(leek_entry, opponent_id, opp_level=None, opp_talent=None):
    """Expected talent delta for a fight vs this opponent (v2 scoring)."""
    p = score_opponent(leek_entry, opponent_id, opp_level, opp_talent)
    if opp_talent is None or leek_entry.get("talent") is None:
        return p  # fall back to raw win prob when talent is unknown
    diff = opp_talent - leek_entry["talent"]
    gain = GAIN_WIN_BASE + GAIN_WIN_PER * diff
    loss = GAIN_LOSS_BASE + GAIN_LOSS_PER * diff
    return p * gain + (1 - p) * loss


def pick_best(leek_entry, opponents):
    """Highest-EV opponent from a garden listing (dicts with id/level/talent).
    v2: maximize expected talent delta (falls back to win prob)."""
    best, best_key = None, None
    for o in opponents:
        s = ev_opponent(leek_entry, o.get("id"), o.get("level"), o.get("talent"))
        key = (round(s, 9), o.get("talent") or 0, o.get("level") or 0)
        if best_key is None or key > best_key:
            best, best_key = o, key
    return best


# ---------------------------------------------------------------- report ----

def smart_policy_rank(opponents):
    """Replicates fast_solo.FastRunner.pick ordering over a set of opponents
    (each {'id','name','level','wins','total'}) for comparison with the model."""
    beatable, unknown, risky = [], [], []
    for o in opponents:
        if o["total"] == 0:
            unknown.append(o)
            continue
        wr = o["wins"] / o["total"]
        losses = o["total"] - o["wins"]
        if o["wins"] >= 2 and wr >= 0.7:
            beatable.append((o, wr))
        elif losses >= 2 and wr <= 0.3:
            risky.append((o, wr))
        else:
            unknown.append((o, 0.5))
    beatable.sort(key=lambda x: -x[1])
    return [x[0] for x in beatable] + [x[0] if isinstance(x, tuple) else x for x in unknown] \
        + [x[0] for x in risky[:2]]


def print_report(cache):
    leeks = cache["leeks"]

    print("\n=== Win rate by enemy archetype (per leek, from fight history) ===")
    all_archs = sorted({a for e in leeks.values() for a in e["archetypes"]})
    header = f"{'leek':<18}{'global':>8}" + "".join(f"{a:>14}" for a in all_archs)
    print(header)
    print("-" * len(header))
    for lid, e in leeks.items():
        line = f"{e['name']:<18}{e['global_wr']:>8.1%}"
        for a in all_archs:
            s = e["archetypes"].get(a)
            line += f"{s['wr']:>13.1%} " if s else f"{'-':>13} "
        print(line)
    print("(n fights per cell below)")
    for lid, e in leeks.items():
        line = f"{e['name']:<18}{e['global_fights']:>8}"
        for a in all_archs:
            s = e["archetypes"].get(a)
            line += f"{s['total']:>13} " if s else f"{'-':>13} "
        print(line)

    print("\n=== Archetype coverage (share of fights vs opponents present in enemy_model_main.json) ===")
    for lid, e in leeks.items():
        n_known = sum(1 for o in e["opponents"].values() if o["archetype"])
        print(f"  {e['name']:<18} {e['archetype_coverage']:>6.1%} of fights, "
              f"{n_known}/{len(e['opponents'])} distinct opponents known")

    for lid, e in leeks.items():
        opps = []
        for oid, o in e["opponents"].items():
            s = score_opponent(e, oid, o.get("level"))
            opps.append((s, o["name"], o["wins"], o["total"],
                         o["wins"] / o["total"], o.get("archetype") or "?"))
        opps.sort(key=lambda x: -x[0])
        print(f"\n=== {e['name']} — top 15 highest-EV opponents (model) ===")
        print(f"  {'score':>6}  {'wr':>6} {'fights':>6}  {'archetype':<13} name")
        for s, name, w, t, wr, arch in opps[:15]:
            print(f"  {s:>6.1%}  {wr:>6.1%} {t:>6}  {arch:<13} {name}")
        print(f"--- {e['name']} — 15 lowest-EV opponents (model) ---")
        for s, name, w, t, wr, arch in opps[-15:]:
            print(f"  {s:>6.1%}  {wr:>6.1%} {t:>6}  {arch:<13} {name}")

        # Smart-policy comparison over the same opponent set (fight-history universe).
        hist = [{"id": oid, "name": o["name"], "level": o.get("level"),
                 "wins": o["wins"], "total": o["total"]}
                for oid, o in e["opponents"].items()]
        smart_top = [o["name"] for o in smart_policy_rank(hist)[:5]]
        model_top = [name for _, name, _, _, _, _ in opps[:5]]
        print(f"--- {e['name']} — smart-policy top5 vs model top5 "
              f"(over {len(hist)} history opponents) ---")
        print(f"  smart: {', '.join(smart_top)}")
        print(f"  model: {', '.join(model_top)}")
        print(f"  overlap: {sorted(set(smart_top) & set(model_top))}")


def main():
    cache = build_all()
    save_cache(cache)
    print(f"cache written to {CACHE_PATH} "
          f"({len(cache['leeks'])} leeks)", file=sys.stderr)
    if "--report" in sys.argv:
        print_report(cache)


if __name__ == "__main__":
    main()
