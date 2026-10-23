"""Evil Pumpkin fight logs, real or simulated, as per-turn records (shared by pumpkin_study.py and the local
Pumpkin simulator's calibration).

    from pumpkin_fights import load, turns
    for src, fid, meta, data in load('win'):     # 'win' = other squads' fights, 'ours' = our V10 fights
        for t in turns(data): ...

A turn record holds the state BEFORE the entity acts (positions, life, alive, Divine Protection holders) and
what it did: says (raw and decoded Glagolitic numbers), chips cast (name, cell), weapon shots, moves, damage
dealt per target, resurrections, protection drop. Chip/weapon ids in fight actions are the generator's
data/chips.json / weapons.json ids.
"""
import glob, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = '/home/ubuntu/leek-wars-generator/data'
CHIPS = {int(k): v for k, v in json.load(open(os.path.join(GEN, 'chips.json'))).items()}
WEAPONS = {int(k): v for k, v in json.load(open(os.path.join(GEN, 'weapons.json'))).items()}
CN = {k: v['name'] for k, v in CHIPS.items()}                  # item id -> name (older fight logs)
CT = {v['template']: v['name'] for v in CHIPS.values()}        # template id -> name (logs since ~2026-10-19)
WN = {k: v['name'] for k, v in WEAPONS.items()}
TELEPORT = {'jump', 'teleportation', 'kemuridama'}   # the caster lands on the target cell
SWAP = {'inversion', 'repotting'}                    # caster and target swap cells
MOBS = ('evil_pumpkin', 'hubbard', 'turban', 'warty', 'offspring')

# ---- Glagolitic numerals and the riddle (forum topic 11152) ----
_G = {}
for _i in range(9):
    _G[0x2C00 + _i] = _i + 1
_G[0x2C09] = 10; _G[0x2C0A] = 10
for _i, _o in enumerate(range(0x2C0B, 0x2C13)):
    _G[_o] = (_i + 2) * 10
for _i, _o in enumerate(range(0x2C13, 0x2C1A)):
    _G[_o] = (_i + 1) * 100
_G[0x2C1B] = 800; _G[0x2C1C] = 900; _G[0x2C1D] = 1000
_GINV = {}
for _o, _v in sorted(_G.items()):
    _GINV.setdefault(_v, chr(_o))


def glag(s):
    """Glagolitic numeral -> int (None if the text is not one)."""
    if not isinstance(s, str) or not s.strip():
        return None
    t = 0
    for ch in s.strip():
        o = ord(ch)
        if 0x2C30 <= o <= 0x2C5E:
            o -= 0x30
        if o not in _G:
            return None
        t += _G[o]
    return t or None


def to_glag(n):
    """int 1..999 -> Glagolitic numeral (hundreds, tens, units)."""
    out = ''
    for unit in (100, 10, 1):
        d = (n // unit) % 10 * unit
        if d:
            out += _GINV[d]
    return out


def best_div(n, cap=612):
    for c in range(min(cap, n), 0, -1):
        if n % c == 0:
            return c
    return 0


def riddle_cell(nums):
    a, b, c = nums
    best = 0
    for p in ((a, b, c), (a, c, b), (b, a, c), (b, c, a), (c, a, b), (c, b, a)):
        best = max(best, best_div(int('%d%d%d' % p)))
    return best or None


# ---- geometry (18x18 diamond map, 613 cells) ----
W = 18


def cxy(c):
    x0 = c % (2 * W - 1); y0 = c // (2 * W - 1)
    y = y0 - x0 % W
    return (c - (W - 1) * y) // W, y


def dist(a, b):
    if a is None or b is None:
        return 99
    ax, ay = cxy(a); bx, by = cxy(b)
    return abs(ax - bx) + abs(ay - by)


# ---- loading ----
def _data(j):
    f = j.get('fight', j)
    d = f.get('data', f)
    d = json.loads(d) if isinstance(d, str) else d
    return f, d


def load(src='win', ids=None):
    """Yield (src, fid, meta, data) for Pumpkin fights. src: 'win' (other squads), 'ours' (V10 fights), or a glob."""
    pat = {'win': ROOT + '/data/boss_fights/[0-9]*.json', 'ours': ROOT + '/data/boss_fights/v10_*.json'}.get(src, src)
    for p in sorted(glob.glob(pat)):
        try:
            j = json.load(open(p))
        except Exception:
            continue
        f, d = _data(j)
        if not isinstance(d, dict) or 'leeks' not in d:
            continue
        if not any(e.get('name') == 'evil_pumpkin' for e in d['leeks']):
            continue
        fid = f.get('id') or os.path.basename(p)
        if ids and fid not in ids:
            continue
        yield src, fid, f, d


def obstacles(d):
    m = d.get('map') or {}
    return set(int(k) for k in (m.get('obstacles') or {}))


def turns(d):
    """Per-turn records in play order with the state before each turn."""
    E = {e['id']: e for e in d['leeks']}
    name = {i: e['name'] for i, e in E.items()}
    team = {i: e['team'] for i, e in E.items()}
    pos = {i: e.get('cellPos') for i, e in E.items()}
    life = {i: e.get('life') or 0 for i, e in E.items()}
    maxl = {i: e.get('life') or 0 for i, e in E.items()}
    alive = {i: life[i] > 0 and not e.get('summon') for i, e in E.items()}
    summ = {i: bool(e.get('summon')) for i, e in E.items()}
    dp = set(); eff = {}
    out = []; rec = None; rnd = 1; cur = None
    # chip ids in USE_CHIP actions: item ids in older logs, template ids in newer ones. The pumpkin's
    # first chip is divine protection (item 419, template 113).
    first = next((a[1] for a in d['actions'] if a[0] == 12), None)
    cmap = CT if first == 113 else CN
    for a in d['actions']:
        c = a[0]
        if c == 6:
            rnd = a[1]; continue
        if c == 7:
            cur = a[1]
            rec = {'turn': rnd, 'id': cur, 'name': name.get(cur), 'team': team.get(cur), 'summon': summ.get(cur),
                   'pos': dict(pos), 'life': dict(life), 'alive': dict(alive), 'dp': set(dp),
                   'says': [], 'nums': [], 'chips': [], 'shots': [], 'moves': [], 'dmg': {}, 'rez': None,
                   'kopile': False, 'drop': False, 'acts': []}
            out.append(rec)
            continue
        if rec is not None:
            rec['acts'].append(a)
        if c == 10 and len(a) > 2:
            if rec is not None and a[1] == cur:
                rec['moves'].append((pos.get(a[1]), a[2], len(a[3]) if len(a) > 3 and isinstance(a[3], list) else 1))
            pos[a[1]] = a[2]
        elif c == 12 and rec is not None:
            cn = cmap.get(a[1], a[1])
            rec['chips'].append((cn, a[2]))
            if cn in TELEPORT:
                pos[cur] = a[2]
            elif cn in SWAP:
                other = next((i for i, p in pos.items() if p == a[2] and alive.get(i) and i != cur), None)
                if other is not None:
                    pos[other], pos[cur] = pos[cur], a[2]
        elif c == 16 and rec is not None:
            rec['shots'].append(a[1])
        elif c in (101, 107, 108, 110) and len(a) > 2:
            life[a[1]] = max(0, life.get(a[1], 0) - a[2])
            if rec is not None and c != 108:
                rec['dmg'][a[1]] = rec['dmg'].get(a[1], 0) + a[2]
        elif c == 103 and len(a) > 2:
            life[a[1]] = min(maxl.get(a[1], 0), life.get(a[1], 0) + a[2])
        elif c == 5:
            alive[a[1]] = False; pos[a[1]] = None
        elif c == 9 and len(a) > 3:
            alive[a[2]] = True; pos[a[2]] = a[3]; summ[a[2]] = True
            name.setdefault(a[2], '?'); team[a[2]] = team.get(a[1])
            life[a[2]] = maxl[a[2]] = (E.get(a[2]) or {}).get('life') or 0
        elif c == 105 and len(a) > 3:
            alive[a[2]] = True; pos[a[2]] = a[3]
            if len(a) > 5:
                life[a[2]] = a[4]; maxl[a[2]] = a[5]
            if rec is not None:
                rec['rez'] = (a[2], a[3])
        elif c in (301, 302) and len(a) > 6:
            eff[a[2]] = (a[4], a[5], a[6])
            if a[5] == 59 and a[6] == 3:
                dp.add(a[4])
        elif c == 303 and a[1] in eff:
            e = eff.pop(a[1])
            if e[1] == 59 and e[2] == 3:
                dp.discard(e[0])
                if rec is not None and e[0] == cur:
                    rec['drop'] = True
        elif c == 203 and rec is not None:
            rec['says'].append(a[1])
            n = glag(a[1])
            if n:
                rec['nums'].append(n)
            if isinstance(a[1], str) and a[1].endswith('!!'):     # "kopile!!" in Glagolitic: the cell was taken
                rec['kopile'] = True
    for r in out:
        r['names'] = name; r['teams'] = team
    return out


# ---- line of sight (generator Map.verifyLoS): walls block, entities block except on the end cells ----
_XY2ID = {}
for _c in range(613):
    _XY2ID[cxy(_c)] = _c


def los(start, end, obs, occupied=()):
    (sx, sy), (ex, ey) = cxy(start), cxy(end)
    a = abs(sy - ey); b = abs(sx - ex)
    dx = -1 if sx > ex else 1
    dy = 1 if sy < ey else -1
    path = []
    if b == 0:
        path += [0, a + 1]
    else:
        d = a / b / 2.0; h = 0
        for i in range(b):
            y = 0.5 + (i * 2 + 1) * d
            path += [h, int(-(-(y - 0.00001) // 1)) - h]
            h = int((y + 0.00001) // 1)
        path += [h, a + 1 - h]
    for p in range(0, len(path), 2):
        for i in range(path[p + 1]):
            c = _XY2ID.get((sx + (p // 2) * dx, sy + (path[p] + i) * dy))
            if c is None or c in obs:
                return False
            if c in occupied:
                if c == start:
                    continue
                if c == end:
                    return True
                return False
    return True


def neighbours(c):
    x, y = cxy(c)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        n = _XY2ID.get((x + dx, y + dy))
        if n is not None:
            yield n


def path_dist(start, obs, occupied, limit=60):
    """BFS walking distance from start over walkable, unoccupied cells: {cell: steps}. Occupied cells are
    reached (distance recorded) but not walked through."""
    D = {start: 0}; fr = [start]
    while fr:
        nx = []
        for c in fr:
            if D[c] >= limit:
                continue
            for n in neighbours(c):
                if n in D or n in obs:
                    continue
                D[n] = D[c] + 1
                if n not in occupied:
                    nx.append(n)
        fr = nx
    return D
