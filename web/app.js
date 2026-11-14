/* ParkFly UI. All numbers come from web/data/*.json (pipeline exports) or are
   computed here with web/model.js on the simulated truth. */
(() => {
  const $ = (id) => document.getElementById(id);
  const C = { orange: "#e07b39", cream: "#f5f0e8", gray: "#8a9bb5", green: "#4ade80", red: "#ef4444", yellow: "#facc15",
              purple: "#b693f5", blue: "#60a5fa", navy: "#0d1f3c" };
  const st = { pct: 25, strategy: "scatter", shuffle: 1, whole: new Set(), spill: true, lesion: false, persona: "commuter",
               day: 0, ti: 48, truth: false, tab: "sense", flySel: null, metric: "map", demo: -1 };
  let D = {}, map, canvasR, spotLayers = [], labelMarkers = [], lots, nL, T, fit, days, surf = {}, cur = null, playTimer = null;

  const fetchJ = (f, optional) => fetch("data/" + f).then((r) => { if (!r.ok) throw new Error(f); return r.json(); })
    .catch((e) => { if (optional) return null; throw e; });
  const short = (n) => n.replace("Poulton Deck - Visitor Pay Area", "Poulton Deck · visitor pay").replace("Poulton Deck - C", "Poulton Deck · C permit")
    .replace("Main Campus Drive - C", "Main Campus Dr").replace("E.B. III / Entrepreneur Drive", "E.B. III").replace(" Lot", "");
  const fmtTime = (m) => { const h = Math.floor(m / 60), mm = m % 60; return `${((h + 11) % 12) + 1}:${String(mm).padStart(2, "0")} ${h < 12 ? "AM" : "PM"}`; };
  const pfColor = (pFree) => {            // red -> yellow -> green
    const mix = (a, b, t) => a.map((x, i) => Math.round(x + (b[i] - x) * t));
    const r = [239, 68, 68], y = [250, 204, 21], g = [74, 222, 128];
    const c = pFree < 0.5 ? mix(r, y, pFree * 2) : mix(y, g, (pFree - 0.5) * 2);
    return `rgb(${c[0]},${c[1]},${c[2]})`;
  };
  const pct1 = (x) => (100 * x).toFixed(0) + "%";

  // ------------------------------------------------------------------ boot
  async function boot() {
    const [lotsDoc, truth, results, surface, raster, sanity, bham] = await Promise.all([
      fetchJ("lots.json"), fetchJ("truth.json"), fetchJ("results.json"), fetchJ("fly_surface.json"),
      fetchJ("fly_raster.json", true), fetchJ("fly_sanity.json", true), fetchJ("birmingham.json", true)]);
    D = { lotsDoc, truth, results, surface, raster, sanity, bham };
    lots = lotsDoc.lots; nL = lots.length; T = truth.n_steps; fit = truth.fitted;
    surf = { intact: new PF.Surface(surface, "intact"), lesion: new PF.Surface(surface, "lesion_gf") };
    const lat0 = lotsDoc.dest.lat, mx = 111320 * Math.cos((lat0 * Math.PI) / 180), my = 110540;
    lots.forEach((l, i) => {
      l.n = l.spaces; l.short = short(l.name); l.below = l.name === "Poulton Deck - C";
      l.xy = l.spots.map(([la, lo]) => [(lo - lotsDoc.dest.lon) * mx, (la - lat0) * my]);
      const e = [(l.entrance[1] - lotsDoc.dest.lon) * mx, (l.entrance[0] - lat0) * my];
      l.entD = l.xy.map((p) => Math.hypot(p[0] - e[0], p[1] - e[1]));
      l.S = [PF.occMatrix(l.n, fit.tau[i][0]), PF.occMatrix(l.n, fit.tau[i][1])];
      l.center = [l.spots.reduce((a, s) => a + s[0], 0) / l.n, l.spots.reduce((a, s) => a + s[1], 0) / l.n];
      const mu = fit.prior.weekday.mu[i]; l.frontier = [];
      for (let t = 0; t < T; t++) { const m = truth.start_min + t * truth.step_min; if (m >= 480 && m <= 1020) l.frontier.push(mu[t] * l.n); }
    });
    days = truth.days.map((d) => ({ ...d, occ: d.occ.map((b, i) => PF.unpack(b, T, lots[i].n)) }));
    let wk = 0;
    $("day").innerHTML = days.map((d, i) => `<option value="${i}">${d.day === "sat" ? "Simulated Saturday" : "Simulated weekday " + "ABCDEFG"[wk++]}</option>`).join("");
    initMap(); bind(); staticPanels(); update(); requestAnimationFrame(rasterLoop);
    if (new URLSearchParams(location.search).get("demo")) startDemo();
  }

  // ------------------------------------------------------------------- map
  function initMap() {
    map = L.map("map", { zoomControl: true, preferCanvas: true, zoomSnap: 0.25 });
    canvasR = L.canvas({ padding: 0.4 });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      { attribution: "© OpenStreetMap contributors · lots: NCSU Transportation GIS", maxZoom: 20, maxNativeZoom: 19, className: "darktiles" }).addTo(map);
    map.zoomControl.setPosition("topright");
    D.lotsDoc.context.forEach((c) => {
      c.polys.forEach((p) => L.polygon(p, c.focus
        ? { color: C.cream, weight: 2, fillColor: "#1a3566", fillOpacity: 0.55, renderer: canvasR }
        : { color: "#4a6a9c", weight: 1, fillColor: "#1a3566", fillOpacity: 0.3, renderer: canvasR })
        .addTo(map).bindTooltip(`${c.name}<br>${c.spaces} spaces (official NCSU) · zone ${c.zone || "n/a"}${c.focus ? "" : "<br>not modeled spot by spot"}`, { sticky: true }));
    });
    const pts = [];
    lots.forEach((l, i) => {
      const arr = l.spots.map((s, k) => {
        pts.push(s);
        const m = L.circleMarker(s, { renderer: canvasR, radius: 4, weight: 0, fillOpacity: 0.9, fillColor: C.gray, color: "#fff" }).addTo(map);
        m.bindTooltip(() => spotTip(i, k), { sticky: true });
        return m;
      });
      spotLayers.push(arr);
      const mk = L.marker(l.center, { icon: L.divIcon({ className: "lotlabel", html: "", iconSize: [0, 0] }), zIndexOffset: 500 }).addTo(map);
      mk.on("click", () => { toggleWhole(i); });
      labelMarkers.push(mk);
    });
    const d = D.lotsDoc.dest;
    L.circleMarker([d.lat, d.lon], { radius: 8, color: "#fff", weight: 2, fillColor: C.orange, fillOpacity: 1 }).addTo(map)
      .bindTooltip("📚 " + d.name + " (destination)", { permanent: true, direction: "right", className: "destlabel", offset: [10, 0] });
    const fit0 = () => { map.invalidateSize(); map.fitBounds(L.latLngBounds(pts).pad(0.1)); };
    fit0(); setTimeout(fit0, 60); window.addEventListener("resize", () => map.invalidateSize());
    map.on("zoomend", () => { const r = spotRadius(); spotLayers.flat().forEach((m) => m.setRadius(r)); placeLabels(); });
  }
  const spotRadius = () => { const z = map.getZoom(); return z >= 19 ? 8 : z >= 18 ? 5.5 : z >= 17.25 ? 4 : z >= 16.5 ? 3 : 2; };
  function spotTip(i, k) {
    if (!cur) return "";
    const l = lots[i], sensed = cur.masks[i][k], pf = 1 - cur.post[i].p_occ[k], occ = cur.occs[i][k];
    return `<b>${l.short}</b> · spot ${k + 1} of ${l.n} (by attractiveness)<br>` +
      (sensed ? `sensor: <b>${occ ? "taken" : "free"}</b>` : `inferred: <b>${pct1(pf)}</b> chance it is free`) +
      (st.truth ? `<br>simulated truth: ${occ ? "taken" : "free"}` : "");
  }

  // ------------------------------------------------------------- compute
  function period() { return D.truth.start_min + st.ti * D.truth.step_min < fit.tau_pm_from_min ? 0 : 1; }
  function buildMasks() {
    return lots.map((l, i) => {
      if (st.whole.has(i)) return new Uint8Array(l.n).fill(1);
      const k = Math.round((st.pct / 100) * l.n);
      return PF.place(st.strategy, k, l.xy, l.entD, l.n, PF.rng32(st.shuffle * 7919 + i * 104729 + 17), l.frontier);
    });
  }
  function freeAt(l, S, mask, occ, f) {
    const row = S[Math.round(f * 100)]; let x = 0;
    for (let k = 0; k < l.n; k++) x += mask[k] ? (occ[k] ? 0 : 1) : 1 - row[k];
    return x;
  }
  function compute() {
    const d = days[st.day], P = fit.prior[d.day], p = period();
    const S = lots.map((l) => l.S[p]), occs = lots.map((_, i) => d.occ[i][st.ti]), masks = buildMasks();
    const mu = P.mu.map((r) => r[st.ti]), sd = P.sd.map((r) => r[st.ti]);
    const across = st.spill ? { D: fit.across.D, rho0: fit.across.rho0, ell: fit.across.ell_m } : null;
    const post = PF.infer(S, occs, masks, mu, sd, across);
    const k15 = Math.round(15 / D.truth.step_min), sf = st.lesion ? surf.lesion : surf.intact;
    const lotsOut = lots.map((l, i) => {
      const risk = st.persona === "visitor" ? (l.pay ? 0 : 1) : 0;
      const rise = P.mu[i][Math.min(st.ti + k15, T - 1)] - P.mu[i][st.ti];
      const t = PF.tastes(l.n, post[i].post, S[i], masks[i], occs[i], l.walk_min, l.price_hr, risk, rise);
      const hz = PF.toHz(t), read = sf.read(hz[0], hz[1], hz[2]);
      const trueFree = occs[i].reduce((a, o) => a + (1 - o), 0);
      let sensed = 0; for (let k = 0; k < l.n; k++) sensed += masks[i][k];
      return { t, hz, read, verdict: PF.verdict(read), trueFree, sensed, free: t.e_free,
               lo: freeAt(l, S[i], masks[i], occs[i], post[i].f90), hi: freeAt(l, S[i], masks[i], occs[i], post[i].f10) };
    });
    const cand = lots.map((l, i) => i).filter((i) => st.persona === "visitor" || !lots[i].pay);
    const fp = PF.flyPick(cand.map((i) => lotsOut[i].read), cand.map((i) => lotsOut[i].hz));
    // live scores for this moment
    let right = 0, rightN = 0, tot = 0, b = 0, bn = 0, nu = 0, fe = 0, fen = 0;
    lots.forEach((l, i) => {
      const nv = PF.naive(occs[i], masks[i]); let ef = 0, efn = 0, tf = 0;
      for (let k = 0; k < l.n; k++) {
        tot++;
        if (masks[i][k]) { right++; rightN++; continue; }
        const pm = post[i].p_occ[k], o = occs[i][k];
        right += (pm > 0.5) === !!o; rightN += (nv > 0.5) === !!o;
        b += (pm - o) ** 2; bn += (nv - o) ** 2; nu++;
        ef += 1 - pm; efn += 1 - nv; tf += 1 - o;
      }
      fe += Math.abs(ef - tf); fen += Math.abs(efn - tf);
    });
    cur = { S, occs, masks, post, mu, sd, lots: lotsOut, cand, pick: cand[fp.pick], committed: fp.committed,
            live: { map: right / tot, mapN: rightN / tot, brier: nu ? b / nu : null, brierN: nu ? bn / nu : null,
                    free: fe / nL, freeN: fen / nL, nu, tot } };
    if (st.flySel == null || !cand.includes(st.flySel)) st.flySel = cur.pick;
  }

  // -------------------------------------------------------------- render
  function update() { compute(); render(); }
  function render() {
    const r = spotRadius();
    lots.forEach((l, i) => {
      const m = cur.masks[i], p = cur.post[i].p_occ, o = cur.occs[i];
      for (let k = 0; k < l.n; k++) {
        const pf = m[k] ? 1 - o[k] : 1 - p[k];
        let style;
        if (st.truth) {
          const wrong = !m[k] && (p[k] > 0.5) !== !!o[k];
          style = { fillColor: pfColor(1 - o[k]), fillOpacity: 0.95, weight: wrong ? 2 : m[k] ? 1.5 : 0, color: wrong ? "#000" : "#fff", radius: r };
        } else {
          style = m[k] ? { fillColor: pfColor(pf), fillOpacity: 1, weight: 1.8, color: "#fff", radius: r }
                       : { fillColor: pfColor(pf), fillOpacity: 0.28 + 0.67 * Math.abs(2 * pf - 1), weight: 0, color: "#fff", radius: r };
        }
        spotLayers[i][k].setStyle(style);
      }
    });
    placeLabels();
    $("pctVal").textContent = st.pct + "%";
    const totalSensed = cur.lots.reduce((a, x) => a + x.sensed, 0), tot = cur.live.tot;
    $("pctNote").textContent = `${totalSensed} of ${tot} spots sensed · about ${Math.ceil(totalSensed / PF.CLUSTER)} Park Shark sensors`;
    $("clock").textContent = fmtTime(D.truth.start_min + st.ti * D.truth.step_min);
    renderSense(); renderSpill(); renderPlace(); renderFly();
  }
  function placeLabels() {
    if (!cur) return;
    lots.forEach((l, i) => {
      const x = cur.lots[i], isPick = i === cur.pick && cur.committed, v = x.verdict.split(" ")[0];
      const inCand = cur.cand.includes(i);
      const html = `<div class="ll ${l.below ? "below" : ""} ${st.whole.has(i) ? "whole" : ""} ${isPick ? "pick" : ""}" title="Click to put sensors on this whole lot">
        <b>${l.short}</b> <span class="fr">${Math.round(x.free)} free</span> <span class="rng">(${Math.round(x.lo)}–${Math.round(x.hi)})</span>
        ${st.truth ? `<span class="rng"> · truth ${x.trueFree}</span>` : ""}
        ${inCand ? `<span class="vd ${v}">${isPick ? "🪰 " : ""}fly: ${verdictText(x.verdict)}</span>` : ""}</div>`;
      labelMarkers[i].setIcon(L.divIcon({ className: "lotlabel", html, iconSize: [0, 0], iconAnchor: [0, 10] }));
    });
  }
  const verdictText = (v) => (v === "COMMIT" ? "commit" : v === "DIVERT" ? "divert" : "back off");

  // ---- charts
  function lineChart(el, o) {
    const W = 436, H = o.h || 190, m = { l: 44, r: 10, t: 8, b: 30 }, iw = W - m.l - m.r, ih = H - m.t - m.b;
    const xs = o.xdom || [0, 100];
    let ys = o.ydom;
    if (!ys) {
      const all = o.series.flatMap((s) => s.y.filter((v) => v != null)).concat((o.markers || []).map((k) => k.y).filter((v) => v != null));
      const lo = Math.min(...all), hi = Math.max(...all), pad = (hi - lo) * 0.1 || 0.01; ys = [lo - pad, hi + pad];
    }
    const X = (v) => m.l + ((v - xs[0]) / (xs[1] - xs[0])) * iw, Y = (v) => m.t + ih - ((v - ys[0]) / (ys[1] - ys[0])) * ih;
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img">`;
    if (o.zone) s += `<rect x="${X(o.zone[0])}" y="${m.t}" width="${X(o.zone[1]) - X(o.zone[0])}" height="${ih}" fill="${C.orange}" opacity=".16"/>`;
    for (let i = 0; i <= 4; i++) {
      const v = ys[0] + ((ys[1] - ys[0]) * i) / 4, y = Y(v);
      s += `<line x1="${m.l}" x2="${W - m.r}" y1="${y}" y2="${y}" stroke="rgba(255,255,255,.09)"/><text x="${m.l - 6}" y="${y + 4}" text-anchor="end" font-size="11" fill="${C.gray}">${(o.yfmt || ((q) => q.toFixed(2)))(v)}</text>`;
    }
    (o.xticks || [0, 25, 50, 75, 100]).forEach((v) => { s += `<text x="${X(v)}" y="${H - 14}" text-anchor="middle" font-size="11" fill="${C.gray}">${v}${o.xunit ?? "%"}</text>`; });
    s += `<text x="${m.l + iw / 2}" y="${H - 1}" text-anchor="middle" font-size="11" fill="${C.gray}">${o.xlabel || "% of spots with sensors"}</text>`;
    o.series.forEach((se) => {
      const pts = se.x.map((x, i) => (se.y[i] == null ? null : [X(x), Y(se.y[i])])).filter(Boolean);
      if (se.band) {
        const up = se.x.map((x, i) => `${X(x)},${Y(Math.min(ys[1], se.y[i] + se.band[i]))}`), dn = se.x.map((x, i) => `${X(x)},${Y(Math.max(ys[0], se.y[i] - se.band[i]))}`).reverse();
        s += `<polygon points="${up.concat(dn).join(" ")}" fill="${se.color}" opacity=".13"/>`;
      }
      s += `<polyline points="${pts.map((p) => p.join(",")).join(" ")}" fill="none" stroke="${se.color}" stroke-width="${se.w || 2.4}" ${se.dash ? `stroke-dasharray="${se.dash}"` : ""} stroke-linejoin="round"/>`;
    });
    (o.markers || []).forEach((k) => { if (k.y != null) s += `<line x1="${X(k.x)}" x2="${X(k.x)}" y1="${m.t}" y2="${m.t + ih}" stroke="rgba(255,255,255,.25)" stroke-dasharray="3 3"/><circle cx="${X(k.x)}" cy="${Y(Math.max(ys[0], Math.min(ys[1], k.y)))}" r="5.5" fill="${k.color}" stroke="#fff" stroke-width="2"/>`; });
    let lx = m.l + 6;
    o.series.forEach((se) => { s += `<rect x="${lx}" y="${m.t + 2}" width="14" height="3.5" fill="${se.color}"/><text x="${lx + 18}" y="${m.t + 8}" font-size="11.5" fill="#fff">${se.name}</text>`; lx += 24 + se.name.length * 6.2; });
    el.innerHTML = s + "</svg>";
  }

  function renderSense() {
    const R = D.results, src = R.density[st.spill ? "spill" : "within"], px = R.pcts, L = cur.live;
    $("kMap").textContent = pct1(L.map);
    $("kMapSub").innerHTML = `naive baseline <b>${pct1(L.mapN)}</b> · right now`;
    $("kBrier").textContent = L.brier == null ? "n/a" : L.brier.toFixed(3);
    $("kBrierSub").innerHTML = L.brier == null ? "every spot has a sensor" : `naive <b>${L.brierN.toFixed(3)}</b> · lower is better`;
    const M = { map: ["model_map_acc", "naive_map_acc", (v) => (100 * v).toFixed(0) + "%", 1, L.map, L.mapN],
                brier: ["model_brier", "naive_brier", (v) => v.toFixed(2), null, L.brier, L.brierN],
                free: ["model_free_mae", "naive_free_mae", (v) => v.toFixed(1), 0, L.free, L.freeN] }[st.metric];
    const x = px.concat(M[3] == null ? [] : [100]);
    const get = (k) => src.map((r) => r[k][0]).concat(M[3] == null ? [] : [M[3]]), band = (k) => src.map((r) => r[k][1]).concat(M[3] == null ? [] : [0]);
    lineChart($("chartDensity"), { zone: [20, 30], yfmt: M[2],
      series: [{ name: "Naive baseline", x, y: get(M[1]), color: C.gray, band: band(M[1]) },
               { name: "ParkFly model", x, y: get(M[0]), color: C.orange, band: band(M[0]), w: 3 }],
      markers: [{ x: st.pct, y: M[5], color: C.gray }, { x: st.pct, y: M[4], color: C.orange }] });
    const i25 = px.indexOf(25), a = src[i25];
    $("densityNote").innerHTML = `Lines: average over ${a.n_evals} held-out simulated moments (band ±1 SD). Dots: this moment, this layout. ` +
      `At 25% sensed the model's Brier error is <b>${a.model_brier[0].toFixed(3)}</b> vs <b>${a.naive_brier[0].toFixed(3)}</b> naive ` +
      `(${Math.round(100 * (1 - a.model_brier[0] / a.naive_brier[0]))}% lower). Shaded: Park Shark's 20–30% target.`;
    $("lotTable").innerHTML = `<tr><th>Lot</th><th>Spaces<br>(NCSU)</th><th>Sensed</th><th>Free, est.</th>${st.truth ? "<th>Truth</th>" : ""}</tr>` +
      lots.map((l, i) => { const x = cur.lots[i]; return `<tr data-i="${i}"><td>${l.short}</td><td>${l.n}</td><td>${x.sensed}</td><td><b>${Math.round(x.free)}</b> <span class="rng">(${Math.round(x.lo)}–${Math.round(x.hi)})</span></td>${st.truth ? `<td>${x.trueFree}</td>` : ""}</tr>`; }).join("");
  }

  function renderSpill() {
    $("wholeList").innerHTML = lots.map((l, i) => `<button data-i="${i}" class="${st.whole.has(i) ? "on" : ""}">${st.whole.has(i) ? "📡 " : ""}${l.short}</button>`).join("");
    // uncertainty bars: time-of-day prior vs what this lot knows now (posterior sd of fill)
    const W = 436, rowH = 22, H = nL * rowH + 22; let s = `<svg viewBox="0 0 ${W} ${H}">`;
    const order = lots.map((_, i) => i).sort((a, b) => lots[a].walk_min - lots[b].walk_min), mx = 0.2, bw = W - 170;
    order.forEach((i, r) => {
      const y = r * rowH + 4, before = Math.max(cur.sd[i], PF.SD_FLOOR);
      let v = 0; const po = cur.post[i].post, fm = cur.post[i].f_mean; for (let g = 0; g < PF.G; g++) v += po[g] * (PF.FGRID[g] - fm) ** 2;
      const after = Math.sqrt(v);
      s += `<text x="0" y="${y + 12}" font-size="12" fill="#fff">${lots[i].short.slice(0, 22)}</text>` +
        `<rect x="150" y="${y + 1}" width="${(Math.min(before, mx) / mx) * bw}" height="7" fill="${C.gray}" opacity=".7" rx="2"/>` +
        `<rect x="150" y="${y + 9}" width="${(Math.min(after, mx) / mx) * bw}" height="7" fill="${st.whole.has(i) ? "#fff" : C.orange}" rx="2"/>` +
        `<text x="${W}" y="${y + 13}" font-size="11" text-anchor="end" fill="${C.gray}">±${(100 * after).toFixed(0)}%</text>`;
    });
    s += `<rect x="150" y="${H - 12}" width="12" height="5" fill="${C.gray}" opacity=".7"/><text x="166" y="${H - 6}" font-size="11" fill="${C.gray}">time of day only</text>` +
      `<rect x="270" y="${H - 12}" width="12" height="5" fill="${C.orange}"/><text x="286" y="${H - 6}" font-size="11" fill="${C.gray}">with the sensors on now</text></svg>`;
    $("chartUnc").innerHTML = s;
    const B = D.bham;
    if (!B) { $("bhamHeadline").textContent = "Birmingham validation not loaded."; return; }
    $("bhamHeadline").innerHTML = `Hide 75% of ${B.n_lots} real car parks, sense 25%: error on the hidden ones drops <b>${B.gain_at_25.gain_pct.toFixed(0)}%</b> ` +
      `(${(100 * B.gain_at_25.mae_none).toFixed(1)} → ${(100 * B.gain_at_25.mae_spill).toFixed(1)} points of occupancy).`;
    lineChart($("chartBham"), { h: 160, xlabel: "% of car parks with sensors", zone: [20, 30], yfmt: (v) => (100 * v).toFixed(0) + " pts",
      series: [{ name: "No sensors (hour × weekday average)", x: B.pcts, y: B.pcts.map(() => B.mae_none), color: C.gray, dash: "5 4" },
               { name: "With spillover", x: B.pcts, y: B.mae_spill, band: B.mae_spill_sd, color: C.green, w: 3 }] });
    $("bhamNote").textContent = B.note;
  }

  function renderPlace() {
    const P = D.results.placement, i25 = P.pcts.indexOf(25);
    document.querySelectorAll("#placeSeg button").forEach((b) => b.classList.toggle("on", b.dataset.s === st.strategy));
    const col = { entrance: C.red, spread: C.blue, frontier: C.orange, scatter: C.gray }, nm = { entrance: "Entrance", spread: "Spread", frontier: "Frontier", scatter: "Scattered" };
    const b = (s) => P.strategies[s][i25].model_brier[0];
    $("placeHeadline").innerHTML = `Same sensors, 25% of spots: <b>spread</b> placement has ${Math.round(100 * (1 - b("spread") / b("entrance")))}% lower error than entrance-clustered ` +
      `(${b("spread").toFixed(3)} vs ${b("entrance").toFixed(3)}); the <b>fill frontier</b> does best (${b("frontier").toFixed(3)}).`;
    lineChart($("chartPlace"), { xdom: [P.pcts[0], P.pcts[P.pcts.length - 1]], xticks: P.pcts, zone: [20, 30],
      series: ["entrance", "spread", "frontier", "scatter"].map((s) => ({ name: nm[s], x: P.pcts, y: P.strategies[s].map((r) => r.model_brier[0]), color: col[s], w: s === st.strategy ? 3.6 : 1.8 })),
      markers: st.pct >= P.pcts[0] && st.pct <= 50 && cur.live.brier != null ? [{ x: st.pct, y: cur.live.brier, color: col[st.strategy] }] : [] });
    $("placeNote").textContent = `Simulated held-out weekdays, clusters of ${P.cluster_size} neighboring spots per sensor. Dot: the layout on the map right now.`;
  }

  function renderFly() {
    const pk = cur.lots[cur.pick], pl = lots[cur.pick];
    let h = cur.committed ? `🪰 The fly commits to <b>${pl.short}</b> (${pl.walk_min} min walk, MN9 at ${pk.read.mn9.toFixed(0)} Hz).`
                          : `🪰 The fly commits to <b>nothing</b>: every lot tastes too bitter or looms. Least bad: ${pl.short}.`;
    if (st.lesion) h += ` <span style="color:${C.red}">Giant Fibre inputs cut: it cannot escape.</span>`;
    if (st.truth) h += ` Truth: ${pl.short} has ${pk.trueFree} free.`;
    $("flyHeadline").innerHTML = h;
    const bar = (v, mx, c) => `<div class="bar"><i style="width:${Math.min(100, (100 * v) / mx)}%;background:${c}"></i></div>`;
    $("flyLots").innerHTML = cur.cand.slice().sort((a, b) => lots[a].walk_min - lots[b].walk_min).map((i) => {
      const x = cur.lots[i], v = x.verdict.split(" ")[0];
      return `<div class="fl ${i === st.flySel ? "sel" : ""} ${i === cur.pick && cur.committed ? "pick" : ""}" data-i="${i}">
        <div class="nm">${i === cur.pick && cur.committed ? "🪰 " : ""}${lots[i].short}<small>${lots[i].walk_min} min walk · ~${Math.round(x.free)} free${lots[i].price_hr ? " · $" + lots[i].price_hr + "/h" : ""}</small></div>
        <div class="tb" title="sugar ${x.hz[0].toFixed(0)} Hz · bitter ${x.hz[1].toFixed(0)} Hz · looming ${x.hz[2].toFixed(0)} Hz">
          <span>🍬</span>${bar(x.hz[0], PF.SENSE.SUGAR_MAX_HZ, C.orange)}<span>☕</span>${bar(x.hz[1], PF.SENSE.BITTER_MAX_HZ, C.purple)}<span>⚠</span>${bar(x.hz[2], PF.SENSE.LOOM_MAX_HZ, C.red)}</div>
        <div class="chip ${v}">${x.verdict === "COMMIT" ? "COMMIT" : x.verdict === "DIVERT" ? "DIVERT" : "BACK OFF"}</div></div>`;
    }).join("");
    const s = cur.lots[st.flySel], gz = (name, sub, v, mx, c) => `<div class="gz"><span><b>${name}</b> <small>${sub}</small></span>${bar(v, mx, c)}<span class="hz">${v.toFixed(0)} Hz</span></div>`;
    const bp = s.t.bitter_parts;
    $("gauges").innerHTML = `<div class="gt">Fly brain reading <b>${lots[st.flySel].short}</b>: sugar ${s.hz[0].toFixed(0)} Hz (chance of a spot × short walk), ` +
      `bitter ${s.hz[1].toFixed(0)} Hz (uncertainty ${(100 * bp.uncertainty).toFixed(0)}%${bp.permit ? ", no permit" : ""}${bp.price ? ", price" : ""}), looming ${s.hz[2].toFixed(0)} Hz (filling fast / full)</div>` +
      gz("MN9", "eat → commit", s.read.mn9, 105, C.green) + gz("MDN", "walk back → back off", s.read.mdn, 30, C.yellow) + gz("Giant Fibre", "escape → divert", s.read.giant_fibre, 270, C.red);
    st.rasterScen = s.verdict === "COMMIT" ? 0 : s.verdict === "DIVERT" ? 2 : 1;
    const Dc = D.results.decision, col = { fly: C.orange, greedy: C.blue, nearest: C.gray, oracle: C.green }, nm = { fly: "Fly brain", greedy: "Same tastes, no neurons", nearest: "Nearest lot", oracle: "Perfect knowledge" };
    lineChart($("chartDecision"), { h: 165, zone: [20, 30], yfmt: (v) => v.toFixed(1),
      series: ["nearest", "greedy", "fly", "oracle"].map((k) => ({ name: nm[k], x: Dc.pcts, y: Dc.policies[k].minutes, color: col[k], w: k === "fly" ? 3.2 : 1.8, dash: k === "oracle" ? "4 4" : null })) });
    const j = Dc.pcts.indexOf(25), f = Dc.policies.fly, g = Dc.policies.greedy;
    $("decisionNote").innerHTML = `${Dc.n_decisions_per_point} simulated arrivals per point; minutes = walk, plus ${Dc.full_penalty_min} if the chosen lot was full. ` +
      `The fly finds a free spot ${pct1(f.success[0])} of the time with no sensors, ${pct1(f.success[j])} at 25%, ${pct1(f.success[f.success.length - 1])} at 100%. ` +
      `A plain score on the same tastes does ${g.minutes[j] < f.minutes[j] ? "better" : "worse"} (${g.minutes[j].toFixed(2)} vs ${f.minutes[j].toFixed(2)} min at 25%): the fly is a fixed filter, not an optimizer.`;
  }

  function staticPanels() {
    const p = D.surface.provenance, sa = D.sanity;
    $("prov").innerHTML = `<p>Every verdict is interpolated from <b>${p.n_runs.toLocaleString()}</b> spiking simulations of the real connectome: ` +
      `<b>${p.n_neurons.toLocaleString()}</b> neurons, <b>${p.n_connections.toLocaleString()}</b> connections (${p.dataset}; file ${p.wiring_file}), ` +
      `${p.ms_per_run} ms per run from rest, ${p.seeds.length} seeds per grid point, run ${p.run_date.slice(0, 16).replace("T", " ")}. ` +
      `Inputs: ${p.group_sizes.sugar} sugar, ${p.group_sizes.bitter} bitter, ${p.group_sizes.looming} looming neurons. Lesion: ${p.lesion}.</p>` +
      (sa ? `<table><tr><th>Sanity check (handbook)</th><th>MN9</th><th>GF</th><th>MDN</th><th></th></tr>` +
        sa.checks.map((c) => `<tr><td>${c.check}<br><small>expect: ${c.expected}</small></td><td>${c.mn9_hz}</td><td>${c.giant_fibre_hz}</td><td>${c.mdn_hz}</td><td class="ok">${c.pass ? "pass" : "FAIL"}</td></tr>`).join("") + "</table>" : "");
    $("foot").innerHTML = `<b>Honest numbers.</b> Lots and space counts: official NCSU Transportation GIS. Stall positions: estimated. Occupancy: <b>simulated</b> ` +
      `(no Park Shark sensor is installed here yet). Fly verdicts: real FlyWire connectome simulations. Birmingham: real 2016 data.`;
  }

  // -------------------------------------------------------------- raster
  const GCOL = { sugar: C.orange, bitter: C.purple, looming: C.red, mn9: C.green, giant_fibre: "#ff7b7b", mdn: C.yellow };
  function rasterLoop(ts) {
    requestAnimationFrame(rasterLoop);
    if (st.tab !== "fly" || !D.raster) return;
    const cv = $("raster"), g = cv.getContext("2d"), R = D.raster, sc = R.scenarios[st.rasterScen || 0];
    const W = cv.width, H = cv.height, lm = 118, n = R.rows[R.rows.length - 1].to, t0 = ((ts / 1000) % 3.2) / 2.6 * R.ms;
    g.clearRect(0, 0, W, H);
    // rows: outputs get tall lanes so single neurons are visible
    const lanes = []; let y = 6;
    R.rows.forEach((r) => { const big = ["mn9", "giant_fibre", "mdn"].includes(r.group), h = big ? 22 : r.group.startsWith("inter") ? 78 : 26; lanes.push({ r, y, h, per: h / (r.to - r.from) }); y += h + 4; });
    g.font = "17px Barlow, sans-serif"; g.textBaseline = "middle";
    const nice = { sugar: "sugar taste", bitter: "bitter taste", looming: "looming vision", mn9: "MN9 · eat", giant_fibre: "Giant Fibre", mdn: "MDN · back" };
    lanes.forEach((l) => { g.fillStyle = GCOL[l.r.group] || "#7f93b5"; g.fillText(nice[l.r.group] || "other neurons", 4, l.y + l.h / 2); g.fillStyle = "rgba(255,255,255,.04)"; g.fillRect(lm, l.y, W - lm - 4, l.h); });
    const laneOf = (j) => lanes.find((l) => j >= l.r.from && j < l.r.to);
    for (let i = 0; i < sc.t.length; i++) {
      const t = sc.t[i]; if (t > t0) continue;
      const l = laneOf(sc.n[i]), x = lm + (t / R.ms) * (W - lm - 6), yy = l.y + (sc.n[i] - l.r.from) * l.per;
      g.fillStyle = GCOL[l.r.group] || "#7f93b5"; g.globalAlpha = t0 - t < 25 ? 1 : 0.55;
      g.fillRect(x, yy, 2.2, Math.max(2, l.per - 0.5));
    }
    g.globalAlpha = 1;
    if (t0 <= R.ms) { g.fillStyle = "rgba(255,255,255,.5)"; g.fillRect(lm + (t0 / R.ms) * (W - lm - 6), 4, 1.5, H - 8); }
    $("rasterLbl").textContent = `recorded run: "${sc.name}" · ${sc.neurons_active.toLocaleString()} neurons active in ${R.ms} ms`;
  }

  // ------------------------------------------------------------ controls
  function toggleWhole(i) { st.whole.has(i) ? st.whole.delete(i) : st.whole.add(i); update(); }
  function setTab(t) {
    st.tab = t;
    document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === t));
    document.querySelectorAll(".tab").forEach((e) => e.classList.toggle("on", e.id === "tab-" + t));
  }
  function syncInputs() {
    $("pct").value = st.pct; $("strategy").value = st.strategy; $("time").value = st.ti; $("day").value = st.day; $("truth").checked = st.truth;
    $("spillOn").checked = st.spill; $("lesion").checked = st.lesion; $("persona").value = st.persona; $("metric").value = st.metric;
  }
  function bind() {
    $("time").max = T - 1;
    $("pct").oninput = (e) => { st.pct = +e.target.value; update(); };
    $("strategy").onchange = (e) => { st.strategy = e.target.value; update(); };
    $("reshuffle").onclick = () => { st.shuffle++; update(); };
    $("time").oninput = (e) => { st.ti = +e.target.value; update(); };
    $("day").onchange = (e) => { st.day = +e.target.value; update(); };
    $("truth").onchange = (e) => { st.truth = e.target.checked; update(); };
    $("metric").onchange = (e) => { st.metric = e.target.value; render(); };
    $("spillOn").onchange = (e) => { st.spill = e.target.checked; update(); };
    $("lesion").onchange = (e) => { st.lesion = e.target.checked; update(); };
    $("persona").onchange = (e) => { st.persona = e.target.value; st.flySel = null; update(); };
    $("clearWhole").onclick = () => { st.whole.clear(); update(); };
    $("play").onclick = () => {
      if (playTimer) { clearInterval(playTimer); playTimer = null; $("play").textContent = "▶"; return; }
      $("play").textContent = "❚❚";
      playTimer = setInterval(() => { st.ti = (st.ti + 1) % T; $("time").value = st.ti; update(); }, 140);
    };
    document.querySelectorAll(".tabs button").forEach((b) => (b.onclick = () => setTab(b.dataset.tab)));
    $("wholeList").onclick = (e) => { const b = e.target.closest("button"); if (b) toggleWhole(+b.dataset.i); };
    $("placeSeg").onclick = (e) => { const b = e.target.closest("button"); if (b) { st.strategy = b.dataset.s; syncInputs(); update(); } };
    $("flyLots").onclick = (e) => { const r = e.target.closest(".fl"); if (r) { st.flySel = +r.dataset.i; render(); } };
    $("lotTable").onclick = (e) => { const r = e.target.closest("tr[data-i]"); if (r) map.flyTo(lots[+r.dataset.i].center, 19, { duration: 0.6 }); };
    $("demoBtn").onclick = () => (st.demo < 0 ? startDemo() : endDemo());
    $("capNext").onclick = () => demoStep(1); $("capPrev").onclick = () => demoStep(-1); $("capExit").onclick = endDemo;
    document.addEventListener("keydown", (e) => {
      if (st.demo < 0) return;
      if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") { e.preventDefault(); demoStep(1); }
      else if (e.key === "ArrowLeft" || e.key === "PageUp") { e.preventDefault(); demoStep(-1); }
      else if (e.key === "Escape") endDemo();
    });
  }

  // ---------------------------------------------------------------- demo
  function beats() {
    const R = D.results, i25 = R.pcts.indexOf(25), a = R.density.spill[i25], P = R.placement, p25 = P.pcts.indexOf(25), B = D.bham;
    const pb = (s) => P.strategies[s][p25].model_brier[0], ld = R.lesion_demo, f = R.decision.policies.fly, j = R.decision.pcts.indexOf(25);
    const base = { whole: [], strategy: "scatter", lesion: false, truth: false, persona: "commuter", spill: true, day: 0, ti: 54, tab: "sense", metric: "map" };
    return [
      { ...base, pct: 0, text: "A fly never sees the whole world. It reads a few senses and acts. Park Shark sensors cost about $65 and see 10 to 15 spots, so no lot will ever be fully sensed. With zero sensors, all we have is the time of day." },
      { ...base, pct: 25, text: `Sense 25% of the spots (white rings). Everything else is inferred, with confidence. Brier error on the unsensed spots: ${a.model_brier[0].toFixed(3)} for our model vs ${a.naive_brier[0].toFixed(3)} for the naive guess.` },
      { ...base, pct: 100, truth: true, text: "Slide to 100% and you get the simulated truth. The curve shows what each extra sensor buys, before a single one is installed." },
      { ...base, pct: 0, whole: [2], tab: "spill", text: B ? `Spillover: sensors on one whole lot move its neighbors' estimates, less with distance. On real Birmingham data, sensing 25% of car parks cuts error on the hidden ones by ${B.gain_at_25.gain_pct.toFixed(0)}%.` : "Spillover: sensors on one whole lot move its neighbors' estimates, less with distance." },
      { ...base, pct: 25, strategy: "entrance", tab: "place", text: "Placement. Sensors bunched at the entrance mostly see spots that are always taken." },
      { ...base, pct: 25, strategy: "spread", tab: "place", text: `Spread the same sensors out and error drops ${Math.round(100 * (1 - pb("spread") / pb("entrance")))}% (${pb("spread").toFixed(3)} vs ${pb("entrance").toFixed(3)}). This is how Park Shark should install.` },
      { ...base, pct: 0, tab: "fly", text: "Now the fly decides. Each lot becomes tastes: sugar = a spot is likely and close; bitter = uncertainty, permit risk, price; looming = filling fast. A real 138,639-neuron connectome answers. With no sensors, uncertainty tastes bitter." },
      { ...base, pct: 40, tab: "fly", text: `Add sensors: the bitterness fades and MN9, the feeding neuron, fires. The fly commits. In simulation it finds a free spot ${pct1(f.success[0])} of the time blind and ${pct1(f.success[j])} at 25% sensed.` },
      ld ? { ...base, pct: ld.pct, day: ld.day, ti: ld.ti, tab: "fly", flySel: ld.lot, text: `${fmtTime(D.truth.start_min + ld.ti * D.truth.step_min)}: ${short(D.truth.lots[ld.lot])} is filling fast. That looms at the fly, its Giant Fibre fires, and it diverts.` } : null,
      ld ? { ...base, pct: ld.pct, day: ld.day, ti: ld.ti, tab: "fly", flySel: ld.lot, lesion: true, text: "Lesion lab: cut the Giant Fibre's inputs. No escape signal, so the fly heads for the lot that is about to fill." } : null,
      { ...base, pct: 25, tab: "sense", metric: "brier", text: "Honest limits: occupancy here is simulated; the spillover result is checked on real Birmingham data; the fly is a fixed filter and we show the baseline that beats it. Next: Park Shark's UNC and Durham pilots replace the simulator with real spots." },
    ].filter(Boolean);
  }
  let BEATS = [];
  function startDemo() { BEATS = beats(); st.demo = 0; $("caption").hidden = false; $("demoBtn").textContent = "■ Exit demo"; applyBeat(); }
  function endDemo() { st.demo = -1; $("caption").hidden = true; $("demoBtn").textContent = "▶ Demo"; }
  function demoStep(d) { st.demo = Math.max(0, Math.min(BEATS.length - 1, st.demo + d)); applyBeat(); }
  function applyBeat() {
    const b = BEATS[st.demo];
    Object.assign(st, { pct: b.pct, strategy: b.strategy, lesion: b.lesion, truth: b.truth, persona: b.persona, spill: b.spill, day: b.day, ti: b.ti, metric: b.metric });
    st.whole = new Set(b.whole); st.flySel = b.flySel ?? null;
    setTab(b.tab); syncInputs(); update();
    $("capText").textContent = b.text; $("capStep").textContent = `${st.demo + 1} / ${BEATS.length} · use → and ←`;
  }

  boot().catch((e) => { document.body.insertAdjacentHTML("beforeend", `<pre style="position:fixed;inset:auto 10px 10px 10px;background:#400;color:#fff;padding:10px;z-index:9999">Could not load data: ${e.message}\nRun: python3 -m http.server -d web 8000</pre>`); console.error(e); });
})();
