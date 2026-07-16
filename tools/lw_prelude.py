# ════════ LeekScript runtime prelude (generated header — do not edit in V8_python) ════════
# Reimplements LS semantics the polyglot bridge does not provide:
# null-tolerant arithmetic, tolerant subscripts, and the collection stdlib
# (non-bridged: it operates on native guest containers). See
# POLYGLOT_PORTING_GUIDE.md sections 2-3.
import math as _math

# The polyglot bridge injects LS stdlib functions named `list`/`dict` (and
# possibly others) into the guest global scope, shadowing Python builtins.
# Capture the real types via literals — immune to shadowing.
_list = type([])
_dict = type({})
_str = type("")
_int = type(0)
_float = type(0.0)
_tuple = type(())


def lw_num(x):
    if x is None:
        return 0
    if isinstance(x, (_int, _float)):
        return x
    if isinstance(x, type(True)):
        return 1 if x else 0
    if isinstance(x, _str):
        try:
            return _int(x)
        except ValueError:
            try:
                return _float(x)
            except ValueError:
                return 0
    return 0


def lw_str(x):
    if x is None:
        return "null"
    if x is True:
        return "true"
    if x is False:
        return "false"
    if isinstance(x, _float) and x == _int(x) and abs(x) < 1e15:
        return _str(_int(x))
    return _str(x)


def lw_add(a, b):
    if type(a) is _int and type(b) is _int:
        return a + b
    if isinstance(a, _str) or isinstance(b, _str):
        return lw_str(a) + lw_str(b)
    if isinstance(a, _list) and isinstance(b, _list):
        return a + b
    return lw_num(a) + lw_num(b)


def lw_sub(a, b):
    if type(a) is _int and type(b) is _int:
        return a - b
    return lw_num(a) - lw_num(b)


def lw_mul(a, b):
    if type(a) is _int and type(b) is _int:
        return a * b
    return lw_num(a) * lw_num(b)


def lw_div(a, b):
    b = lw_num(b)
    if b == 0:
        return 0
    return lw_num(a) / b


def lw_mod(a, b):
    # Java remainder semantics (sign of the dividend), not Python floor-mod
    a = lw_num(a)
    b = lw_num(b)
    if b == 0:
        return 0
    r = _math.fmod(a, b)
    if isinstance(a, _int) and isinstance(b, _int):
        return _int(r)
    return r


def lw_get(o, k):
    if o is None:
        return None
    try:
        if isinstance(o, _dict):
            return o.get(k)
        if isinstance(o, (_list, _str)):
            i = _int(k)
            n = len(o)
            if -n <= i < n:
                return o[i]
            return None
        return o[k]  # host proxies (game API arrays/maps)
    except Exception:
        return None


def lw_put(o, k, v):
    if isinstance(o, _list):
        i = _int(k)
        if i == len(o):
            o.append(v)
        else:
            o[i] = v
    else:
        o[k] = v
    return v


def lw_values(coll):
    if coll is None:
        return []
    if isinstance(coll, _dict):
        return _list(coll.values())
    if isinstance(coll, (_list, _tuple, _str)):
        return _list(coll)
    try:
        return _list(coll.values())
    except Exception:
        pass
    try:
        return _list(coll)
    except Exception:
        return []


def lw_count(x):
    if x is None:
        return 0
    try:
        return len(x)
    except Exception:
        try:
            return sum(1 for _ in x)
        except Exception:
            return 0


def _lwcall(f, *a):
    try:
        n = f.__code__.co_argcount
    except AttributeError:
        return f(*a)
    return f(*a[:n])


# ── LS collection stdlib (non-bridged) ──

def count(x):
    return lw_count(x)


def push(arr, v):
    arr.append(v)
    return v


def pop(arr):
    if arr:
        return arr.pop()
    return None


def insert(arr, element, position):
    arr.insert(_int(position), element)


def remove(arr, position):
    try:
        return arr.pop(_int(position))
    except Exception:
        return None


def removeElement(arr, element):
    try:
        arr.remove(element)
        return True
    except ValueError:
        return False


def inArray(arr, v):
    try:
        return v in lw_values(arr) if isinstance(arr, _dict) else v in arr
    except Exception:
        return False


def indexOf(haystack, needle, start=0):
    try:
        if isinstance(haystack, _str):
            return haystack.find(lw_str(needle), _int(start))
        return _list(haystack).index(needle, _int(start))
    except ValueError:
        return -1
    except Exception:
        return -1


def contains(haystack, needle):
    try:
        if isinstance(haystack, _str):
            return lw_str(needle) in haystack
        if isinstance(haystack, _dict):
            return needle in haystack.values()
        return needle in haystack
    except Exception:
        return False


def substring(s, start, length=None):
    s = lw_str(s)
    start = _int(start)
    if length is None:
        return s[start:]
    return s[start:start + _int(length)]


class _CmpKey:
    # hand-rolled functools.cmp_to_key: stdlib imports can fail inside the
    # polyglot sandbox, so avoid them entirely
    __slots__ = ("v", "cmp")

    def __init__(self, v, cmp):
        self.v = v
        self.cmp = cmp

    def __lt__(self, other):
        return lw_num(_lwcall(self.cmp, self.v, other.v)) < 0


def arraySort(arr, cmp=None):
    if cmp is None:
        arr.sort(key=lambda v: (v is None, v))
    else:
        arr.sort(key=lambda v: _CmpKey(v, cmp))
    return arr


def sort(arr, cmp=None):
    return arraySort(arr, cmp)


def arrayFilter(arr, cb):
    if isinstance(arr, _dict):
        return {k: v for k, v in arr.items() if _lwcall(cb, v, k, arr)}
    return [v for v in arr if _lwcall(cb, v)]


def arrayMap(arr, cb):
    if isinstance(arr, _dict):
        return {k: _lwcall(cb, v, k, arr) for k, v in arr.items()}
    return [_lwcall(cb, v) for v in arr]


def mapContainsKey(m, k):
    if m is None:
        return False
    try:
        return k in m
    except Exception:
        return False


def mapKeys(m):
    if m is None:
        return []
    try:
        return _list(m.keys())
    except Exception:
        return _list(iter(m))


def mapValues(m):
    return lw_values(m)


def mapGet(m, k, default=None):
    v = lw_get(m, k)
    return default if v is None else v


def mapPut(m, k, v):
    m[k] = v
    return v


def mapRemove(m, k):
    if isinstance(m, _dict):
        return m.pop(k, None)
    try:
        del m[k]
    except Exception:
        return None


def arrayClear(arr):
    try:
        arr.clear()
    except Exception:
        pass
    return arr


def mapMerge(m1, m2):
    out = {}
    if m1:
        out.update(m1)
    if m2:
        out.update(m2)
    return out


def mapClear(m):
    try:
        m.clear()
    except Exception:
        pass
    return m


def mapSize(m):
    return lw_count(m)


def mapFilter(m, cb):
    out = {}
    if m is None:
        return out
    for k in _list(m.keys()):
        v = m[k]
        if _lwcall(cb, v, k, m):
            out[k] = v
    return out


def clone(x):
    if isinstance(x, _list):
        return _list(x)
    if isinstance(x, _dict):
        return _dict(x)
    return x


def floor(x):
    return _math.floor(lw_num(x))


def ceil(x):
    return _math.ceil(lw_num(x))


def round(x):
    # LS round = half away from zero (Java Math.round), not banker's
    x = lw_num(x)
    return _math.floor(x + 0.5) if x >= 0 else _math.ceil(x - 0.5)


def sqrt(x):
    x = lw_num(x)
    return _math.sqrt(x) if x >= 0 else 0


def pow(a, b):
    return lw_num(a) ** lw_num(b)


def abs(x):
    x = lw_num(x)
    return x if x >= 0 else -x


def min(*args):
    vals = args[0] if len(args) == 1 else args
    vals = [v for v in lw_values(vals) if v is not None] if len(args) == 1 else [lw_num(v) for v in args]
    if not vals:
        return None
    m = vals[0]
    for v in vals[1:]:
        if v < m:
            m = v
    return m


def max(*args):
    vals = args[0] if len(args) == 1 else args
    vals = [v for v in lw_values(vals) if v is not None] if len(args) == 1 else [lw_num(v) for v in args]
    if not vals:
        return None
    m = vals[0]
    for v in vals[1:]:
        if v > m:
            m = v
    return m
# ════════ end prelude ════════
