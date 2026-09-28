# ---- 40_value: prod value model (P(win) for the side about to act) --------
# Feature layout = tools/value_dataset.NAMES; weights in 05_value_data.
_ctx_cache = {}


def side_features(S, dist):
    hp = max(0.0, S['life'])
    x = [hp / 3000.0, hp / max(1.0, S['max'] + S['burn']), S['max'] / 3000.0, S['level'] / 301.0,
         S['tp'] / 30.0, S['mp'] / 8.0]
    x += [S['strength'] / 600.0, S['magic'] / 600.0, S['agility'] / 600.0,
          S['resistance'] / 600.0, S['wisdom'] / 600.0, S['science'] / 600.0]
    g = S['groups']
    x += [g[k] / VN_GSCALE[i] for i, k in enumerate(VN_GROUPS)]
    x += [S['pf'] / 1000.0, S['summons'] / 2.0]
    rng, kd, kn, kp = S['kit']
    x += [S['burn'] / 3000.0, rng / 10.0, kd / 1000.0, kn / 1000.0, kp / 1000.0,
          1.0 if dist <= S['mp'] + rng else 0.0]
    return x


def features(turn, dist, los, A, B):
    return [turn / 30.0, dist / 20.0, 1.0 if los else 0.0] + side_features(A, dist) + side_features(B, dist)


def _ctx_out(z):
    h1 = [math.tanh(VN_B1[j] + sum(z[VN_CI[k]] * VN_W1[k][j] for k in range(len(VN_CI)))) for j in range(len(VN_B1))]
    h2 = [math.tanh(VN_B2[j] + sum(h1[k] * VN_W2[k][j] for k in range(len(h1)))) for j in range(len(VN_B2))]
    out = []
    for o in range(len(VN_B3)):
        s = VN_B3[o] + sum(h2[k] * VN_W3[k][o] for k in range(len(h2)))
        out.append(s if o == 0 else (s if s > 20 else math.log1p(math.exp(s))))
    return out


def value(x, key=None):
    """P(win) for the first side of the feature vector. `key` caches the
    context net (it only reads non-actionable features)."""
    z = [max(-6.0, min(6.0, (x[i] - VN_MU[i]) / VN_SD[i])) for i in range(len(x))]
    out = _ctx_cache.get(key) if key is not None else None
    if out is None:
        out = _ctx_out(z)
        if key is not None:
            _ctx_cache[key] = out
    logit = out[0]
    for m in range(len(VN_MI)):
        logit += VN_SIGN[m] * out[m + 1] * z[VN_MI[m]]
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, logit))))


def our_value(turn, dist, los, A, B):
    """Our P(win) at the end of our turn: the opponent acts next."""
    if B['life'] <= 0:
        return 1.0
    if A['life'] <= 0:
        return 0.0
    return 1.0 - value(features(turn, dist, los, B, A), key=(dist, los))
