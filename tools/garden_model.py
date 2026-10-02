#!/usr/bin/env python3
"""Win-probability model for solo garden opponents.

Trained on our own garden fights (tools/fight_history_<leek>.db): each fight's JSON
(data/fight_cache, fetched when missing) gives both leeks' real stats and talent at
fight time. Logistic regression in numpy (no sklearn here):

  opponent profile: talent gap, level, life, STR/MAG/AGI/SCI/RES/WIS, TP/MP, frequency,
                    archetype flags (magic / agility / tank / science)
  our leek:         one-hot, and leek x archetype interactions (each leek has its own
                    good and bad matchups)
  history:          recency-weighted win rate vs this opponent before the fight, and how
                    many fights it rests on (0 when we never met)

    python3 tools/garden_model.py build            # fetch missing fights, fit, report, save
    python3 tools/garden_model.py build --since 2026-09-20 --account main

Saved to tools/garden_model.json; garden_fast.py loads it through `Model`.
"""
import argparse, json, math, os, sqlite3, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, 'data', 'fight_cache')
OUT = os.path.join(HERE, 'garden_model.json')
sys.path.insert(0, HERE)

ACCOUNTS = {'main': {'AdaLovelace': 20443, 'EdsgerDijkstra': 129288, 'KurtGodel': 129295, 'MargaretHamilton': 129296},
            'cure': {'LeekRain': 19703, 'DawnFall': 21175, 'DuskHope': 129801, 'ProdigalSon': 130236}}
WINDOW, DECAY = 10, 0.8
STATS = ('life', 'strength', 'magic', 'agility', 'science', 'resistance', 'wisdom', 'tp', 'mp', 'frequency')
SCALE = {'life': 1000.0, 'tp': 10.0, 'mp': 5.0}
ARCH = ('magic', 'agility', 'tank', 'science')


def archetype(s):
    st, mg, ag = s.get('strength', 0), s.get('magic', 0), s.get('agility', 0)
    return {'magic': float(mg > st + 100), 'agility': float(ag >= 400 and ag >= st - 100),
            'tank': float(s.get('resistance', 0) >= 300), 'science': float(s.get('science', 0) >= 300)}


def hist_feats(results):
    """(recency-weighted win rate - 0.5, log1p(count)) over the last WINDOW results, newest last."""
    if not results:
        return 0.0, 0.0
    ww = ws = 0.0; w = 1.0
    for r in reversed(results[-WINDOW:]):
        ww += w * (1.0 if r == 'WIN' else (0.5 if r == 'DRAW' else 0.0)); ws += w; w *= DECAY
    return ww / ws - 0.5, math.log1p(len(results))


def features(leek_names, me_name, me_talent, opp, hist):
    """opp: dict with talent, level and the STATS keys (real totals). hist: list of past results."""
    x = [1.0, (opp['talent'] - me_talent) / 100.0, (opp.get('level', 301) - 300) / 10.0]
    for k in STATS:
        x.append(opp.get(k, 0) / SCALE.get(k, 100.0))
    a = archetype(opp)
    x += [a[k] for k in ARCH]
    for n in leek_names:
        on = 1.0 if n == me_name else 0.0
        x.append(on)
        x += [on * a[k] for k in ARCH]
        x.append(on * (opp['talent'] - me_talent) / 100.0)
    h, c = hist_feats(hist)
    x += [h, c, h * c]
    return x


def names_of(leek_names):
    n = ['bias', 'talent_gap', 'level'] + list(STATS) + ['is_' + k for k in ARCH]
    for l in leek_names:
        n += [l] + ['%s_x_%s' % (l, k) for k in ARCH] + ['%s_x_gap' % l]
    return n + ['hist', 'hist_n', 'hist_x_n']


class Model:
    def __init__(self, path=OUT):
        d = json.load(open(path))
        self.w = np.array(d['w']); self.mu = np.array(d['mu']); self.sd = np.array(d['sd'])
        self.leeks = d['leeks']

    def p(self, me_name, me_talent, opp, hist):
        x = (np.array(features(self.leeks, me_name, me_talent, opp, hist)) - self.mu) / self.sd
        return float(1.0 / (1.0 + math.exp(-float(x @ self.w))))


def load_fight(lw, fid):
    p = os.path.join(CACHE, '%d.json' % fid)
    if os.path.exists(p):
        try:
            return json.load(open(p))
        except Exception:
            pass
    if lw is None:
        return None
    for _ in range(3):
        try:
            f = lw.get('/fight/get/%d' % fid)
            f = f.get('fight', f) if isinstance(f, dict) else None
            if f and f.get('status') == 2:
                json.dump(f, open(p, 'w'))
                return f
            return None
        except Exception:
            time.sleep(1)
    return None


def side_stats(f, lid):
    """(our talent, opponent dict) from a solo fight JSON, or None."""
    l1 = f.get('leeks1') or []; l2 = f.get('leeks2') or []
    mine1 = any(l['id'] == lid for l in l1)
    me = next((l for l in (l1 if mine1 else l2) if l['id'] == lid), None)
    op = ((l2 if mine1 else l1) or [None])[0]
    if not me or not op:
        return None
    data = (f.get('data') or {}).get('leeks') or []
    # fight data entities: match by name (fight entity ids are 0..n, not leek ids)
    od = next((e for e in data if e.get('name') == op.get('name') and not e.get('summon')), None)
    if not od:
        return None
    opp = {k: od.get(k, 0) or 0 for k in STATS}
    # pre-fight talents: the report's `talent` is the value BEFORE the fight (the
    # leeks1/leeks2 field is after it, i.e. +-gain: using either post value leaks the result)
    rep = f.get('report') or {}
    pre = {l.get('id'): l.get('talent') or 0 for l in (rep.get('leeks1') or []) + (rep.get('leeks2') or [])}
    if lid not in pre or op['id'] not in pre:
        return None
    opp['talent'] = pre[op['id']]; opp['level'] = op.get('level') or 301
    return pre[lid], opp


def fit(X, y, l2=1.0, iters=50):
    """L2 logistic regression by Newton's method (bias column unpenalised)."""
    w = np.zeros(X.shape[1]); R = np.eye(X.shape[1]) * l2; R[0, 0] = 0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(X @ w)))
        g = X.T @ (p - y) + R @ w
        H = (X * (p * (1 - p))[:, None]).T @ X + R
        step = np.linalg.solve(H, g); w -= step
        if np.abs(step).max() < 1e-6:
            break
    return w


def logloss(p, y):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def auc(p, y):
    o = np.argsort(p); r = np.empty(len(p)); r[o] = np.arange(1, len(p) + 1)
    n1 = y.sum(); n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / max(1, n1 * n0))


def build(a):
    from lw_api import LWSession
    leeks = ACCOUNTS[a.account]; names = list(leeks)
    lw = LWSession(a.account)
    rows = []; fetched = 0; missing = 0
    for n, lid in leeks.items():
        db = sqlite3.connect(os.path.join(HERE, 'fight_history_%d.db' % lid))
        hist = {}
        for fid, oid, res, ts in db.execute('SELECT fight_id, opponent_id, result, timestamp FROM fight_history ORDER BY timestamp'):
            h = hist.setdefault(oid, [])
            if ts >= a.since:
                had = os.path.exists(os.path.join(CACHE, '%d.json' % fid))
                f = load_fight(lw, fid)
                if not had and f is not None:
                    fetched += 1; time.sleep(0.11)
                s = side_stats(f, lid) if f else None
                if s is None:
                    missing += 1
                else:
                    rows.append((ts, n, s[0], s[1], list(h), 1.0 if res == 'WIN' else (0.5 if res == 'DRAW' else 0.0)))
            h.append(res)
        print('  %s: %d rows so far (fetched %d, missing %d)' % (n, len(rows), fetched, missing), flush=True)
    rows.sort(key=lambda r: r[0])
    X = np.array([features(names, r[1], r[2], r[3], r[4]) for r in rows]); y = np.array([r[5] for r in rows])
    y = (y >= 0.75).astype(float)             # draws count as non-wins
    mu = X.mean(0); sd = X.std(0); mu[0] = 0; sd[0] = 1; sd[sd < 1e-9] = 1
    Z = (X - mu) / sd
    cut = int(len(rows) * 0.75)
    hcols = [names_of(names).index(k) for k in ('hist', 'hist_n', 'hist_x_n')]
    nohist = [i for i in range(Z.shape[1]) if i not in hcols]
    print('\n%d fights (%s .. %s), win rate %.1f%%; test = last %d' % (len(rows), rows[0][0][:10], rows[-1][0][:10],
                                                                     100 * y.mean(), len(rows) - cut))
    base = np.full(len(rows) - cut, y[:cut].mean())
    # the current selector's categories, as probabilities learned on the train part
    def cat(r):
        h = r[4]
        if len(h) < 2:
            return 'unknown'
        e = hist_feats(h)[0] + 0.5
        return 'beatable' if e >= 0.7 else ('dangerous' if e <= 0.45 else 'even')
    cats = [cat(r) for r in rows]
    rate = {c: y[:cut][[i for i in range(cut) if cats[i] == c]].mean() for c in set(cats[:cut])}
    pc = np.array([rate.get(c, y[:cut].mean()) for c in cats[cut:]])
    for l2 in (1.0, 10.0, 30.0):
        w_all = fit(Z[:cut], y[:cut], l2); w_nh = fit(Z[:cut][:, nohist], y[:cut], l2)
        p_all = 1 / (1 + np.exp(-(Z[cut:] @ w_all))); p_nh = 1 / (1 + np.exp(-(Z[cut:][:, nohist] @ w_nh)))
        print('l2 %-5s  model+history  logloss %.4f auc %.3f | profile only %.4f auc %.3f' % (
            l2, logloss(p_all, y[cut:]), auc(p_all, y[cut:]), logloss(p_nh, y[cut:]), auc(p_nh, y[cut:])))
    print('          categories     logloss %.4f auc %.3f | constant %.4f' % (
        logloss(pc, y[cut:]), auc(pc, y[cut:]), logloss(base, y[cut:])))
    # unknown opponents only (where the current selector has nothing)
    unk = np.array([i - cut for i in range(cut, len(rows)) if cats[i] == 'unknown'])
    if len(unk):
        w_all = fit(Z[:cut], y[:cut], a.l2); p_all = 1 / (1 + np.exp(-(Z[cut:] @ w_all)))
        print('unknown opponents in test: %d, model auc %.3f' % (len(unk), auc(p_all[unk], y[cut:][unk])))
    w_cal = fit(Z[:cut], y[:cut], a.l2); p_cal = 1 / (1 + np.exp(-(Z[cut:] @ w_cal)))
    print('calibration (test):', '  '.join('%.1f-%.1f: n %d pred %.2f real %.2f' % (
        lo, lo + 0.2, m.sum(), p_cal[m].mean(), y[cut:][m].mean()) for lo in (0.0, 0.2, 0.4, 0.6, 0.8)
        for m in [(p_cal >= lo) & (p_cal < lo + 0.2)] if m.sum()))
    w = fit(Z, y, a.l2)
    json.dump({'w': w.tolist(), 'mu': mu.tolist(), 'sd': sd.tolist(), 'leeks': names, 'names': names_of(names),
               'n': len(rows), 'since': a.since, 'l2': a.l2}, open(OUT, 'w'), indent=1)
    top = sorted(zip(names_of(names), w), key=lambda t: -abs(t[1]))[:14]
    print('saved %s; strongest weights: %s' % (OUT, ', '.join('%s %+.2f' % t for t in top)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['build'])
    ap.add_argument('--account', default='main', choices=sorted(ACCOUNTS))
    ap.add_argument('--since', default='2026-09-20')
    ap.add_argument('--l2', type=float, default=10.0)
    a = ap.parse_args()
    build(a)


if __name__ == '__main__':
    main()
