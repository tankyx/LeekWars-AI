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

Team fights (both accounts, separate daily pool) run on their own thread through the MCP
leekwars_team_fights tool (--no-team to skip).

It never uploads code or changes kits: the build under test stays fixed.

    python3 tools/daily_garden.py            # run (lasts until the dump, ~23 h)
    python3 tools/daily_garden.py --dry-run  # credits + talent only
"""
import argparse, collections, csv, datetime, json, os, re, subprocess, sys, time

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

    def team(self, account):
        """leekwars_team_fights (smart): drains every composition's daily team pool, one fight
        at a time. Returns (fights, wins, losses, draws, text)."""
        r = self.call('tools/call', {'name': 'leekwars_team_fights', 'arguments': {'account': account, 'strategy': 'smart'}})
        text = ''.join(c.get('text', '') for c in (r or {}).get('content', []))
        m = re.search(r'Total fights:\s*(\d+)', text)
        rec = re.search(r'Record:\s*(\d+)W\s*/\s*(\d+)L\s*/\s*(\d+)D', text)
        n = int(m.group(1)) if m else 0
        w, l, d = (int(x) for x in rec.groups()) if rec else (0, 0, 0)
        return n, w, l, d, text

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


XP_CHUNK = 15


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
    # chunks of XP_CHUNK fights so the run stops as soon as every leek reaches 300 (owner 2026-10-19:
    # DawnFall to 300, then the credits go to DuskHope's talent - see --focus)
    agg = {}
    while True:
        avail = credits(lw)
        left = [(n, lid) for n, lid in todo if (lw.leek(lid).get('level') or 0) < 300]
        if avail <= 0 or not left:
            break
        res = gf.run_alloc([n for n, _ in left], dict(left), min(avail, XP_CHUNK), inflight, gf.Bucket(4.5), acct,
                           None, 30.0, None, model)
        played = 0
        for n, r in res.items():
            t = agg.setdefault(n, [0, 0, 0, 0])
            t[0] += r[0]; t[1] += r[1]['W']; t[2] += r[1]['L']; t[3] += r[1]['D']; played += r[0]
        if played == 0:
            break                  # no fight went through (degraded server, no offers): stop here
    out[acct] = {n: tuple(t) for n, t in agg.items()}
    xl = xf.Limited(lw, 4.0)
    for n, lid in todo:
        try:
            sp = xf.spend_capital(xl, lid, n)
            l = lw.leek(lid)
            print('  %s level %s, capital spent on %s' % (n, l.get('level'), sorted(set(sp)) or '-'), flush=True)
        except Exception as ex:
            print('  %s capital spending failed: %s' % (n, ex), flush=True)
    print('%s: %d credits left' % (acct, credits(lw)), flush=True)


def run_xp_farmer(acct, leeks, out, inflight=2, cap=None):
    """XP mode with FARMER fights: one credit levels all the account's leeks at once
    (main's farmer fights: ~33k XP per credit across 4 leeks, vs ~3.8k for a solo fight).
    Opponent = weakest offered farmer (safest win). Health probe + cut pause as in garden_fast.
    Logs XP per fight to data/ladder/xp_farmer.jsonl."""
    import garden_fast as gf
    import xp_farm as xf
    lw = LWSession(acct); ids = {lid for _, lid in leeks}
    avail = credits(lw) if cap is None else min(cap, credits(lw))
    print('%s: farmer fights, %d credits%s' % (acct, avail, '' if cap is None else ' (cap %d)' % cap), flush=True)
    out[acct] = {}
    if avail <= 0:
        return
    if not gf.health_probe(lw, leeks[0][1]):
        print('%s: health probe DEGRADED - no farmer fights now' % acct, flush=True); return
    logf = open(os.path.join(ROOT, 'data', 'ladder', 'xp_farmer.jsonl'), 'a')
    pend = {}; started = done = xp_tot = 0; rec = [0, 0, 0]; recent = []; fails = 0; loot = collections.Counter()
    names = {int(k): v.get('name') for k, v in (lw.get('/item/get-all') or {}).items() if str(k).isdigit()}
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
            got = collections.Counter()
            for l in rp.get('leeks1') or []:
                if l.get('id') in ids:
                    res_ = l.get('resources') or {}
                    if isinstance(res_, str):
                        res_ = json.loads(res_.replace("'", '"'))
                    for t, q in res_.items():
                        got[names.get(int(t), str(t))] += q
            loot.update(got)
            bad = gf.fight_degraded(lw.get, fid); recent = (recent + [bad])[-6:]
            logf.write(json.dumps({'fight': fid, 'opp': o.get('name'), 'opp_talent': o.get('talent'), 'result': res,
                                   'xp': xp, 'degraded': bad, 'loot': dict(got)}) + '\n'); logf.flush()
            if sum(recent) >= 3:
                print('  %s farmer fights degraded (3 of last 6) - stopping' % acct, flush=True)
                avail = started
    print('%s: %d farmer fights %dW/%dL/%dD, %.0f XP per fight | loot %s' % (acct, done, rec[0], rec[1], rec[2], xp_tot / max(1, done),
          dict(loot.most_common(12))), flush=True)
    out[acct] = {n: (done, rec[0], rec[1], rec[2]) for n, _ in leeks}
    xl = xf.Limited(lw, 4.0)
    for n, lid in leeks:
        try:
            sp = xf.spend_capital(xl, lid, n); l = lw.leek(lid)
            print('  %s level %s, capital spent on %s' % (n, l.get('level'), sorted(set(sp)) or '-'), flush=True)
        except Exception as ex:
            print('  %s capital spending failed: %s' % (n, ex), flush=True)


def run_team(accts, out):
    """Team fights for every account (separate daily pool, ~28k XP per fight on Cure)."""
    try:
        mcp = MCP()
    except Exception as ex:
        print('team fights: MCP unavailable (%s)' % ex, flush=True); return
    try:
        for acct in accts:
            try:
                n, w, l, d, text = mcp.team(acct)
                out[acct] = (n, w, l, d)
                print('%s: team fights %d  %dW/%dL/%dD' % (acct, n, w, l, d), flush=True)
            except Exception as ex:
                print('%s: team fights failed (%s)' % (acct, ex), flush=True)
    finally:
        mcp.close()


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
    ap.add_argument('--xp-mode', default='auto', choices=['auto', 'farmer', 'solo'],
                    help='XP mode fight type: farmer levels all leeks per credit; auto = farmer while 2+ leeks are under '
                         '300, solo on the last one, talent mode once all are 300')
    ap.add_argument('--no-team', action='store_true', help='skip the daily team fights')
    ap.add_argument('--focus', default='',
                    help='talent mode only on these leeks, "acct:Leek+Leek,acct2:..." (owner 2026-10-19: Cure talent on '
                         'DuskHope); also where an XP account spends what is left once every leek is 300; "" = all leeks')
    ap.add_argument('--boss-slot', default='off',               # owner 2026-10-20 evening: back to normal ladder
                    help='8-leek boss fights (main + Cure, tools/boss_slot.py) before anything else: "<boss>:<n|all>" '
                         '(3 = Pumpkin, 2 = Fennel) or "off" (owner 2026-10-20: "Focus on bosses", every credit to the Pumpkin)')
    ap.add_argument('--caps', default='cure:200', help='per-account caps overriding --cap, "acct:N,..." '
                    '(owner 2026-10-21: Cure farms talent and resources with its bought credits)')
    ap.add_argument('--farmer-after', default='cure:20',       # owner 2026-10-23: cut from 100 (commons only; talent gets the rest)
                    help='before an account\'s talent fights (runs first), up to N farmer fights for loot '
                         '(4 rolls a credit, leek talent untouched): "acct:N,..."; "" = none')
    ap.add_argument('--talent', default='on', choices=['on', 'off'],
                    help='garden talent / XP fights after the boss slot (owner 2026-10-20: off - everything to bosses)')
    a = ap.parse_args()
    # Label by the Paris day of the credit pool (pools open at midnight Paris).
    from zoneinfo import ZoneInfo
    today = datetime.datetime.now(ZoneInfo('Europe/Paris')).date().isoformat()
    # dated focus override (owner 2026-10-27: the 6 leeks respecced for the Pumpkin sit out the ladder until the
    # revert): data/ladder/garden_focus_override.json = {"until": "<paris date>", "focus": "acct:A+B,...", "no_team": true}
    try:
        fo = json.load(open(os.path.join(ROOT, 'data', 'ladder', 'garden_focus_override.json')))
        if today <= fo['until'] and not a.focus:
            a.focus = fo['focus']; a.no_team = a.no_team or bool(fo.get('no_team'))
            # owner 2026-10-27 "beat the pumpkin, whatever is necessary": the nightly 8-leek Pumpkin slot and no
            # loot farmer fights, so the credits go to the Pumpkin
            if 'boss_slot' in fo and a.boss_slot == 'off':
                a.boss_slot = fo['boss_slot']
            if 'farmer_after' in fo:
                a.farmer_after = fo['farmer_after']
            print('focus override until %s: %s%s, boss slot %s, farmer fights %r' % (
                fo['until'], a.focus, ', no team fights' if a.no_team else '', a.boss_slot, a.farmer_after), flush=True)
    except FileNotFoundError:
        pass
    print('=== daily_garden %s (%s selector)' % (datetime.datetime.now().isoformat(timespec='seconds'), a.selector), flush=True)
    accts = [x for x in LEEKS if x in a.accounts.split(',')]
    out = {}
    if not a.dry_run and a.boss_slot != 'off' and 'main' in accts and 'cure' in accts:
        boss, n = a.boss_slot.split(':')
        try:
            p = subprocess.run([sys.executable, '-u', os.path.join(HERE, 'boss_slot.py'), '--boss', boss, '--n', n],
                               cwd=ROOT, timeout=6 * 3600)
            if p.returncode == 2:
                print('main is not on its ladder setup after the boss slot - main skipped today', flush=True)
                accts = [x for x in accts if x != 'main']
        except subprocess.TimeoutExpired:
            print('boss slot timed out - main skipped today (check its loadouts)', flush=True)
            accts = [x for x in accts if x != 'main']
    if not a.dry_run:
        xp = [x for x in a.xp_accounts.split(',') if x]

        def xp_runner(acct):
            """Farmer fights share a credit's XP across all 4 leeks (~11k per fight, 2026-10 log), solo gives
            one leek ~3.5k: farmer pays while 2+ leeks still level, solo once only one does."""
            if a.xp_mode != 'auto':
                return run_xp_farmer if a.xp_mode == 'farmer' else run_xp
            lw = LWSession(acct)
            under = [n for n, lid in LEEKS[acct] if (lw.leek(lid).get('level') or 0) < 300]
            print('%s: leeks under 300: %s' % (acct, under or 'none - back to talent mode'), flush=True)
            return run_xp_farmer if len(under) >= 2 else (run_xp if under else None)
        runners = {x: xp_runner(x) if x in xp else None for x in accts}
        # one-off per-day caps (owner 2026-10-19: free credits for Pumpkin tests while keeping the
        # 300-credit reserve): data/ladder/garden_cap_override.json = {"<paris pool date>": {"main": 60}}
        caps = {x: a.cap for x in accts}
        for item in (a.caps or '').split(','):
            if ':' in item and item.split(':')[0] in caps:
                caps[item.split(':')[0]] = int(item.split(':')[1])
        farmer_after = {i.split(':')[0]: int(i.split(':')[1]) for i in (a.farmer_after or '').split(',') if ':' in i}
        try:
            ov = json.load(open(os.path.join(ROOT, 'data', 'ladder', 'garden_cap_override.json'))).get(today) or {}
            for x, v in ov.items():
                if x in caps:
                    caps[x] = min(caps[x], int(v)); print('%s: cap override for %s -> %d' % (x, today, caps[x]), flush=True)
        except FileNotFoundError:
            pass
        focus = {}
        for item in (a.focus or '').split(','):
            if ':' in item:
                acc, nms = item.split(':', 1)
                focus[acc.strip()] = [n.strip() for n in nms.split('+') if n.strip()]

        def talent_leeks(x):
            return [(n, lid) for n, lid in LEEKS[x] if not focus.get(x) or n in focus[x]]

        def xp_then_talent(x):
            # XP mode until every leek is 300, then the focus leeks' talent with the credits left
            o1, o2 = {}, {}
            runners[x](x, LEEKS[x], o1)
            if focus.get(x) and credits(LWSession(x)) > 0:
                print('%s: XP done - talent mode on %s with the credits left' % (x, focus[x]), flush=True)
                run_model(x, talent_leeks(x), caps[x], a.dump_at, a.min_ev, o2, a.reroll_ev, a.reroll_after)
            m = dict(o1.get(x, {}))
            for n, t in o2.get(x, {}).items():
                m[n] = tuple(u + v for u, v in zip(m.get(n, (0, 0, 0, 0)), t))
            out[x] = m

        if a.talent == 'off':
            print('talent fights off (--talent off): credits stay for the boss slot', flush=True)
            th = []
        elif a.selector == 'model':
            def farmer_then_talent(x):
                # loot farmer fights first (~10 min; they don't touch leek talent), then the all-day talent run,
                # so nothing runs into the next night's 22:17 start
                if farmer_after.get(x):
                    run_xp_farmer(x, LEEKS[x], {}, cap=farmer_after[x])
                run_model(x, talent_leeks(x), caps[x], a.dump_at, a.min_ev, out, a.reroll_ev, a.reroll_after)
            th = [threading.Thread(target=xp_then_talent, args=(x,)) if runners[x] else
                  threading.Thread(target=farmer_then_talent, args=(x,)) for x in accts]
        else:
            th = [threading.Thread(target=run_mcp, args=(x, LEEKS[x], caps[x], out)) for x in accts]
        team_out = {}
        if not a.no_team:
            th.append(threading.Thread(target=run_team, args=(accts, team_out)))
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
