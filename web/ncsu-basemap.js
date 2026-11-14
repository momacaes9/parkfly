/* Official NC State campus map as a Leaflet base layer.
   Source: NC State University GIS ArcGIS MapServer (public, no key).
   The services are dynamic (not tiled), so one image per service is requested
   for the current view and swapped in when it has loaded.
   Fires 'tileload' / 'tileerror' for the street base so the fallback chain can react. */
(() => {
  const ROOT = 'https://gismaps.oit.ncsu.edu/arcgis/rest/services/';
  const SERVICES = [
    { id: 'base', path: 'CampusBaseMap/CampusBaseMap', transparent: false },
    // Buildings_OnlineCampusMap already draws building names; the labels-only service would duplicate them.
    { id: 'buildings', path: 'Buildings/Buildings_OnlineCampusMap', transparent: true },
  ];
  // Official service extent (EPSG:3857); outside it the layer has nothing to draw.
  const EXTENT = L.latLngBounds([35.716, -78.756], [35.836, -78.629]);

  L.NcsuCampusLayer = L.Layer.extend({
    options: { attribution: 'Basemap: NC State University GIS', pad: 0.2, maxPixels: 2048 },
    initialize(options) { L.setOptions(this, options); this._live = {}; this._seq = 0; },
    onAdd(map) {
      this._map = map;
      map.on('moveend', this._update, this);
      this._update();
    },
    onRemove(map) {
      map.off('moveend', this._update, this);
      Object.values(this._live).forEach((o) => o && map.removeLayer(o));
      this._live = {}; this._seq++;
    },
    getAttribution() { return this.options.attribution; },
    _update() {
      const map = this._map;
      if (!map || !map._loaded) return;
      const size = map.getSize();
      if (!size.x || !size.y) return;
      const bounds = map.getBounds().pad(this.options.pad);
      if (!bounds.intersects(EXTENT)) return;
      const sw = L.CRS.EPSG3857.project(bounds.getSouthWest());
      const ne = L.CRS.EPSG3857.project(bounds.getNorthEast());
      const ratio = Math.min(2, window.devicePixelRatio || 1);
      const grow = 1 + 2 * this.options.pad;
      let w = Math.round(size.x * grow * ratio), h = Math.round(size.y * grow * ratio);
      const shrink = Math.min(1, this.options.maxPixels / Math.max(w, h));
      w = Math.round(w * shrink); h = Math.round(h * shrink);
      const query = `bbox=${sw.x},${sw.y},${ne.x},${ne.y}&bboxSR=3857&imageSR=3857&size=${w},${h}`
        + `&dpi=${Math.round(96 * ratio * shrink)}&format=png32&f=image`;
      const seq = ++this._seq;
      SERVICES.forEach((s, z) => {
        const url = `${ROOT}${s.path}/MapServer/export?${query}&transparent=${s.transparent}`;
        const next = L.imageOverlay(url, bounds, { pane: 'tilePane', zIndex: z + 1, opacity: 0, interactive: false });
        next.once('load', () => {
          if (seq !== this._seq || !this._map) { map.removeLayer(next); return; }
          const old = this._live[s.id];
          next.setOpacity(1);
          this._live[s.id] = next;
          if (old) map.removeLayer(old);
          if (s.id === 'base') this.fire('tileload');
        });
        next.once('error', () => {
          map.removeLayer(next);
          if (s.id === 'base' && seq === this._seq) this.fire('tileerror');
        });
        next.addTo(map);
      });
    },
  });
  L.ncsuCampusLayer = (options) => new L.NcsuCampusLayer(options);
})();
