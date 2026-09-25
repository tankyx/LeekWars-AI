#!/usr/bin/env python3
"""Daily garden run for the talent read (installed in crontab 2026-09-25).

Spends every garden credit on both accounts through the MCP server's own
`leekwars_solo_fight` smart selector (the same opponent picks as a manual
run), splitting each account's credits evenly across its leeks and
re-requesting the fights the selector drops (~40% "errors" per call). Then
appends one row per leek to data/ladder/talent_log.csv:
    date, account, leek, talent, fights, wins, losses, draws

It never uploads code or changes kits: the build under test stays fixed.

    python3 tools/daily_garden.py            # run
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


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true'); a = ap.parse_args()
    today = datetime.date.today().isoformat()
    print('=== daily_garden %s' % datetime.datetime.now().isoformat(timespec='seconds'), flush=True)
    rows = []
    mcp = None if a.dry_run else MCP()
    try:
        for acct, leeks in LEEKS.items():
            lw = LWSession(acct)
            avail = credits(lw)
            print('%s: %d credits' % (acct, avail), flush=True)
            per = {lid: avail // len(leeks) + (1 if k < avail % len(leeks) else 0) for k, (_, lid) in enumerate(leeks)}
            for name, lid in leeks:
                tot = [0, 0, 0, 0]
                if not a.dry_run:
                    need = per[lid]; tries = 0
                    while need > 0 and tries < 8:
                        tries += 1
                        done, w, l, d, _ = mcp.solo(acct, lid, need)
                        tot[0] += done; tot[1] += w; tot[2] += l; tot[3] += d
                        need -= done
                        if done == 0:
                            time.sleep(5)
                        if credits(lw) == 0:
                            break
                t = talent(lw, lid)
                print('  %-17s fights %2d  %dW/%dL/%dD  talent %d' % (name, tot[0], tot[1], tot[2], tot[3], t), flush=True)
                rows.append([today, acct, name, t] + tot)
            print('%s: %d credits left' % (acct, credits(lw)), flush=True)
    finally:
        if mcp:
            mcp.close()
    if not a.dry_run:
        new = not os.path.exists(LOG_CSV)
        with open(LOG_CSV, 'a', newline='') as fh:
            wr = csv.writer(fh)
            if new:
                wr.writerow(['date', 'account', 'leek', 'talent', 'fights', 'wins', 'losses', 'draws'])
            wr.writerows(rows)
        print('appended %d rows to %s' % (len(rows), LOG_CSV), flush=True)


if __name__ == '__main__':
    main()
