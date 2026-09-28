#!/usr/bin/env python3
"""Per-turn state features from prod fights -> value-model dataset (2026-09-28).

One sample at the start of every turn of either MAIN leek of a 1v1 solo
fight, from the perspective of the leek about to act ("me") against the
enemy main leek ("opp"). Label: the eventual result for "me" (1 win, 0 loss,
0.5 draw), plus the final HP-fraction difference as an auxiliary target.

Features are things our AI can observe in-game (getLife, getEffects, stats,
cells), so the trained model can run inside LeekScript. Positions follow
MOVE_TO, teleport/jump casts and summons; attract/push slides are not in the
action stream and are missed (rare).

    python3 tools/value_dataset.py                 # all fights in data/prod
    python3 tools/value_dataset.py --limit 2000    # quick check
Writes data/prod/value_ds.npz (X, y, hp_y, fid, turn, names).
"""
import argparse, glob, gzip, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_decode import Decoder
from lw_geometry import Geometry

D = Decoder()
OUT = os.path.join(ROOT, 'data', 'prod', 'value_ds.npz')

# effect type -> feature group (engine Effect.TYPE_*)
GROUP = {13: 'poison', 2: 'heal_ot', 5: 'rel_shield', 54: 'rel_shield', 6: 'abs_shield', 37: 'abs_shield',
         19: 'shk_str', 24: 'shk_mag', 18: 'shk_tp', 17: 'shk_mp', 47: 'shk_agi',
         3: 'buf_str', 38: 'buf_str', 39: 'buf_mag', 4: 'buf_agi', 41: 'buf_agi', 8: 'buf_tp', 32: 'buf_tp',
         7: 'buf_mp', 31: 'buf_mp', 21: 'buf_res', 42: 'buf_res', 22: 'buf_wis', 44: 'buf_wis', 52: 'buf_pow',
         20: 'dmg_return', 26: 'vuln', 27: 'vuln_abs'}
GROUPS = sorted(set(GROUP.values()))
# scale per group so features are O(1)
GSCALE = {'buf_tp': 3.0, 'buf_mp': 2.0, 'shk_tp': 3.0, 'shk_mp': 2.0, 'buf_agi': 200.0, 'poison': 300.0, 'heal_ot': 300.0, 'rel_shield': 30.0, 'abs_shield': 150.0, 'dmg_return': 30.0,
          'vuln': 20.0, 'vuln_abs': 60.0}
STATS = ['strength', 'magic', 'agility', 'resistance', 'wisdom', 'science']
TELE = {'teleportation', 'jump'}


def names():
    n = ['turn', 'dist', 'los']
    for side in ('me', 'op'):
        n += ['%s_hp' % side, '%s_hpfrac' % side, '%s_maxhp' % side, '%s_level' % side, '%s_tp' % side, '%s_mp' % side]
        n += ['%s_%s' % (side, s[:3]) for s in STATS]
        n += ['%s_eff_%s' % (side, g) for g in GROUPS]
        n += ['%s_poison_future' % side, '%s_summons' % side]
        # v2 (2026-09-28): max HP burned since the start (nova/erosion attrition),
        # kit potential per turn (best single item at full TP) and reach
        n += ['%s_burned' % side, '%s_wrange' % side, '%s_kdmg' % side, '%s_knova' % side,
              '%s_kpois' % side, '%s_reach' % side]
    return n


def kit_stats(items, l):
    """(max range, best direct / nova / poison per turn) over the weapons and
    damage chips a leek uses; per item: value per use x min(max uses, TP // cost)."""
    tp = max(1, l.get('tp', 20))
    stre, mag, sci = max(0, l.get('strength', 0)), max(0, l.get('magic', 0)), max(0, l.get('science', 0))
    rng = 0; kd = kn = kp = 0.0
    for name in items:
        info = D.info(name) or {}
        effs = info.get('effects') or []
        cost = max(1, info.get('cost') or 1)
        uses = min(info.get('max_uses') or 99, tp // cost) if (info.get('max_uses') or 0) > 0 else tp // cost
        dmg = sum((e['value1'] + e['value2'] / 2) for e in effs if e.get('id') == 1) * (1 + stre / 100.0)
        nova = sum((e['value1'] + e['value2'] / 2) for e in effs if e.get('id') == 30) * (1 + sci / 100.0)
        pois = sum((e['value1'] + e['value2'] / 2) * max(1, e.get('turns') or 1) for e in effs if e.get('id') == 13) * (1 + mag / 100.0)
        if dmg + nova + pois <= 0:
            continue
        rng = max(rng, info.get('max_range') or 0)
        kd = max(kd, dmg * uses); kn = max(kn, nova * uses); kp = max(kp, pois * uses)
    return rng, kd, kn, kp


NAMES = names()


def fight_samples(f):
    d = f.get('data') or {}
    leeks = d.get('leeks') or []
    mains = [l for l in leeks if not l.get('summon')]
    if len(mains) != 2 or not d.get('actions'):
        return []
    a, b = mains
    if a.get('team') == b.get('team'):
        return []
    winner = f.get('winner')          # team number, 0 = draw
    try:
        geo = Geometry(obstacles=(d.get('map') or {}).get('obstacles') or {})
    except Exception:
        return []
    ent = {}
    for l in leeks:
        # summons are pre-listed; they come alive on their SUMMON action
        ent[l['id']] = {'team': l.get('team'), 'cell': l.get('cellPos'), 'hp': l.get('life', 1),
                        'max': max(1, l.get('life', 1)), 'alive': not l.get('summon'), 'summon': bool(l.get('summon')), 'l': l}
    effects = {}                      # instance id -> [target, type, value, turns_left, caster]
    # kit = items each entity uses during the fight (in game: equipped items)
    items = {}
    pc = None; held = {}
    for act in d['actions']:
        if not isinstance(act, list) or not act:
            continue
        if act[0] == 7 and len(act) > 1:
            pc = act[1]
        elif act[0] == 13 and len(act) > 1 and pc is not None:
            items.setdefault(pc, set()).add(D.weapon(act[1]))
        elif act[0] == 12 and len(act) > 1 and pc is not None:
            items.setdefault(pc, set()).add(D.chip(act[1]))
    for eid, e in ent.items():
        e['burn'] = 0
        e['kit'] = kit_stats(items.get(eid, set()), e['l']) if e['l'] else (0, 0.0, 0.0, 0.0)
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
            # durations tick at the caster's turn start
            for k in [k for k, e in effects.items() if e[4] == cur]:
                effects[k][3] -= 1
                if effects[k][3] <= 0:
                    effects.pop(k)
            if cur in (a['id'], b['id']) and ent[a['id']]['alive'] and ent[b['id']]['alive']:
                me = cur; op = b['id'] if cur == a['id'] else a['id']
                out.append((T, me, op, snapshot(T, me, op, ent, effects, geo)))
        elif c == 10 and len(act) > 2 and act[1] in ent:
            ent[act[1]]['cell'] = act[2]
        elif c == 12 and len(act) > 3 and cur in ent and act[3] and act[3] > 0:
            if D.chip(act[1]) in TELE:
                ent[cur]['cell'] = act[2]
        elif c == 9 and len(act) > 3:
            # [9, caster, summon_id, cell, ...]
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
            # nova damage lowers MAX life only (death-consistency check on
            # 1,308 prod deaths: 100% with this rule, 85% if counted as damage)
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
            # duration -1 = permanent (passives / permanent buffs): never tick down
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


def snapshot(T, me, op, ent, effects, geo):
    x = [T / 30.0]
    cm, co = ent[me]['cell'], ent[op]['cell']
    try:
        dist = geo.dist(cm, co)
        occ = {e['cell'] for i, e in ent.items() if e['alive'] and i not in (me, op) and e['cell'] is not None}
        los = 1.0 if geo.los(cm, co, occupied=occ) else 0.0
    except Exception:
        dist, los = 10, 1.0
    x += [(dist or 0) / 20.0, los]
    for side in (me, op):
        e = ent[side]; l = e['l']
        # hpfrac vs max HP before attrition, so nova/erosion don't raise it
        x += [max(0, e['hp']) / 3000.0, max(0, e['hp']) / max(1, e['max'] + e.get('burn', 0)), e['max'] / 3000.0, l.get('level', 301) / 301.0,
              l.get('tp', 20) / 30.0, l.get('mp', 6) / 8.0]
        x += [l.get(s, 0) / 600.0 for s in STATS]
        g = dict.fromkeys(GROUPS, 0.0); pf = 0.0
        for tgt, typ, val, left, _ in effects.values():
            if tgt != side or typ not in GROUP:
                continue
            g[GROUP[typ]] += val
            if typ == 13:
                pf += val * min(left, 64)
        x += [g[k] / GSCALE.get(k, 100.0) for k in GROUPS]
        team = e['team']
        summons = sum(1 for o in ent.values() if o['alive'] and o['summon'] and o['team'] == team)
        x += [pf / 1000.0, summons / 2.0]
        rng, kd, kn, kp = e['kit']
        other = ent[op] if side == me else ent[me]
        reach = 1.0 if (dist is not None and dist <= l.get('mp', 6) + rng) else 0.0
        x += [e.get('burn', 0) / 3000.0, rng / 10.0, kd / 1000.0, kn / 1000.0, kp / 1000.0, reach]
    return x


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--limit', type=int, default=0); a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(ROOT, 'data', 'prod', 'fights', '*', '*.json.gz')))
    if a.limit:
        files = files[:a.limit]
    X, Y, H, F, TT, W = [], [], [], [], [], []
    bad = 0
    for i, p in enumerate(files):
        try:
            f = json.load(gzip.open(p, 'rt'))
            rows = fight_samples(f)
        except Exception:
            bad += 1; continue
        for x, y, h, t, _ in rows:
            # each fight weighs 1 in total: 64-turn draws would otherwise swamp the set
            X.append(x); Y.append(y); H.append(h); F.append(f['id']); TT.append(t); W.append(1.0 / len(rows))
        if (i + 1) % 2000 == 0:
            print('  %d/%d fights, %d samples' % (i + 1, len(files), len(X)), flush=True)
    X = np.asarray(X, dtype=np.float32)
    np.savez_compressed(OUT, X=X, y=np.asarray(Y, np.float32), hp_y=np.asarray(H, np.float32),
                        fid=np.asarray(F, np.int64), turn=np.asarray(TT, np.int32), w=np.asarray(W, np.float32),
                        names=np.asarray(NAMES))
    print('fights %d (skipped %d)  samples %d  features %d -> %s' % (len(files), bad, len(X), X.shape[1] if len(X) else 0, OUT))
    if len(X):
        Wa = np.asarray(W); Ya = np.asarray(Y)
        print('fight-weighted: label mean %.3f  draws %.1f%%' % (float(np.sum(Wa * Ya) / Wa.sum()), 100 * float(np.sum(Wa * (Ya == 0.5)) / Wa.sum())))


if __name__ == '__main__':
    main()
