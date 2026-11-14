/* Finite fallback chain. All official polygons and estimated spots remain local. */
(() => {
  function init(map) {
    const cfg = window.PARKFLY_CONFIG || {};
    const label = L.control({ position: 'bottomleft' });
    label.onAdd = () => { const d = L.DomUtil.create('div', 'bmlabel'); d.textContent = 'basemap: loading'; return d; };
    label.addTo(map);
    const setLabel = text => label.getContainer().textContent = 'basemap: ' + text;
    map.attributionControl.addAttribution('lots: NCSU Transportation GIS');
    const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors', maxZoom: 21, maxNativeZoom: 19 });
    const carto = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap © CARTO', subdomains: 'abcd', maxZoom: 21, maxNativeZoom: 19 });
    const plain = L.layerGroup();
    const NCSU = 'NC State campus map (official)';
    const ncsu = L.ncsuCampusLayer ? L.ncsuCampusLayer() : null;
    const layers = { ...(ncsu ? { [NCSU]: ncsu } : {}), OpenStreetMap: osm, 'Carto light': carto, 'Offline NCSU polygons': plain };
    const ctl = L.control.layers(layers, null, { position: 'topright' }).addTo(map);
    let active = null, generation = 0, googleLayer = null, changing = false;
    function use(layer, name) {
      generation++; changing = true;
      Object.values(layers).forEach(l => { if (map.hasLayer(l)) map.removeLayer(l); });
      if (googleLayer && map.hasLayer(googleLayer)) map.removeLayer(googleLayer);
      active = layer; layer.addTo(map); setLabel(name); changing = false;
    }
    const choices = [...(ncsu ? [[ncsu, NCSU]] : []), [osm, 'OpenStreetMap'], [carto, 'Carto light'], [plain, 'Offline NCSU polygons']];
    function activate(index) {
      const [layer, name] = choices[index];
      use(layer, name);
      if (layer === plain) return;
      const gen = generation;
      let loaded = false, errors = 0;
      layer.once('tileload', () => { loaded = true; });
      const fallback = () => { if (active === layer && generation === gen && !loaded) activate(index + 1); };
      layer.on('tileerror', () => { if (++errors >= (layer === ncsu ? 1 : 4)) fallback(); });
      setTimeout(fallback, 5000);
    }
    map.on('baselayerchange', e => {
      if (changing) return;
      generation++; active = e.layer; setLabel(e.name);
      const index = choices.findIndex(c => c[0] === e.layer);
      if (index >= 0) activate(index);
    });
    activate(0);
    if (!cfg.GOOGLE_MAPS_KEY) return;
    let failed = false, ready = false;
    const fail = () => {
      if (failed) return;
      failed = true;
      if (googleLayer) { map.removeLayer(googleLayer); ctl.removeLayer(googleLayer); }
      activate(0);
    };
    window.gm_authFailure = fail;
    window.__pfGmReady = () => {
      if (failed) return;
      try {
        googleLayer = L.gridLayer.googleMutant({ type: 'roadmap', maxZoom: 21 });
        ctl.addBaseLayer(googleLayer, 'Google roadmap');
        use(googleLayer, 'Google roadmap'); ready = true;
      } catch { fail(); }
    };
    const script = document.createElement('script');
    script.src = 'https://maps.googleapis.com/maps/api/js?key=' + encodeURIComponent(cfg.GOOGLE_MAPS_KEY) + '&callback=__pfGmReady&loading=async';
    script.async = true; script.onerror = fail; document.head.append(script);
    setTimeout(() => { if (!ready) fail(); }, 8000);
  }
  window.PFBasemap = { init };
})();
