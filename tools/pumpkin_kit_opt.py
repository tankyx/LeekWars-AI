#!/usr/bin/env python3
"""Chip-kit optimizer for the 8-leek Evil Pumpkin fight, on the local simulator (tools/local_pumpkin.py).

Swaps defensive chips (shields, heals) for owned damage chips / poisons, leek by leek, and keeps what the
simulator says helps. Weapons, stats and the AI are untouched; every kit is checked against what the two
accounts own (main = Virus: Kirby54 / GTGabi / Zoulman / Payou, Cure: LeekRain / DawnFall / DuskHope /
ProdigalSon) and against each leek's live chip slots (max_chips = the RAM of the live fights).

    python3 tools/pumpkin_kit_opt.py inventory                 # READ-ONLY API: owned chips, slots, Pumpkin loadouts
    python3 tools/pumpkin_kit_opt.py baseline                  # live Pumpkin kits -> data/sim_pumpkin/kitopt/base.kits.json
    python3 tools/pumpkin_kit_opt.py check FILE.kits.json      # slots, ownership, mandatory chips
    python3 tools/pumpkin_kit_opt.py eval FILE.kits.json --tag T --seed 301 --n 20 --parallel 4
    python3 tools/pumpkin_kit_opt.py compare A B               # paired by seed: all metrics, sign tests
    python3 tools/pumpkin_kit_opt.py usage TAG                 # per leek: chips cast, TP per category, damage
    python3 tools/pumpkin_kit_opt.py search --seed 301 --n 20 --budget-min 110 --parallel 4

Objective per fight (wins are ~0 in the sim): damage dealt to the mobs + 3000 x mob kills
- 2000 x our leeks dead by round 12 (bulbs / prototaxite excluded); wins are reported too.

search: coordinate descent from the baseline. Round 1 tries squad-wide moves (every STR leek, every mage,
everyone: k defensive chips -> k damage chips). Then per leek, in turn order, a few variants of that leek's
kit (more / fewer swaps, shields-first or heals-first drop order) with the other seven fixed; a variant is
kept when its mean objective beats the incumbent on the same seeds by more than --margin x the paired
standard error, and again once both are extended to the next n seeds (--no-recheck skips that). Every evaluated kit lands in data/sim_pumpkin/kitopt/log.jsonl; fights are cached by tag
(<tag>_<seed>.json), so an interrupted search resumes for free. Confirm the result on fresh seeds:

    python3 tools/pumpkin_kit_opt.py eval data/sim_pumpkin/kitopt/best.kits.json --tag kbest_c --seed 401 --n 40
    python3 tools/pumpkin_kit_opt.py eval data/sim_pumpkin/kitopt/base.kits.json --tag kbase_c --seed 401 --n 40
    python3 tools/pumpkin_kit_opt.py compare kbase_c kbest_c

Never writes to the server: the API calls are GETs (plus the login).
"""
import argparse, glob, hashlib, json, math, os, statistics, sys, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import local_pumpkin as lp  # noqa: E402
from pumpkin_fights import CHIPS, turns  # noqa: E402
from pumpkin_ab import fight_stats, sign_p  # noqa: E402

OUT = lp.OUT
KDIR = os.path.join(OUT, 'kitopt')
INV = os.path.join(KDIR, 'inventory.json')
LOG = os.path.join(KDIR, 'log.jsonl')
ACCOUNTS = {'main': {'Kirby54': 20443, 'GTGabi': 129288, 'Zoulman': 129295, 'Payou': 129296},
            'cure': {'LeekRain': 19703, 'DawnFall': 21175, 'DuskHope': 129801, 'ProdigalSon': 130236}}
ACCOUNT_OF = {n: a for a, L in ACCOUNTS.items() for n in L}
LOADOUT = {'Kirby54': 'AL Pumpkin', 'GTGabi': 'ED Pumpkin', 'Zoulman': 'KG Pumpkin', 'Payou': 'MH Pumpkin'}
ORDER = ('Kirby54', 'ProdigalSon', 'DawnFall', 'Zoulman', 'GTGabi', 'LeekRain', 'Payou', 'DuskHope')  # turn order
MAGES = ('Payou', 'DawnFall', 'DuskHope')          # MAG > STR (template 54297638)
STRIKERS = ('Kirby54', 'ProdigalSon', 'Zoulman', 'GTGabi', 'LeekRain')

# riddle / blocking tools: never swapped out (teleportation is mandatory on every leek)
MANDATORY = ('teleportation',)
PROTECTED = {'teleportation', 'prototaxite', 'seven_league_boots', 'leather_boots', 'jump', 'puny_bulb', 'wizard_bulb',
             'savant_bulb', 'tactician_bulb', 'lightning_bulb', 'healer_bulb', 'metallic_bulb', 'iced_bulb', 'rocky_bulb',
             'fire_bulb', 'resurrection'}
# defensive chips, in drop order (first dropped first). 'shields': the shields V10 casts every turn the army is
# near (pumpkin_turn / pk_defend: solidification, fortress, wall first, then armor ... ) go before the heals;
# 'heals': the reverse.
SHIELDS = ['armor', 'helmet', 'shield', 'carapace', 'dome', 'rampart', 'wall', 'fortress', 'solidification']
HEALS = ['serum', 'vaccine', 'elevation', 'antidote', 'regeneration', 'knowledge', 'remission']
UTIL = ['armoring', 'liberation']
DROP = {'shields': UTIL + SHIELDS + HEALS, 'heals': UTIL + HEALS + SHIELDS}
# damage chips by preference. STR: point damage first (V10 never casts an area that covers an ally, and 8
# leeks crowd the mobs), then area chips by damage per TP; MAG: poisons (V10's attack() casts them first for
# a mage; pk_provoke casts them on invincible mobs too, where they only tick once the protection drops).
# 'shk': MAG-scaled shackles - they land through Divine Protection (generator: only damage / poison ticks check
# INVINCIBLE), and V10's pk_provoke casts debuffing chips on the invincible mobs with the TP left after shields.
DMG = {'str': ['stalactite', 'iceberg', 'rockfall', 'meteorite', 'lightning', 'rock', 'flame', 'burning', 'flash'],
       'mag': ['covid', 'arsenic', 'plague', 'toxin', 'venom'],
       'shk': ['fracture', 'tranquilizer', 'soporific', 'ball_and_chain', 'slow_down']}
W_KILL, W_DEAD = 3000, 2000


def role(name):
    return 'mag' if name in MAGES else 'str'


# ---------------------------------------------------------------- inventory (read-only API)
def cmd_inventory(a):
    from lw_api import LWSession
    out = {'fetched': time.strftime('%Y-%m-%d %H:%M:%S'), 'accounts': {}}
    names = None
    for acct, leeks in ACCOUNTS.items():
        lw = LWSession(acct)
        if names is None:
            I = lw.get('/item/get-all'); I = I.get('items', I)
            names = {int(k): v['name'] for k, v in I.items()}
        nm = lambda t: names.get(t, str(t)).replace('chip_', '')
        f = lw.get('/farmer/get-from-token'); f = f.get('farmer', f)
        inv = {}
        for x in f.get('chips') or []:
            if (x.get('quantity') or 0) > 0:
                inv[nm(x['template'])] = inv.get(nm(x['template']), 0) + x['quantity']
        L = {}
        for n, lid in leeks.items():
            l = lw.leek(lid)
            L[n] = {'id': lid, 'max_chips': l['max_chips'], 'equipped': [nm(c['template']) for c in l['chips']]}
        owned = dict(inv)
        for v in L.values():
            for c in v['equipped']:
                owned[c] = owned.get(c, 0) + 1
        lo = {}
        if acct == 'main':
            d = lw.get('/loadout/get-all')
            for x in d.get('loadouts') or []:
                if x['name'].endswith('Pumpkin'):
                    lo[x['name']] = [nm(t) for t in x['chips']]
        out['accounts'][acct] = {'inventory': inv, 'leeks': L, 'owned': owned, 'loadouts': lo}
        print('%s: %d chip kinds owned; slots %s' % (acct, len(owned), {n: v['max_chips'] for n, v in L.items()}))
    os.makedirs(KDIR, exist_ok=True)
    json.dump(out, open(INV, 'w'), indent=1)
    print('saved', INV)


def inventory():
    if not os.path.exists(INV):
        sys.exit('no %s - run "inventory" first' % INV)
    return json.load(open(INV))


def slots(inv):
    return {n: inv['accounts'][ACCOUNT_OF[n]]['leeks'][n]['max_chips'] for n in ORDER}


def owned(inv, acct):
    return dict(inv['accounts'][acct]['owned'])


# ---------------------------------------------------------------- kits
def baseline_kits(inv):
    """The live Pumpkin kits: main = the 'XX Pumpkin' loadouts (boss_swap.PK_KITS cut to the slots by
    boss_swap prepare --set pumpkin), Cure = cure_kit.KITS['pumpkin'] cut to max_chips (cure_kit apply)."""
    import boss_swap, cure_kit
    S = slots(inv); out = {}
    los = inv['accounts']['main']['loadouts']
    pool = owned(inv, 'main')
    for n in ('Kirby54', 'GTGabi', 'Zoulman', 'Payou'):
        if LOADOUT[n] in los:
            out[n] = list(los[LOADOUT[n]])
        else:
            kit = []
            for c in boss_swap.PK_KITS[lp.MAIN_KIT[n]]:
                if pool.get(c, 0) > 0 and len(kit) < S[n] and c not in kit:
                    kit.append(c); pool[c] -= 1
            out[n] = kit
    for n in ('LeekRain', 'DawnFall', 'DuskHope', 'ProdigalSon'):
        out[n] = list(cure_kit.KITS['pumpkin'][n][:S[n]])
    return out


def problems(K, inv, base=None):
    """Feasibility: slot counts, no duplicates, ownership per account, chips the generator knows, the
    mandatory / protected chips of the baseline kept."""
    S = slots(inv); bad = []
    for n in ORDER:
        k = K.get(n)
        if k is None:
            bad.append('%s: no kit' % n); continue
        if len(k) > S[n]:
            bad.append('%s: %d chips > %d slots' % (n, len(k), S[n]))
        if len(set(k)) != len(k):
            bad.append('%s: duplicate chips' % n)
        unk = [c for c in k if c not in lp.CHIP_ID]
        if unk:
            bad.append('%s: unknown to the generator %s' % (n, unk))
        for c in MANDATORY:
            if c not in k:
                bad.append('%s: no %s' % (n, c))
        if base:
            lost = [c for c in base[n] if c in PROTECTED and c not in k]
            if lost:
                bad.append('%s: protected chips dropped %s' % (n, lost))
    for acct, leeks in ACCOUNTS.items():
        own = owned(inv, acct); use = {}
        for n in leeks:
            for c in K.get(n, []):
                use[c] = use.get(c, 0) + 1
        for c, q in use.items():
            if q > own.get(c, 0):
                bad.append('%s: %d x %s needed, %d owned' % (acct, q, c, own.get(c, 0)))
    return bad


def pool_left(K, inv, acct):
    own = owned(inv, acct)
    for n in ACCOUNTS[acct]:
        for c in K[n]:
            own[c] = own.get(c, 0) - 1
    return own


def swap_variant(K, inv, name, k, order='shields', base=None, dmg=None):
    """Leek `name`'s kit from the baseline kit with its first k droppable chips (DROP[order]) replaced by the
    first k damage chips still available on its account. Returns (kit, [(out, in), ...]) or None."""
    base = base or K
    kit = list(base[name])
    drops = [c for c in DROP[order] if c in kit]
    other = dict(K); other[name] = [c for c in kit if c not in drops]     # pool without this leek's swappables
    left = pool_left(other, inv, ACCOUNT_OF[name])
    adds = [c for c in (dmg or DMG[role(name)]) if c not in kit and left.get(c, 0) > 0 and c in lp.CHIP_ID]
    k = min(k, len(drops), len(adds))
    if k <= 0:
        return None
    out = drops[:k]; inn = adds[:k]
    new = [c for c in kit if c not in out]
    # damage chips right after the protected tools: V10's attack() walks the chip list in order
    pos = max([i for i, c in enumerate(new) if c in PROTECTED] + [-1]) + 1
    new = new[:pos] + inn + new[pos:]
    return new, list(zip(out, inn))


def ktag(K):
    return 'k' + hashlib.sha1(json.dumps({n: K[n] for n in ORDER}, sort_keys=True).encode()).hexdigest()[:8]


def diff(A, B):
    out = {}
    for n in ORDER:
        rem = [c for c in A[n] if c not in B[n]]; add = [c for c in B[n] if c not in A[n]]
        if rem or add:
            out[n] = {'out': rem, 'in': add}
    return out


# ---------------------------------------------------------------- evaluation
def objective(s):
    return s['dealt'] + W_KILL * s['kills'] - W_DEAD * s['dead12']


def evaluate(K, tag, seeds, parallel=4, ai='V10/ab/pk_b.py', mob_ai='SIM/pumpkin_mob.leek', template=lp.TEMPLATE,
             verbose=True):
    """Run (or reuse) <tag>_<seed>.json for every seed; returns {seed: stats + 'obj'}."""
    os.makedirs(KDIR, exist_ok=True)
    json.dump(K, open(os.path.join(KDIR, '%s.kits.json' % tag), 'w'), indent=1)
    todo = [s for s in seeds if not os.path.exists(os.path.join(OUT, '%s_%d.json' % (tag, s)))]

    def one(seed):
        p = os.path.join(OUT, '%s_%d.json' % (tag, seed))
        for attempt in range(2):
            try:
                data = lp.run(lp.scenario(seed, ai, mob_ai, template=template, kit_override=K))
                break
            except Exception as ex:
                if attempt:
                    raise
                print('  seed %d: %s - retry' % (seed, str(ex)[:200]), flush=True)
        json.dump(data, open(p + '.tmp', 'w')); os.replace(p + '.tmp', p)
        return seed

    t0 = time.time()
    if todo:
        with ThreadPoolExecutor(parallel) as ex:
            list(ex.map(one, todo))
    res = {}
    for s in seeds:
        st = fight_stats(os.path.join(OUT, '%s_%d.json' % (tag, s)))
        st['obj'] = objective(st)
        res[s] = st
    if verbose:
        n = len(res)
        print('  %s: %d fights (%d run, %.0fs) wins %d obj %.0f dealt %.0f kills %.2f dead12 %.2f kopile %.2f taken %.0f' % (
            tag, n, len(todo), time.time() - t0, sum(r['win'] for r in res.values()),
            statistics.mean(r['obj'] for r in res.values()), statistics.mean(r['dealt'] for r in res.values()),
            statistics.mean(r['kills'] for r in res.values()), statistics.mean(r['dead12'] for r in res.values()),
            statistics.mean(r['kopile'] for r in res.values()), statistics.mean(r['taken'] for r in res.values())),
            flush=True)
    return res


def paired(A, B, key='obj'):
    seeds = sorted(set(A) & set(B))
    d = [B[s][key] - A[s][key] for s in seeds]
    m = statistics.mean(d) if d else 0.0
    se = statistics.stdev(d) / math.sqrt(len(d)) if len(d) > 1 else float('inf')
    pos = sum(1 for x in d if x > 0); neg = sum(1 for x in d if x < 0)
    return dict(n=len(d), mean=m, se=se, pos=pos, neg=neg, p=sign_p(pos, neg))


KEYS = ('win', 'obj', 'dealt', 'kills', 'dead8', 'dead12', 'kopile', 'rez', 'taken', 'turns', 'blocks', 'slots')


def table(A, B, a='A', b='B'):
    seeds = sorted(set(A) & set(B))
    lines = ['%d paired seeds' % len(seeds), '%-8s %10s %10s %10s %8s %10s' % ('', a[:10], b[:10], 'b - a', 'se', 'sign b>a/b<a p')]
    for k in KEYS:
        ma = statistics.mean(A[s][k] for s in seeds); mb = statistics.mean(B[s][k] for s in seeds)
        P = paired({s: A[s] for s in seeds}, {s: B[s] for s in seeds}, k)
        lines.append('%-8s %10.2f %10.2f %+10.2f %8.2f %4d/%-4d %.3f' % (k, ma, mb, mb - ma, P['se'], P['pos'], P['neg'], P['p']))
    return '\n'.join(lines)


def arm(tag):
    out = {}
    for p in glob.glob(os.path.join(OUT, '%s_*.json' % tag)):
        tail = p.rsplit('_', 1)[1][:-5]
        if not tail.isdigit():
            continue
        st = fight_stats(p); st['obj'] = objective(st); out[int(tail)] = st
    return out


# ---------------------------------------------------------------- usage
CAT = {}
for _c in SHIELDS:
    CAT[_c] = 'shield'
for _c in HEALS:
    CAT[_c] = 'heal'
for _c in DMG['str'] + DMG['mag']:
    CAT[_c] = 'damage'
for _c in DMG['shk']:
    CAT[_c] = 'shackle'
for _c in PROTECTED:
    CAT[_c] = 'tool'


def usage(tag):
    """Per leek over the arm's fights: casts per chip, TP per category, damage dealt to mobs, turns alive."""
    cost = {v['name']: v['cost'] for v in CHIPS.values()}
    U = {}
    files = [p for p in glob.glob(os.path.join(OUT, '%s_*.json' % tag)) if p.rsplit('_', 1)[1][:-5].isdigit()]
    for p in files:
        j = json.load(open(p))
        f = j.get('fight', j)
        T = turns(f)
        teams = T[0]['teams']
        for r in T:
            if r['team'] != 1 or r['name'] not in ACCOUNT_OF:
                continue
            u = U.setdefault(r['name'], {'turns': 0, 'dealt': 0, 'chips': {}, 'tp': {}})
            u['turns'] += 1
            u['dealt'] += sum(v for k, v in r['dmg'].items() if teams.get(k) == 2)
            for cn, _ in r['chips']:
                u['chips'][cn] = u['chips'].get(cn, 0) + 1
                c = CAT.get(cn, 'other')
                u['tp'][c] = u['tp'].get(c, 0) + cost.get(cn, 0)
    n = max(1, len(files))
    return U, n


def cmd_usage(a):
    U, n = usage(a.tag)
    print('%s: %d fights, per fight' % (a.tag, n))
    for name in ORDER:
        u = U.get(name)
        if not u:
            continue
        tp = ' '.join('%s %.0f' % (k, v / n) for k, v in sorted(u['tp'].items(), key=lambda x: -x[1]))
        ch = ' '.join('%s %.1f' % (k, v / n) for k, v in sorted(u['chips'].items(), key=lambda x: -x[1]))
        print('%-12s turns %.1f dealt %5.0f | TP %s\n             casts %s' % (name, u['turns'] / n, u['dealt'] / n, tp, ch))


# ---------------------------------------------------------------- commands
def load_kits(path):
    K = json.load(open(path))
    return {n: list(K[n]) for n in ORDER}


def cmd_baseline(a):
    inv = inventory(); K = baseline_kits(inv)
    bad = problems(K, inv)
    os.makedirs(KDIR, exist_ok=True)
    p = os.path.join(KDIR, 'base.kits.json')
    json.dump(K, open(p, 'w'), indent=1)
    S = slots(inv)
    for n in ORDER:
        print('%-12s %2d/%2d %s' % (n, len(K[n]), S[n], K[n]))
    print('problems:', bad or 'none'); print('saved', p)
    d = lp.kits()
    print('vs local_pumpkin defaults (leek_configs slot counts):')
    for n in ORDER:
        dk = [CHIPS[i]['name'] for i in d[n]['chips']]
        rem = [c for c in dk if c not in K[n]]; add = [c for c in K[n] if c not in dk]
        if rem or add:
            print('  %-12s default %d chips, live %d: default only %s, live only %s' % (n, len(dk), len(K[n]), rem, add))


def cmd_check(a):
    inv = inventory(); K = load_kits(a.kits)
    base = baseline_kits(inv)
    bad = problems(K, inv, base)
    print('\n'.join(bad) if bad else 'feasible')
    for n, d in diff(base, K).items():
        print('  %-12s out %s in %s' % (n, d['out'], d['in']))
    return 1 if bad else 0


def cmd_eval(a):
    inv = inventory(); K = load_kits(a.kits)
    bad = problems(K, inv, baseline_kits(inv))
    if bad and not a.force:
        sys.exit('infeasible kit:\n' + '\n'.join(bad))
    tag = a.tag or ktag(K)
    lp_clear_cache()
    evaluate(K, tag, list(range(a.seed, a.seed + a.n)), a.parallel, a.ai)


def cmd_compare(a):
    A, B = arm(a.a), arm(a.b)
    print(table(A, B, a.a, a.b))


def lp_clear_cache():
    for pat in ('*.class', '*.java', '*.lines', '*.sig'):   # same as local_pumpkin.main: compiled mob AI
        for p in glob.glob(os.path.join(lp.GEN, 'ai', pat)):
            if 'pumpkin' in os.path.basename(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


def log_eval(rec):
    with open(LOG, 'a') as f:
        f.write(json.dumps(rec) + '\n')


def cmd_search(a):
    inv = inventory(); base = baseline_kits(inv)
    assert not problems(base, inv), problems(base, inv)
    seeds = list(range(a.seed, a.seed + a.n)); ext = list(range(a.seed + a.n, a.seed + 2 * a.n))
    t_start = time.time(); budget = a.budget_min * 60
    lp_clear_cache()
    print('baseline'); R0 = evaluate(base, 'kbase', seeds, a.parallel, a.ai)
    st = {'best': base, 'R': R0, 'tag': 'kbase'}
    log_eval({'tag': 'kbase', 'label': 'baseline', 'kits': base, 'diff_base': {}, 'obj': statistics.mean(r['obj'] for r in R0.values())})
    tried = {ktag(base)}

    def trial(K, label):
        if time.time() - t_start > budget:
            print('  budget spent, skip %s' % label); return False
        t = ktag(K)
        if t in tried:
            return False
        tried.add(t)
        bad = problems(K, inv, base)
        if bad:
            print('  skip %s: %s' % (label, bad)); return False
        print('%s  %s' % (label, json.dumps(diff(st['best'], K))), flush=True)
        R = evaluate(K, t, seeds, a.parallel, a.ai)
        P = paired(st['R'], R); Pb = paired(R0, R)
        keep = P['mean'] > a.margin * P['se']
        P40 = None
        if keep and a.recheck:
            # re-check on the next n seeds before replacing the incumbent (20-seed screens pass on noise
            # about one time in six at margin 1)
            print('    screen %+.0f (se %.0f): re-check on seeds %d-%d' % (P['mean'], P['se'], ext[0], ext[-1]), flush=True)
            st['R'].update(evaluate(st['best'], st['tag'], ext, a.parallel, a.ai))
            R.update(evaluate(K, t, ext, a.parallel, a.ai))
            P40 = paired(st['R'], R)
            keep = P40['mean'] > a.margin * P40['se']
            print('    %d seeds: %+.0f (se %.0f, %d/%d, p=%.2f)' % (P40['n'], P40['mean'], P40['se'], P40['pos'], P40['neg'], P40['p']), flush=True)
        log_eval({'tag': t, 'label': label, 'kits': K, 'diff_base': diff(base, K),
                  'obj': statistics.mean(r['obj'] for r in R.values()),
                  'dealt': statistics.mean(r['dealt'] for r in R.values()),
                  'kills': statistics.mean(r['kills'] for r in R.values()),
                  'dead12': statistics.mean(r['dead12'] for r in R.values()),
                  'wins': sum(r['win'] for r in R.values()),
                  'vs_best': P, 'vs_best_recheck': P40, 'vs_base': Pb, 'incumbent': st['tag'], 'kept': keep,
                  'elapsed_min': round((time.time() - t_start) / 60, 1)})
        print('    vs incumbent %+.0f (se %.0f, %d/%d, p=%.2f) | vs base %+.0f -> %s' % (
            P['mean'], P['se'], P['pos'], P['neg'], P['p'], Pb['mean'], 'KEEP' if keep else 'no'), flush=True)
        if keep:
            st.update(best=K, R=R, tag=t)
            json.dump(K, open(os.path.join(KDIR, 'best.kits.json'), 'w'), indent=1)
        return keep

    def variant(names, k, order, dset=None):
        """The incumbent with each leek of `names` back to its baseline kit plus k swaps."""
        K = {n: list(st['best'][n]) for n in ORDER}
        for n in names:
            K[n] = list(base[n])
        for n in names:
            v = swap_variant(K, inv, n, k, order, base=K, dmg=DMG[dset or role(n)])
            if v:
                K[n] = v[0]
        return K

    # phase 1: squad-wide moves
    P1 = [(STRIKERS, 2, 'shields', 'str'), (STRIKERS, 4, 'shields', 'str'), (STRIKERS, 99, 'shields', 'str'),
          (STRIKERS, 4, 'heals', 'str'), (MAGES, 99, 'shields', 'mag'), (MAGES, 2, 'shields', 'shk'),
          (MAGES, 4, 'shields', 'shk')]
    for names, k, order, dset in P1:
        trial(variant(names, k, order, dset), 'P1 %s k=%s %s-first %s' % ('strikers' if names == STRIKERS else 'mages', k, order, dset))
    # phase 2+: coordinate descent, leek by leek (biggest damage dealers first), others at the incumbent
    for rnd in range(a.rounds):
        changed = False
        for n in ('Kirby54', 'ProdigalSon', 'Zoulman', 'LeekRain', 'GTGabi', 'Payou', 'DawnFall', 'DuskHope'):
            if n in MAGES:
                V = [(2, 'shields', 'shk'), (4, 'shields', 'shk'), (99, 'shields', 'mag'), (2, 'heals', 'shk')]
            else:
                V = [(2, 'shields', 'str'), (4, 'shields', 'str'), (99, 'shields', 'str'), (4, 'heals', 'str')]
            for k, order, dset in V:
                changed |= trial(variant([n], k, order, dset), 'P%d %s k=%s %s-first %s' % (rnd + 2, n, k, order, dset))
            if st['best'][n] != base[n]:
                K = {m: list(st['best'][m]) for m in ORDER}; K[n] = list(base[n])
                changed |= trial(K, 'P%d %s baseline kit' % (rnd + 2, n))
        if not changed or time.time() - t_start > budget:
            break
    print('\nsearch done in %.0f min, %d kits tried; best %s' % ((time.time() - t_start) / 60, len(tried), st['tag']))
    print(table(R0, st['R'], 'kbase', st['tag']))
    for n, d in diff(base, st['best']).items():
        print('  %-12s out %s in %s' % (n, d['out'], d['in']))
    json.dump(st['best'], open(os.path.join(KDIR, 'best.kits.json'), 'w'), indent=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    sp.add_parser('inventory')
    sp.add_parser('baseline')
    p = sp.add_parser('check'); p.add_argument('kits')
    p = sp.add_parser('eval'); p.add_argument('kits'); p.add_argument('--tag'); p.add_argument('--seed', type=int, default=301)
    p.add_argument('--n', type=int, default=20); p.add_argument('--parallel', type=int, default=4)
    p.add_argument('--ai', default='V10/ab/pk_b.py'); p.add_argument('--force', action='store_true')
    p = sp.add_parser('compare'); p.add_argument('a'); p.add_argument('b')
    p = sp.add_parser('usage'); p.add_argument('tag')
    p = sp.add_parser('search'); p.add_argument('--seed', type=int, default=301); p.add_argument('--n', type=int, default=20)
    p.add_argument('--parallel', type=int, default=4); p.add_argument('--ai', default='V10/ab/pk_b.py')
    p.add_argument('--budget-min', type=float, default=110); p.add_argument('--rounds', type=int, default=2)
    p.add_argument('--margin', type=float, default=1.0, help='keep a variant when mean diff > margin x paired se')
    p.add_argument('--no-recheck', dest='recheck', action='store_false',
                   help='keep on the 20-seed screen alone (default: a passing screen is re-checked on the next n seeds)')
    a = ap.parse_args()
    r = {'inventory': cmd_inventory, 'baseline': cmd_baseline, 'check': cmd_check, 'eval': cmd_eval,
         'compare': cmd_compare, 'usage': cmd_usage, 'search': cmd_search}[a.cmd](a)
    sys.exit(r or 0)


if __name__ == '__main__':
    main()
