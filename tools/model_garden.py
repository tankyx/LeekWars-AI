#!/usr/bin/env python3
"""Garden opponent selection by the prod value model (2026-09-29).

For every garden fight, score each offered opponent with the sign-constrained
value model (data/prod/value_mono.json) at the turn-1 state - full HP, no
effects, typical start distance (24 cells, no LoS), stats = /leek/get total_*,
kit = equipped weapons + damage chips - averaged over who acts first:
    p = (V(us to act) + 1 - V(them to act)) / 2
and fight the opponent with the highest p (offered opponents sit at nearly the
same talent, so max P(win) = max expected talent gain). The fights themselves
are played by whatever AI the leek is assigned (unchanged).

Logs every pick to data/ladder/model_garden_log.csv (date, leek, opponent,
opponent talent, p of the pick, p range of the offer, fight id, result) and
appends the talent rows to data/ladder/talent_log.csv like daily_garden.py.

    python3 tools/model_garden.py              # all credits, 4 main leeks
    python3 tools/model_garden.py --dry-run    # show the scored offers only
    python3 tools/model_garden.py --results    # fill in results + calibration
"""
import argparse, csv, datetime, json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession
import value_dataset as vd

MODEL = os.path.join(ROOT, 'data', 'prod', 'value_mono.json')
PICKS = os.path.join(ROOT, 'data', 'ladder', 'model_garden_log.csv')
TALENT = os.path.join(ROOT, 'data', 'ladder', 'talent_log.csv')
LEEKS = [('AdaLovelace', 20443), ('EdsgerDijkstra', 129288), ('KurtGodel', 129295), ('MargaretHamilton', 129296)]
GEN = '/home/ubuntu/leek-wars-generator/data'
W_ITEM = {v['item']: v['name'] for v in json.load(open(os.path.join(GEN, 'weapons.json'))).values()}
C_ID = {int(k): v['name'] for k, v in json.load(open(os.path.join(GEN, 'chips.json'))).items()}


class Model:
    def __init__(self):
        m = json.load(open(MODEL))
        self.names = m['names']
        assert self.names == vd.NAMES, 'value model / feature layout mismatch'
        self.mu, self.sd = np.array(m['mu']), np.array(m['sd'])
        self.ci = [self.names.index(n) for n in m['ctx']]
        self.mi = [self.names.index(n) for n in m['mono']]
        self.S = np.array(m['sign'])
        self.L = [(np.array(W), np.array(b)) for W, b in m['layers']]

    def __call__(self, x):
        z = np.clip((np.array(x) - self.mu) / self.sd, -6, 6)
        h = np.tanh(z[self.ci] @ self.L[0][0] + self.L[0][1])
        h = np.tanh(h @ self.L[1][0] + self.L[1][1])
        o = h @ self.L[2][0] + self.L[2][1]
        return float(1 / (1 + np.exp(-(o[0] + np.sum(self.S * np.logaddexp(0, o[1:]) * z[self.mi])))))


def profile(lw, lid, cache):
    if lid in cache:
        return cache[lid]
    l = lw.get('/leek/get/%d' % lid); l = l.get('leek', l)
    T = lambda k: l.get('total_' + k, l.get(k, 0)) or 0
    st = {'life': T('life'), 'tp': T('tp'), 'mp': T('mp'), 'strength': T('strength'), 'magic': T('magic'),
          'agility': T('agility'), 'resistance': T('resistance'), 'wisdom': T('wisdom'), 'science': T('science'),
          'level': l.get('level', 301), 'talent': l.get('talent'), 'name': l.get('name')}
    items = {W_ITEM.get(w['template']) for w in (l.get('weapons') or [])} | {C_ID.get(c['template']) for c in (l.get('chips') or [])}
    st['kit'] = vd.kit_stats({i for i in items if i}, st)
    cache[lid] = st
    return st


def side(st, dist):
    rng, kd, kn, kp = st['kit']
    x = [st['life'] / 3000.0, 1.0, st['life'] / 3000.0, st['level'] / 301.0, st['tp'] / 30.0, st['mp'] / 8.0]
    x += [st[s] / 600.0 for s in vd.STATS]
    x += [0.0] * len(vd.GROUPS)
    x += [0.0, 0.0]                                   # poison future, summons
    x += [0.0, rng / 10.0, kd / 1000.0, kn / 1000.0, kp / 1000.0, 1.0 if dist <= st['mp'] + rng else 0.0]
    return x


def predict(model, us, them, dist=24, los=0.0):
    a = model([1 / 30.0, dist / 20.0, los] + side(us, dist) + side(them, dist))
    b = model([1 / 30.0, dist / 20.0, los] + side(them, dist) + side(us, dist))
    return (a + 1 - b) / 2


def credits(lw):
    g = lw.get('/garden/get'); g = g.get('garden', g)
    return int(g.get('fights') or 0)


def run(a):
    lw = LWSession('main'); model = Model(); cache = {}
    from zoneinfo import ZoneInfo
    today = datetime.datetime.now(ZoneInfo('Europe/Paris')).date().isoformat()
    avail = credits(lw)
    per = {lid: avail // len(LEEKS) + (1 if k < avail % len(LEEKS) else 0) for k, (_, lid) in enumerate(LEEKS)}
    print('%s: %d credits, %s' % (today, avail, per), flush=True)
    new = not os.path.exists(PICKS)
    out = open(PICKS, 'a', newline=''); wr = csv.writer(out)
    if new:
        wr.writerow(['date', 'leek', 'opponent', 'opp_id', 'opp_talent', 'p_pick', 'p_min', 'p_max', 'n_offer', 'fight', 'result'])
    t0 = {}
    for name, lid in LEEKS:
        us = profile(lw, lid, {})
        t0[name] = us['talent']
        n = per[lid] if not a.dry_run else 1
        done = 0; tries = 0
        while done < n and tries < n * 3:
            tries += 1
            offer = (lw.get('/garden/get-leek-opponents/%d' % lid) or {}).get('opponents') or []
            if not offer:
                time.sleep(2); continue
            scored = sorted(((predict(model, us, profile(lw, o['id'], cache)), o) for o in offer), key=lambda t: -t[0])
            p, o = scored[0]
            ps = [s for s, _ in scored]
            if a.dry_run:
                print('  %-17s offer: %s' % (name, '  '.join('%s(%d) %.2f' % (x['name'], x.get('talent') or 0, s) for s, x in scored)))
                break
            r = lw.post('/garden/start-solo-fight', leek_id=lid, target_id=o['id'])
            fid = r.get('fight') if isinstance(r, dict) else None
            if not fid:
                print('  start failed', name, str(r)[:120], flush=True); time.sleep(3)
                if credits(lw) == 0:
                    break
                continue
            done += 1
            wr.writerow([today, name, o['name'], o['id'], o.get('talent'), '%.4f' % p, '%.4f' % min(ps), '%.4f' % max(ps), len(ps), fid, ''])
            out.flush()
            print('  %-17s #%d vs %-18s p=%.3f (offer %.3f-%.3f) fight %s' % (name, done, o['name'], p, min(ps), max(ps), fid), flush=True)
            time.sleep(1.0)
    out.close()
    if a.dry_run:
        return
    time.sleep(30)
    rows = []
    for name, lid in LEEKS:
        l = lw.get('/leek/get/%d' % lid); l = l.get('leek', l)
        print('  %-17s talent %s -> %s' % (name, t0[name], l.get('talent')), flush=True)
        rows.append([today, 'main', name, l.get('talent')])
    fill_results(lw)
    # talent rows (fight counts / W-L filled from the pick log)
    picks = [r for r in csv.DictReader(open(PICKS)) if r['date'] == today]
    with open(TALENT, 'a', newline='') as fh:
        w = csv.writer(fh)
        for d, acct, name, tal in rows:
            mine = [r for r in picks if r['leek'] == name]
            w.writerow([d, acct, name, tal, len(mine), sum(r['result'] == 'W' for r in mine),
                        sum(r['result'] == 'L' for r in mine), sum(r['result'] == 'D' for r in mine)])
    print('appended %d talent rows (selector = value model)' % len(rows), flush=True)


def fill_results(lw):
    rows = list(csv.DictReader(open(PICKS)))
    ids = {n: i for n, i in LEEKS}
    for r in rows:
        if r['result'] or not r['fight']:
            continue
        for _ in range(10):
            f = lw.get('/fight/get/%s' % r['fight']); f = f.get('fight', f)
            if isinstance(f, dict) and f.get('winner') is not None and f.get('status', 2) != 0:
                break
            time.sleep(3)
        side = 1 if any(x.get('id') == ids.get(r['leek']) for x in (f.get('leeks1') or [])) else 2
        r['result'] = 'D' if f.get('winner') == 0 else ('W' if f.get('winner') == side else 'L')
    with open(PICKS, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    done = [r for r in rows if r['result'] in 'WLD' and r['result']]
    if done:
        p = np.array([float(r['p_pick']) for r in done]); y = np.array([1.0 if r['result'] == 'W' else (0.5 if r['result'] == 'D' else 0.0) for r in done])
        print('calibration over %d model-picked fights: mean p %.3f, actual %.3f, Brier %.3f' % (len(done), p.mean(), y.mean(), np.mean((p - y) ** 2)))
        for lo, hi in ((0, .45), (.45, .55), (.55, 1.01)):
            m = (p >= lo) & (p < hi)
            if m.any():
                print('  p %.2f-%.2f: %d fights, mean p %.2f, won %.2f' % (lo, min(hi, 1), m.sum(), p[m].mean(), y[m].mean()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--results', action='store_true')
    a = ap.parse_args()
    if a.results:
        fill_results(LWSession('main'))
    else:
        run(a)


if __name__ == '__main__':
    main()
