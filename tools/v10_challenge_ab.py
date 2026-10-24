#!/usr/bin/env python3
"""Paired A/B of two server AI paths on seeded challenges against real
opponents (their real AIs). Challenges do not move talent.

    python3 tools/v10_challenge_ab.py --leek 129295 --opps 105863,81204 --seeds 4 \
        --a 10.0/V10/v10.py --b 10.0/V10/v10_test.py

For each arm the leek is switched to that AI path, every (opponent, seed)
challenge is started, then the leek goes back to the AI it had before. Pairs
share opponent and seed, so the discordant pairs compare the two AIs.
"""
import argparse, json, math, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lw_api import LWSession


def post(lw, path, data):
    for _ in range(8):
        try:
            r = lw.s.post('https://leekwars.com/api' + path, data=data, timeout=30).json()
        except Exception as ex:          # 2026-10-24: an untimed request hung the run for 9.5 h
            r = {'error': 'request_failed: %s' % ex}
            time.sleep(3)
            continue
        if isinstance(r, dict) and r.get('error') == 'rate_limit':
            time.sleep(1.5)
            continue
        return r
    return r


def hp_lead(lw, fid, lid):
    """Our end HP fraction minus the opponent main leek's (from the action stream), None if unreadable."""
    try:
        f = lw.get('/fight/get/%d' % fid); f = f.get('fight', f); d = f['data']
        d = json.loads(d) if isinstance(d, str) else d
        life = {e['id']: e.get('life') or 0 for e in d['leeks']}; mx = dict(life)
        for x in d['actions']:
            if x[0] in (101, 107, 108, 110) and len(x) > 2 and x[1] in life:
                life[x[1]] -= x[2]
            elif x[0] == 103 and len(x) > 2 and x[1] in life:
                life[x[1]] = min(mx[x[1]], life[x[1]] + x[2])
            elif x[0] == 5 and x[1] in life:
                life[x[1]] = 0
        team = next(l for l in (f.get('leeks1') or []) + (f.get('leeks2') or []) if l['id'] == lid)
        mine = 1 if any(l['id'] == lid for l in f.get('leeks1') or []) else 2
        me = next(e for e in d['leeks'] if e.get('team') == mine and not e.get('summon') and e['name'] == team['name'])
        op = next(e for e in d['leeks'] if e.get('team') != mine and not e.get('summon'))
        return max(0, life[me['id']]) / max(1, mx[me['id']]) - max(0, life[op['id']]) / max(1, mx[op['id']])
    except Exception:
        return None


def leek_ai(lw, lid):
    l = lw.get('/leek/get/%d' % lid); l = l.get('leek', l)
    return l['ai']['path'] if l.get('ai') else None


def result(lw, fid, lid):
    """1 win, 0.5 draw, 0 loss, None if not finished / unknown."""
    f = lw.get('/fight/get/%d' % fid)
    f = f.get('fight', f) if isinstance(f, dict) else {}
    if f.get('status') != 2:
        return None
    team = 1 if any(l['id'] == lid for l in f.get('leeks1') or []) else 2
    w = f.get('winner')
    return 1.0 if w == team else (0.5 if w == 0 else 0.0)


def sign_p(k, n):
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(0, min(k, n - k) + 1)) / 2 ** n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--leek', type=int, required=True)
    ap.add_argument('--opps', required=True, help='comma list of opponent leek ids')
    ap.add_argument('--seeds', type=int, default=4)
    ap.add_argument('--a', required=True); ap.add_argument('--b', required=True)
    ap.add_argument('--account', default='main')
    ap.add_argument('--interleave', action='store_true', help='A then B per (opponent, seed): pairs stay complete if the challenge allowance runs out')
    a = ap.parse_args()
    lw = LWSession(a.account)
    orig = leek_ai(lw, a.leek)
    opps = [int(x) for x in a.opps.split(',')]
    fights = {}; res = {}
    try:
        if a.interleave:
            stop = False
            for o in opps:
                for s in range(1, a.seeds + 1):
                    for arm, path in (('A', a.a), ('B', a.b)):
                        post(lw, '/leek/set-ai', {'leek_id': a.leek, 'ai_path': path})
                        r = post(lw, '/garden/start-solo-challenge', {'leek_id': a.leek, 'target_id': o, 'seed': s, 'side': 0})
                        fid = r if isinstance(r, int) else (r.get('fight') if isinstance(r, dict) else None)
                        if not fid:
                            print('  %s opp %d seed %d: %s' % (arm, o, s, str(r)[:120]), flush=True)
                            stop = 'not_enought' in str(r)
                            break
                        fights[(arm, o, s)] = fid
                        for _ in range(60):
                            rr = result(lw, fid, a.leek)
                            if rr is not None:
                                res[(arm, o, s)] = rr
                                break
                            time.sleep(3)
                    if stop:
                        break
                if stop:
                    break
            print('%d challenges played' % len(fights), flush=True)
        for arm, path in (() if a.interleave else (('A', a.a), ('B', a.b))):
            post(lw, '/leek/set-ai', {'leek_id': a.leek, 'ai_path': path})
            if leek_ai(lw, a.leek) != path:
                sys.exit('could not set %s' % path)
            for o in opps:
                for s in range(1, a.seeds + 1):
                    r = post(lw, '/garden/start-solo-challenge', {'leek_id': a.leek, 'target_id': o, 'seed': s, 'side': 0})
                    fid = r if isinstance(r, int) else (r.get('fight') if isinstance(r, dict) else None)
                    if not fid:
                        print('  %s opp %d seed %d: %s' % (arm, o, s, str(r)[:120]), flush=True)
                        continue
                    fights[(arm, o, s)] = fid
            print('%s (%s): %d challenges started' % (arm, path, sum(1 for k in fights if k[0] == arm)), flush=True)
            # the fights must be generated with this arm's AI before switching
            for k, fid in [(k, f) for k, f in fights.items() if k[0] == arm]:
                for _ in range(60):
                    r = result(lw, fid, a.leek)
                    if r is not None:
                        res[k] = r
                        break
                    time.sleep(3)
    finally:
        post(lw, '/leek/set-ai', {'leek_id': a.leek, 'ai_path': orig})
        print('leek back on %s' % leek_ai(lw, a.leek), flush=True)
    for k, fid in fights.items():
        if k in res:
            continue
        for _ in range(30):
            r = result(lw, fid, a.leek)
            if r is not None:
                res[k] = r
                break
            time.sleep(4)
    pairs = [(o, s, res.get(('A', o, s)), res.get(('B', o, s))) for o in opps for s in range(1, a.seeds + 1)]
    # paired end-of-fight HP lead (our HP fraction - theirs): every pair carries information, not only the
    # ~10% whose result flips (2026-10-24: 5 discordant pairs of 50 per A/B, too few to see a few points)
    leads = []
    for o in opps:
        for s in range(1, a.seeds + 1):
            fa, fb = fights.get(('A', o, s)), fights.get(('B', o, s))
            if fa and fb:
                la, lb = hp_lead(lw, fa, a.leek), hp_lead(lw, fb, a.leek)
                if la is not None and lb is not None:
                    leads.append(lb - la)
    ok = [p for p in pairs if p[2] is not None and p[3] is not None]
    print('\n%d pairs' % len(ok))
    for o in opps:
        sub = [p for p in ok if p[0] == o]
        print('  opp %-7d A %.1f  B %.1f  / %d' % (o, sum(p[2] for p in sub), sum(p[3] for p in sub), len(sub)))
    bw = sum(1 for p in ok if p[3] > p[2]); aw = sum(1 for p in ok if p[2] > p[3])
    print('A %s: %.1f   B %s: %.1f   discordant B better %d / A better %d   sign p = %.3f' % (
        a.a, sum(p[2] for p in ok), a.b, sum(p[3] for p in ok), bw, aw, sign_p(bw, bw + aw)))
    if len(leads) > 2:
        m = sum(leads) / len(leads); sd = math.sqrt(sum((x - m) ** 2 for x in leads) / (len(leads) - 1)) or 1e-9
        print('HP lead B - A over %d pairs: %+.3f (sd %.3f, t %.2f); B better %d, A better %d' % (
            len(leads), m, sd, m / (sd / math.sqrt(len(leads))), sum(1 for x in leads if x > 0.01), sum(1 for x in leads if x < -0.01)))


if __name__ == '__main__':
    main()
