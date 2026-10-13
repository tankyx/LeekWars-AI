#!/usr/bin/env python3
"""Loss miner: why are our leeks losing? Step 2 of the loss-driven AI loop.

Reads each leek's recent garden losses (tools/fight_history_<leek>.db), the fight JSON
(data/fight_cache) and V10's own turn logs (data/fight_logs, fetched once), measures what
happened and tags the likely cause(s), then ranks the causes by the talent they cost.

Tags (a loss can carry several; the first that applies, in this order, is its primary cause).
The same tags are measured on the wins as a control: a tag only points to a cause when it is
clearly more frequent in losses than in wins (the "x" lift column).
  CRASH      our AI did nothing (server-side failure) or 2+ turns cut by the watchdog
  RETURN     damage return took >= 25% of our max life (bramble / mirror / thorn)
  BULBS      the opponent's summons dealt >= 25% of the damage we took
  POISON     poison dealt >= 40% of the damage we took
  OUTHEALED  their heals undid >= 50% of what we dealt (and we dealt >= half their life)
  PASSIVE    we dealt < 40% of their life and chose no damage on >= 40% of our turns
  BURST      one enemy turn took >= 50% of our max life, or we died by turn 4
  CLOSE      they finished with <= 25% life: a race we nearly won
  OTHER      none of the above (lost the damage race outright)

    python3 tools/loss_miner.py                    # main, last 7 days
    python3 tools/loss_miner.py --days 3 --account cure --examples 5
Report also saved to data/ladder/loss_report_<date>.json.
"""
import argparse, collections, datetime, json, os, re, sqlite3, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession
from garden_model import ACCOUNTS, archetype, load_fight

LOGS = os.path.join(ROOT, 'data', 'fight_logs')
ORDER = ('CRASH', 'RETURN', 'BULBS', 'POISON', 'OUTHEALED', 'PASSIVE', 'BURST', 'CLOSE', 'OTHER')
# in-game names since 2026-10-08 (fight data before that carries the old names)
SHOWN = {'AdaLovelace': 'Kirby54', 'EdsgerDijkstra': 'GTGabi', 'KurtGodel': 'Zoulman', 'MargaretHamilton': 'Payou'}


def fight_logs(lw, fid):
    os.makedirs(LOGS, exist_ok=True)
    p = os.path.join(LOGS, '%d.json' % fid)
    if os.path.exists(p):
        try:
            return open(p).read()
        except Exception:
            pass
    s = json.dumps(lw.get('/fight/get-logs/%d' % fid))
    open(p, 'w').write(s)
    time.sleep(0.11)
    return s


def analyse(f, logs, lid):
    """Measurements of one fight from our leek's point of view, or None."""
    data = f.get('data') or {}
    l1 = f.get('leeks1') or []; l2 = f.get('leeks2') or []
    mine1 = any(l.get('id') == lid for l in l1)
    me_l = next((l for l in (l1 if mine1 else l2) if l.get('id') == lid), None)
    op_l = ((l2 if mine1 else l1) or [None])[0]
    ents = {e['id']: e for e in data.get('leeks') or []}
    if not me_l or not op_l:
        return None
    me = next((i for i, e in ents.items() if e.get('name') == me_l.get('name') and not e.get('summon')), None)
    foe = next((i for i, e in ents.items() if e.get('name') == op_l.get('name') and not e.get('summon')), None)
    if me is None or foe is None:
        return None
    m = {'my_max': ents[me].get('life') or 1, 'foe_max': ents[foe].get('life') or 1,
         'to_me': collections.Counter(), 'by_me': 0, 'foe_healed': 0, 'antidotes': 0,
         'turns': 0, 'max_enemy_turn': 0, 'died_turn': None, 'foe_life_end': ents[foe].get('life') or 0,
         'uses': 0, 'my_turns': 0, 'bugs': 0, 'opp': dict(ents[foe]), 'opp_name': op_l.get('name')}
    summons = set(); cur = None; turn = 0; enemy_turn_dmg = 0
    for a in data.get('actions') or []:
        k = a[0]
        if k == 6:
            turn = a[1] if len(a) > 1 else turn + 1; m['turns'] = turn
        elif k == 7:
            if cur is not None and cur != me:
                m['max_enemy_turn'] = max(m['max_enemy_turn'], enemy_turn_dmg)
            cur = a[1]; enemy_turn_dmg = 0
            if cur == me:
                m['my_turns'] += 1
        elif k == 9 and len(a) > 2 and a[1] == foe:
            summons.add(a[2])
        elif k in (12, 16) and cur == me:
            m['uses'] += 1
        elif k == 1002 and cur == me:
            m['bugs'] += 1
        elif k in (101, 107, 108, 110) and len(a) > 2:
            tgt, d = a[1], a[2]
            if tgt == me:
                src = {101: 'bulbs' if cur in summons else 'direct', 107: 'nova', 108: 'return', 110: 'poison'}[k]
                m['to_me'][src] += d
                if cur != me:
                    enemy_turn_dmg += d
            elif tgt == foe:
                m['by_me'] += d; m['foe_life_end'] -= d
        elif k == 103 and len(a) > 2 and a[1] == foe:
            m['foe_healed'] += a[2]; m['foe_life_end'] += a[2]
        elif k == 307 and len(a) > 1 and a[1] == foe:
            m['antidotes'] += 1
        elif k == 5 and len(a) > 1 and a[1] == me:
            m['died_turn'] = turn
    m['max_enemy_turn'] = max(m['max_enemy_turn'], enemy_turn_dmg)
    plans = re.findall(r'V10 T(\d+) V=\S+ plans=\d+ ops=\d+ dealt=(\d+) end_d=(\d+)', logs)
    m['no_dmg_turns'] = sum(1 for _, d, _ in plans if int(d) == 0)
    m['logged_turns'] = len(plans)
    m['cuts'] = logs.count('too_much_ops')
    m['end_d'] = [int(e) for _, _, e in plans]
    m['to_me_total'] = sum(m['to_me'].values())
    return m


def tags_of(m):
    t = []; total = max(1, m['to_me_total'])
    if (m['uses'] == 0 and m['bugs'] >= 2) or m['cuts'] >= 2:
        t.append('CRASH')
    if m['to_me']['return'] >= 0.25 * m['my_max']:
        t.append('RETURN')
    if m['to_me']['bulbs'] >= 0.25 * total:
        t.append('BULBS')
    if m['to_me']['poison'] >= 0.40 * total:
        t.append('POISON')
    if m['by_me'] >= 0.5 * m['foe_max'] and m['foe_healed'] >= 0.5 * m['by_me']:
        t.append('OUTHEALED')
    if m['by_me'] < 0.4 * m['foe_max'] and m['logged_turns'] and m['no_dmg_turns'] >= 0.4 * m['logged_turns']:
        t.append('PASSIVE')
    if m['max_enemy_turn'] >= 0.5 * m['my_max'] or (m['died_turn'] is not None and m['died_turn'] <= 4):
        t.append('BURST')
    if m['foe_life_end'] <= 0.25 * m['foe_max']:
        t.append('CLOSE')
    return t or ['OTHER']


def arch_name(opp):
    a = archetype(opp)
    for k in ('magic', 'agility', 'science', 'tank'):
        if a[k]:
            return k
    return 'strength'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--account', default='main', choices=sorted(ACCOUNTS))
    ap.add_argument('--days', type=float, default=7.0)
    ap.add_argument('--examples', type=int, default=3)
    a = ap.parse_args()
    lw = LWSession(a.account)
    since = (datetime.datetime.utcnow() - datetime.timedelta(days=a.days)).isoformat()
    report = {'account': a.account, 'since': since, 'leeks': {}}
    allp = collections.Counter(); all_cost = collections.Counter(); n_all = 0
    for name, lid in ACCOUNTS[a.account].items():
        db = sqlite3.connect(os.path.join(HERE, 'fight_history_%d.db' % lid))
        rows = db.execute("SELECT fight_id, result FROM fight_history WHERE timestamp >= ? ORDER BY timestamp", (since,)).fetchall()
        losses = [fid for fid, r in rows if r == 'LOSS']
        prim = collections.Counter(); anyt = collections.Counter(); cost = collections.Counter()
        arch = collections.Counter(); ex = collections.defaultdict(list); talent = 0
        for fid in losses:
            f = load_fight(lw, fid)
            if not f:
                continue
            m = analyse(f, fight_logs(lw, fid), lid)
            if not m:
                continue
            tg = tags_of(m)
            gain = next((l.get('talent_gain') or 0 for side in ('leeks1', 'leeks2')
                         for l in ((f.get('report') or {}).get(side) or []) if l.get('id') == lid), 0)
            p = next(t for t in ORDER if t in tg)
            prim[p] += 1; cost[p] += gain; talent += gain
            for t in tg:
                anyt[t] += 1
            arch[arch_name(m['opp'])] += 1
            if len(ex[p]) < a.examples:
                ex[p].append('%d vs %s (T%s, took %d: %s)' % (fid, m['opp_name'], m['turns'], m['to_me_total'],
                             ', '.join('%s %d' % kv for kv in m['to_me'].most_common(3))))
        # control: the same measurements on the wins - a tag is a cause only if it is more common in losses
        win_tags = collections.Counter(); n_w = 0
        for fid in [fid for fid, r in rows if r == 'WIN']:
            f = load_fight(lw, fid)
            m = analyse(f, fight_logs(lw, fid), lid) if f else None
            if m:
                n_w += 1
                for t in tags_of(m):
                    win_tags[t] += 1
        n = sum(prim.values()); n_all += n
        allp.update(prim); all_cost.update(cost)
        shown = SHOWN.get(name, name)
        print('\n== %s: %d fights, %d losses analysed, talent lost in them %d' % (shown, len(rows), n, talent))
        if not n:
            continue
        print('   primary cause      losses  share  talent | present in losses vs wins (%d wins)' % n_w)
        for t in ORDER:
            if prim[t] or anyt[t]:
                pl = 100.0 * anyt[t] / n; pw = 100.0 * win_tags[t] / max(1, n_w)
                print('   %-12s       %4d   %4.0f%%  %6d | %4.0f%% vs %4.0f%%  %s' % (
                    t, prim[t], 100.0 * prim[t] / n, cost[t], pl, pw, 'x%.1f' % (pl / pw) if pw > 0 else 'only in losses'))
        print('   lost to: %s' % ', '.join('%s %d' % kv for kv in arch.most_common()))
        for t in ORDER:
            for e in ex.get(t, []):
                print('     %-10s %s' % (t, e))
        report['leeks'][shown] = {'fights': len(rows), 'losses': n, 'talent': talent, 'primary': dict(prim),
                                  'present': dict(anyt), 'cost': dict(cost), 'archetypes': dict(arch), 'examples': dict(ex),
                                  'wins': n_w, 'present_in_wins': dict(win_tags)}
    print('\n== all leeks: %d losses' % n_all)
    for t, c in allp.most_common():
        print('   %-12s %4d  (%4.0f%%)  talent %d' % (t, c, 100.0 * c / max(1, n_all), all_cost[t]))
    out = os.path.join(ROOT, 'data', 'ladder', 'loss_report_%s_%s.json' % (a.account, datetime.date.today().isoformat()))
    json.dump(report, open(out, 'w'), indent=1)
    print('saved', os.path.relpath(out, ROOT))


if __name__ == '__main__':
    main()
