# ---- 40_value: prod value model (P(win) for the side about to act) --------
# Feature layout = tools/value_dataset.NAMES; weights in 05_value_data.
_ctx_cache = {}
_MUL = float.__mul__


_SF_INV = [1 / 3000.0, 1.0, 1 / 3000.0, 1 / 301.0, 1 / 30.0, 1 / 8.0] + [1 / 600.0] * 6
_G_INV = [1.0 / VN_GSCALE[i] for i in range(len(VN_GROUPS))]
_TAIL_INV = [1 / 1000.0, 1 / 2.0, 1 / 3000.0, 1 / 10.0, 1 / 1000.0, 1 / 1000.0, 1 / 1000.0, 1.0]


def side_features(S, dist):
    """Features of one side (layout = tools/value_dataset.NAMES), scaled with
    native map chains."""
    hp = max(0.0, S['life'])
    rng, kd, kn, kp = S['kit']
    x = list(map(_MUL, map(float, (hp, hp / max(1.0, S['max'] + S['burn']), S['max'], S['level'], S['tp'], S['mp'],
                                    S['strength'], S['magic'], S['agility'], S['resistance'], S['wisdom'],
                                    S['science'])), _SF_INV))
    x += map(_MUL, map(float, map(S['groups'].__getitem__, VN_GROUPS)), _G_INV)
    x += map(_MUL, map(float, (S['pf'], S['summons'], S['burn'], rng, kd, kn, kp,
                               1.0 if dist <= S['mp'] + rng else 0.0)), _TAIL_INV)
    return x


def features(turn, dist, los, A, B):
    return [turn / 30.0, dist / 20.0, 1.0 if los else 0.0] + side_features(A, dist) + side_features(B, dist)


# transposed weights (one row per output unit) so each unit is one native
# dot product: sum(map(float.__mul__, row, inputs)) runs in C and is billed by
# length, instead of ~8 counted guest ops per multiply-add
_W1T = [[float(VN_W1[k][j]) for k in range(len(VN_CI))] for j in range(len(VN_B1))]
_W2T = [[float(VN_W2[k][j]) for k in range(len(VN_B1))] for j in range(len(VN_B2))]
_W3T = [[float(VN_W3[k][o]) for k in range(len(VN_B2))] for o in range(len(VN_B3))]


def _ctx_out(z):
    zc = [float(z[i]) for i in VN_CI]
    tanh = math.tanh
    h1 = [tanh(b + sum(map(_MUL, row, zc))) for b, row in zip(VN_B1, _W1T)]
    h2 = [tanh(b + sum(map(_MUL, row, h1))) for b, row in zip(VN_B2, _W2T)]
    out = [VN_B3[0] + sum(map(_MUL, _W3T[0], h2))]
    for o in range(1, len(VN_B3)):
        s = VN_B3[o] + sum(map(_MUL, _W3T[o], h2))
        out.append(s if s > 20 else math.log1p(math.exp(s)))
    return out


_MU = [float(v) for v in VN_MU]
_ISD = [1.0 / float(v) for v in VN_SD]
_LO = [-6.0] * len(VN_MU)
_HI = [6.0] * len(VN_MU)
_SIGNF = [float(v) for v in VN_SIGN]
_SUB = float.__sub__


def value(x, key=None):
    """P(win) for the first side of the feature vector. `key` caches the
    context net (it only reads non-actionable features). Normalisation and
    the sign-constrained slopes run as native map/sum chains."""
    z = list(map(min, _HI, map(max, _LO, map(_MUL, map(_SUB, map(float, x), _MU), _ISD))))
    out = _ctx_cache.get(key) if key is not None else None
    if out is None:
        out = _ctx_out(z)
        if key is not None:
            _ctx_cache[key] = out
    logit = out[0] + sum(map(_MUL, map(_MUL, _SIGNF, out[1:]), map(z.__getitem__, VN_MI)))
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, logit))))


def our_value(turn, dist, los, A, B):
    """Our P(win) at the end of our turn: the opponent acts next."""
    if B['life'] <= 0:
        return 1.0
    if A['life'] <= 0:
        return 0.0
    return 1.0 - value(features(turn, dist, los, B, A), key=(dist, los))
