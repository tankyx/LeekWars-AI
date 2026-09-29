# ---- 00_compat: runtime helpers (object API only) --------------------------
# System / Debug / Fight exist both on prod and in the updated local generator
# (objects.py), so no flat-API fallback is needed.
import math

# Prod budget (probed 2026-09-29): a Python turn is cut by the 5 s wall-clock
# watchdog (reported as TOO_MUCH_OPERATIONS), not by System.maxOperations (14M).
# Prod Python currently runs ~0.4M reported ops/s of plain guest code, and the
# clock is frozen, so reported ops are the only gauge. A watchdog cut closes the
# context (the module reloads on the next turn) and 3 cuts disable the AI for
# the fight. Search stops at a share of the reported budget: 4% on the first
# turn (context cold start), 6% on warm turns, 2% after a reload mid-fight.
COLD_FRAC = 0.04
WARM_FRAC = 0.06
SAFE_FRAC = 0.02
OPS_STOP = 560000       # refreshed each turn from System.maxOperations (see refresh_budget)
_LOADED_AT = [0]        # Fight.turn (0 = not yet) of the first turn() since this module was loaded


def refresh_budget():
    global OPS_STOP
    t = Fight.turn
    if _LOADED_AT[0] == 0:
        _LOADED_AT[0] = t
    if _LOADED_AT[0] > 1:
        frac = SAFE_FRAC
    elif t == 1:
        frac = COLD_FRAC
    else:
        frac = WARM_FRAC
    try:
        OPS_STOP = int(System.maxOperations * frac)
    except Exception:
        OPS_STOP = int(14000000 * frac)


def ops():
    return System.operations


def over(frac=1.0):
    """True once the search should stop (ops past frac x OPS_STOP)."""
    return ops() > OPS_STOP * frac


def log(msg):
    Debug.log(msg)


def me():
    return Fight.me
