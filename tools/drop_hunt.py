#!/usr/bin/env python3
"""Hunt an item drop with farmer fights: every one of our leeks gets its own loot roll in a farmer
fight (one credit = 4 rolls on main, vs 1 in a solo fight), and farmer fights move the farmer's
talent only, never the leeks'. Losers get loot too (scheme drops in the garden cache: 65 to winners,
34 to losers, 8 draws), so the opponent is the weakest offered farmer.

Stops starting fights as soon as the target item lands in one of our leeks' loot (or when the
credits run out / --max is reached). Every drop is logged to data/ladder/drop_hunt.jsonl.

    python3 tools/drop_hunt.py --item 610 --max 1000          # 610 = scheme_glowing_saber
"""
import argparse, collections, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession

MAIN = {'Kirby54': 20443, 'GTGabi': 129288, 'Zoulman': 129295, 'Payou': 129296}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--item', type=int, default=610, help='item id to hunt (610 = scheme_glowing_saber)')
    ap.add_argument('--max', type=int, default=1000, help='max farmer fights to start')
    ap.add_argument('--inflight', type=int, default=4)
    a = ap.parse_args()
    lw = LWSession('main')
    items = lw.get('/item/get-all'); items = items.get('items', items)
    info = {int(k): v for k, v in items.items()}
    target = info.get(a.item, {}).get('name', a.item)
    ids = set(MAIN.values())
    log = open(os.path.join(ROOT, 'data', 'ladder', 'drop_hunt.jsonl'), 'a')
    pend = {}; started = done = fails = 0; found = None
    rec = collections.Counter(); drops = collections.Counter(); schemes = []
    t0 = time.time()
    print('hunting %s with up to %d farmer fights' % (target, a.max), flush=True)
    while (started < a.max and found is None or pend) and fails < 20:
        while found is None and started < a.max and len(pend) < a.inflight:
            ops = (lw.get('/garden/get-farmer-opponents') or {}).get('opponents') or []
            if not ops:
                fails += 1; time.sleep(5); break
            o = min(ops, key=lambda x: x.get('talent') or 0)
            r = lw.post('/garden/start-farmer-fight', target_id=o['id'])
            fid = r if isinstance(r, int) else (r.get('fight') if isinstance(r, dict) else None)
            if not fid:
                err = r.get('error') if isinstance(r, dict) else r
                if err in ('too_many_fights', 'no_more_fights', 'not_enough_fights'):
                    print('no credits left (%s)' % err, flush=True); a.max = started; break
                fails += 1; time.sleep(2); continue
            pend[fid] = o; started += 1; fails = 0
        time.sleep(3)
        for fid in list(pend):
            f = lw.get('/fight/get/%d' % fid); f = f.get('fight', f)
            if f.get('status') != 2:
                continue
            pend.pop(fid); done += 1
            ours1 = any(l.get('id') in ids for l in f.get('leeks1') or [])
            w = f.get('winner'); res = 'D' if w == 0 else ('W' if w == (1 if ours1 else 2) else 'L')
            rec[res] += 1
            got = {}
            for side in ('leeks1', 'leeks2'):
                for l in (f.get('report') or {}).get(side) or []:
                    if l.get('id') in ids and l.get('resources'):
                        got[l['name']] = l['resources']
                        for k, q in l['resources'].items():
                            it = info.get(int(k), {})
                            drops[it.get('type')] += q
                            if it.get('type') == 9:
                                schemes.append((it.get('name'), l['name'], fid))
                                print('  SCHEME %s -> %s (fight %d)' % (it.get('name'), l['name'], fid), flush=True)
                            if int(k) == a.item and found is None:
                                found = (l['name'], fid)
                                print('  FOUND %s on %s in fight %d - no new fights' % (target, l['name'], fid), flush=True)
            log.write(json.dumps({'fight': fid, 'result': res, 'loot': got}) + '\n'); log.flush()
            if done % 50 == 0:
                print('  %d fights done (%dW/%dL/%dD), %d schemes so far, %.0f min' % (
                    done, rec['W'], rec['L'], rec['D'], len(schemes), (time.time() - t0) / 60), flush=True)
    print('RESULT: %d farmer fights %dW/%dL/%dD, schemes %s, target %s' % (
        done, rec['W'], rec['L'], rec['D'], [s[0] for s in schemes], 'FOUND on %s (fight %d)' % found if found else 'not found'), flush=True)


if __name__ == '__main__':
    main()
