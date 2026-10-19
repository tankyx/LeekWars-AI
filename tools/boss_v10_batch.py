#!/usr/bin/env python3
"""Run Fennel boss fights with the main squad on V10's boss mode and summarize each one: result, graal
death round, crystal resurrections, our deaths, army kills, damage to the army, AI errors. Fight data +
our AI logs are saved to data/boss_fights/v10_<fight>.json.

    python3 tools/boss_v10_batch.py 10            # 10 new fights, 2 in flight
    python3 tools/boss_v10_batch.py --ids 1,2,3   # re-analyze finished fights
"""
import argparse, collections, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession

# participant order = spawn slot (53581862): slot1 interior near the crystals, slot2 corridor front
LEEKS = [129296, 129295, 20443, 129288]
OURS = {129296: 'MH', 129295: 'KG', 20443: 'AL', 129288: 'ED'}
ARMY = ('fennel_scribe', 'fennel_knight', 'fennel_king', 'fennel_squire',
        'evil_pumpkin', 'hubbard', 'turban', 'warty', 'offspring')
OUT = os.path.join(ROOT, 'data', 'boss_fights')


def analyze(lw, fid, save=True):
    f = lw.get('/fight/get/%d' % fid); f = f.get('fight', f)
    if f.get('status') != 2:
        return None
    d = f.get('data') or {}
    if isinstance(d, str):
        d = json.loads(d)
    ents = {e['id']: e for e in d.get('leeks') or []}
    name = {k: e.get('name') or '' for k, e in ents.items()}
    by_name = {'Payou': 'MH', 'Zoulman': 'KG', 'Kirby54': 'AL', 'GTGabi': 'ED'}
    ours = {k: by_name.get(e.get('name'), (e.get('name') or '?')[:6]) for k, e in ents.items() if e.get('team') == 1 and e.get('type') == 0}
    cur = None; rnd = 0; graal = None; res = []; deaths = []; army_dead = []; bugs = collections.Counter()
    dmg = collections.Counter(); taken = collections.Counter(); crystal_deaths = 0
    for a in d.get('actions') or []:
        c = a[0]
        if c == 6:
            rnd = a[1]
        elif c == 7:
            cur = a[1]
        elif c == 1002:
            bugs[ours.get(cur, name.get(cur, '?'))] += 1
        elif c == 105 and len(a) > 2:
            res.append((rnd, ours.get(cur, '?'), name.get(a[2], '?')))
        elif c == 5 and len(a) > 1:
            n = name.get(a[1], '')
            if n == 'graal':
                graal = rnd
            elif a[1] in ours:
                deaths.append((rnd, ours[a[1]]))
            elif n in ARMY:
                army_dead.append((rnd, n.replace('fennel_', '')))
            elif 'crystal' in n:
                crystal_deaths += 1
        elif c in (101, 107, 108, 110) and len(a) > 2:
            tgt = a[1]
            if name.get(tgt, '') in ARMY and cur in ours:
                dmg[ours[cur]] += a[2]
            elif tgt in ours:
                taken[ours[tgt]] += a[2]
    logs = {}
    try:
        lg = lw.get('/fight/get-logs/%d' % fid)
        lines = []

        def walk(o):
            if isinstance(o, dict):
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
            elif isinstance(o, str) and ('BOSS' in o or 'rror' in o or 'Traceback' in o):
                lines.append(o)
        walk(lg)
        logs = {'raw': lg, 'boss_lines': lines}
    except Exception as ex:
        logs = {'error': str(ex)}
    if save:
        os.makedirs(OUT, exist_ok=True)
        json.dump({'fight': f, 'logs': logs}, open(os.path.join(OUT, 'v10_%d.json' % fid), 'w'))
    rez_c = [r for r in res if 'crystal' in r[2]]
    return {'fid': fid, 'win': f.get('winner') == 1, 'turns': rnd, 'graal': graal, 'crystal_rez': rez_c,
            'deaths': deaths, 'army_dead': army_dead, 'dmg': dict(dmg), 'taken': dict(taken), 'bugs': dict(bugs),
            'boss_lines': len(logs.get('boss_lines') or []),
            'errors': [l for l in logs.get('boss_lines') or [] if 'rror' in l or 'Traceback' in l][:3]}


def show(r):
    print('%d: %s T%d | graal %s | crystal rez %d %s | our deaths %s | army dead %s | dmg to army %s (total %d) | taken %s | 1002 %s | boss log %d%s' % (
        r['fid'], 'WIN ' if r['win'] else 'loss', r['turns'], 'T%d' % r['graal'] if r['graal'] else '-',
        len(r['crystal_rez']), [(t, w) for t, w, _ in r['crystal_rez']], r['deaths'], r['army_dead'], r['dmg'],
        sum(r['dmg'].values()), r['taken'], r['bugs'] or '-', r['boss_lines'],
        (' | errors %s' % r['errors']) if r['errors'] else ''), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('n', type=int, nargs='?', default=0)
    ap.add_argument('--ids', default='')
    ap.add_argument('--inflight', type=int, default=2)
    ap.add_argument('--boss', type=int, default=2, help='2 = Fennel King, 3 = Evil Pumpkin')
    a = ap.parse_args()
    lw = LWSession('main')
    done = []
    if a.ids:
        for fid in [int(x) for x in a.ids.split(',') if x]:
            r = analyze(lw, fid)
            if r:
                show(r); done.append(r)
    pend = []; started = 0; fails = 0
    while (started < a.n or pend) and fails < 10:
        while started < a.n and len(pend) < a.inflight:
            r = lw.post('/garden/start-boss-fight', boss_id=a.boss, participants=json.dumps(LEEKS))
            fid = r.get('fight') if isinstance(r, dict) else (r if isinstance(r, int) else None)
            if not fid:
                print('start failed: %s' % str(r)[:200], flush=True); fails += 1; time.sleep(5)
                if fails >= 3:
                    a.n = started
                break
            pend.append(fid); started += 1; fails = 0
            print('started %d (%d/%d)' % (fid, started, a.n), flush=True)
            time.sleep(2)
        time.sleep(10)
        for fid in list(pend):
            r = analyze(lw, fid)
            if r is not None:
                pend.remove(fid); show(r); done.append(r)
    if done:
        w = sum(1 for r in done if r['win']); g = [r['graal'] for r in done if r['graal']]
        print('== %d fights: %d wins, graal killed in %d (median T%s), avg crystal rez %.1f, avg dmg to army %d, 1002 in %d fights' % (
            len(done), w, len(g), sorted(g)[len(g) // 2] if g else '-', sum(len(r['crystal_rez']) for r in done) / len(done),
            sum(sum(r['dmg'].values()) for r in done) / len(done), sum(1 for r in done if r['bugs'])), flush=True)


if __name__ == '__main__':
    main()
