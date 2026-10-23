#!/usr/bin/env python3
"""Compare value models (value_train_mono.py outputs) on the held-out test split of a dataset.

    python3 tools/value_compare.py data/prod/value_mono.json data/prod/value_mono2.json [--ds data/prod/value_ds2.npz]

Test split = fid % 10 == 9 (the split value_train_mono.py never trains on). Reports logloss / Brier / AUC on:
our V10-era fights (src 1, from 2026-09-29), all our fights, prod fights, and our V10 fights by turn bucket.
A model only reads the features it was trained on (looked up by name), so v1 (83) and v2 (93) compare on the
same samples.
"""
import argparse, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from value_train import metrics

V10_START = 1790640000   # 2026-09-29


def predict(model, X, names):
    m = json.load(open(model))
    idx = [names.index(n) for n in m['names']]
    Xm = X[:, idx].astype(np.float64)
    mu, sd = np.array(m['mu']), np.array(m['sd'])
    Z = np.clip((Xm - mu) / sd, -6, 6)
    ci = [m['names'].index(n) for n in m['ctx']]; mi = [m['names'].index(n) for n in m['mono']]
    (W1, b1), (W2, b2), (W3, b3) = [(np.array(a), np.array(b)) for a, b in m['layers']]
    out = []
    for s in range(0, len(Z), 200000):
        z = Z[s:s + 200000]
        h1 = np.tanh(z[:, ci] @ W1 + b1); h2 = np.tanh(h1 @ W2 + b2); o = h2 @ W3 + b3
        logit = o[:, 0] + np.sum(np.array(m['sign']) * np.logaddexp(0, o[:, 1:]) * z[:, mi], axis=1)
        out.append(1 / (1 + np.exp(-np.clip(logit, -30, 30))))
    return np.concatenate(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('models', nargs='+')
    ap.add_argument('--ds', default=os.path.join(ROOT, 'data', 'prod', 'value_ds2.npz'))
    a = ap.parse_args()
    d = np.load(a.ds)
    names = [str(n) for n in d['names']]
    te = d['fid'] % 10 == 9
    X, y, w, turn = d['X'][te], d['y'][te].astype(np.float64), d['w'][te].astype(np.float64), d['turn'][te]
    src = d['src'][te] if 'src' in d.files else np.zeros(len(y), int)
    date = d['date'][te] if 'date' in d.files else np.zeros(len(y), int)
    subsets = [('ours V10', (src == 1) & (date >= V10_START)), ('ours all', src == 1), ('prod', src == 0)]
    buckets = [('T1-2', turn <= 2), ('T3-5', (turn >= 3) & (turn <= 5)), ('T6-10', (turn >= 6) & (turn <= 10)),
               ('T11+', turn >= 11)]
    preds = {m: predict(m, X, names) for m in a.models}
    for label, sel in subsets:
        print('%s: %d samples, %d fights' % (label, sel.sum(), len(np.unique(d['fid'][te][sel]))))
        for m, p in preds.items():
            ll, br, auc, acc = metrics(p[sel], y[sel], w[sel])
            print('   %-40s logloss %.4f  brier %.4f  AUC %.3f  acc %.3f' % (os.path.basename(m), ll, br, auc, acc))
    sel = subsets[0][1]
    print('ours V10 by turn (AUC):')
    for m, p in preds.items():
        print('   %-40s %s' % (os.path.basename(m), '  '.join('%s %.3f' % (b, metrics(p[sel & bm], y[sel & bm], w[sel & bm])[2])
                                                           for b, bm in buckets)))


if __name__ == '__main__':
    main()
