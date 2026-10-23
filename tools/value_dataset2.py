#!/usr/bin/env python3
"""Value-model dataset v2 (2026-10-23): v1's features (tools/value_dataset.NAMES, same order) + item readiness.

v1 sees each side's kit (best direct / nova / poison per turn) but not cooldowns, so V10's search cannot tell a
turn that burns the big chip from one that keeps it for the kill. v2 appends, per side, the same kit values over
the items READY for that side's next action (me: cooldown 0 now; opponent: cooldown <= 1, ready at the start of
its next turn - the convention V10 already uses for enemy chips), plus the best ready heal and shield:
    <side>_rdmg, <side>_rnova, <side>_rpois, <side>_rheal, <side>_rshield
Sources: the prod crawl (data/prod/fights, other players' 1v1 solo fights) and our own fights
(data/fight_cache, solo only), tagged in `src` (0 prod, 1 ours).

Chip ids in USE_CHIP actions are template ids in most logs but item ids in some periods (seen in Oct 2026
boss logs); effect actions (301/302) always carry the item id, so each fight's space is detected from the
first USE_CHIP followed by an effect.

    python3 tools/value_dataset2.py [--limit N] [--ours-only]
Writes data/prod/value_ds2.npz (X, y, hp_y, fid, turn, w, talent, context, src, date, names).
"""
import argparse, glob, gzip, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import value_dataset as v1
from value_dataset import D, GROUP, STATS, TELE, Geometry, kit_stats

OUT = os.path.join(ROOT, 'data', 'prod', 'value_ds2.npz')
CHIPS = json.load(open('/home/ubuntu/leek-wars-generator/data/chips.json'))
WEAPONS = json.load(open('/home/ubuntu/leek-wars-generator/data/weapons.json'))
ITEM_CHIP = {int(k): v['name'] for k, v in CHIPS.items()}                 # item id -> name
ITEM_TPL = {int(k): v['template'] for k, v in CHIPS.items()}               # item id -> template
ITEM_WEAPON = {v['item']: v['name'] for v in WEAPONS.values()}
NEW = ['rdmg', 'rnova', 'rpois', 'rheal', 'rshield']


def names():
    return list(v1.NAMES) + ['%s_%s' % (s, k) for s in ('me', 'op') for k in NEW]


NAMES = names()


def ready_stats(items, l, cd, owner, opp_side):
    """Ready kit (direct / nova / poison per turn, like kit_stats) + best ready heal and shield (HP-equivalent).
    Ready = cooldown 0 for the side about to act, <= 1 for the opponent (ready at its next turn)."""
    tp = max(1, l.get('tp', 20))
    stre, mag, sci = max(0, l.get('strength', 0)), max(0, l.get('magic', 0)), max(0, l.get('science', 0))
    wis, res = max(0, l.get('wisdom', 0)), max(0, l.get('resistance', 0))
    lim = 1 if opp_side else 0
    kd = kn = kp = heal = shield = 0.0
    for name in items:
        if cd.get((owner, name), 0) > lim:
            continue
        info = D.info(name) or {}
        effs = info.get('effects') or []
        cost = max(1, info.get('cost') or 1)
        mu = info.get('max_uses') or 0
        uses = min(mu, tp // cost) if mu > 0 else tp // cost
        if info.get('cooldown', 0) and info.get('cooldown') > 0:
            uses = min(uses, 1)
        dmg = sum((e['value1'] + e['value2'] / 2) for e in effs if e.get('id') == 1) * (1 + stre / 100.0)
        nova = sum((e['value1'] + e['value2'] / 2) for e in effs if e.get('id') == 30) * (1 + sci / 100.0)
        pois = sum((e['value1'] + e['value2'] / 2) * max(1, e.get('turns') or 1) for e in effs if e.get('id') == 13) * (1 + mag / 100.0)
        hl = sum((e['value1'] + e['value2'] / 2) * max(1, e.get('turns') or 1) for e in effs if e.get('id') == 2) * (1 + wis / 100.0)
        sh = sum((e['value1'] + e['value2'] / 2) for e in effs if e.get('id') in (6, 37)) * (1 + res / 100.0) \
            + 20.0 * sum((e['value1'] + e['value2'] / 2) for e in effs if e.get('id') in (5, 54)) * (1 + res / 100.0)
        kd = max(kd, dmg * uses); kn = max(kn, nova * uses); kp = max(kp, pois * uses)
        heal = max(heal, hl * min(uses, 1)); shield = max(shield, sh * min(uses, 1))
    return [kd / 1000.0, kn / 1000.0, kp / 1000.0, heal / 1000.0, shield / 1000.0]


def id_space(actions):
    """'item' or 'template': how USE_CHIP actions number chips in this fight."""
    last = None
    for a in actions:
        if not isinstance(a, list) or not a:
            continue
        if a[0] == 7:
            last = None
        elif a[0] == 12 and len(a) > 1:
            last = a[1]
        elif a[0] in (301, 302) and len(a) > 1 and last is not None:
            y = a[1]
            if y == last and y in ITEM_CHIP:
                return 'item'
            if ITEM_TPL.get(y) == last:
                return 'template'
            last = None
    return 'template'


def fight_samples(f):
    d = f.get('data') or {}
    if isinstance(d, str):
        d = json.loads(d)
    leeks = d.get('leeks') or []
    mains = [l for l in leeks if not l.get('summon')]
    if len(mains) != 2 or not d.get('actions'):
        return []
    a, b = mains
    if a.get('team') == b.get('team'):
        return []
    winner = f.get('winner')
    try:
        geo = Geometry(obstacles=(d.get('map') or {}).get('obstacles') or {})
    except Exception:
        return []
    space = id_space(d['actions'])
    chip_name = (lambda x: ITEM_CHIP.get(x, 'chip?%s' % x)) if space == 'item' else D.chip
    weapon_name = (lambda x: ITEM_WEAPON.get(x, 'weapon?%s' % x)) if space == 'item' else D.weapon
    ent = {}
    for l in leeks:
        ent[l['id']] = {'team': l.get('team'), 'cell': l.get('cellPos'), 'hp': l.get('life', 1),
                        'max': max(1, l.get('life', 1)), 'alive': not l.get('summon'), 'summon': bool(l.get('summon')), 'l': l}
    effects = {}
    items = {}
    pc = None
    for act in d['actions']:
        if not isinstance(act, list) or not act:
            continue
        if act[0] == 7 and len(act) > 1:
            pc = act[1]
        elif act[0] == 13 and len(act) > 1 and pc is not None:
            items.setdefault(pc, set()).add(weapon_name(act[1]))
        elif act[0] == 12 and len(act) > 1 and pc is not None:
            items.setdefault(pc, set()).add(chip_name(act[1]))
    cd = {}
    for eid, e in ent.items():
        e['burn'] = 0
        e['kit'] = kit_stats(items.get(eid, set()), e['l']) if e['l'] else (0, 0.0, 0.0, 0.0)
        for name in items.get(eid, ()):
            ic = (D.info(name) or {}).get('initial_cooldown') or 0
            if ic > 0:
                cd[(eid, name)] = ic + 1
    out = []
    cur = None; T = 1
    for act in d['actions']:
        if not isinstance(act, list) or not act:
            continue
        c = act[0]
        if c == 6:
            T = act[1] if len(act) > 1 else T + 1
        elif c == 7:
            cur = act[1] if len(act) > 1 else None
            for k in [k for k, e in effects.items() if e[4] == cur]:
                effects[k][3] -= 1
                if effects[k][3] <= 0:
                    effects.pop(k)
            for k in [k for k in cd if k[0] == cur]:
                cd[k] = max(0, cd[k] - 1)
            if cur in (a['id'], b['id']) and ent[a['id']]['alive'] and ent[b['id']]['alive']:
                me = cur; op = b['id'] if cur == a['id'] else a['id']
                x = v1.snapshot(T, me, op, ent, effects, geo)
                x += ready_stats(items.get(me, ()), ent[me]['l'], cd, me, False)
                x += ready_stats(items.get(op, ()), ent[op]['l'], cd, op, True)
                out.append((T, me, op, x))
        elif c == 10 and len(act) > 2 and act[1] in ent:
            ent[act[1]]['cell'] = act[2]
        elif c == 12 and len(act) > 1 and cur in ent:
            name = chip_name(act[1])
            info = D.info(name) or {}
            cool = info.get('cooldown') or 0
            if cool and cool != 0:
                cd[(cur, name)] = cool if cool > 0 else 10 ** 6
            if len(act) > 3 and act[3] and act[3] > 0 and name in TELE:
                ent[cur]['cell'] = act[2]
        elif c == 9 and len(act) > 3:
            if act[2] in ent:
                ent[act[2]]['alive'] = True; ent[act[2]]['cell'] = act[3]
            else:
                caster = ent.get(act[1])
                ent[act[2]] = {'team': caster['team'] if caster else None, 'cell': act[3], 'hp': 1, 'max': 1,
                               'alive': True, 'summon': True, 'l': {}}
        elif c in (101, 108, 109, 110) and len(act) > 2 and act[1] in ent:
            e = ent[act[1]]
            e['hp'] -= act[2]
            if len(act) > 3 and act[3]:
                e['max'] = max(1, e['max'] - act[3])
                e['burn'] = e.get('burn', 0) + act[3]
        elif c == 107 and len(act) > 2 and act[1] in ent:
            e = ent[act[1]]
            e['max'] = max(1, e['max'] - act[2]); e['hp'] = min(e['hp'], e['max'])
            e['burn'] = e.get('burn', 0) + act[2]
        elif c == 103 and len(act) > 2 and act[1] in ent:
            e = ent[act[1]]; e['hp'] = min(e['max'], e['hp'] + act[2])
        elif c in (104, 112) and len(act) > 2 and act[1] in ent:
            e = ent[act[1]]; e['max'] += act[2]; e['hp'] += act[2] if c == 104 else 0
        elif c == 5 and len(act) > 1 and act[1] in ent:
            ent[act[1]]['alive'] = False
            for k in [k for k, e in effects.items() if e[0] == act[1]]:
                effects.pop(k)
        elif c in (301, 302) and len(act) > 7:
            left = act[7] if (act[7] and act[7] > 0) else (10 ** 6 if act[7] == -1 else 1)
            effects[act[2]] = [act[4], act[5], act[6] or 0, left, cur]
        elif c == 14 and len(act) > 2 and act[1] in effects:
            effects[act[1]][2] += act[2]
        elif c == 304 and len(act) > 2 and act[1] in effects:
            effects[act[1]][2] = act[2]
        elif c == 303 and len(act) > 1:
            effects.pop(act[1], None)
        elif c == 307 and len(act) > 1:
            for k in [k for k, e in effects.items() if e[0] == act[1] and e[1] == 13]:
                effects.pop(k)
        elif c == 308 and len(act) > 1:
            for k in [k for k, e in effects.items() if e[0] == act[1] and e[1] in (17, 18, 19, 24, 47, 48)]:
                effects.pop(k)
    rows = []
    for T, me, op, x in out:
        mt = ent[me]['team']
        y = 0.5 if not winner else (1.0 if winner == mt else 0.0)
        hp_y = (max(0, ent[me]['hp']) / ent[me]['max']) - (max(0, ent[op]['hp']) / ent[op]['max'])
        rows.append((x, y, hp_y, T, me))
    return rows


def sources(limit, ours_only):
    files = []
    if not ours_only:
        files += [(0, p) for p in sorted(glob.glob(os.path.join(ROOT, 'data', 'prod', 'fights', '*', '*.json.gz')))]
    files += [(1, p) for p in sorted(glob.glob(os.path.join(ROOT, 'data', 'fight_cache', '*.json')))]
    if limit:
        step = max(1, len(files) // limit)
        files = files[::step][:limit]
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--ours-only', action='store_true')
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()
    files = sources(a.limit, a.ours_only)
    CH = {k: [] for k in 'XYHFTWACSD'}
    buf = {k: [] for k in 'XYHFTWACSD'}

    def flush():
        if not buf['X']:
            return
        types = dict(X=np.float32, Y=np.float32, H=np.float32, F=np.int64, T=np.int32, W=np.float32, A=np.float32,
                     C=np.int8, S=np.int8, D=np.int64)
        for k in buf:
            CH[k].append(np.asarray(buf[k], types[k])); buf[k].clear()
    bad = 0
    for i, (src, p) in enumerate(files):
        try:
            f = json.load(gzip.open(p, 'rt')) if p.endswith('.gz') else json.load(open(p))
            f = f.get('fight', f) if 'data' not in f else f
            if src == 1 and f.get('type') not in (0, None):
                continue
            rows = fight_samples(f)
        except Exception:
            bad += 1; continue
        tal = [l.get('talent') for l in (f.get('leeks1') or []) + (f.get('leeks2') or []) if l.get('talent') is not None]
        tal = sum(tal) / len(tal) if tal else 0.0
        for x, y, h, t, _ in rows:
            buf['X'].append(x); buf['Y'].append(y); buf['H'].append(h); buf['F'].append(f['id']); buf['T'].append(t)
            buf['W'].append(1.0 / len(rows)); buf['A'].append(tal); buf['C'].append(f.get('context') or 0)
            buf['S'].append(src); buf['D'].append(f.get('date') or 0)
        if (i + 1) % 2000 == 0:
            flush()
            print('  %d/%d fights, %d samples' % (i + 1, len(files), sum(len(c) for c in CH['X'])), flush=True)
    flush()
    cat = lambda k: np.concatenate(CH[k]) if CH[k] else np.zeros(0)
    np.savez_compressed(a.out, X=cat('X'), y=cat('Y'), hp_y=cat('H'), fid=cat('F'), turn=cat('T'), w=cat('W'),
                        talent=cat('A'), context=cat('C'), src=cat('S'), date=cat('D'), names=np.asarray(NAMES))
    X = cat('X')
    print('files %d (bad %d)  samples %d  features %d -> %s' % (len(files), bad, len(X), X.shape[1] if len(X) else 0, a.out))


if __name__ == '__main__':
    main()
