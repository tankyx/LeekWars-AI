#!/usr/bin/env python3
"""Matchup-feature experiment for the garden model (2026-10-12, NOT adopted): compares the current
features with + strength archetype, + opponent kit main effects, + per-leek kit interactions on our
main-account garden fights (server-degraded 2026-10-07/08 window excluded). Result: no gain
(test AUC 0.629 / 0.629 / 0.630 / 0.620). Needs the kit-feature version of garden_model.py
(commit history) - kept for reference."""
import sys, os, sqlite3, json
sys.path.insert(0, '/home/ubuntu/LeekWars-AI/tools')
import numpy as np
import garden_model as gm
from lw_api import LWSession
leeks = gm.ACCOUNTS['main']; names = list(leeks)
lw = LWSession('main'); prof = gm.Profiles(); kits = {}
rows = []
DEGRADED = ('2026-10-07T17', '2026-10-08T12')     # server cut / crashed fights (prod Python OOM)
for n, lid in leeks.items():
    db = sqlite3.connect(os.path.join(gm.HERE, 'fight_history_%d.db' % lid)); hist = {}
    for fid, oid, res, ts in db.execute('SELECT fight_id, opponent_id, result, timestamp FROM fight_history ORDER BY timestamp'):
        h = hist.setdefault(oid, [])
        if ts >= '2026-09-21' and not (DEGRADED[0] <= ts < DEGRADED[1]):
            f = gm.load_fight(None, fid); s = gm.side_stats(f, lid) if f else None
            if s is not None:
                if oid not in kits:
                    kits[oid] = ((prof.get(oid, lw.get) or {}).get('kit') or {}) if oid else {}
                s[1]['kit'] = kits[oid]
                rows.append((ts, n, s[0], s[1], list(h), 1.0 if res == 'WIN' else 0.0))
        h.append(res)
rows.sort(key=lambda r: r[0]); y = np.array([r[5] for r in rows]); cut = int(len(rows) * 0.75)
def variant(kit_main, kit_inter, strength):
    def feats(r):
        n, me_t, opp, hist = r[1], r[2], r[3], r[4]
        x = [1.0, (opp['talent'] - me_t) / 100.0, (opp.get('level', 301) - 300) / 10.0]
        x += [opp.get(k, 0) / gm.SCALE.get(k, 100.0) for k in gm.STATS]
        a = gm.archetype(opp); arch = [k for k in gm.ARCH if strength or k != 'strength']
        kv = [float((opp.get('kit') or {}).get(k, 0.0)) for k in gm.KIT]
        x += [a[k] for k in arch] + (kv if kit_main else [])
        for l in names:
            on = 1.0 if l == n else 0.0
            x += [on] + [on * a[k] for k in arch] + ([on * v for v in kv] if kit_inter else []) + [on * (opp['talent'] - me_t) / 100.0]
        hh, c = gm.hist_feats(hist); x += [hh, c, hh * c]
        return x
    X = np.array([feats(r) for r in rows]); mu = X.mean(0); sd = X.std(0); mu[0] = 0; sd[0] = 1; sd[sd < 1e-9] = 1
    Z = (X - mu) / sd; w = gm.fit(Z[:cut], y[:cut], 10.0); p = 1 / (1 + np.exp(-(Z[cut:] @ w)))
    per = {}
    for l in names:
        idx = np.array([i - cut for i in range(cut, len(rows)) if rows[i][1] == l])
        per[l] = gm.auc(p[idx], y[cut:][idx])
    return gm.logloss(p, y[cut:]), gm.auc(p, y[cut:]), per
print('%d fights (degraded window excluded), test %d' % (len(rows), len(rows) - cut))
for lab, km, ki, st in (('baseline (old features)', 0, 0, 0), ('+ strength archetype', 0, 0, 1), ('+ kit main effects', 1, 0, 1),
                        ('+ kit main + per-leek kit', 1, 1, 1)):
    ll, au, per = variant(km, ki, st)
    print('%-28s logloss %.4f auc %.3f | %s' % (lab, ll, au, '  '.join('%s %.3f' % (k[:6], v) for k, v in per.items())))
