#!/usr/bin/env python3
"""W2: train the value model P(win|state) on data/dataset_v1.jsonl.

Constraints from deployment: the model must run inside LeekScript ops limits,
so it's a small MLP (25→16→8→1) exported as JSON weights (string-literal
pattern, like the enemy model). Split is FIGHT-level (no leakage).

Usage: websocket_env/bin/python tools/train_value_model.py [--dataset data/dataset_v1.jsonl]
"""
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score, log_loss, accuracy_score
from sklearn.neural_network import MLPClassifier

ROOT = Path(__file__).parent.parent
FEATURES = ["turn", "hp_us", "hp_foe", "maxhp_us", "maxhp_foe", "dist",
            "abssh_us", "abssh_foe", "relsh_us", "relsh_foe",
            "pois_us", "pois_foe", "poisdpt_us", "poisdpt_foe",
            "str_us", "str_foe", "mag_us", "mag_foe", "agi_us", "agi_foe",
            "wis_us", "wis_foe", "res_us", "res_foe", "sci_us", "sci_foe",
            "tp_us", "tp_foe", "mp_us", "mp_foe", "lvl_us", "lvl_foe"]
# engineered: the model shouldn't have to rediscover arithmetic relationships
DERIVED = ["hp_diff", "hp_ratio", "sh_diff", "maxhp_ratio", "poisdpt_diff",
           "str_diff", "mag_diff", "agi_diff"]
# archetype indicators (2026-08-18 calibration audit: tank-subset was the
# model's weakest cell — AUC 0.717 and 9pts pessimistic — give the MLP the
# offsets explicitly instead of hoping it infers them from raw stats)
DERIVED += ["foe_is_tank", "foe_is_burst", "foe_is_sustain"]


def load(path):
    X, y, fights = [], [], []
    for line in open(path):
        r = json.loads(line)
        if r.get("dist") is None:
            continue
        base = [r.get(f, 0) or 0 for f in FEATURES]
        # NB: hp values are genuine zeros on dead states — do NOT `or 1` them
        # (that taught the model "dead = full HP" in the first dataset).
        hp_u, hp_f = r.get("hp_us", 0) or 0, r.get("hp_foe", 0) or 0
        sh_u = (r.get("abssh_us", 0) or 0) + (r.get("relsh_us", 0) or 0)
        sh_f = (r.get("abssh_foe", 0) or 0) + (r.get("relsh_foe", 0) or 0)
        der = [hp_u - hp_f,
               hp_u / max(0.01, hp_f),
               sh_u - sh_f,
               (r.get("maxhp_us", 1) or 1) / max(1, r.get("maxhp_foe", 1) or 1),
               (r.get("poisdpt_us", 0) or 0) - (r.get("poisdpt_foe", 0) or 0),
               (r.get("str_us", 0) or 0) - (r.get("str_foe", 0) or 0),
               (r.get("mag_us", 0) or 0) - (r.get("mag_foe", 0) or 0),
               (r.get("agi_us", 0) or 0) - (r.get("agi_foe", 0) or 0),
               1.0 if ((r.get("res_foe", 0) or 0) >= 300 and (r.get("sci_foe", 0) or 0) >= 200) else 0.0,
               1.0 if ((r.get("str_foe", 0) or 0) >= 400 and (r.get("res_foe", 0) or 0) < 300) else 0.0,
               1.0 if (r.get("wis_foe", 0) or 0) >= 400 else 0.0]
        X.append(base + der)
        y.append(r["y"])
        fights.append(r["fight"])
    return np.array(X, dtype=np.float64), np.array(y), np.array(fights)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=str(ROOT / "data" / "dataset_v1.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "data" / "value_model.json"))
    args = ap.parse_args()

    X, y, fights = load(args.dataset)
    print(f"{len(X)} rows, {len(set(fights))} fights, {len(FEATURES)} features")

    uniq = np.unique(fights)
    rng = np.random.RandomState(42)
    rng.shuffle(uniq)
    cut = int(len(uniq) * 0.8)
    train_f, test_f = set(uniq[:cut]), set(uniq[cut:])
    tr = np.array([f in train_f for f in fights])
    te = ~tr
    print(f"train {tr.sum()} rows / test {te.sum()} rows")

    mean, std = X[tr].mean(0), X[tr].std(0) + 1e-9
    Xtr = (X[tr] - mean) / std
    Xte = (X[te] - mean) / std

    clf = MLPClassifier(hidden_layer_sizes=(16, 8), activation="relu", alpha=1.0,
                        max_iter=400, early_stopping=True, random_state=42)
    clf.fit(Xtr, y[tr])
    p_te = clf.predict_proba(Xte)[:, 1]
    p_tr = clf.predict_proba(Xtr)[:, 1]

    # naive baseline: hp-diff ranking
    hp_te = X[te, FEATURES.index("hp_us")] - X[te, FEATURES.index("hp_foe")]
    hp_tr = X[tr, FEATURES.index("hp_us")] - X[tr, FEATURES.index("hp_foe")]
    print(f"AUC  train {roc_auc_score(y[tr], p_tr):.4f}  test {roc_auc_score(y[te], p_te):.4f}")
    print(f"AUC  hp-diff baseline: train {roc_auc_score(y[tr], hp_tr):.4f}  test {roc_auc_score(y[te], hp_te):.4f}")
    print(f"logloss {log_loss(y[te], p_te):.4f}  acc@0.5 {accuracy_score(y[te], p_te > 0.5):.4f}")

    # per-turn-bucket AUC: the scorer needs mid/late discrimination most
    turns_te = X[te, FEATURES.index("turn")]
    for lo, hi in ((1, 3), (4, 7), (8, 12), (13, 20), (21, 99)):
        m = (turns_te >= lo) & (turns_te <= hi)
        if m.sum() > 20:
            print(f"  turns {lo:2d}-{hi:2d}: AUC model {roc_auc_score(y[te][m], p_te[m]):.3f} "
                  f"vs hp-diff {roc_auc_score(y[te][m], hp_te[m]):.3f}  (n={m.sum()})")

    # calibration buckets
    for lo in range(0, 10, 2):
        m = (p_te >= lo / 10) & (p_te < (lo + 2) / 10)
        if m.sum():
            print(f"  p[{lo/10:.1f},{(lo+2)/10:.1f}): n={m.sum():4d} winrate={y[te][m].mean():.3f}")

    model = {
        "features": FEATURES,
        "mean": mean.tolist(),
        "std": std.tolist(),
        "hidden": [16, 8],
        "w": [w_.tolist() for w_ in clf.coefs_],
        "b": [b_.tolist() for b_ in clf.intercepts_],
        "auc_test": float(roc_auc_score(y[te], p_te)),
        "auc_hp_diff_test": float(roc_auc_score(y[te], hp_te)),
    }
    Path(args.out).write_text(json.dumps(model))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
