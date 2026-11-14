"""
senses.py - turn a lot's posterior into fly tastes, and read the fly's answer
off the measured response surface. web/model.js mirrors this file.

  sugar   = chance of a free usable spot, discounted by the walk
  bitter  = uncertainty about the lot + permit risk + price  (uncertainty tastes bitter)
  looming = the lot is filling fast, or is probably full when you arrive

Each raw taste lives in [0, 1] and is clipped there (the handbook's "clip your
inputs" rule), then scaled to a firing rate inside the range where the measured
surface responds. Verdict thresholds come from the connectome runs:
  Giant Fibre >= GF_DIVERT_HZ -> DIVERT. The Giant Fibre follows looming almost
      linearly (about 34 Hz at 10 Hz of looming input, 265 Hz at 150 Hz), so "any
      spike" would always divert; we use half of its rate in the handbook's
      looming sanity test (265 Hz -> 130 Hz).
  MDN > MN9, or MN9 below one spike per 200 ms run (5 Hz) -> BACK OFF
  otherwise COMMIT with strength = MN9 rate.
"""
import numpy as np

SUGAR_MAX_HZ, BITTER_MAX_HZ, LOOM_MAX_HZ = 200.0, 150.0, 50.0
UNC_FULL = 0.20        # posterior sd of the free fraction that counts as "fully uncertain"
PRICE_FULL = 4.0       # $/h that counts as fully bitter
WALK_SCALE_MIN = 8.0
FREE_SCALE = 3.0       # expected free spots at which "a spot is likely" saturates
RISE_FULL = 0.06       # fill increase over the next 15 min that counts as "rushing at you"
MN9_MIN_HZ = 5.0       # one spike in a 200 ms run
GF_DIVERT_HZ = 130.0   # half of the Giant Fibre's rate in the looming sanity test


def tastes(n, p_occ, post, S, mask, occ, walk_min, price_hr, permit_risk, rise15):
    """Raw tastes in [0,1] plus the numbers they came from."""
    free_g = (1 - S[:, ~mask]).sum(1) + (~occ[mask]).sum()     # expected free spots at each f
    e_free = float(post @ free_g)
    sd_free = float(np.sqrt(max(post @ (free_g - e_free) ** 2, 0.0)))
    p_full = float(post[free_g < 1.0].sum())
    sugar = (1 - np.exp(-e_free / FREE_SCALE)) * np.exp(-walk_min / WALK_SCALE_MIN) * (1 - permit_risk)
    bitter = min(1.0, (sd_free / n) / UNC_FULL + permit_risk + price_hr / PRICE_FULL)
    loom = min(1.0, min(1.0, max(rise15, 0.0) / RISE_FULL) + p_full)
    return {"sugar": float(sugar), "bitter": float(bitter), "loom": float(loom),
            "e_free": e_free, "sd_free": sd_free, "p_full": p_full,
            "availability": float(post @ (1 - np.exp(-free_g / FREE_SCALE))),
            "near_full": float(post[np.linspace(0, 1, len(post)) >= .95].sum()),
            "uncertainty": sd_free / n / UNC_FULL}


def to_hz(t):
    return (SUGAR_MAX_HZ * min(max(t["sugar"], 0), 1), BITTER_MAX_HZ * min(max(t["bitter"], 0), 1),
            LOOM_MAX_HZ * min(max(t["loom"], 0), 1))


class Surface:
    def __init__(self, doc, mode="intact"):
        g = doc["grid"]
        self.ax = [np.array(g["sugar"], float), np.array(g["bitter"], float), np.array(g["loom"], float)]
        self.tab = {k: np.array(doc[mode][k], float) for k in ("mn9", "giant_fibre", "mdn")}

    def _w(self, a, v):
        v = float(np.clip(v, a[0], a[-1]))
        i = int(min(np.searchsorted(a, v, side="right") - 1, len(a) - 2))
        return i, (v - a[i]) / (a[i + 1] - a[i])

    def read(self, s, b, l):
        (i, u), (j, v), (k, w) = self._w(self.ax[0], s), self._w(self.ax[1], b), self._w(self.ax[2], l)
        out = {}
        for name, T in self.tab.items():
            c = T[i:i + 2, j:j + 2, k:k + 2]
            c = c[0] * (1 - u) + c[1] * u
            c = c[0] * (1 - v) + c[1] * v
            out[name] = float(c[0] * (1 - w) + c[1] * w)
        return out


def verdict(r):
    if r["giant_fibre"] >= GF_DIVERT_HZ:
        return "DIVERT"
    if r["mdn"] > r["mn9"] or r["mn9"] < MN9_MIN_HZ:
        return "BACK OFF"
    return "COMMIT"


def fly_pick(reads, hz):
    """Index of the lot the fly goes for: strongest MN9 among COMMIT lots; if it commits
    to nothing, the least-bad lot (not diverting, highest MN9 - MDN, then sweetest)."""
    v = [verdict(r) for r in reads]
    key = lambda i: (reads[i]["mn9"] - reads[i]["mdn"], hz[i][0])
    commit = [i for i in range(len(reads)) if v[i] == "COMMIT"]
    if commit:
        return max(commit, key=key), v
    rest = [i for i in range(len(reads)) if v[i] != "DIVERT"] or list(range(len(reads)))
    return max(rest, key=lambda i: (key(i)[0] - reads[i]["giant_fibre"], key(i)[1])), v


def calibrated_hz(t, walk_min, price_hr, permit_risk, rise15, weights):
    """Training-fitted parking encoder; the real brain wiring/readout is unchanged."""
    sugar = t["availability"] * np.exp(-walk_min / weights["walk_scale"]) * (1 - permit_risk)
    bitter = weights["uncertainty_gain"] * t["uncertainty"] + permit_risk + price_hr / PRICE_FULL
    looming = weights["loom_gain"] * max(rise15, 0) / RISE_FULL + weights["near_full_gain"] * t["near_full"]
    return (SUGAR_MAX_HZ * float(np.clip(sugar, 0, 1)), BITTER_MAX_HZ * float(np.clip(bitter, 0, 1)),
            LOOM_MAX_HZ * float(np.clip(looming, 0, 1)))
