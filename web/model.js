/* ParkFly inference model in JavaScript. Mirrors pipeline/model.py and
   pipeline/senses.py line for line; tests/parity.test.mjs checks they agree.
   Works in the browser (window.PF) and in Node (module.exports). */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.PF = factory();
})(typeof self !== "undefined" ? self : this, function () {
  const G = 101, SD_FLOOR = 0.06, CLUSTER = 12;
  const FGRID = Float64Array.from({ length: G }, (_, i) => i / 100);
  const sig = (a) => 1 / (1 + Math.exp(-Math.max(-40, Math.min(40, a))));

  function occMatrix(n, tau) {            // S[g][i] = P(spot rank i occupied | f = FGRID[g])
    const S = new Array(G);
    for (let g = 0; g < G; g++) {
      const row = new Float64Array(n);
      for (let i = 0; i < n; i++) row[i] = sig((FGRID[g] * n - i - 0.5) / tau);
      S[g] = row;
    }
    return S;
  }

  function loglik(S, occ, mask) {
    const ll = new Float64Array(G);
    let any = false;
    for (let i = 0; i < mask.length; i++) {
      if (!mask[i]) continue;
      any = true;
      for (let g = 0; g < G; g++) {
        const p = Math.min(1 - 1e-9, Math.max(1e-9, S[g][i]));
        ll[g] += occ[i] ? Math.log(p) : Math.log(1 - p);
      }
    }
    return { ll, any };
  }

  function gaussPrior(m, s) {
    const p = new Float64Array(G); let t = 0;
    s = Math.max(s, 1e-3);
    for (let g = 0; g < G; g++) { p[g] = Math.exp(-0.5 * ((FGRID[g] - m) / s) ** 2); t += p[g]; }
    for (let g = 0; g < G; g++) p[g] /= t;
    return p;
  }

  function likSummary(ll) {
    let mx = -Infinity; for (let g = 0; g < G; g++) mx = Math.max(mx, ll[g]);
    let t = 0, m = 0, v = 0; const w = new Float64Array(G);
    for (let g = 0; g < G; g++) { w[g] = Math.exp(ll[g] - mx); t += w[g]; }
    for (let g = 0; g < G; g++) m += (w[g] / t) * FGRID[g];
    for (let g = 0; g < G; g++) v += (w[g] / t) * (FGRID[g] - m) ** 2;
    return [m, v + 1e-5];
  }

  function solve(A, B) {                  // Gaussian elimination, A (k x k), B (k x m) -> X
    const k = A.length, m = B[0].length;
    const M = A.map((r, i) => r.concat(B[i]));
    for (let c = 0; c < k; c++) {
      let p = c;
      for (let r = c + 1; r < k; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
      [M[c], M[p]] = [M[p], M[c]];
      for (let r = 0; r < k; r++) {
        if (r === c) continue;
        const f = M[r][c] / M[c][c];
        for (let j = c; j < k + m; j++) M[r][j] -= f * M[c][j];
      }
    }
    return M.map((r, i) => r.slice(k).map((x) => x / M[i][i]));
  }

  function kernel(D, sd, rho0, ell) {
    const n = sd.length, K = [];
    for (let a = 0; a < n; a++) {
      K.push(new Array(n));
      for (let b = 0; b < n; b++) K[a][b] = a === b ? sd[a] * sd[a] : rho0 * Math.exp(-D[a][b] / ell) * sd[a] * sd[b];
    }
    return K;
  }

  /* Posterior for every lot at one moment. across = {D, rho0, ell} or null. */
  function infer(lotsS, occs, masks, mu, sdIn, across) {
    const nL = lotsS.length;
    const sd = sdIn.map((s) => Math.max(s, SD_FLOOR));
    const L = lotsS.map((S, i) => loglik(S, occs[i], masks[i]));
    const pm = mu.slice(), ps = sd.slice();
    if (across) {
      const K = kernel(across.D, sd, across.rho0, across.ell);
      const obs = []; for (let i = 0; i < nL; i++) if (L[i].any) obs.push(i);
      const summ = {}; obs.forEach((i) => (summ[i] = likSummary(L[i].ll)));
      for (let i = 0; i < nL; i++) {
        const o = obs.filter((j) => j !== i);
        if (!o.length) continue;
        const Koo = o.map((a, x) => o.map((b, y) => K[a][b] + (x === y ? summ[a][1] : 0)));
        const rhs = o.map((a) => [summ[a][0] - mu[a], K[i][a]]);
        const sol = solve(Koo, rhs);
        let dm = 0, dv = 0;
        o.forEach((a, x) => { dm += K[i][a] * sol[x][0]; dv += K[i][a] * sol[x][1]; });
        pm[i] = mu[i] + dm;
        ps[i] = Math.sqrt(Math.max(K[i][i] - dv, 1e-4));
      }
    }
    const out = [];
    for (let i = 0; i < nL; i++) {
      const prior = gaussPrior(pm[i], ps[i]), ll = L[i].ll, S = lotsS[i], n = S[0].length;
      let mx = -Infinity; for (let g = 0; g < G; g++) mx = Math.max(mx, ll[g]);
      const post = new Float64Array(G); let t = 0;
      for (let g = 0; g < G; g++) { post[g] = prior[g] * Math.exp(ll[g] - mx); t += post[g]; }
      const p = new Float64Array(n); let fm = 0;
      for (let g = 0; g < G; g++) {
        post[g] /= t; fm += post[g] * FGRID[g];
        const w = post[g]; if (w < 1e-12) continue;
        const row = S[g]; for (let k = 0; k < n; k++) p[k] += w * row[k];
      }
      const q = [0.1, 0.5, 0.9].map((x) => { let c = 0; for (let g = 0; g < G; g++) { c += post[g]; if (c >= x) return FGRID[g]; } return 1; });
      out.push({ p_occ: p, post, prior_m: pm[i], prior_s: ps[i], f_mean: fm, f10: q[0], f50: q[1], f90: q[2] });
    }
    return out;
  }

  function naive(occ, mask) {
    let k = 0, o = 0;
    for (let i = 0; i < mask.length; i++) if (mask[i]) { k++; o += occ[i]; }
    return k ? o / k : 0.5;
  }

  // ------------------------------------------------------------ sensor placement
  function rng32(seed) {                  // mulberry32
    let a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function quantile(arr, q) {
    const a = Array.from(arr).sort((x, y) => x - y), h = (a.length - 1) * q, lo = Math.floor(h);
    return a[lo] + (h - lo) * ((a[Math.min(lo + 1, a.length - 1)]) - a[lo]);
  }
  function place(strategy, k, xy, entD, n, rnd, frontierRanks) {
    const mask = new Uint8Array(n);
    if (k <= 0) return mask;
    if (k >= n) return mask.fill(1);
    const idx = Array.from({ length: n }, (_, i) => i);
    if (strategy === "scatter") {
      for (let i = n - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [idx[i], idx[j]] = [idx[j], idx[i]]; }
      for (let i = 0; i < k; i++) mask[idx[i]] = 1;
      return mask;
    }
    if (strategy === "entrance") {
      idx.sort((a, b) => entD[a] - entD[b]);
      for (let i = 0; i < k; i++) mask[idx[i]] = 1;
      return mask;
    }
    const ns = Math.ceil(k / CLUSTER), dist = (a, b) => Math.hypot(xy[a][0] - xy[b][0], xy[a][1] - xy[b][1]);
    let seeds = [];
    if (strategy === "frontier" && frontierRanks) {
      for (let s = 0; s < ns; s++) seeds.push(Math.max(0, Math.min(n - 1, Math.round(quantile(frontierRanks, (s + 0.5) / ns)))));
    } else {
      seeds = [Math.floor(rnd() * n)];
      const d = idx.map((i) => dist(i, seeds[0]));
      while (seeds.length < ns) {
        let j = 0; for (let i = 1; i < n; i++) if (d[i] > d[j]) j = i;
        seeds.push(j);
        for (let i = 0; i < n; i++) d[i] = Math.min(d[i], dist(i, j));
      }
    }
    let left = k;
    for (let s = 0; s < seeds.length && left > 0; s++) {
      const take = s < seeds.length - 1 ? Math.min(CLUSTER, left) : left;
      const cand = idx.filter((i) => !mask[i]).sort((a, b) => dist(a, seeds[s]) - dist(b, seeds[s]));
      for (let i = 0; i < take && i < cand.length; i++) mask[cand[i]] = 1;
      left -= take;
    }
    return mask;
  }

  // ------------------------------------------------------------------ fly senses
  const SENSE = { SUGAR_MAX_HZ: 200, BITTER_MAX_HZ: 150, LOOM_MAX_HZ: 50, UNC_FULL: 0.2, PRICE_FULL: 4,
                  WALK_SCALE_MIN: 8, FREE_SCALE: 3, RISE_FULL: 0.06, MN9_MIN_HZ: 5, GF_DIVERT_HZ: 130 };

  function tastes(n, post, S, mask, occ, walkMin, priceHr, permitRisk, rise15) {
    let sensedFree = 0;
    for (let i = 0; i < n; i++) if (mask[i] && !occ[i]) sensedFree++;
    let eFree = 0, pFull = 0; const freeG = new Float64Array(G);
    for (let g = 0; g < G; g++) {
      let f = sensedFree; const row = S[g];
      for (let i = 0; i < n; i++) if (!mask[i]) f += 1 - row[i];
      freeG[g] = f; eFree += post[g] * f; if (f < 1) pFull += post[g];
    }
    let v = 0; for (let g = 0; g < G; g++) v += post[g] * (freeG[g] - eFree) ** 2;
    const sdFree = Math.sqrt(Math.max(v, 0));
    const sugar = (1 - Math.exp(-eFree / SENSE.FREE_SCALE)) * Math.exp(-walkMin / SENSE.WALK_SCALE_MIN) * (1 - permitRisk);
    const unc = (sdFree / n) / SENSE.UNC_FULL;
    const bitter = Math.min(1, unc + permitRisk + priceHr / SENSE.PRICE_FULL);
    const loom = Math.min(1, 0.5 * Math.min(1, Math.max(rise15, 0) / SENSE.RISE_FULL) + pFull);
    return { sugar, bitter, loom, e_free: eFree, sd_free: sdFree, p_full: pFull,
             bitter_parts: { uncertainty: Math.min(1, unc), permit: permitRisk, price: priceHr / SENSE.PRICE_FULL } };
  }
  const clamp01 = (x) => Math.min(1, Math.max(0, x));
  const toHz = (t) => [SENSE.SUGAR_MAX_HZ * clamp01(t.sugar), SENSE.BITTER_MAX_HZ * clamp01(t.bitter), SENSE.LOOM_MAX_HZ * clamp01(t.loom)];

  function Surface(doc, mode) {
    this.ax = [doc.grid.sugar, doc.grid.bitter, doc.grid.loom];
    this.tab = { mn9: doc[mode].mn9, giant_fibre: doc[mode].giant_fibre, mdn: doc[mode].mdn };
  }
  Surface.prototype._w = function (a, v) {
    v = Math.min(a[a.length - 1], Math.max(a[0], v));
    let i = 0; while (i < a.length - 2 && a[i + 1] <= v) i++;
    return [i, (v - a[i]) / (a[i + 1] - a[i])];
  };
  Surface.prototype.read = function (s, b, l) {
    const [i, u] = this._w(this.ax[0], s), [j, v] = this._w(this.ax[1], b), [k, w] = this._w(this.ax[2], l), out = {};
    for (const name in this.tab) {
      const T = this.tab[name]; let acc = 0;
      for (let a = 0; a < 2; a++) for (let c = 0; c < 2; c++) for (let d = 0; d < 2; d++)
        acc += T[i + a][j + c][k + d] * (a ? u : 1 - u) * (c ? v : 1 - v) * (d ? w : 1 - w);
      out[name] = acc;
    }
    return out;
  };
  function verdict(r) {
    if (r.giant_fibre >= SENSE.GF_DIVERT_HZ) return "DIVERT";
    if (r.mdn > r.mn9 || r.mn9 < SENSE.MN9_MIN_HZ) return "BACK OFF";
    return "COMMIT";
  }
  function flyPick(reads, hz) {
    const v = reads.map(verdict), ids = reads.map((_, i) => i);
    const k0 = (i) => reads[i].mn9 - reads[i].mdn;
    const best = (list, key) => list.reduce((a, b) => { const ka = key(a), kb = key(b); return kb[0] > ka[0] || (kb[0] === ka[0] && kb[1] > ka[1]) ? b : a; });
    const commit = ids.filter((i) => v[i] === "COMMIT");
    if (commit.length) return { pick: best(commit, (i) => [k0(i), hz[i][0]]), verdicts: v, committed: true };
    let rest = ids.filter((i) => v[i] !== "DIVERT"); if (!rest.length) rest = ids;
    return { pick: best(rest, (i) => [k0(i) - reads[i].giant_fibre, hz[i][0]]), verdicts: v, committed: false };
  }

  function unpack(b64, T, n) {            // base64(packbits(matrix[time][spot])) -> array of Uint8Array
    const bin = typeof atob === "function" ? atob(b64) : Buffer.from(b64, "base64").toString("binary");
    const rows = new Array(T);
    for (let t = 0; t < T; t++) {
      const r = new Uint8Array(n);
      for (let i = 0; i < n; i++) { const k = t * n + i; r[i] = (bin.charCodeAt(k >> 3) >> (7 - (k & 7))) & 1; }
      rows[t] = r;
    }
    return rows;
  }

  return { G, FGRID, SD_FLOOR, CLUSTER, SENSE, occMatrix, loglik, infer, naive, rng32, quantile, place, tastes, toHz,
           Surface, verdict, flyPick, unpack };
});
