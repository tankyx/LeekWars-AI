#!/usr/bin/env python3
"""Replay a server fennel fight to a given (leek, turn) board state and analyze
the crystal-solve geometry (dive stands / PDIVE / slides / inversion)."""
import json, sys

W = 18
STRIDE = 2 * W - 1  # 35

def cell_xy(cid):
    row = cid % STRIDE
    y0 = cid // STRIDE
    y = y0 - (row % W)
    x = (cid - (W - 1) * y) // W
    return x - (W - 1), y

XY2CELL = {}
for cid in range(613):
    XY2CELL[cell_xy(cid)] = cid

def cell_at(x, y):
    return XY2CELL.get((x, y))

def dist(a, b):
    ax, ay = cell_xy(a); bx, by = cell_xy(b)
    return abs(ax - bx) + abs(ay - by)

def los(start, end, obstacles, occupied=(), ignore_end=True):
    """Port of Map.verifyLoS. obstacles: set of unwalkable cell ids.
    occupied: set of entity-occupied cell ids (blockers unless start/end)."""
    sx, sy = cell_xy(start); ex, ey = cell_xy(end)
    a = abs(sy - ey); b = abs(sx - ex)
    dx = -1 if sx > ex else 1
    dy = -1 if sy < ey else 1
    path = []
    if b == 0:
        path = [0, a + 1]
    else:
        d = a / b / 2.0
        h = 0
        for i in range(b):
            y = 0.5 + (i * 2 + 1) * d
            path.append(h)
            path.append(int(__import__("math").ceil(y - 0.00001)) - h)
            h = int(__import__("math").floor(y + 0.00001))
        path.append(h)
        path.append(a + 1 - h)
    for p in range(0, len(path), 2):
        for i in range(path[p + 1]):
            cx = sx + (p // 2) * dx
            cy = sy + (path[p] + i) * dy
            cell = cell_at(cx, cy)
            if cell is None:
                return False
            if cell in obstacles:
                return False
            if cell in occupied:
                if cell == start:
                    continue
                if cell == end and ignore_end:
                    return True
                return False
    return True

def main(fid, target_name, target_turn):
    d = json.load(open(f"data/fight_cache/{fid}.json"))
    dd = d["data"]
    if isinstance(dd, str): dd = json.loads(dd)
    m = dd["map"]
    obstacles = set(int(k) for k in m["obstacles"].keys())
    leeks = {l["id"]: l for l in dd["leeks"]}
    names = {i: l["name"] for i, l in leeks.items()}
    pos = {i: l["cellPos"] for i, l in leeks.items()}
    dead = set()
    target_id = next(i for i, n in names.items() if n == target_name)

    turn = 0
    cur = None
    stop = False
    for a in dd["actions"]:
        if not isinstance(a, list) or not a: continue
        c = a[0]
        if c == 6:
            turn = a[1]
        elif c == 7:
            cur = a[1]
            if cur == target_id and turn == target_turn:
                stop = True
                break
        elif c == 10:  # MOVE
            pos[a[1]] = a[2]
        elif c == 5:  # DEAD
            dead.add(a[1])
        elif c == 12:  # USE_CHIP raw [12, tpl, cell, result]
            tpl, cell, res = a[1], a[2], a[3]
            if res >= 1 and cur is not None:
                if tpl == 37:  # teleportation
                    pos[cur] = cell
                elif tpl == 39:  # inversion: swap
                    # target entity = entity on `cell`
                    tgt = next((e for e in pos if pos[e] == cell and e not in dead), None)
                    if tgt is not None:
                        pos[cur], pos[tgt] = pos[tgt], pos[cur]
    print(f"=== {fid} board at {target_name} T{target_turn} ===")
    for i, n in sorted(names.items(), key=lambda kv: kv[1]):
        flag = "DEAD" if i in dead else ""
        print(f"  {i:3d} {n:16s} cell {pos[i]:4d} {cell_xy(pos[i])} {flag}")
    graal = next(i for i, n in names.items() if n == "graal")
    gx, gy = cell_xy(pos[graal])
    print(f"graal at {pos[graal]} = ({gx},{gy})")
    occupied = {pos[i] for i in pos if i not in dead}
    axes = {"red_crystal": "south", "blue_crystal": "east", "yellow_crystal": "west", "green_crystal": "north"}
    my = pos[target_id]
    print(f"{target_name} at {my} = {cell_xy(my)}, MP~3-4, TP full")
    for cn, axis in axes.items():
        cid = next(i for i, n in names.items() if n == cn)
        if cid in dead: print(f"{cn}: DEAD"); continue
        cc = pos[cid]
        cx, cy = cell_xy(cc)
        # axis direction
        axd = {"south": (0, 1), "north": (0, -1), "east": (1, 0), "west": (-1, 0)}[axis]
        on_axis = (cx == gx) if axis in ("south", "north") else (cy == gy)
        # ray-clear solved cells (obstacle-only LoS)
        ray_clear = []
        for sd in range(1, 25):
            sc = cell_at(gx + axd[0] * sd, gy + axd[1] * sd)
            if sc is None: break
            if sc in obstacles or sc in occupied: continue
            if los(sc, pos[graal], obstacles, occupied=()):  # ray ignores entities
                ray_clear.append(sc)
        d_me_cr = dist(my, cc)
        # full-dive stands: within 10 of crystal AND within 2+MP(=6) of a ray-clear cell
        stands = []
        for sc in ray_clear:
            sx, sy = cell_xy(sc)
            for px in range(sx - 6, sx + 7):
                for py in range(sy - 6, sy + 7):
                    if abs(px - sx) + abs(py - sy) > 6 or (px == sx and py == sy): continue
                    pc = cell_at(px, py)
                    if pc is None or pc in obstacles or (pc in occupied and pc != my): continue
                    if dist(pc, cc) > 10: continue
                    stands.append((pc, dist(my, pc)))
        # nearest axis distance of the crystal (to nearest ray-clear cell)
        dcg = min((dist(cc, sc) for sc in ray_clear), default=None)
        print(f"{cn} @{cc} {cell_xy(cc)} axis={axis} on_axis={on_axis} dMe={d_me_cr} "
              f"ray_clear={len(ray_clear)} nearest_rayclear_d={dcg} dive_stands={len(stands)}"
              + (f" nearest_stand_d={min(s[1] for s in stands)}" if stands else ""))
        if ray_clear:
            print(f"   ray-clear cells: {[(sc, cell_xy(sc)) for sc in ray_clear[:8]]}")

if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2], int(sys.argv[3]))
