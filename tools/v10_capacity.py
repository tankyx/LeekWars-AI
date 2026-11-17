#!/usr/bin/env python3
"""Server speed probe for V10: how many reported operations of real V10 search fit in the 5 s turn watchdog.

A free test fight (no credits, no talent) of the probe AI 10.0/V10/v10_probe.py - the neutral V10 with no budget,
searching again and again from turn 2 until the watchdog cuts the turn, logging its operation count every 250k.
The last count logged before each cut is the capacity. Up to 3 samples per fight (3 cuts disable an AI).
V10 budgets 7M a turn: watchdog cuts on the ladder happen when the capacity falls near that.

    python3 tools/v10_capacity.py              # one probe, prints the samples (millions of operations)
    python3 tools/v10_capacity.py --upload     # rebuild the probe from V10/ab/cap_min.py first
    python3 tools/v10_capacity.py --watch 600  # one probe every 600 s, appended to data/ladder/capacity_log.csv
"""
import argparse, json, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession

PROBE_AI = '10.0/V10/v10_probe.py'
LOG = os.path.join(ROOT, 'data', 'ladder', 'capacity_log.csv')
RC = re.compile(r'V10C T(\d+) ops (\d+)')


def capacity_probe(lw, leek_id=20443, wait=150):
    """[capacity in operations per cut turn] (empty list = no cut: the fight ended first), or None on failure."""
    sid = None
    try:
        sid = lw.post('/test-scenario/new', name='cap_%d' % (int(time.time()) % 100000)).get('id')
        lw.post('/test-scenario/update', id=sid, data=json.dumps({'type': 0, 'map': None, 'ai': PROBE_AI}))
        lw.post('/test-scenario/add-leek', scenario_id=sid, leek=leek_id, team=0, ai=PROBE_AI)
        lw.post('/test-scenario/add-leek', scenario_id=sid, leek=-1, team=1, ai=-2)
        r = lw.post('/ai/test-scenario', scenario_id=sid, ai_id=PROBE_AI)
        fid = r.get('fight') if isinstance(r, dict) else None
        if not fid:
            return None
        t0 = time.time(); done = False
        while time.time() - t0 < wait:
            time.sleep(5)
            f = lw.get('/fight/get/%d' % fid); f = f.get('fight', f) if isinstance(f, dict) else {}
            if f.get('status') == 2:
                done = True
                break
        if not done:
            return None
        lg = lw.get('/fight/get-logs/%d' % fid)
        caps = []; last = None
        for ent in (lg.values() if isinstance(lg, dict) else []):
            for k in sorted(ent, key=int):
                for it in ent[k]:
                    s = it[2] if len(it) > 2 and isinstance(it[2], str) else ''
                    m = RC.match(s)
                    if m:
                        last = int(m.group(2))
                    elif 'too_much_ops' in json.dumps(it) and last is not None:
                        caps.append(last); last = None
        return caps
    except Exception as ex:
        print('capacity probe error %s: %s' % (type(ex).__name__, ex), flush=True)
        return None
    finally:
        if sid:
            try:
                lw.call('DELETE', '/test-scenario/delete', id=sid)
            except Exception:
                pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--account', default='main'); ap.add_argument('--leek', type=int, default=20443)
    ap.add_argument('--upload', action='store_true'); ap.add_argument('--watch', type=float, default=0.0)
    a = ap.parse_args()
    lw = LWSession(a.account)
    if a.upload:
        code = open(os.path.join(ROOT, 'V10', 'ab', 'cap_min.py')).read()
        r = lw.s.post('https://leekwars.com/api/ai/write', data={'path': PROBE_AI, 'code': code}).json()
        print('upload:', str(r)[:160])
    while True:
        caps = capacity_probe(lw, a.leek)
        line = '%s,%s' % (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()), 'fail' if caps is None else ' '.join('%.2f' % (c / 1e6) for c in caps))
        print(line, flush=True)
        if a.watch <= 0:
            break
        with open(LOG, 'a') as f:
            f.write(line + '\n')
        time.sleep(a.watch)


if __name__ == '__main__':
    main()
