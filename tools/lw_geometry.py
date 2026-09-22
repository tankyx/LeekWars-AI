"""Exact LeekWars map geometry, ported from the generator (Map.java / Cell.java).

Cell ids -> (x, y) as the generator computes them, manhattan distance in that
frame (= getCellDistance), and verifyLoS with the same Bresenham walk and the
same rules: obstacles block, entities block unless the cell is the start
(ignored) or the end (target)."""
import math

class Geometry:
    def __init__(self, width=18, height=18, obstacles=None):
        self.w = width; self.h = height
        self.nb = (width * 2 - 1) * height - (width - 1)
        self.xy = {}; self.byxy = {}
        for i in range(self.nb):
            x = i % (width * 2 - 1); y = i // (width * 2 - 1)
            cy = y - x % width; cx = (i - (width - 1) * cy) // width
            self.xy[i] = (cx, cy); self.byxy[(cx, cy)] = i
        self.obstacles = set(int(k) for k in (obstacles or {}).keys())

    def dist(self, a, b):
        if a not in self.xy or b not in self.xy: return None
        (x1, y1), (x2, y2) = self.xy[a], self.xy[b]
        return abs(x1 - x2) + abs(y1 - y2)

    def walkable(self, c):
        return c in self.xy and c not in self.obstacles

    def los(self, start, end, occupied=()):
        """occupied: cells holding entities (other than start, which is ignored)."""
        if start not in self.xy or end not in self.xy: return None
        sx, sy = self.xy[start]; ex, ey = self.xy[end]
        a = abs(sy - ey); b = abs(sx - ex)
        dx = -1 if sx > ex else 1; dy = 1 if sy < ey else -1
        path = []
        if b == 0:
            path += [0, a + 1]
        else:
            d = a / b / 2.0; h = 0
            for i in range(b):
                y = 0.5 + (i * 2 + 1) * d
                path.append(h); path.append(int(math.ceil(y - 0.00001)) - h)
                h = int(math.floor(y + 0.00001))
            path.append(h); path.append(a + 1 - h)
        occ = set(occupied)
        for p in range(0, len(path), 2):
            for i in range(path[p + 1]):
                c = self.byxy.get((sx + (p // 2) * dx, sy + (path[p] + i) * dy))
                if c is None: return False
                if c in self.obstacles: return False
                if c in occ:
                    if c == start: continue
                    if c == end: return True
                    return False
        return True
