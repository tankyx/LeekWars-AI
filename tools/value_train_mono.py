#!/usr/bin/env python3
"""Sign-constrained value model (2026-09-28).

v0 (tools/value_train.py) predicts well but is correlational: an opponent
STR shackle came out NEGATIVE, so search would avoid fracture. Here every
actionable feature x_k (HP, effects on either side, summons, max HP) enters
the logit as

    logit = base(ctx) + sum_k  s_k * softplus(h_k(ctx)) * z_k

with a fixed sign s_k (+ good for me, - bad) and a context-dependent,
always-positive slope. ctx = non-actionable features only (turn, distance,
LoS, levels, TP/MP, stats), so no actionable feature can reach the
unconstrained part: monotone by construction, but a shackle can still be
worth more against the build it hurts.

    python3 tools/value_train_mono.py
Writes data/prod/value_mono.json and prints test metrics + exchange rates.
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from value_train import metrics, Adam, sig

DS = os.path.join(ROOT, 'data', 'prod', 'value_ds.npz')
OUT = os.path.join(ROOT, 'data', 'prod', 'value_mono.json')
rng = np.random.default_rng(0)

CTX_BASE = ['turn', 'dist', 'los']
CTX_SIDE = ['level', 'tp', 'mp', 'str', 'mag', 'agi', 'res', 'wis', 'sci', 'wrange', 'kdmg', 'knova', 'kpois', 'reach']
# sign for "me" side; the "op" side gets the opposite sign
GOOD_FOR_OWNER = {'burned': -1, 'hp': +1, 'hpfrac': +1, 'maxhp': +1, 'summons': +1,
                  'eff_abs_shield': +1, 'eff_rel_shield': +1, 'eff_heal_ot': +1, 'eff_dmg_return': +1,
                  'eff_buf_str': +1, 'eff_buf_mag': +1, 'eff_buf_agi': +1, 'eff_buf_tp': +1, 'eff_buf_mp': +1,
                  'eff_buf_res': +1, 'eff_buf_wis': +1, 'eff_buf_pow': +1,
                  'eff_poison': -1, 'poison_future': -1, 'eff_shk_str': -1, 'eff_shk_mag': -1, 'eff_shk_tp': -1,
                  'eff_shk_mp': -1, 'eff_shk_agi': -1, 'eff_vuln': -1, 'eff_vuln_abs': -1}


def split_features(names):
    ctx = [n for n in names if n in CTX_BASE or n.split('_', 1)[1] in CTX_SIDE]
    mono, sign = [], []
    for n in names:
        if n in ctx:
            continue
        side, key = n.split('_', 1)
        if key not in GOOD_FOR_OWNER:
            raise SystemExit('feature %s has no sign' % n)
        mono.append(n); sign.append(GOOD_FOR_OWNER[key] * (1 if side == 'me' else -1))
    return ctx, mono, np.array(sign, dtype=float)


def softplus(x):
    return np.logaddexp(0, x)


def forward(C, M, P, S):
    W1, b1, W2, b2, W3, b3 = P
    h1 = np.tanh(C @ W1 + b1); h2 = np.tanh(h1 @ W2 + b2); o = h2 @ W3 + b3
    base = o[:, 0]; pre = o[:, 1:]; slope = softplus(pre)
    logit = base + np.sum(S * slope * M, axis=1)
    return sig(logit), (h1, h2, pre, slope)


def train(C, M, S, y, w, Cv, Mv, yv, wv, h=(32, 24), l2=1e-5, epochs=60, patience=6):
    K = M.shape[1]; d = C.shape[1]
    P = [rng.normal(0, 1 / np.sqrt(d), (d, h[0])), np.zeros(h[0]),
         rng.normal(0, 1 / np.sqrt(h[0]), (h[0], h[1])), np.zeros(h[1]),
         rng.normal(0, 0.1 / np.sqrt(h[1]), (h[1], 1 + K)), np.concatenate([[0.0], np.full(K, -2.0)])]
    opt = Adam(P, lr=2e-3)
    best = (1e9, [p.copy() for p in P]); bad = 0
    for ep in range(epochs):
        idx = rng.permutation(len(C))
        for s in range(0, len(C), 1024):
            j = idx[s:s + 1024]
            cb, mb = C[j], M[j]
            p, (h1, h2, pre, slope) = forward(cb, mb, P, S)
            g = w[j] * (p - y[j]) / w[j].sum()                     # dL/dlogit
            go = np.empty((len(j), 1 + K))
            go[:, 0] = g
            go[:, 1:] = g[:, None] * S * mb * sig(pre)             # softplus' = sigmoid
            gW3 = h2.T @ go; gb3 = go.sum(0)
            d2 = (go @ P[4].T) * (1 - h2 ** 2)
            gW2 = h1.T @ d2; gb2 = d2.sum(0)
            d1 = (d2 @ P[2].T) * (1 - h1 ** 2)
            gW1 = cb.T @ d1; gb1 = d1.sum(0)
            opt.step([gW1 + l2 * P[0], gb1, gW2 + l2 * P[2], gb2, gW3 + l2 * P[4], gb3])
        vl = metrics(forward(Cv, Mv, P, S)[0], yv, wv)[0]
        if vl < best[0] - 1e-5:
            best = (vl, [p.copy() for p in P]); bad = 0
        else:
            bad += 1
            if bad >= patience:
                break
        print('    epoch %d  val logloss %.4f' % (ep, vl), flush=True)
    return best[1]


def main():
    d = np.load(DS)
    X, y, w, fid, turn = d['X'].astype(np.float64), d['y'].astype(np.float64), d['w'].astype(np.float64), d['fid'], d['turn']
    names = [str(n) for n in d['names']]
    ctx, mono, S = split_features(names)
    ci = [names.index(n) for n in ctx]; mi = [names.index(n) for n in mono]
    part = fid % 10; tr, va, te = part < 8, part == 8, part == 9
    mu = np.average(X[tr], axis=0, weights=w[tr])
    sd = np.sqrt(np.average((X[tr] - mu) ** 2, axis=0, weights=w[tr])) + 1e-6
    Z = np.clip((X - mu) / sd, -6, 6)
    C, M = Z[:, ci], Z[:, mi]
    print('context %d features, monotone %d features' % (len(ctx), len(mono)))
    P = train(C[tr], M[tr], S, y[tr], w[tr], C[va], M[va], y[va], w[va])
    p = forward(C, M, P, S)[0]
    buckets = [('T1-2', turn <= 2), ('T3-5', (turn >= 3) & (turn <= 5)), ('T6-10', (turn >= 6) & (turn <= 10)), ('T11+', turn >= 11)]
    ll, br, auc, acc = metrics(p[te], y[te], w[te])
    by = [metrics(p[te & m], y[te & m], w[te & m])[2] for _, m in buckets]
    print('\nTEST mono: logloss %.4f  brier %.4f  AUC %.3f  acc %.3f | AUC by turn %s' % (
        ll, br, auc, acc, '  '.join('%.3f' % v for v in by)))

    # exchange rates on test states T3-15
    sel = te & (turn >= 3) & (turn <= 15)
    Xs = X[sel][rng.choice(sel.sum(), min(20000, sel.sum()), replace=False)]
    ix = names.index

    def f(Xr):
        Zr = np.clip((Xr - mu) / sd, -6, 6)
        return forward(Zr[:, ci], Zr[:, mi], P, S)[0]
    p0 = f(Xs)

    def rate(desc, fn):
        Y = Xs.copy(); fn(Y); dp = f(Y) - p0
        print('  %-44s %+6.2f pp' % (desc, 100 * dp.mean()))

    def dmg(side, amt):
        def g(Y):
            hp = Y[:, ix(side + '_hp')] * 3000
            base = (Y[:, ix(side + '_maxhp')] + Y[:, ix(side + '_burned')]) * 3000   # max before attrition
            hp2 = np.maximum(0, hp - amt)
            Y[:, ix(side + '_hp')] = hp2 / 3000; Y[:, ix(side + '_hpfrac')] = hp2 / np.maximum(1, base)
        return g

    def add(*kv):
        def g(Y):
            for k, v in kv:
                Y[:, ix(k)] += v
        return g
    print('\nexchange rates (mean over test states T3-15):')
    rate('deal 300 direct', dmg('op', 300))
    rate('take 300', dmg('me', 300))
    rate('opponent poison 300/turn, 600 queued', add(('op_eff_poison', 1.0), ('op_poison_future', 0.6)))
    rate('opponent STR -150', add(('op_eff_shk_str', 1.5)))
    rate('opponent TP -3', add(('op_eff_shk_tp', 1.0)))
    rate('opponent MP -2', add(('op_eff_shk_mp', 1.0)))
    rate('my relative shield +15%', add(('me_eff_rel_shield', 0.5)))
    rate('my absolute shield +150', add(('me_eff_abs_shield', 1.0)))
    rate('my STR buff +150', add(('me_eff_buf_str', 1.5)))
    rate('+1 summon for me', add(('me_summons', 0.5)))
    rate('distance +4 cells', add(('dist', 0.2)))

    def nova(amt):
        def g(Y):
            Y[:, ix('op_maxhp')] -= amt / 3000.0
            Y[:, ix('op_burned')] += amt / 3000.0
        return g
    rate('nova: burn 450 of opponent max HP', nova(450))
    rate('opponent can no longer reach me', lambda Y: Y.__setitem__((slice(None), ix('op_reach')), 0.0))
    rate('I can reach the opponent next turn', lambda Y: Y.__setitem__((slice(None), ix('me_reach')), 1.0))

    json.dump({'kind': 'mono', 'names': names, 'ctx': ctx, 'mono': mono, 'sign': S.tolist(),
               'mu': mu.tolist(), 'sd': sd.tolist(), 'clip': 6,
               'layers': [[q.tolist() for q in P[i:i + 2]] for i in (0, 2, 4)]}, open(OUT, 'w'))
    print('\nexported %s' % OUT)


if __name__ == '__main__':
    main()
