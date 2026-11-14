// The JavaScript model must give the same numbers as the Python model.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const PF = require("../web/model.js");
const J = (p) => JSON.parse(readFileSync(new URL(p, import.meta.url)));
const lots = J("../web/data/lots.json").lots, truth = J("../web/data/truth.json");
const surfDoc = J("../web/data/fly_surface.json"), cases = J("./parity_case.json").cases;
const calibration = J("../web/data/fly_calibration.json").encoder;
const fit = truth.fitted, nL = lots.length, N = lots.map((l) => l.spaces);
const close = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol, `${msg}: ${a} vs ${b}`);

test("JS model matches Python on fixed cases", () => {
  const surf = new PF.Surface(surfDoc, "intact");
  for (const c of cases) {
    const d = truth.days[c.day];
    const S = N.map((n, i) => PF.occMatrix(n, fit.tau[i][c.period]));
    const occs = N.map((n, i) => PF.unpack(d.occ[i], truth.n_steps, n)[c.ti]);
    const P = fit.prior[d.day], mu = P.mu.map((r) => r[c.ti]), sd = P.sd.map((r) => r[c.ti]);
    const across = c.across ? { D: fit.across.D, rho0: fit.across.rho0, ell: fit.across.ell_m } : null;
    const post = PF.infer(S, occs, c.masks, mu, sd, across);
    const ts = [], hz = [], reads = [];
    for (let i = 0; i < nL; i++) {
      for (let k = 0; k < N[i]; k++) close(post[i].p_occ[k], c.p_occ[i][k], 2e-5, `p_occ lot ${i} spot ${k}`);
      close(post[i].f_mean, c.f_mean[i], 1e-5, "f_mean"); close(post[i].prior_s, c.prior_s[i], 1e-5, "prior_s");
      close(post[i].f10, c.f10[i], 1e-9, "f10"); close(post[i].f90, c.f90[i], 1e-9, "f90");
      close(PF.naive(occs[i], c.masks[i]), c.naive[i], 1e-6, "naive");
      const t = PF.tastes(N[i], post[i].post, S[i], c.masks[i], occs[i], lots[i].walk_min, lots[i].price_hr, 0, 0.02);
      ["sugar", "bitter", "loom", "e_free", "sd_free", "p_full"].forEach((k, j) => close(t[k], c.tastes[i][j], 2e-5, `taste ${k}`));
      ts.push(t); hz.push(PF.toHz(t)); reads.push(surf.read(...hz[i]));
      ["mn9", "giant_fibre", "mdn"].forEach((k, j) => close(reads[i][k], c.reads[i][j], 2e-3, `read ${k}`));
    }
    const calibratedHz = ts.map((t,i)=>PF.calibratedHz(t,lots[i].walk_min+2,lots[i].price_hr,0,.02,calibration));
    calibratedHz.forEach((h,i)=>h.forEach((v,j)=>close(v,c.calibrated_hz[i][j],2e-5,"calibrated sensory Hz")));
    const calibratedReads = calibratedHz.map(h=>surf.read(...h));
    calibratedReads.forEach((r,i)=>["mn9","giant_fibre","mdn"].forEach(k=>close(r[k],c.calibrated_reads[i][k],2e-3,"calibrated neuron read")));
    assert.equal(PF.flyPick(calibratedReads,calibratedHz).pick,c.calibrated_pick);
    const fp = PF.flyPick(reads, hz);
    assert.equal(fp.pick, c.pick); assert.deepEqual(fp.verdicts, c.verdicts);
  }
});

test("sensor placement returns exactly k spots for every strategy", () => {
  const xy = lots[2].spots.map(([a, b]) => [b * 90000, a * 110000]), n = xy.length;
  const ent = xy.map((p) => Math.hypot(p[0] - xy[0][0], p[1] - xy[0][1]));
  for (const s of ["scatter", "spread", "entrance", "frontier"])
    for (const k of [0, 1, 7, 19, 40, n]) {
      const m = PF.place(s, k, xy, ent, n, PF.rng32(3), [10, 20, 30, 40, 50]);
      assert.equal(m.reduce((a, b) => a + b, 0), k, `${s} k=${k}`);
    }
});
