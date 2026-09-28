# ---- 00_compat: prod object API vs local polyglot differences ------------
import math
OPS_BUDGET = 14000000
OPS_STOP = 8500000          # stop searching past this; execution needs headroom


def ops():
    try:
        return System.operations
    except NameError:
        return getOperations()


def log(msg):
    try:
        Debug.log(msg)
        return
    except Exception:
        pass
    try:
        debug(msg)
    except Exception:
        pass


def me():
    return Fight.me
