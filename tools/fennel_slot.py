#!/usr/bin/env python3
"""Nightly 8-leek Fennel slot. Owner 2026-10-19 chose a "fixed daily Fennel slot": after the
midnight-Paris refill, before the garden spends the rest.

main's 4 leeks go on the chip-only Boss kits (no respec, no restat potion). Cure's 4 leeks stay on
their ladder kits. Fights go through tools/boss_squad.mjs, at 1 credit per account per fight;
8-leek chip-only won 7/10 on 2026-10-19. The script waits until every fight has been generated,
then restores main's ladder loadouts and verifies them: main's garden must never run on boss kits.
Appends a row to data/ladder/fennel_slot.csv (date, fights, wins, ids).

    python3 tools/fennel_slot.py [--n 40]

Exit 0: done, or skipped, with main on its ladder setup. Exit 2: main is NOT on its ladder setup
(the garden must skip main).
"""
import argparse, csv, datetime, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession

MAIN = [20443, 129288, 129295, 129296]
BOSS_ONLY = {'spark', 'resurrection'}      # in every Boss kit, in no ladder kit
CSV = os.path.join(ROOT, 'data', 'ladder', 'fennel_slot.csv')


def say(s):
    print('%s fennel_slot: %s' % (time.strftime('%H:%M:%S', time.gmtime()), s), flush=True)


def credits(lw):
    g = lw.get('/garden/get'); g = g.get('garden', g)
    return int(g.get('fights') or 0)


def run(args, timeout):
    try:
        p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        return p.stdout + p.stderr
    except subprocess.TimeoutExpired as ex:
        out = ex.stdout or ''
        return out.decode('utf-8', 'replace') if isinstance(out, bytes) else out


def on_boss_kits(lw):
    names = json.load(open(os.path.join(HERE, 'item_get-all.json')))
    for lid in MAIN:
        for c in lw.leek(lid).get('chips') or []:
            if names.get(str(c.get('template')), {}).get('name', '')[5:] in BOSS_ONLY:
                return True
    return False


def restore():
    for k in range(2):
        out = run([sys.executable, '-u', 'tools/boss_swap.py', 'restore'], 300)
        if 'all four leeks match the snapshot' in out:
            say('main restored and verified')
            return True
        say('restore pass %d did not verify:\n%s' % (k + 1, '\n'.join(l for l in out.splitlines() if 'DIFF' in l or 'rror' in l)[:800]))
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=40)
    a = ap.parse_args()
    lwm, lwc = LWSession('main'), LWSession('cure')
    if on_boss_kits(lwm):
        say('main is still on boss kits from an earlier slot - restoring from the existing snapshot, no fights')
        return 0 if restore() else 2
    cm, cc = credits(lwm), credits(lwc)
    n = min(a.n, cm, cc)
    if n < 5:
        say('only %d main / %d cure credits - skipped' % (cm, cc))
        return 0
    say('%d fights (credits main %d, cure %d)' % (n, cm, cc))
    ids = []
    out = run([sys.executable, '-u', 'tools/boss_swap.py', 'snapshot', '--force'], 180)
    if 'saved' not in out:
        say('snapshot failed - skipped, nothing changed:\n' + out[-500:])
        return 0
    try:
        out = run([sys.executable, '-u', 'tools/boss_swap.py', 'prepare'], 300)
        out += run([sys.executable, '-u', 'tools/boss_swap.py', 'boss'], 300)
        if 'WARNING' in out or 'Traceback' in out:
            say('boss kits not applied cleanly - no fights:\n' + out[-800:])
        else:
            out = run(['node', 'tools/boss_squad.mjs', '--boss', '2', '--n', str(n)], 20 * n + 120)
            ids = [int(x) for x in re.findall(r'started (\d+)', out)]
            say('%d fights started%s' % (len(ids), '' if len(ids) == n else ' (stopped: %s)' % out.strip().splitlines()[-1][:200]))
            # the fights read the leeks' kits when they are generated: wait for all of them
            pend = set(ids); t0 = time.time()
            while pend and time.time() - t0 < 2400:
                time.sleep(20)
                for fid in list(pend):
                    f = lwm.get('/fight/get/%d' % fid); f = f.get('fight', f)
                    if f.get('status') == 2:            # 2 = generated (boss_v10_batch.analyze)
                        pend.discard(fid)
            if pend:
                say('%d fights still pending after 40 min - restoring anyway' % len(pend))
    finally:
        ok = restore()
    wins = 0
    if ids:
        out = run([sys.executable, '-u', 'tools/boss_v10_batch.py', '0', '--ids', ','.join(map(str, ids)), '--boss', '2'], 1800)
        m = re.search(r'== (\d+) fights: (\d+) wins.*', out)
        wins = int(m.group(2)) if m else 0
        say(m.group(0) if m else 'no summary')
        new = not os.path.exists(CSV)
        with open(CSV, 'a', newline='') as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(['date', 'fights', 'wins', 'ids'])
            w.writerow([datetime.date.today().isoformat(), len(ids), wins, ' '.join(map(str, ids))])
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
