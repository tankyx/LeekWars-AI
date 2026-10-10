#!/usr/bin/env python3
"""Paired challenge A/B of one chip slot on one leek: arm A with chip A equipped, arm B with
chip B, same opponent / seed / side for both arms (seeded challenges do not move talent).
Opponents = real leeks the leek met in the garden, talent within +-band of its own.
Pairs alternate the arm order (AB, BA, ...) so one chip swap serves each pair. Stops at the
daily challenge allowance. The leek's chip and AI path are restored at the end.

    python3 tools/chip_ab.py --leek 129296 --a chip_superinfection --b chip_jump --ai 10.0/probe/v10_fix.py --pairs 40
"""
import argparse, csv, json, math, os, random, sqlite3, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from lw_api import LWSession
OUT = os.path.join(ROOT, 'data', 'ladder', 'chip_ab.csv')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--leek', type=int, required=True)
    ap.add_argument('--a', required=True); ap.add_argument('--b', required=True)
    ap.add_argument('--ai', default=None, help='AI path for both arms (restored after)')
    ap.add_argument('--ai-a', default=None, help='AI path for arm A only'); ap.add_argument('--ai-b', default=None, help='AI path for arm B only')
    ap.add_argument('--skip', type=int, default=0, help='skip the first N opponents (resume)')
    ap.add_argument('--pairs', type=int, default=40); ap.add_argument('--band', type=int, default=150)
    ap.add_argument('--account', default='main'); ap.add_argument('--seed', type=int, default=7)
    a = ap.parse_args()
    lw = LWSession(a.account); I = lw.get('/item/get-all'); nm = lambda t: I.get(str(t), {}).get('name', t)
    rng = random.Random(a.seed)
    me = lw.leek(a.leek); talent = me['talent']; ai0 = me['ai']['path']
    db = sqlite3.connect(os.path.join(HERE, 'fight_history_%d.db' % a.leek))
    ids = [r[0] for r in db.execute('SELECT DISTINCT opponent_id FROM fight_history ORDER BY timestamp DESC LIMIT 400')]
    rng.shuffle(ids); opps = []
    for oid in ids:
        if len(opps) >= a.pairs: break
        o = lw.leek(oid)
        if o.get('id') and abs((o.get('talent') or 0) - talent) <= a.band and (o.get('level') or 0) >= 290:
            opps.append({'id': oid, 'name': o.get('name'), 'talent': o.get('talent')})
    print('%s (talent %d): %d opponents within +-%d' % (me['name'], talent, len(opps), a.band), flush=True)

    def chip_inv(name):
        f = lw.get('/farmer/get-from-token'); f = f.get('farmer', f)
        return next(x['id'] for x in f.get('chips') or [] if nm(x['template']) == name)

    def set_ai(arm):
        path = (a.ai_a if arm == 'A' else a.ai_b) or a.ai
        if path: lw.post('/leek/set-ai', leek_id=a.leek, ai_path=path)

    def equip(want, other):
        l = lw.leek(a.leek)
        names = {nm(c['template']): c['id'] for c in l['chips']}
        if want in names: return
        if other in names:
            lw.call('DELETE', '/leek/remove-chip', leek_id=a.leek, chip_id=names[other])
        r = lw.post('/leek/add-chip', leek_id=a.leek, chip_id=chip_inv(want))
        if not (isinstance(r, dict) and r.get('id')):
            raise RuntimeError('could not equip %s: %s' % (want, r))

    def challenge(o, seed):
        r = lw.post('/garden/start-solo-challenge', leek_id=a.leek, target_id=o['id'], seed=seed, side=0)
        fid = r.get('fight') if isinstance(r, dict) else (r if isinstance(r, int) else None)
        if not fid:
            return None, str(r)
        for _ in range(120):
            f = lw.get('/fight/get/%d' % fid); f = f.get('fight', f)
            if f.get('status') == 2: break
            time.sleep(2)
        mine1 = any(l.get('id') == a.leek for l in f.get('leeks1') or [])
        w = f.get('winner'); res = 0.5 if w == 0 else (1.0 if w == (1 if mine1 else 2) else 0.0)
        s = json.dumps(lw.get('/fight/get-logs/%d' % fid))
        return (fid, res, s.count('too_much_ops'), s.count('superi')), None

    new = not os.path.exists(OUT); fh = open(OUT, 'a', newline=''); wr = csv.writer(fh)
    if new: wr.writerow(['date', 'leek', 'arm', 'chip', 'opp_id', 'opp_talent', 'seed', 'fight', 'result', 'cuts', 'si_logs'])
    res = {'A': [], 'B': []}; pairs = 0
    try:
        if a.ai: lw.post('/leek/set-ai', leek_id=a.leek, ai_path=a.ai)
        for i, o in enumerate(opps):
            if i < a.skip: continue
            seed = 1000 + i
            order = ('A', 'B') if i % 2 == 0 else ('B', 'A')
            got = {}
            for arm in order:
                chip, other = (a.a, a.b) if arm == 'A' else (a.b, a.a)
                equip(chip, other); set_ai(arm)
                out, err = challenge(o, seed)
                if out is None:
                    print('stop: %s' % err[:120], flush=True); raise StopIteration
                got[arm] = out
                wr.writerow([time.strftime('%Y-%m-%d %H:%M'), me['name'], arm, chip, o['id'], o['talent'], seed] + list(out)); fh.flush()
            res['A'].append(got['A'][1]); res['B'].append(got['B'][1]); pairs += 1
            print('pair %2d vs %-16s (%s): A %s  B %s   cuts %d/%d' % (pairs, o['name'][:16], o['talent'], got['A'][1], got['B'][1], got['A'][2], got['B'][2]), flush=True)
    except StopIteration:
        pass
    finally:
        try:
            equip(a.a, a.b)        # leave arm A's chip equipped (the deployed kit)
        except Exception as ex:
            print('restore chip failed: %s' % ex, flush=True)
        lw.post('/leek/set-ai', leek_id=a.leek, ai_path=ai0)
        print('restored %s + AI %s' % (a.a, ai0), flush=True)
    A, B = res['A'], res['B']
    if pairs:
        better = sum(1 for x, y in zip(A, B) if x > y); worse = sum(1 for x, y in zip(A, B) if x < y)
        n = better + worse
        p = min(1.0, 2 * sum(math.comb(n, k) for k in range(0, min(better, worse) + 1)) / 2 ** n) if n else 1.0
        print('%d pairs: A (%s) %.1f  vs  B (%s) %.1f | discordant A better %d, B better %d, sign test p=%.3f' % (
            pairs, a.a, sum(A), a.b, sum(B), better, worse, p))


if __name__ == '__main__':
    main()
