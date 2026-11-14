"""
flybrain.py - the organizers' fly_brain_starter simulator, as a module.

Loads the real FlyWire connectome in Shiu et al. 2024 form (Connectivity_783,
signed synapse counts) and simulates leaky integrate-and-fire neurons with
Shiu's exact settings. `simulate` is the starter notebook's function with the
same maths and the same random-number order; the only additions are optional
and do not change results:
  input_until_ms  stop the Poisson input after this time ("input stops" check)
  late_from_ms    also return spike counts after this time
  track           record spike times for a chosen set of neurons (raster)

No FlyWire token is needed for any of this.
"""
import os
import urllib.request

import numpy as np
import pandas as pd
import scipy.sparse as sp

SHIU = "https://github.com/philshiu/Drosophila_brain_model/raw/main/"
LABELS_URL = ("https://github.com/flyconnectome/flywire_annotations/raw/main/supplemental_files/"
              "Supplemental_file1_neuron_annotations.tsv")
MN9_ROOT_ID = 720575940660219265  # not in the label file; ID from Shiu et al. 2024
WIRING_FILE = "Connectivity_783.parquet"
NEURON_FILE = "Completeness_783.csv"

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(os.path.dirname(HERE), "data", "fly")


def _get(url, name):
    os.makedirs(CACHE, exist_ok=True)
    dest = os.path.join(CACHE, name)
    if not (os.path.exists(dest) and os.path.getsize(dest) > 0):
        print("[get ]", url, flush=True)
        tmp = dest + ".part"
        req = urllib.request.Request(url, headers={"User-Agent": "parkfly-hackday/0.1"})
        with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
        os.replace(tmp, dest)
    return dest


class Brain:
    """W[pre, post] = signed synapse count. Rows presynaptic, columns postsynaptic."""

    def __init__(self):
        neurons = pd.read_csv(_get(SHIU + NEURON_FILE, NEURON_FILE), index_col=0)
        wiring = pd.read_parquet(_get(SHIU + WIRING_FILE, WIRING_FILE))
        labels = pd.read_csv(_get(LABELS_URL, "neuron_annotations.tsv"), sep="\t", low_memory=False)
        self.N = N = len(neurons)
        self.W = sp.csr_matrix((wiring["Excitatory x Connectivity"],
                                (wiring["Presynaptic_Index"], wiring["Postsynaptic_Index"])), shape=(N, N))
        self.n_connections = int(self.W.nnz)
        row = {root_id: i for i, root_id in enumerate(neurons.index)}

        def find(mask):
            return np.array([row[r] for r in labels.root_id[mask] if r in row])

        self.groups = {
            "sugar": find(labels.cell_type == "LB3c"),
            "bitter": find(labels.cell_sub_class == "bitter"),
            "looming": find(labels.cell_type.isin(["LC4", "LPLC2"])),
            "giant_fibre": find(labels.cell_type == "DNp01"),
            "mdn": find(labels.cell_type == "MDN"),
            "dnp09": find(labels.cell_type == "DNp09"),
            "mn9": np.array([row[MN9_ROOT_ID]]),
        }
        self._lesions = {}

    def lesioned(self, group):
        """Cut every synapse ONTO the group (zero its input columns) so it cannot
        be driven. (The starter's `diags(keep) @ W` cuts its outputs instead:
        the neuron still fires, which would not change a verdict read from it.)"""
        if group not in self._lesions:
            keep = np.ones(self.N)
            keep[self.groups[group]] = 0
            self._lesions[group] = (self.W @ sp.diags(keep)).tocsr()
        return self._lesions[group]

    def simulate(self, inputs, ms=200, W=None, seed=0, input_until_ms=None, late_from_ms=None, track=None):
        """inputs: [(neuron_indices, rate_hz), ...] -> spike count per neuron.
        Returns counts, or (counts, extras) when late_from_ms or track is given."""
        W = self.W if W is None else W
        N = self.N
        dt, v0, vth, tm, ts, ref = 0.1, -52.0, -45.0, 20.0, 5.0, 2.2
        wsyn, kick, delay = 0.275, 250 * 0.275, int(1.8 / 0.1)
        rng = np.random.default_rng(seed)
        v, g = np.full(N, v0), np.zeros(N)
        last, counts = np.full(N, -1e9), np.zeros(N, int)
        late = np.zeros(N, int) if late_from_ms is not None else None
        driven = np.zeros(N, bool)
        for idx, _ in inputs:
            driven[idx] = True
        ring = np.zeros((delay, N))
        tracked = None
        if track is not None:
            tracked = np.full(N, -1)
            tracked[track] = np.arange(len(track))
        spikes = []
        decay = np.exp(-dt / ts)
        for k in range(int(ms / dt)):
            t, slot = k * dt, k % delay
            g += ring[slot]; ring[slot] = 0
            free = ((t - last) > ref) | driven
            v[free] += dt * (v0 - v[free] + g[free]) / tm
            g[free] *= decay
            for idx, hz in inputs:
                fire = idx[rng.random(len(idx)) < hz * dt / 1000]
                if input_until_ms is None or t < input_until_ms:
                    v[fire] += kick
            s = np.flatnonzero(v > vth)
            v[s], g[s], last[s] = v0, 0.0, t
            counts[s] += 1
            if late is not None and t >= late_from_ms:
                late[s] += 1
            if tracked is not None and len(s):
                hit = tracked[s]
                for j in hit[hit >= 0]:
                    spikes.append((round(t, 1), int(j)))
            if len(s):
                ring[slot] += np.asarray(W[s].sum(0)).ravel() * wsyn
        if late is None and tracked is None:
            return counts
        return counts, {"late": late, "spikes": spikes}

    def rate(self, counts, group, ms=200):
        idx = self.groups[group] if isinstance(group, str) else group
        return float(counts[idx].sum() / len(idx) / (ms / 1000))
