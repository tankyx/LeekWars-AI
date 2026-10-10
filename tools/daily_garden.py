#!/usr/bin/env python3
"""Daily garden run for the talent read (crontab 22:17 UTC: credits refresh at
22:00 UTC, i.e. midnight Paris; installed 2026-09-25, moved 2026-09-26).

Since 2026-10-03 it uses garden_fast's model selector (tools/garden_model.py), both
accounts in parallel: all day it only starts fights with positive expected talent
(each fight goes to the leek whose best offered opponent is worth the most; offers
are re-checked every 5 minutes) until 23:55 Paris;
it can spend what is left (--dump-at; off by default since 2026-10-04: dump fights won 29%).
--selector mcp restores the old MCP
`leekwars_solo_fight` path. Then appends one row per leek to data/ladder/talent_log.csv:
    date, account, leek, talent, fights, wins, losses, draws

It never uploads code or changes kits: the build under test stays fixed.

    python3 tools/daily_garden.py            # run (lasts until the dump, ~23 h)
    python3 tools/daily_garden.py --dry-run  # credits + talent only
"""
import argparse, csv, datetime, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession

LEEKS = {
    'main': [('AdaLovelace', 20443), ('EdsgerDijkstra', 129288), ('KurtGodel', 129295), ('MargaretHamilton', 129296)],
    'cure': [('LeekRain', 19703), ('DawnFall', 21175), ('DuskHope', 129801), ('ProdigalSon', 130236)],
}
LOG_CSV = os.path.join(ROOT, 'data', 'ladder', 'talent_log.csv')


class MCP:
    """Minimal JSON-RPC client for the stdio MCP server in .mcp.json."""

    def __init__(self):
        cfg = json.load(open(os.path.join(ROOT, '.mcp.json')))['mcpServers']['leekwars']
        env = dict(os.environ); env.update(cfg.get('env', {}))
        self.p = subprocess.Popen([cfg['command']] + cfg['args'], cwd=ROOT, env=env,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.n = 0
        self.call('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {},
                                 'clientInfo': {'name': 'daily_garden', 'version': '1'}})
        self.p.stdin.write(json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'}) + '\n'); self.p.stdin.flush()

    def call(self, method, params):
        self.n += 1; rid = self.n
        self.p.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params}) + '\n'); self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError('MCP server closed')
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if msg.get('id') == rid:
                if 'error' in msg:
                    raise RuntimeError(msg['error'])
                return msg.get('result')

    def solo(self, account, leek_id, n):
        r = self.call('tools/call', {'name': 'leekwars_solo_fight',
                                     'arguments': {'account': account, 'leek_id': leek_id, 'num_fights': n}})
        text = ''.join(c.get('text', '') for c in (r or {}).get('content', []))
        m = re.search(r'Fights:\s*(\d+)/(\d+)', text)
        rec = re.search(r'Record:\s*(\d+)W\s*/\s*(\d+)L\s*/\s*(\d+)D', text)
        done = int(m.group(1)) if m else 0
        w, l, d = (int(x) for x in rec.groups()) if rec else (0, 0, 0)
        return done, w, l, d, text

    def close(self):
        try:
            self.p.terminate()
        except Exception:
            pass


def credits(lw):
    g = lw.get('/garden/get'); g = g.get('garden', g)
    return int(g.get('fights') or 0)


def talent(lw, lid):
    l = lw.get('/leek/get/%d' % lid); l = l.get('leek', l)
    return int(l.get('talent', 0))


def run_model(acct, leeks, cap, dump_at, min_ev, out, reroll_ev=None, reroll_after=60.0):
    """garden_fast allocation for one account; out[acct] = {leek: (fights, W, L, D)}."""
    import garden_fast as gf
    from garden_model import Model
    lw = LWSession(acct)
    avail = min(credits(lw), cap)
    print('%s: %d credits available (model selector, min-ev %+.1f, reroll >= %s after %.0f min, %s)' % (
        acct, avail, min_ev, reroll_ev, reroll_after,
        ('dump at %s Paris' % dump_at) if dump_at else 'no dump: unspent credits carry over'), flush=True)
    if avail <= 0:
        out[acct] = {}
        return
    try:
        model = Model(acct)
    except Exception as ex:            # no model for this account yet: old MCP selector
        print('%s: no garden model (%s) - MCP selector instead' % (acct, ex), flush=True)
        return run_mcp(acct, leeks, cap, out)
    names = [n for n, _ in leeks]; ids = dict(leeks)
    if dump_at:
        res = gf.run_alloc(names, ids, avail, 4, gf.Bucket(4.5), acct, min_ev, 0.0, gf.paris_ts(dump_at), model)
    else:
        # positive offers only, until just before the next pool opens; the rest lapses
        wait = max(1.0, (gf.paris_ts('23:55') - time.time()) / 60.0)
        res = gf.run_alloc(names, ids, avail, 4, gf.Bucket(4.5), acct, min_ev, wait, None, model,
                           reroll_ev, reroll_after)
    out[acct] = {n: (r[0], r[1]['W'], r[1]['L'], r[1]['D']) for n, r in res.items()}
    print('%s: %d credits left' % (acct, credits(lw)), flush=True)


def run_xp(acct, leeks, out, inflight=2):
    """XP mode (Cure, levelling toward 300 for the Pumpkin): spend EVERY credit, best offer each
    time (no expected-talent floor), on the leeks still under level 300, then spend new capital
    with the xp_farm plans. Same health gate / crash guard / cut pause as the talent mode."""
    import garden_fast as gf
    import xp_farm as xf
    from garden_model import Model
    lw = LWSession(acct)
    avail = credits(lw)
    todo = [(n, lid) for n, lid in leeks if (lw.leek(lid).get('level') or 0) < 300]
    print('%s: XP mode, %d credits, leeks under 300: %s' % (acct, avail, [n for n, _ in todo]), flush=True)
    out[acct] = {}
    if avail <= 0 or not todo:
        return
    try:
        model = Model(acct)
    except Exception:
        model = None
    if model is None:
        print('%s: no garden model - XP mode needs one' % acct, flush=True); return
    names = [n for n, _ in todo]; ids = dict(todo)
    res = gf.run_alloc(names, ids, avail, inflight, gf.Bucket(4.5), acct, None, 30.0, None, model)
    out[acct] = {n: (r[0], r[1]['W'], r[1]['L'], r[1]['D']) for n, r in res.items()}
    xl = xf.Limited(lw, 4.0)
    for n, lid in todo:
        try:
            sp = xf.spend_capital(xl, lid, n)
            l = lw.leek(lid)
            print('  %s level %s, capital spent on %s' % (n, l.get('level'), sorted(set(sp)) or '-'), flush=True)
        except Exception as ex:
            print('  %s capital spending failed: %s' % (n, ex), flush=True)
    print('%s: %d credits left' % (acct, credits(lw)), flush=True)


def run_xp_farmer(acct, leeks, out, inflight=2):
    """XP mode with FARMER fights: one credit levels all the account's leeks at once
    (main's farmer fights: ~33k XP per credit across 4 leeks, vs ~3.8k for a solo fight).
    Opponent = weakest offered farmer (safest win). Health probe + cut pause as in garden_fast.
    Logs XP per fight to data/ladder/xp_farmer.jsonl."""
    import garden_fast as gf
    import xp_farm as xf
    lw = LWSession(acct); ids = {lid for _, lid in leeks}
    avail = credits(lw)
    print('%s: XP mode (farmer fights), %d credits' % (acct, avail), flush=True)
    out[acct] = {}
    if avail <= 0:
        return
    if not gf.health_probe(lw, leeks[0][1]):
        print('%s: health probe DEGRADED - no farmer fights now' % acct, flush=True); return
    logf = open(os.path.join(ROOT, 'data', 'ladder', 'xp_farmer.jsonl'), 'a')
    pend = {}; started = done = xp_tot = 0; rec = [0, 0, 0]; recent = []; fails = 0
    while (started < avail or pend) and fails < 10:
        while started < avail and len(pend) < inflight:
            ops = (lw.get('/garden/get-farmer-opponents') or {}).get('opponents') or []
            if not ops:
                fails += 1; time.sleep(5); break
            o = min(ops, key=lambda x: x.get('talent') or 0)
            r = lw.post('/garden/start-farmer-fight', target_id=o['id'])
            fid = r if isinstance(r, int) else (r.get('fight') if isinstance(r, dict) else None)
            if not fid:
                err = r.get('error') if isinstance(r, dict) else r
                if err in ('too_many_fights', 'no_more_fights'):
                    avail = started; break
                fails += 1; time.sleep(2); continue
            pend[fid] = o; started += 1
        time.sleep(3)
        for fid in list(pend):
            f = lw.get('/fight/get/%d' % fid); f = f.get('fight', f)
            if f.get('status') != 2:
                continue
            o = pend.pop(fid); rp = f.get('report') or {}
            ours1 = any(l.get('id') in ids for l in f.get('leeks1') or [])
            w = f.get('winner'); res = 'D' if w == 0 else ('W' if w == (1 if ours1 else 2) else 'L')
            rec['WLD'.index(res)] += 1
            xp = sum(l.get('xp') or 0 for side in ('leeks1', 'leeks2') for l in rp.get(side) or [] if l.get('id') in ids)
            xp_tot += xp; done += 1
            bad = gf.fight_degraded(lw.get, fid); recent = (recent + [bad])[-6:]
            logf.write(json.dumps({'fight': fid, 'opp': o.get('name'), 'opp_talent': o.get('talent'), 'result': res,
                                   'xp': xp, 'degraded': bad}) + '\n'); logf.flush()
            if sum(recent) >= 3:
                print('  %s farmer fights degraded (3 of last 6) - stopping' % acct, flush=True)
                avail = started
    print('%s: %d farmer fights %dW/%dL/%dD, %.0f XP per fight' % (acct, done, rec[0], rec[1], rec[2], xp_tot / max(1, done)), flush=True)
    out[acct] = {n: (done, rec[0], rec[1], rec[2]) for n, _ in leeks}
    xl = xf.Limited(lw, 4.0)
    for n, lid in leeks:
        try:
            sp = xf.spend_capital(xl, lid, n); l = lw.leek(lid)
            print('  %s level %s, capital spent on %s' % (n, l.get('level'), sorted(set(sp)) or '-'), flush=True)
        except Exception as ex:
            print('  %s capital spending failed: %s' % (n, ex), flush=True)


def run_mcp(acct, leeks, cap, out):
    lw = LWSession(acct)
    avail = credits(lw)
    print('%s: %d credits, spending up to %d (MCP selector)' % (acct, avail, cap), flush=True)
    avail = min(avail, cap)
    per = {lid: avail // len(leeks) + (1 if k < avail % len(leeks) else 0) for k, (_, lid) in enumerate(leeks)}
    mcp = MCP(); out[acct] = {}
    try:
        for name, lid in leeks:
            tot = [0, 0, 0, 0]; need = per[lid]; tries = 0
            while need > 0 and tries < 8:
                tries += 1
                done, w, l, d, _ = mcp.solo(acct, lid, need)
                tot[0] += done; tot[1] += w; tot[2] += l; tot[3] += d
                need -= done
                if done == 0:
                    time.sleep(5)
                if credits(lw) == 0:
                    break
            out[acct][name] = tuple(tot)
    finally:
        mcp.close()


def main():
    import threading
    ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--accounts', default='main,cure', help='comma list (default both)')
    ap.add_argument('--cap', type=int, default=100, help='max fights per account per run (bought fights stay for manual batches)')
    ap.add_argument('--selector', default='model', choices=['model', 'mcp'])
    ap.add_argument('--dump-at', default=None, help='Paris time to spend the remaining credits anyway (default: never; '
                    'dump fights won 29%% on 2026-10-03, talent is the metric)')
    ap.add_argument('--min-ev', type=float, default=0.0, help='expected talent a fight needs before the dump')
    ap.add_argument('--reroll-ev', type=float, default=-2.5,
                    help='a leek whose list has been stale for --reroll-after min takes an offer >= this (refreshes its list)')
    ap.add_argument('--reroll-after', type=float, default=45.0)
    ap.add_argument('--xp-accounts', default='cure', help='accounts run in XP mode (spend all credits)')
    ap.add_argument('--xp-mode', default='farmer', choices=['farmer', 'solo'], help='XP mode fight type (farmer levels all leeks per credit)')
    a = ap.parse_args()
    # Label by the Paris day of the credit pool (pools open at midnight Paris).
    from zoneinfo import ZoneInfo
    today = datetime.datetime.now(ZoneInfo('Europe/Paris')).date().isoformat()
    print('=== daily_garden %s (%s selector)' % (datetime.datetime.now().isoformat(timespec='seconds'), a.selector), flush=True)
    accts = [x for x in LEEKS if x in a.accounts.split(',')]
    out = {}
    if not a.dry_run:
        xp = [x for x in a.xp_accounts.split(',') if x]
        if a.selector == 'model':
            th = [threading.Thread(target=(run_xp_farmer if a.xp_mode == 'farmer' else run_xp), args=(x, LEEKS[x], out)) if x in xp else
                  threading.Thread(target=run_model, args=(x, LEEKS[x], a.cap, a.dump_at, a.min_ev, out,
                                                           a.reroll_ev, a.reroll_after)) for x in accts]
        else:
            th = [threading.Thread(target=run_mcp, args=(x, LEEKS[x], a.cap, out)) for x in accts]
        for t in th:
            t.start()
        for t in th:
            t.join()
    rows = []
    for acct in accts:
        lw = LWSession(acct)
        for name, lid in LEEKS[acct]:
            tot = list(out.get(acct, {}).get(name, (0, 0, 0, 0)))
            t = talent(lw, lid)
            print('  %-17s fights %2d  %dW/%dL/%dD  talent %d' % (name, tot[0], tot[1], tot[2], tot[3], t), flush=True)
            rows.append([today, acct, name, t] + tot)
    if a.dry_run:
        for acct in accts:
            print('%s: %d credits' % (acct, credits(LWSession(acct))), flush=True)
        return
    if sum(r[4] for r in rows) == 0:
        print('no fights played (no credits) - nothing logged', flush=True)
        return
    new = not os.path.exists(LOG_CSV)
    with open(LOG_CSV, 'a', newline='') as fh:
        wr = csv.writer(fh)
        if new:
            wr.writerow(['date', 'account', 'leek', 'talent', 'fights', 'wins', 'losses', 'draws'])
        wr.writerows(rows)
    print('appended %d rows to %s' % (len(rows), LOG_CSV), flush=True)


if __name__ == '__main__':
    main()
