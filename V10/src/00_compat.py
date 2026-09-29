# ---- 00_compat: runtime helpers (object API only) --------------------------
# System / Debug / Fight exist both on prod and in the updated local generator
# (objects.py), so no flat-API fallback is needed.
import math

OPS_STOP_FRAC = 0.6     # stop searching past this share of the budget; execution needs headroom
OPS_STOP = 8500000      # refreshed each turn from System.maxOperations (see refresh_budget)


def refresh_budget():
    global OPS_STOP
    try:
        OPS_STOP = int(System.maxOperations * OPS_STOP_FRAC)
    except Exception:
        pass


def ops():
    return System.operations


def log(msg):
    Debug.log(msg)


def me():
    return Fight.me
