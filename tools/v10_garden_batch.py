#!/usr/bin/env python3
"""V10 ladder rollout: play garden fights in batches through the MCP smart
selector (same picks as tools/daily_garden.py), then audit the batch's fights.

    python3 tools/v10_garden_batch.py --per-leek 10
    python3 tools/v10_garden_batch.py --per-leek 50 --leeks KurtGodel

Per leek: fights played, W/L/D, talent before/after, and from the fight logs
the turns cut by the server watchdog (error 101 / too_much_ops), turns where
V10 hit its exception fallback, and turns with no V10 decision log. Appends a
row per leek to data/ladder/v10_garden.csv.
"""
import argparse, csv, datetime, os, sys, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession
from daily_garden import MCP, LEEKS, credits, talent

LOG = os.path.join(ROOT, 'data', 'ladder', 'v10_garden.csv')


def audit(lw, lid, since, farmer_key):
    """Fights of leek `lid` started after `since`: (n, cut turns, fallback turns, our turns)."""
    h = lw.get('/history/get-leek-history/%d' % lid) or {}
    fids = [f['id'] for f in h.get('fights', []) if f.get('type') == 0 and (f.get('date') or 0) >= since]
    cut = fb = turns = 0
    for fid in fids:
        logs = (lw.get('/fight/get-logs/%d' % fid) or {}).get(farmer_key) or {}
        for entries in logs.values():
            for e in entries:
                if len(e) > 3 and e[3] == 101:
                    cut += 1
                txt = str(e[2]) if len(e) > 2 else ''
                if txt.startswith('V10 T'):
                    turns += 1
                elif txt.startswith('V10 error') or txt.startswith('V10 fallback'):
                    fb += 1
    return len(fids), cut, fb, turns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--per-leek', type=int, default=10)
    ap.add_argument('--leeks', default='', help='comma list of leek names (default: all four main leeks)')
    a = ap.parse_args()
    leeks = [(n, i) for n, i in LEEKS['main'] if not a.leeks or n in a.leeks.split(',')]
    lw = LWSession('main')
    farmer_key = '18035'
    t_start = int(time.time()) - 5
    before = {i: talent(lw, i) for _, i in leeks}
    print('credits %d' % credits(lw), flush=True)
    rows = []

    def play(name, lid):
        """One leek, its own MCP session (leeks run in parallel: the time is
        fight generation, not API calls)."""
        mcp = MCP(); lw_l = LWSession('main')
        try:
            tot = [0, 0, 0, 0]; need = a.per_leek; tries = 0
            while need > 0 and tries < 8 and credits(lw_l) > 0:
                tries += 1
                done, w, l, d, _ = mcp.solo('main', lid, need)
                tot[0] += done; tot[1] += w; tot[2] += l; tot[3] += d
                need -= done
                if done == 0:
                    time.sleep(5)
        finally:
            mcp.close()
        after = talent(lw_l, lid)
        n, cut, fb, turns = audit(lw_l, lid, t_start, farmer_key)
        print('  %-17s %2d fights %2dW/%2dL/%dD  talent %d -> %d (%+d) | audited %d fights: %d V10 turns, '
              '%d watchdog cuts, %d fallbacks' % (name, tot[0], tot[1], tot[2], tot[3], before[lid], after,
                                                 after - before[lid], n, turns, cut, fb), flush=True)
        return [datetime.datetime.now().isoformat(timespec='seconds'), name, tot[0], tot[1], tot[2], tot[3],
                before[lid], after, turns, cut, fb]

    with ThreadPoolExecutor(max_workers=len(leeks)) as ex:
        rows = list(ex.map(lambda nl: play(*nl), leeks))
    new = not os.path.exists(LOG)
    with open(LOG, 'a', newline='') as fh:
        wr = csv.writer(fh)
        if new:
            wr.writerow(['time', 'leek', 'fights', 'wins', 'losses', 'draws', 'talent_before', 'talent_after',
                         'v10_turns', 'watchdog_cuts', 'fallbacks'])
        wr.writerows(rows)
    print('credits left %d' % credits(lw), flush=True)


if __name__ == '__main__':
    main()
