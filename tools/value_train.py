#!/usr/bin/env python3
"""Train the prod value model: P(win | state at the start of my turn).

numpy only (the model must be re-implementable as plain arithmetic in
LeekScript). Split by fight id (id % 10: 8 = validation, 9 = test, rest
train) so no fight leaks across sets. Every fight weighs 1 (sample weight =
1 / samples in that fight); draws are labelled 0.5.

Compares, on the test set:
  hpdiff   logistic on me_hpfrac - op_hpfrac (the obvious baseline)
  hp4      logistic on the 4 HP features
  linear   logistic on all features
  mlp      71 -> 32 -> 16 -> 1 tanh MLP, Adam, early stopping
and prints log-loss / Brier / AUC / accuracy overall and by turn bucket.

    python3 tools/value_train.py            # train + report + export
Writes data/prod/value_model.json (scaler + MLP weights + feature names).
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DS = os.path.join(ROOT, 'data', 'prod', 'value_ds.npz')
OUT = os.path.join(ROOT, 'data', 'prod', 'value_model.json')
rng = np.random.default_rng(0)


def sig(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def metrics(p, y, w):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    ll = -np.sum(w * (y * np.log(p) + (1 - y) * np.log(1 - p))) / w.sum()
    br = np.sum(w * (p - y) ** 2) / w.sum()
    m = y != 0.5
    acc = np.sum(w[m] * ((p[m] > 0.5) == (y[m] > 0.5))) / w[m].sum() if m.any() else float('nan')
    # weighted AUC over decisive samples (rank-based, ties ignored)
    pp, yy, ww = p[m], y[m], w[m]
    o = np.argsort(pp)
    pp, yy, ww = pp[o], yy[o], ww[o]
    pos = ww * (yy > 0.5); neg = ww * (yy < 0.5)
    auc = np.sum(pos * np.cumsum(neg)) / max(1e-9, pos.sum() * neg.sum())
    return ll, br, auc, acc


class Adam:
    def __init__(self, params, lr=1e-3):
        self.p = params; self.lr = lr
        self.m = [np.zeros_like(x) for x in params]; self.v = [np.zeros_like(x) for x in params]; self.t = 0

    def step(self, grads):
        self.t += 1
        for i, (x, g) in enumerate(zip(self.p, grads)):
            self.m[i] = 0.9 * self.m[i] + 0.1 * g
            self.v[i] = 0.999 * self.v[i] + 0.001 * g * g
            mh = self.m[i] / (1 - 0.9 ** self.t); vh = self.v[i] / (1 - 0.999 ** self.t)
            x -= self.lr * mh / (np.sqrt(vh) + 1e-8)


def train_logistic(X, y, w, Xv, yv, wv, l2=1e-4, epochs=60):
    W = np.zeros(X.shape[1]); b = np.zeros(1)
    opt = Adam([W, b], lr=0.01)
    best = (1e9, W.copy(), b.copy())
    for ep in range(epochs):
        idx = rng.permutation(len(X))
        for s in range(0, len(X), 2048):
            j = idx[s:s + 2048]
            p = sig(X[j] @ W + b)
            g = w[j] * (p - y[j])
            opt.step([X[j].T @ g / w[j].sum() + l2 * W, np.array([g.sum() / w[j].sum()])])
        vl = metrics(sig(Xv @ W + b), yv, wv)[0]
        if vl < best[0]:
            best = (vl, W.copy(), b.copy())
    return best[1], best[2]


def mlp_forward(X, P):
    W1, b1, W2, b2, W3, b3 = P
    h1 = np.tanh(X @ W1 + b1); h2 = np.tanh(h1 @ W2 + b2)
    return sig((h2 @ W3 + b3).ravel()), (h1, h2)


def train_mlp(X, y, w, Xv, yv, wv, h=(32, 16), l2=1e-4, epochs=80, patience=8):
    d = X.shape[1]
    P = [rng.normal(0, 1 / np.sqrt(d), (d, h[0])), np.zeros(h[0]),
         rng.normal(0, 1 / np.sqrt(h[0]), (h[0], h[1])), np.zeros(h[1]),
         rng.normal(0, 1 / np.sqrt(h[1]), (h[1], 1)), np.zeros(1)]
    opt = Adam(P, lr=2e-3)
    best = (1e9, [p.copy() for p in P]); bad = 0
    for ep in range(epochs):
        idx = rng.permutation(len(X))
        for s in range(0, len(X), 1024):
            j = idx[s:s + 1024]
            xb = X[j]; p, (h1, h2) = mlp_forward(xb, P)
            g = (w[j] * (p - y[j]) / w[j].sum())[:, None]
            gW3 = h2.T @ g; gb3 = g.sum(0)
            d2 = (g @ P[4].T) * (1 - h2 ** 2)
            gW2 = h1.T @ d2; gb2 = d2.sum(0)
            d1 = (d2 @ P[2].T) * (1 - h1 ** 2)
            gW1 = xb.T @ d1; gb1 = d1.sum(0)
            opt.step([gW1 + l2 * P[0], gb1, gW2 + l2 * P[2], gb2, gW3 + l2 * P[4], gb3])
        vl = metrics(mlp_forward(Xv, P)[0], yv, wv)[0]
        if vl < best[0] - 1e-5:
            best = (vl, [p.copy() for p in P]); bad = 0
        else:
            bad += 1
            if bad >= patience:
                break
        if ep % 10 == 0:
            print('    mlp epoch %d  val logloss %.4f' % (ep, vl), flush=True)
    return best[1]


def main():
    d = np.load(DS)
    X, y, w, fid, turn = d['X'].astype(np.float64), d['y'].astype(np.float64), d['w'].astype(np.float64), d['fid'], d['turn']
    names = [str(n) for n in d['names']]
    part = fid % 10
    tr, va, te = part < 8, part == 8, part == 9
    mu = np.average(X[tr], axis=0, weights=w[tr])
    sd = np.sqrt(np.average((X[tr] - mu) ** 2, axis=0, weights=w[tr])) + 1e-6
    Z = np.clip((X - mu) / sd, -6, 6)
    print('samples: train %d / val %d / test %d   fights: %d' % (tr.sum(), va.sum(), te.sum(), len(set(fid.tolist()))))

    res = {}
    ix = names.index
    feats = {'hpdiff': None, 'hp4': [ix('me_hp'), ix('op_hp'), ix('me_hpfrac'), ix('op_hpfrac')]}
    hd = (X[:, ix('me_hpfrac')] - X[:, ix('op_hpfrac')])[:, None]
    hdz = (hd - hd[tr].mean()) / (hd[tr].std() + 1e-6)
    Wl, bl = train_logistic(hdz[tr], y[tr], w[tr], hdz[va], y[va], w[va]); res['hpdiff'] = sig(hdz @ Wl + bl)
    c = feats['hp4']; Wl, bl = train_logistic(Z[tr][:, c], y[tr], w[tr], Z[va][:, c], y[va], w[va]); res['hp4'] = sig(Z[:, c] @ Wl + bl)
    Wl, bl = train_logistic(Z[tr], y[tr], w[tr], Z[va], y[va], w[va]); res['linear'] = sig(Z @ Wl + bl)
    lin_w = Wl
    print('  training mlp ...', flush=True)
    P = train_mlp(Z[tr], y[tr], w[tr], Z[va], y[va], w[va]); res['mlp'] = mlp_forward(Z, P)[0]

    buckets = [('T1-2', turn <= 2), ('T3-5', (turn >= 3) & (turn <= 5)), ('T6-10', (turn >= 6) & (turn <= 10)), ('T11+', turn >= 11)]
    print('\nTEST (fight-weighted)       logloss  brier   AUC    acc   | AUC by turn: ' + '  '.join(b for b, _ in buckets))
    for k in ('hpdiff', 'hp4', 'linear', 'mlp'):
        ll, br, auc, acc = metrics(res[k][te], y[te], w[te])
        by = [metrics(res[k][te & m], y[te & m], w[te & m])[2] if (te & m).sum() > 50 else float('nan') for _, m in buckets]
        print('  %-8s                   %.4f  %.4f  %.3f  %.3f |  %s' % (k, ll, br, auc, acc, '  '.join('%.3f' % v for v in by)))
    ll0 = metrics(np.full(te.sum(), 0.5), y[te], w[te])[0]
    print('  constant 0.5 logloss %.4f' % ll0)
    top = np.argsort(-np.abs(lin_w))[:15]
    print('\nlinear model, largest standardized weights:')
    for i in top:
        print('  %-22s %+.3f' % (names[i], lin_w[i]))

    json.dump({'names': names, 'mu': mu.tolist(), 'sd': sd.tolist(), 'clip': 6,
               'layers': [[p.tolist() for p in P[i:i + 2]] for i in (0, 2, 4)], 'act': 'tanh', 'out': 'sigmoid'},
              open(OUT, 'w'))
    print('\nexported %s' % OUT)


if __name__ == '__main__':
    main()
