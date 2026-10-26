#!/usr/bin/env python3
"""Multi-day live challenge A/B of two server AI paths, pooled (2026-10-26).

50-pair A/Bs only see effects of ~15 points: run the same A/B every day on several leeks of both accounts and
pool. One call = one day: per leek, fresh opponents within +-200 talent (from its garden history), 1 seed each,
interleaved A/B challenges through tools/v10_challenge_ab.py, pairs appended to --out.

    python3 tools/multi_ab.py run --b 10.0/V10/v10_e.py --out data/ladder/combo_ab.jsonl \\
        --leeks main:20443:17,main:129288:17,main:129295:16,cure:130236:25,cure:19703:25
    python3 tools/multi_ab.py report data/ladder/combo_ab.jsonl
"""
import argparse, datetime, json, math, os, random, sqlite3, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def opponents(acct, lid, n, band, seed):
    from lw_api import LWSession
    lw = LWSession(acct); t = lw.leek(lid)['talent']
    db = sqlite3.connect(os.path.join(HERE, 'fight_history_%d.db' % lid))
    ids = [r[0] for r in db.execute('SELECT DISTINCT opponent_id FROM fight_history ORDER BY timestamp DESC LIMIT 600')]
    random.Random(seed).shuffle(ids); out = []
    for oid in ids:
        if len(out) >= n:
            break
        o = lw.leek(oid)
        if o.get('id') and abs((o.get('talent') or 0) - t) <= band and (o.get('level') or 0) >= 290:
            out.append(oid)
    return out


def run_account(acct, jobs, a, day):
    for lid, n in jobs:
        opps = opponents(acct, lid, n, a.band, int(day.replace('-', '')) * 1000003 + lid)
        if not opps:
            continue
        cmd = [sys.executable, '-u', os.path.join(HERE, 'v10_challenge_ab.py'), '--account', acct, '--leek', str(lid),
               '--opps', ','.join(map(str, opps)), '--seeds', '1', '--a', a.a, '--b', a.b, '--interleave', '--out', a.out]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        tail = [l for l in r.stdout.splitlines() if l.startswith(('A ', 'HP lead', '  A ', '  B ')) or 'challenges' in l]
        print('%s %s %d: %s' % (day, acct, lid, ' | '.join(tail[-3:])), flush=True)
        if 'not_enought' in r.stdout:
            break


def cmd_run(a):
    day = datetime.date.today().isoformat()
    by = {}
    for x in a.leeks.split(','):
        acct, lid, n = x.split(':')
        by.setdefault(acct, []).append((int(lid), int(n)))
    with ThreadPoolExecutor(len(by)) as ex:            # the two accounts' allowances are separate: in parallel
        list(ex.map(lambda kv: run_account(kv[0], kv[1], a, day), by.items()))
    cmd_report(argparse.Namespace(file=a.out))


def cmd_report(a):
    rows = [json.loads(l) for l in open(a.file) if l.strip()]
    ok = [r for r in rows if r.get('ra') is not None and r.get('rb') is not None]
    bw = sum(1 for r in ok if r['rb'] > r['ra']); aw = sum(1 for r in ok if r['ra'] > r['rb'])
    n = bw + aw; k = min(bw, aw)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n) if n else 1.0
    print('%d pairs (%d days): A %.1f  B %.1f | discordant B better %d / A better %d, sign p = %.3f' % (
        len(ok), len({datetime.date.fromtimestamp(r['date']) for r in ok}), sum(r['ra'] for r in ok), sum(r['rb'] for r in ok), bw, aw, p))
    d = [r['lb'] - r['la'] for r in ok if r.get('la') is not None and r.get('lb') is not None]
    if len(d) > 2:
        m = sum(d) / len(d); sd = math.sqrt(sum((x - m) ** 2 for x in d) / (len(d) - 1)) or 1e-9
        print('HP lead B - A: %+.3f over %d pairs (sd %.3f, t %.2f)' % (m, len(d), sd, m / (sd / math.sqrt(len(d)))))
    for lid in sorted({r['leek'] for r in ok}):
        sub = [r for r in ok if r['leek'] == lid]
        print('  leek %-7d %3d pairs  A %.1f  B %.1f' % (lid, len(sub), sum(r['ra'] for r in sub), sum(r['rb'] for r in sub)))


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('--a', default='10.0/V10/v10.py'); r.add_argument('--b', required=True)
    r.add_argument('--leeks', required=True, help='account:leek_id:pairs,...')
    r.add_argument('--out', required=True); r.add_argument('--band', type=int, default=200)
    p = sub.add_parser('report'); p.add_argument('file')
    a = ap.parse_args()
    (cmd_run if a.cmd == 'run' else cmd_report)(a)


if __name__ == '__main__':
    main()
