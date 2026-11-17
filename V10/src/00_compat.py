# ---- 00_compat: runtime helpers (object API only) --------------------------
# System / Debug / Fight exist both on prod and in the updated local generator
# (objects.py), so no flat-API fallback is needed.
import math

# Prod budget: a Python turn is cut by the 5 s wall-clock watchdog (reported
# as TOO_MUCH_OPERATIONS), not by System.maxOperations. Prod speed varies: on
# 2026-09-29 plain guest Python died at ~2M reported ops in the morning and at
# ~79M in the evening. The clock is frozen, so reported ops are the only gauge.
# A cut closes the context (the module reloads on the next turn) and 3 cuts
# disable the AI for the fight, so after a reload mid-fight the budget drops to
# the slow-server level. Otherwise: 30% on the first turn (context cold
# start), 50% on warm turns.
COLD_FRAC = 0.30
WARM_FRAC = 0.50
SAFE_FRAC = 0.04
SAFE_NEXT = 0.04       # budget on the turns AFTER the reload turn (0.04 = live: a fight with one cut then plays ~3 plans a
                       # turn to the end and is won 7.5% of the time, ladder 2026-11-09..16; turn 1 runs ~1.5M ops = 11%
                       # of the maximum and is cut 0.4% of the time)
CPU_STOP = 0           # CPU_STOP: milliseconds of process CPU time after which the turn's search stops (0 = off, live).
                       # time.process_time is the one clock prod leaves running; the 5 s watchdog cut lands at 4.93-4.99 s
                       # on it (18 cuts probed 2026-11-17). Without it (import fails / clock frozen) the ops budget rules alone
OPS_STOP = 560000       # refreshed each turn from System.maxOperations (see refresh_budget)
WARM_CLOCK = 0.90      # warm-turn budget while the CPU clock runs (CPU_STOP builds): the clock stops the search in
                       # time, so the ops budget only has to stay under System.maxOperations. Clock frozen or missing
                       # -> WARM_FRAC again
_T0 = [0]               # process CPU time (ns) at the start of this turn
_CLK = [0, False]       # [last reading at a turn start (or at load), the clock moved since: it is alive this turn]
try:
    import time as _tm
    _CLK[0] = _tm.process_time_ns()
except BaseException:
    _tm = None
_LOADED_AT = [0]        # Fight.turn (0 = not yet) of the first turn() since this module was loaded


def refresh_budget():
    global OPS_STOP
    if CPU_STOP and _tm is not None:
        try:
            now = _tm.process_time_ns()
            _CLK[1] = now != _CLK[0]         # a frozen clock reads the same value every time
            _CLK[0] = now; _T0[0] = now
        except BaseException:
            _CLK[1] = False
    t = Fight.turn
    if _LOADED_AT[0] == 0:
        _LOADED_AT[0] = t
    if _LOADED_AT[0] > 1:
        frac = SAFE_FRAC if t == _LOADED_AT[0] else SAFE_NEXT      # the reload turn itself runs on a cold context
    elif t == 1:
        frac = COLD_FRAC
    else:
        frac = WARM_CLOCK if _CLK[1] else WARM_FRAC
    try:
        OPS_STOP = int(System.maxOperations * frac)
    except Exception:
        OPS_STOP = int(14000000 * frac)


def ops():
    return System.operations


def over(frac=1.0):
    """True once the search should stop (ops past frac x OPS_STOP)."""
    return ops() > OPS_STOP * frac


def over_cpu(frac=1.0):
    """over() with the CPU clock as a second limit (CPU_STOP builds)."""
    return System.operations > OPS_STOP * frac or (_CLK[1] and _tm.process_time_ns() - _T0[0] > CPU_STOP * 1000000 * frac)


def used_frac():
    """Share of this turn's budget already spent: the larger of the ops share and the clock share."""
    f = System.operations / float(OPS_STOP)
    if _CLK[1]:
        g = (_tm.process_time_ns() - _T0[0]) / (CPU_STOP * 1000000.0)
        if g > f:
            f = g
    return f


def cpu_ms():
    """CPU milliseconds spent in this turn (-1: no clock)."""
    return (_tm.process_time_ns() - _T0[0]) // 1000000 if _CLK[1] else -1


if CPU_STOP and _tm is not None:
    over = over_cpu


def log(msg):
    Debug.log(msg)


def me():
    return Fight.me
