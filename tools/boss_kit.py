#!/usr/bin/env python3
"""Swap the main leeks between their ladder setup and the Fennel boss setup.

    python3 tools/boss_kit.py snapshot           # save chips + AI path of each leek
    python3 tools/boss_kit.py apply  [--dry-run] # boss chips + 10.0/BOSS/fennel.lk
    python3 tools/boss_kit.py restore [--dry-run]# back to the snapshot

The snapshot lives in data/ladder/boss_kit_snapshot.json; apply refuses to run
without one, restore puts back exactly the snapshot's chips (by template) and AI.
Weapons are not touched.
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession

LEEKS = {'AdaLovelace': 20443, 'EdsgerDijkstra': 129288, 'KurtGodel': 129295, 'MargaretHamilton': 129296}
SNAP = os.path.join(ROOT, 'data', 'ladder', 'boss_kit_snapshot.json')
BOSS_AI = '10.0/BOSS/fennel.lk'
KIT = ['resurrection', 'spark', 'teleportation', 'adrenaline', 'rage', 'seven_league_boots', 'fortress', 'wall',
       'armor', 'solidification', 'regeneration', 'remission', 'knowledge', 'elevation', 'liberation', 'antidote', 'serum',
       'rampart', 'protein', 'steroid']
EXTRA = {'MargaretHamilton': ['plague', 'arsenic', 'toxin', 'covid', 'venom', 'fracture']}   # damage for phase 2


def call(lw, method, path, **data):
    for _ in range(6):
        r = lw.call(method, path, **data)
        if isinstance(r, dict) and r.get('error') == 'rate_limit':
            time.sleep(1.2); continue
        return r
    return r


def names(lw):
    I = lw.get('/item/get-all')
    return {int(k): v['name'].replace('chip_', '') for k, v in I.items() if v['name'].startswith('chip_')}


def inventory(lw, nm):
    f = lw.get('/farmer/get-from-token'); f = f.get('farmer', f)
    return {nm.get(x['template']): x for x in f['chips'] if x.get('quantity', 0) > 0}


def set_chips(lw, lid, want_templates, nm, dry):
    l = lw.leek(lid)
    have = {c['template']: c['id'] for c in l['chips']}
    remove = [t for t in have if t not in want_templates]
    add = [t for t in want_templates if t not in have]
    print('  %s: remove %s' % (l['name'], [nm.get(t, t) for t in remove]))
    print('  %s: add    %s' % (l['name'], [nm.get(t, t) for t in add]))
    if dry:
        return
    for t in remove:
        r = call(lw, 'DELETE', '/leek/remove-chip', leek_id=lid, chip_id=have[t])
        if isinstance(r, dict) and r.get('error'):
            print('    remove %s failed: %s' % (nm.get(t, t), r))
    for t in add:
        inv = inventory(lw, nm).get(nm.get(t))
        if not inv:
            print('    add %s: none in inventory' % nm.get(t, t)); continue
        r = call(lw, 'POST', '/leek/add-chip', leek_id=lid, chip_id=inv['id'])
        if isinstance(r, dict) and r.get('error'):
            print('    add %s failed: %s' % (nm.get(t, t), r))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['snapshot', 'apply', 'restore'])
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    lw = LWSession('main'); nm = names(lw); rev = {v: k for k, v in nm.items()}
    if a.action == 'snapshot':
        snap = {}
        for n, lid in LEEKS.items():
            l = lw.leek(lid)
            snap[n] = {'ai_path': (l.get('ai') or {}).get('path'), 'chips': [c['template'] for c in l['chips']]}
            print(n, snap[n]['ai_path'], [nm.get(t) for t in snap[n]['chips']])
        if os.path.exists(SNAP) and not a.dry_run:
            sys.exit('snapshot exists (%s): restore first or delete it' % SNAP)
        if not a.dry_run:
            json.dump(snap, open(SNAP, 'w'), indent=1)
        return
    if not os.path.exists(SNAP):
        sys.exit('no snapshot: run snapshot first')
    snap = json.load(open(SNAP))
    for n, lid in LEEKS.items():
        l = lw.leek(lid)
        if a.action == 'apply':
            want = [rev[k] for k in KIT][:l['max_chips']]
            for k in EXTRA.get(n, []):
                if len(want) < l['max_chips'] and rev[k] not in want:
                    want.append(rev[k])
            ai = BOSS_AI
        else:
            want = snap[n]['chips']; ai = snap[n]['ai_path']
        set_chips(lw, lid, want, nm, a.dry_run)
        if not a.dry_run:
            r = call(lw, 'POST', '/leek/set-ai', leek_id=lid, ai_path=ai)
            got = sorted(c['template'] for c in lw.leek(lid)['chips'])
            miss = [nm.get(t) for t in want if t not in got]
            print('  %s: ai -> %s (%s)  missing %s' % (n, (lw.leek(lid).get('ai') or {}).get('path'), r if r != {} else 'ok', miss or 'none'))
    if a.action == 'restore' and not a.dry_run:
        os.rename(SNAP, SNAP + '.restored-%d' % int(time.time()))


if __name__ == '__main__':
    main()
