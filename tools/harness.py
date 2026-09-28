#!/usr/bin/env python3
"""Phase-0 evaluation harness: paired local A/B of any git refs against
clones of real ladder leeks (2026-09-28).

Why: challenges resolve ~±15 pp at 20 per arm, StrongSTR fights are too short
and crash-prone, talent takes weeks. This runs hundreds of paired fights per
arm on the real engine (local generator), against opponents cloned from the
live API (exact equipped kit and stats), driven by V8 so it is not a mirror.

  # clone real leeks (by id or by name from data/ladder/our_solo.json)
  python3 tools/harness.py clone 103710 103626 84212 104242
  # A/B: arms are git refs (or WORKTREE, or V8); optional per-arm kit
  python3 tools/harness.py ab --leek MargaretHamilton \\
      --opps clone_TheLeaker,clone_BretzelLeekide --arm ctl=12e6e563 --arm citf=9114bef2 \\
      --kit '{"chips":[...],"weapons":[...]}' -n 60 -j 8 --log /tmp/h.json

Every arm plays the same seeds; the verdict per arm vs the first arm is
McNemar on the pooled discordant pairs, plus damage dealt / taken per turn,
turns per fight and end-HP lead (where most of the information is).
"""
import argparse, json, math, os, shutil, subprocess, sys, tempfile
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import local_test as lt
from lw_decode import Decoder, parse_fight

DEC = Decoder()
ARMS_DIR = os.path.join(REPO, 'harness_arms')
CONFIG = os.path.join(HERE, 'leek_configs.json')


# ---------------------------------------------------------------- clones
def cmd_clone(a):
    from lw_api import LWSession
    lw = LWSession(a.account)
    names = {}
    try:
        for f in json.load(open(os.path.join(REPO, 'data/ladder/our_solo.json'))).values():
            for l in (f.get('leeks1') or []) + (f.get('leeks2') or []):
                names[l.get('name')] = l.get('id')
    except Exception:
        pass
    cfg = json.load(open(CONFIG))
    opp = cfg.setdefault('opponents', {})
    for x in a.leeks:
        lid = int(x) if x.lstrip('-').isdigit() else names.get(x)
        if lid is None:
            print('unknown leek', x); continue
        l = lw.get('/leek/get/%d' % lid); l = l.get('leek', l)
        key = 'clone_' + ''.join(ch for ch in l['name'] if ch.isalnum())
        T = lambda k: l.get('total_' + k, l.get(k, 0))
        opp[key] = {
            'name': l['name'], 'id_live': lid, 'type': 0, 'level': l.get('level', 301),
            # total_* include equipment/components; the plain fields are base stats
            'life': T('life'), 'cores': 14, 'ram': 50, 'tp': T('tp'), 'mp': T('mp'),
            'strength': T('strength'), 'magic': T('magic'), 'agility': T('agility'),
            'wisdom': T('wisdom'), 'resistance': T('resistance'), 'science': T('science'),
            'frequency': T('frequency'),
            'weapons': [w['template'] for w in (l.get('weapons') or [])],
            'chips': [c['template'] for c in (l.get('chips') or [])],
            'ai_relative': a.ai, 'talent_at_clone': l.get('talent'),
        }
        print('%-28s talent %s  life %s TP %s MP %s STR %s MAG %s AGI %s RES %s WIS %s  %d chips %d weapons' % (
            key, l.get('talent'), T('life'), T('tp'), T('mp'), T('strength'), T('magic'), T('agility'), T('resistance'), T('wisdom'),
            len(opp[key]['chips']), len(opp[key]['weapons'])))
    json.dump(cfg, open(CONFIG, 'w'), indent=2)


# ---------------------------------------------------------------- arms
def materialise(name, ref):
    if ref == 'WORKTREE':
        return 'V9_modules/main.lk'
    if ref == 'V8':
        return 'V8_modules/main.lk'
    dst = os.path.join(ARMS_DIR, name)
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst, exist_ok=True)
    tar = subprocess.run(['git', 'archive', ref, 'V9_modules'], cwd=REPO, capture_output=True)
    if tar.returncode != 0:
        sys.exit('git archive %s failed: %s' % (ref, tar.stderr.decode()[:200]))
    with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as f:
        f.write(tar.stdout); tp = f.name
    subprocess.run(['tar', 'xf', tp, '-C', dst, '--strip-components=1'], check=True)
    os.remove(tp)
    link = os.path.join(str(lt.GENERATOR_DIR), 'H_' + name)
    if os.path.islink(link):
        os.remove(link)
    os.symlink(dst, link)
    return 'H_%s/main.lk' % name


def clear_cache():
    import glob
    for pat in ('*.class', '*.java', '*.lines', '*.sig'):
        for f in glob.glob(str(lt.GENERATOR_DIR / 'ai' / pat)):
            try:
                os.remove(f)
            except OSError:
                pass


# ---------------------------------------------------------------- fights
def _one(job):
    arm, leek_cfg, opp_key, opp_cfg, seed, ai = job
    lt.AI_PATH = ai
    scn = lt.build_scenario(leek_cfg, opp_cfg, seed=seed)
    for team in scn['entities']:
        for e in team:
            if e['team'] == 1:
                e['ai'] = ai
    r = lt.run_fight(scn)
    row = {'arm': arm, 'opp': opp_key, 'seed': seed}
    if r.get('error'):
        row.update(result='ERR', err=str(r['error'])[:200]); return row
    start = {l['id']: (max(l.get('life', 1), 1), l.get('team')) for l in r['leeks']}
    st = parse_fight({'leeks': r['leeks'], 'actions': r['actions']}, DEC)
    ours = them = 0.0; dealt = taken = 0
    for eid, (mx, team) in start.items():
        e = st.get(eid)
        if not e:
            continue
        hp = mx - sum(v for k, v in e['taken'].items() if k != 'nova') + e['healed']  # nova lowers max HP only
        pct = 0.0 if e['died'] else 100.0 * min(max(hp, 0), mx) / mx
        if team == 1:
            ours += pct; taken += sum(e['taken'].values())
        else:
            them += pct; dealt += sum(e['taken'].values())
    T = max(1, r['total_turns'])
    row.update(result=r['result'], turns=r['total_turns'], hp=ours - them, dealt_t=dealt / T,
               taken_t=taken / T, bug=bool(r.get('has_bug')))
    return row


def mcnemar_p(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def cmd_ab(a):
    cfg = lt.load_configs()
    leek = dict(cfg['leeks'][a.leek])
    arms = []
    for spec in a.arm:
        name, ref = spec.split('=', 1)
        arms.append((name, ref))
    kits = {}
    for spec in (a.arm_kit or []):
        name, js = spec.split('=', 1)
        kits[name] = json.loads(js)
    base_kit = json.loads(a.kit) if a.kit else {}
    opps = [o.strip() for o in a.opps.split(',') if o.strip()]
    for o in opps:
        if o not in cfg['opponents']:
            sys.exit('unknown opponent %s (clone it first)' % o)
    ai = {name: materialise(name, ref) for name, ref in arms}
    clear_cache()
    seeds = [a.seed0 + i for i in range(a.n)]
    jobs = []
    for name, _ in arms:
        lc = dict(leek); lc.update(base_kit); lc.update(kits.get(name, {}))
        for o in opps:
            for s in seeds:
                jobs.append((name, lc, o, cfg['opponents'][o], s, ai[name]))
    print('harness: %s vs %d opponents x %d seeds x %d arms = %d fights' % (
        a.leek, len(opps), a.n, len(arms), len(jobs)), flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=a.j) as ex:
        for i, r in enumerate(ex.map(_one, jobs, chunksize=2)):
            rows.append(r)
            if (i + 1) % 100 == 0:
                print('  ... %d/%d' % (i + 1, len(jobs)), flush=True)
    if a.log:
        json.dump({'leek': a.leek, 'arms': arms, 'opps': opps, 'rows': rows}, open(a.log, 'w'))
    report(rows, [n for n, _ in arms], opps)


def report(rows, arms, opps):
    by = {(r['arm'], r['opp'], r['seed']): r for r in rows}
    ok = lambda r: r and r['result'] != 'ERR'
    base = arms[0]

    def line(arm, sel):
        rs = [r for r in sel if ok(r)]
        n = len(rs)
        if not n:
            return '  %-10s n=0' % arm
        w = sum(r['result'] == 'WIN' for r in rs)
        m = lambda k: sum(r[k] for r in rs) / n
        return '  %-10s win %5.1f%% (%3d/%3d)  dealt/t %5.0f  taken/t %5.0f  turns %4.1f  hpLead %+6.1f' % (
            arm, 100 * w / n, w, n, m('dealt_t'), m('taken_t'), m('turns'), m('hp'))

    for o in opps + ['POOLED']:
        print('\n=== %s' % o)
        for arm in arms:
            sel = [r for r in rows if r['arm'] == arm and (o == 'POOLED' or r['opp'] == o)]
            print(line(arm, sel))
            if arm != base:
                keys = [(r['opp'], r['seed']) for r in sel]
                b = c = 0
                for (op, s) in keys:
                    x, y = by.get((base, op, s)), by.get((arm, op, s))
                    if not (ok(x) and ok(y)):
                        continue
                    if x['result'] == 'WIN' and y['result'] != 'WIN':
                        b += 1
                    if y['result'] == 'WIN' and x['result'] != 'WIN':
                        c += 1
                print('             vs %s: +%d / -%d flips, McNemar p=%.3f' % (base, c, b, mcnemar_p(b, c)))
    errs = [r for r in rows if r['result'] == 'ERR']
    if errs:
        print('\n%d errored fights; first: %s' % (len(errs), errs[0].get('err')))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('clone'); c.add_argument('leeks', nargs='+')
    c.add_argument('--ai', default='V8_modules/main.lk'); c.add_argument('--account', default='main')
    b = sub.add_parser('ab')
    b.add_argument('--leek', required=True); b.add_argument('--opps', required=True)
    b.add_argument('--arm', action='append', required=True, help='name=gitref|WORKTREE|V8 (first = baseline)')
    b.add_argument('--kit', help='JSON {"chips":[..],"weapons":[..]} applied to every arm')
    b.add_argument('--arm-kit', action='append', help='name=JSON kit override for one arm')
    b.add_argument('-n', type=int, default=60); b.add_argument('-j', type=int, default=8)
    b.add_argument('--seed0', type=int, default=9000); b.add_argument('--log')
    a = ap.parse_args()
    {'clone': cmd_clone, 'ab': cmd_ab}[a.cmd](a)


if __name__ == '__main__':
    main()
