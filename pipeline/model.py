"""
model.py - the Park Shark inference model (numpy). web/model.js is the same
maths in JavaScript; tests/ check that both give the same numbers.

Within a lot (one fill-level parameter, as in the brief):
    spots are ranked by attractiveness, r = 0 .. N-1
    P(spot i occupied | fill f) = sigmoid((f*N - r_i - 0.5) / tau)
    posterior over f on a 101-point grid = prior(f) x likelihood of the sensed spots
    P(spot i occupied) = sum_f posterior(f) * sigmoid(...)

Across lots (spillover): fill residuals z = f - mu(t) are jointly Gaussian with
    K[L, M] = s_L * s_M * rho0 * exp(-d_LM / ell)     (L != M)
Each lot with sensors acts as a noisy observation of its own fill; every other
lot's prior is the Gaussian conditioned on those observations, so its mean
shifts and its variance grows with distance from the sensed lots.

Naive baseline (from the brief): every unsensed spot gets the occupied
fraction among that lot's sensed spots (0.5 when nothing is sensed).
"""
import numpy as np

FGRID = np.linspace(0.0, 1.0, 101)
SD_FLOOR = 0.06


def sigmoid(a):
    return 1.0 / (1.0 + np.exp(-np.clip(a, -40, 40)))


def occ_matrix(n, tau):
    """S[g, i] = P(spot rank i occupied | f = FGRID[g])."""
    r = np.arange(n)
    return sigmoid((FGRID[:, None] * n - r[None, :] - 0.5) / tau)


def loglik(S, occ, mask):
    """log-likelihood over the f grid of the sensed spots (mask) with states occ."""
    if not mask.any():
        return np.zeros(len(FGRID))
    Sm = np.clip(S[:, mask], 1e-9, 1 - 1e-9)
    o = occ[mask].astype(bool)
    return np.log(Sm[:, o]).sum(1) + np.log(1 - Sm[:, ~o]).sum(1)


def gauss_prior(m, s):
    p = np.exp(-0.5 * ((FGRID - m) / max(s, 1e-3)) ** 2)
    return p / p.sum()


def lik_summary(ll):
    """Mean and variance of f under the likelihood alone (flat prior)."""
    w = np.exp(ll - ll.max()); w /= w.sum()
    m = float((w * FGRID).sum())
    return m, float((w * (FGRID - m) ** 2).sum()) + 1e-5


def kernel(D, sd, rho0, ell):
    K = rho0 * np.exp(-D / ell) * np.outer(sd, sd)
    K[np.diag_indices_from(K)] = sd ** 2
    return K


def infer(lots_S, occs, masks, mu, sd, across=None):
    """Posterior for every lot at one moment.
    lots_S[L]: occ_matrix of lot L; occs[L]: true states (only masked ones are read);
    masks[L]: bool sensed; mu[L], sd[L]: time-of-day prior; across: dict(D, rho0, ell) or None.
    Returns list of dicts: p_occ per spot, post over f, prior mean/sd used, f10/f50/f90."""
    nL = len(lots_S)
    sd = np.maximum(np.asarray(sd, float), SD_FLOOR)
    mu = np.asarray(mu, float)
    lls = [loglik(lots_S[L], occs[L], masks[L]) for L in range(nL)]
    pm, ps = mu.copy(), sd.copy()
    if across is not None:
        K = kernel(across["D"], sd, across["rho0"], across["ell"])
        obs = [L for L in range(nL) if masks[L].any()]
        summ = {L: lik_summary(lls[L]) for L in obs}
        for L in range(nL):
            o = [M for M in obs if M != L]
            if not o:
                continue
            y = np.array([summ[M][0] - mu[M] for M in o])
            Koo = K[np.ix_(o, o)] + np.diag([summ[M][1] for M in o])
            KLo = K[L, o]
            sol = np.linalg.solve(Koo, np.column_stack([y, KLo]))
            pm[L] = mu[L] + KLo @ sol[:, 0]
            ps[L] = np.sqrt(max(K[L, L] - KLo @ sol[:, 1], 1e-4))
    out = []
    for L in range(nL):
        post = gauss_prior(pm[L], ps[L]) * np.exp(lls[L] - lls[L].max())
        post /= post.sum()
        p = post @ lots_S[L]
        cdf = np.cumsum(post)
        q = [float(FGRID[min(np.searchsorted(cdf, x), 100)]) for x in (0.1, 0.5, 0.9)]
        out.append({"p_occ": p, "post": post, "prior_m": float(pm[L]), "prior_s": float(ps[L]),
                    "f_mean": float(post @ FGRID), "f10": q[0], "f50": q[1], "f90": q[2]})
    return out


def naive(occ, mask):
    return float(occ[mask].mean()) if mask.any() else 0.5


def metrics(p, truth):
    """accuracy at 0.5, Brier, log loss for P(occupied) vs truth (0/1)."""
    p = np.asarray(p, float); t = np.asarray(truth, float)
    pc = np.clip(p, 0.01, 0.99)
    return (float(((p > 0.5) == (t > 0.5)).mean()), float(((p - t) ** 2).mean()),
            float(-(t * np.log(pc) + (1 - t) * np.log(1 - pc)).mean()))


# ----------------------------------------------------------- sensor placement
CLUSTER = 12   # one Park Shark sensor sees a contiguous group of 10-15 spots


def place(strategy, k, xy, ent_d, n, rng, frontier_ranks=None):
    """Bool mask of k sensed spots. xy: (n,2) metres in rank order; ent_d: distance to entrance."""
    mask = np.zeros(n, bool)
    if k <= 0:
        return mask
    if k >= n:
        mask[:] = True; return mask
    if strategy == "scatter":
        mask[rng.choice(n, k, replace=False)] = True
        return mask
    if strategy == "entrance":
        mask[np.argsort(ent_d, kind="stable")[:k]] = True
        return mask
    ns = int(np.ceil(k / CLUSTER))
    if strategy == "frontier" and frontier_ranks is not None:
        qs = (np.arange(ns) + 0.5) / ns
        seeds = [int(np.clip(round(np.quantile(frontier_ranks, q)), 0, n - 1)) for q in qs]
    else:  # spread: farthest-point sampling in space
        seeds = [int(rng.integers(n))]
        d = np.linalg.norm(xy - xy[seeds[0]], axis=1)
        while len(seeds) < ns:
            j = int(np.argmax(d)); seeds.append(j)
            d = np.minimum(d, np.linalg.norm(xy - xy[j], axis=1))
    left = k
    for i, s in enumerate(seeds):
        take = min(CLUSTER, left) if i < len(seeds) - 1 else left
        dd = np.linalg.norm(xy - xy[s], axis=1)
        dd[mask] = np.inf
        mask[np.argsort(dd, kind="stable")[:take]] = True
        left -= take
        if left <= 0:
            break
    return mask
