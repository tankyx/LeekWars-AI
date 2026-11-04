#!/usr/bin/env python3
"""Nightly 8-leek boss slot (main + Cure through tools/boss_squad.mjs). Owner 2026-10-19: a daily Fennel
slot before the garden; 2026-10-20: "Focus on bosses" - 8-leek Pumpkin first, every credit to bosses.

main's 4 leeks go on the chip-only Boss (Fennel) or Pumpkin kits: no respec, no restat potion.
Cure's 4 leeks keep the chips they carry (tools/cure_kit.py applies Cure's boss kit).
Each fight costs 1 credit per account. 8-leek chip-only Fennel won 12/15 on 2026-10-19.
The script waits until every fight has been generated, then restores main's ladder loadouts and
verifies them: main must never be left on boss kits. Appends a row to data/ladder/boss_slot.csv
(date, boss, fights, wins, ids).

    python3 tools/boss_slot.py --boss 3 --n all      # every credit pair on the Pumpkin
    python3 tools/boss_slot.py --boss 2 --n 40       # 40 Fennel fights
    python3 tools/boss_slot.py --boss 3 --dry        # apply + restore main's kits, no fight

Exit 0: done, or skipped, with main on its ladder setup. Exit 2: main is NOT on its ladder setup
(the garden must skip main).
"""
import argparse, csv, datetime, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession

MAIN = [20443, 129288, 129295, 129296]
BOSS_ONLY = {'spark', 'resurrection', 'puny_bulb', 'wizard_bulb', 'savant_bulb', 'prototaxite'}   # boss kits only
CSV = os.path.join(ROOT, 'data', 'ladder', 'boss_slot.csv')


def say(s):
    print('%s boss_slot: %s' % (time.strftime('%H:%M:%S', time.gmtime()), s), flush=True)


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
    ap.add_argument('--boss', type=int, default=3, choices=[2, 3], help='2 = Fennel King, 3 = Evil Pumpkin')
    ap.add_argument('--n', default='all', help='number of fights, or "all" (every credit pair)')
    ap.add_argument('--dry', action='store_true', help='apply and restore main\'s kits, no fight')
    a = ap.parse_args()
    setf = ['--set', 'pumpkin'] if a.boss == 3 else []
    lwm, lwc = LWSession('main'), LWSession('cure')
    if on_boss_kits(lwm):
        say('main is still on boss kits from an earlier slot - restoring from the existing snapshot, no fights')
        return 0 if restore() else 2
    cm, cc = credits(lwm), credits(lwc)
    n = min(cm, cc) if a.n == 'all' else min(int(a.n), cm, cc)
    if a.dry:
        n = 0
    elif n < 5:
        say('only %d main / %d cure credits - skipped' % (cm, cc))
        return 0
    say('%d fights (credits main %d, cure %d)' % (n, cm, cc))
    ids = []
    # Cure's chips for this boss: its saved ladder chips for Fennel (12/15 as fighters while main's leeks
    # solve the crystals), the Pumpkin kit for the Pumpkin
    out = run([sys.executable, '-u', 'tools/cure_kit.py'] + (['apply', 'pumpkin'] if a.boss == 3 else ['restore']), 300)
    if 'MISMATCH' in out or 'Traceback' in out:
        say('Cure kit not set cleanly:\n' + out[-600:])
    out = run([sys.executable, '-u', 'tools/boss_swap.py', 'snapshot', '--force'], 180)
    if 'saved' not in out:
        say('snapshot failed - skipped, nothing changed:\n' + out[-500:])
        return 0
    try:
        out = run([sys.executable, '-u', 'tools/boss_swap.py', 'prepare'] + setf, 300)
        out += run([sys.executable, '-u', 'tools/boss_swap.py', 'boss'] + setf, 300)
        if 'WARNING' in out or 'Traceback' in out:
            say('boss kits not applied cleanly - no fights:\n' + out[-800:])
        elif a.dry:
            say('dry run: main on the %s kits:\n%s' % ('Pumpkin' if a.boss == 3 else 'Boss',
                '\n'.join(l[:160] for l in out.splitlines() if 'kit' in l or 'missing' in l)))
        else:
            if a.boss == 3:     # drop tracking (owner 2026-11-03: farm the permanent Pumpkin for components)
                run([sys.executable, '-u', 'tools/pk_progress.py', '--log', 'batch_start'], 120)
            out = run(['node', 'tools/boss_squad.mjs', '--boss', str(a.boss), '--n', str(n)], 20 * n + 120)
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
        # Cure back on its ladder chips too (2026-11-02: the team fights that follow the slot use them)
        out_c = run([sys.executable, '-u', 'tools/cure_kit.py', 'restore'], 300)
        say('Cure ladder chips %s' % ('restored' if 'MISMATCH' not in out_c and 'Traceback' not in out_c else 'NOT restored:\n' + out_c[-300:]))
    wins = 0
    if ids:
        out = run([sys.executable, '-u', 'tools/boss_v10_batch.py', '0', '--ids', ','.join(map(str, ids)), '--boss', str(a.boss)], 1800)
        m = re.search(r'== (\d+) fights: (\d+) wins.*', out)
        wins = int(m.group(2)) if m else 0
        say(m.group(0) if m else 'no summary')
        if a.boss == 3:
            run([sys.executable, '-u', 'tools/pk_progress.py', '--log', 'batch_end:%d' % len(ids)], 120)
            # craft + equip the target parts the drops now allow (owner 2026-11-03: "Craft everything we need")
            out_k = run([sys.executable, '-u', 'tools/pk_craft.py'], 900)
            say('pk_craft: ' + ' | '.join(l.strip() for l in out_k.splitlines() if 'equip' in l or 'FAILED' in l or 'crafted and equipped' in l)[:600])
        new = not os.path.exists(CSV)
        with open(CSV, 'a', newline='') as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(['date', 'boss', 'fights', 'wins', 'ids'])
            w.writerow([datetime.date.today().isoformat(), a.boss, len(ids), wins, ' '.join(map(str, ids))])
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
