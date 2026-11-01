#!/usr/bin/env python3
"""Local Evil Pumpkin simulator: our 8 leeks (V10) vs the Pumpkin army on the local generator.

The army runs sim/pumpkin_mob.leek, a reconstruction of the mobs' AI from 708 real Pumpkin fights (the riddle
and the resurrections are exact on the logs; combat is fitted). Geometry, map and our leeks' stats come from a
real 8-leek fight of ours (the template, --template); chips and weapons are the Pumpkin kits (boss_swap.PK_KITS for main,
cure_kit.KITS for Cure) cut to each leek's chip slots.

    python3 tools/local_pumpkin.py --n 8 --parallel 4            # 8 seeds, summary per fight
    python3 tools/local_pumpkin.py --n 1 --seed 7 --keep         # keep the fight JSON in data/sim_pumpkin/
    python3 tools/local_pumpkin.py --n 20 --tag v17 --ai V10/v10.py

Fights are saved to data/sim_pumpkin/<tag>_<seed>.json (pumpkin_fights.load('data/sim_pumpkin/<tag>_*.json')
reads them like real fights). Needs the generator patch (EntityInfo type/skin/dead, mob/Mob.java) and the
symlink leek-wars-generator/SIM -> sim/.
"""
import argparse, json, os, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from pumpkin_fights import load, CHIPS, WEAPONS, turns, MOBS  # noqa: E402

GEN = os.environ.get('LW_GEN', '/home/ubuntu/leek-wars-generator')   # LW_GEN: another generator checkout
JAVA = '/usr/lib/jvm/java-25-openjdk-amd64/bin/java'
OUT = os.path.join(ROOT, 'data', 'sim_pumpkin')
TEMPLATE = 54297638            # first fight of the v17 live batch (2026-10-23): current stats, spawns, turn order
CHIP_ID = {v['name']: k for k, v in CHIPS.items()}
WEAPON_ID = {v['name']: v['item'] for v in WEAPONS.values()}
MAIN_KIT = {'Kirby54': 'AL', 'GTGabi': 'ED', 'Zoulman': 'KG', 'Payou': 'MH'}
MOB_KIT = {
    'evil_pumpkin': (['lightning', 'flash', 'jump', 'thunder', 'plasma', 'liberation', 'steroid', 'exasperation', 'teleportation',
                      'divine_protection', 'adrenaline', 'covetousness', 'awakening', 'antidote', 'sugar'], ['scythe']),
    'hubbard': (['lightning', 'exasperation', 'flash', 'plasma', 'steroid', 'inversion', 'liberation', 'awakening', 'adrenaline',
                 'covetousness', 'antidote'], []),
    'turban': (['lightning', 'flash', 'jump', 'liberation', 'steroid', 'exasperation', 'awakening', 'covetousness', 'adrenaline',
                'antidote'], []),
    'warty': (['venom', 'toxin', 'liberation', 'exasperation', 'plague', 'awakening', 'antidote', 'covetousness'], []),
    'offspring': (['flash', 'jump', 'exasperation', 'awakening'], []),
}
MOB_SKIN = {'evil_pumpkin': 3, 'turban': 9, 'warty': 10, 'hubbard': 11, 'offspring': 12}
# 2026-10-28 STR fudge (pumpkin 1540, hubbard 940) retired 2026-11-01: the real gap was target choice - the mobs
# hit the leeks whose shields let damage through (sim/pumpkin_mob.leek effLife / shieldFactor); --mob-cal brings it back
MOB_CAL = {}
MOB_CAL_OLD = {'evil_pumpkin': {'strength': 1540}, 'hubbard': {'strength': 940}}
STATS = ('life', 'strength', 'magic', 'wisdom', 'agility', 'resistance', 'science', 'frequency', 'tp', 'mp', 'level')


def kits(override=None):
    """Chips / weapons per leek. override = {leek name: [chip names]} (--kits): that leek gets exactly
    those chips, in that order, not cut to the leek_configs slot count (the caller checks slots and
    ownership, e.g. tools/pumpkin_kit_opt.py); leeks not in it keep the default kit."""
    import boss_swap, cure_kit
    cfg = json.load(open(os.path.join(HERE, 'leek_configs.json')))
    cfg = cfg.get('leeks', cfg)
    out = {}
    for name in ('Kirby54', 'GTGabi', 'Zoulman', 'Payou', 'LeekRain', 'DawnFall', 'DuskHope', 'ProdigalSon'):
        c = cfg[name]
        slots = len(c['chips'])
        if name in MAIN_KIT:
            k = MAIN_KIT[name]
            chips = boss_swap.PK_KITS[k]; weapons = [WEAPON_ID[w] for w in boss_swap.PK_WEAPONS[k] if w in WEAPON_ID]
        else:
            chips = cure_kit.KITS['pumpkin'][name]; weapons = list(c['weapons'])
        if override and name in override:
            unknown = [n for n in override[name] if n not in CHIP_ID]
            if unknown:
                raise ValueError('%s: chips unknown to the generator: %s' % (name, unknown))
            chips = list(override[name]); slots = len(chips)
        ids = []
        for n in chips:
            if n in CHIP_ID and CHIP_ID[n] not in ids:
                ids.append(CHIP_ID[n])
        out[name] = dict(chips=ids[:slots], weapons=weapons, cores=c.get('cores', 14), ram=c.get('ram', 50))
    return out


def scenario(seed, ai, mob_ai, template=TEMPLATE, max_turns=64, kit_override=None, stat_override=None, cell_override=None):
    """Our leeks' stats and frequencies come from the template fight: re-point it after any respec or
    component change (2026-10-23: the v16 template had DawnFall at frequency 190, today 169 - another turn order)."""
    d = next(d for _, fid, f, d in load('ours', ids={template}))
    K = kits(kit_override)
    ours, mobs, farmers = [], [], [{'id': 1, 'name': 'Virus', 'country': 'fr'}, {'id': 2, 'name': 'Cure', 'country': 'fr'},
                                    {'id': 3, 'name': 'Leek Wars', 'country': 'fr'}]
    for e in d['leeks']:
        if e.get('summon'):
            continue
        ent = {'id': e['id'], 'name': e['name'], 'team': e['team'], 'cell': e.get('cellPos')}
        if e['team'] == 1 and cell_override and e['name'] in cell_override:   # squad order = spawn slot
            ent['cell'] = cell_override[e['name']]
        for k in STATS:
            ent[k] = e.get(k) or 0
        if e['team'] == 1:
            kit = K[e['name']]
            ent.update(ai=ai, farmer=1 if e['name'] in MAIN_KIT else 2, chips=kit['chips'], weapons=kit['weapons'],
                       cores=kit['cores'], ram=kit['ram'], type=0)
            # what-if builds: {leek: {stat: value, 'weapons': [names]}} (e.g. a mage respecced to STR)
            for k, v in ((stat_override or {}).get(e['name']) or {}).items():
                ent[k] = [WEAPON_ID[w] for w in v if w in WEAPON_ID] if k == 'weapons' else v
            ours.append(ent)
        else:
            chips, weapons = MOB_KIT[e['name']]
            # 2026-10-28 calibration on the 60-fight squad-play batch: live pumpkin / hubbard hits land 49% harder
            # than here (turban matches) - damage scales with 1 + STR/100
            for k, v in (MOB_CAL.get(e['name']) or {}).items():
                ent[k] = v
            ent.update(ai=mob_ai, farmer=3, type=4, skin=MOB_SKIN[e['name']], cores=30, ram=30,
                       chips=[CHIP_ID[c] for c in chips], weapons=[WEAPON_ID[w] for w in weapons])
            if not ent['life']:
                ent['dead'] = True; ent['cell'] = None
                ent['life'] = {'hubbard': 12000, 'turban': 11000, 'warty': 13000, 'offspring': 6000}[e['name']]
            mobs.append(ent)
    m = dict(d['map'])
    m['team1'] = [e['cell'] for e in ours]
    m['team2'] = [e['cell'] for e in mobs if e['cell'] is not None]
    m.setdefault('pattern', [])
    return {'boss': 3, 'farmers': farmers, 'teams': [{'id': 1, 'name': 'Squad'}, {'id': 2, 'name': 'Pumpkin'}],
            'entities': [ours, mobs], 'map': m, 'random_seed': seed, 'max_turns': max_turns}


def run(scn, timeout=1800):
    with tempfile.NamedTemporaryFile('w', suffix='.json', prefix='lw_pk_', delete=False, dir='/tmp') as f:
        json.dump(scn, f); path = f.name
    cp = open(os.path.join(GEN, 'runtime_classpath.txt')).read().strip()
    t0 = time.time()
    try:
        r = subprocess.run([JAVA, '-cp', cp, 'com.leekwars.Main', path], capture_output=True, text=True, timeout=timeout,
                           cwd=GEN, env=dict(os.environ, JAVA_HOME=os.path.dirname(os.path.dirname(JAVA))))
    finally:
        os.remove(path)
    out = r.stdout
    i = out.find('{"')
    if i < 0:
        raise RuntimeError('no JSON from the generator:\n' + (r.stdout[-2000:] + r.stderr[-2000:]))
    data = json.loads(out[i:], strict=False)
    data['_wall'] = round(time.time() - t0, 1)
    return data


def summary(data):
    f = data.get('fight', data)
    T = turns(f)
    names = T[0]['names'] if T else {}
    teams = T[0]['teams'] if T else {}
    rez = sum(1 for r in T if r['rez'] and teams.get(r['id']) == 2)
    drops = sum(1 for r in T if r['kopile'])
    umri = sum(1 for r in T if any(s == 'ⱆⰿⱃⰻ!' for s in r['says']))
    dealt = sum(v for r in T if r['team'] == 1 for k, v in r['dmg'].items() if teams.get(k) == 2)
    taken = sum(v for r in T if r['team'] == 2 for k, v in r['dmg'].items() if teams.get(k) == 1)
    deaths = []
    rnd = 1
    for a in f['actions']:
        if a[0] == 6:
            rnd = a[1]
        elif a[0] == 5 and teams.get(a[1]) == 1 and not str(names.get(a[1], '')).endswith(('bulb', 'prototaxite')):
            deaths.append(rnd)
    bugs = sum(1 for a in f['actions'] if a[0] == 1002)
    w = data.get('winner')
    return dict(winner=w, turns=max((r['turn'] for r in T), default=0), rez=rez, kopile=drops, umri=umri,
                dealt=dealt, taken=taken, deaths=sorted(deaths), bugs=bugs, wall=data.get('_wall'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=1)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--parallel', type=int, default=2)
    ap.add_argument('--ai', default='V10/v10.py')
    ap.add_argument('--mob-ai', default='SIM/pumpkin_mob.leek')
    ap.add_argument('--tag', default='sim')
    ap.add_argument('--max-turns', type=int, default=64)
    ap.add_argument('--template', type=int, default=TEMPLATE, help='real 8-leek fight whose geometry and our stats are cloned')
    ap.add_argument('--keep', action='store_true', help='keep the fight JSONs (default: yes for --n <= 40)')
    ap.add_argument('--stats', help='JSON file {leek name: {stat: value, "weapons": [names]}}: what-if builds')
    ap.add_argument('--kits', help='JSON file {leek name: [chip names]}: per-leek chip overrides (default: the Pumpkin kits)')
    ap.add_argument('--cells', help='JSON {leek name: start cell}: another squad order (spawn slots 92 301 475 515 520 384 224 80)')
    ap.add_argument('--no-mob-cal', action='store_true', help='(default now) mob stats as in the template')
    ap.add_argument('--mob-cal', action='store_true', help='the retired 2026-10-28 STR fudge on pumpkin / hubbard')
    a = ap.parse_args()
    if a.mob_cal:
        MOB_CAL.update(MOB_CAL_OLD)
    override = json.load(open(a.kits)) if a.kits else None
    os.makedirs(OUT, exist_ok=True)
    for pat in ('*.class', '*.java', '*.lines', '*.sig'):   # the generator caches compiled LeekScript by root file
        for p in __import__('glob').glob(os.path.join(GEN, 'ai', pat)):
            if 'pumpkin' in os.path.basename(p):
                os.remove(p)

    def one(seed):
        data = run(scenario(seed, a.ai, a.mob_ai, template=a.template, max_turns=a.max_turns, kit_override=override,
                                stat_override=json.load(open(a.stats)) if a.stats else None,
                                cell_override=json.load(open(a.cells)) if a.cells else None))
        json.dump(data, open(os.path.join(OUT, '%s_%d.json' % (a.tag, seed)), 'w'))
        return seed, summary(data)

    rows = []
    with ThreadPoolExecutor(a.parallel) as ex:
        for seed, s in ex.map(one, range(a.seed, a.seed + a.n)):
            rows.append(s)
            print('seed %3d: winner %s, T%d, rez %d, kopile %d, umri %d, dealt %dk, taken %dk, deaths %s, bugs %d, %ss' % (
                seed, s['winner'], s['turns'], s['rez'], s['kopile'], s['umri'], s['dealt'] // 1000, s['taken'] // 1000,
                s['deaths'], s['bugs'], s['wall']), flush=True)
    n = len(rows)
    if n:
        print('== %d fights: %d wins (winner 0 = us), mean T%.1f, rez %.1f, kopile %.1f, dealt %.1fk, taken %.1fk' % (
            n, sum(1 for r in rows if r['winner'] == 0), sum(r['turns'] for r in rows) / n, sum(r['rez'] for r in rows) / n,
            sum(r['kopile'] for r in rows) / n, sum(r['dealt'] for r in rows) / n / 1000, sum(r['taken'] for r in rows) / n / 1000))


if __name__ == '__main__':
    main()
