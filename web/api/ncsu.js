// Public, read-only proxy for official lot geometry/counts. No occupancy feed exists here.
const SOURCE = 'https://gismaps.oit.ncsu.edu/arcgis/rest/services/Transportation/Transportation_OnlineCampusMap/MapServer/1/query?where=1%3D1&outFields=*&outSR=4326&f=geojson';
module.exports = async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).json({error:'Use GET'});
  try {
    const response = await fetch(SOURCE, {signal:AbortSignal.timeout(10000)});
    if (!response.ok) throw new Error('Official endpoint returned ' + response.status);
    const data = await response.json();
    if (!Array.isArray(data.features)) throw new Error('Official endpoint did not return GeoJSON');
    res.setHeader('Cache-Control','public, s-maxage=600, stale-while-revalidate=3600');
    return res.status(200).json({source:SOURCE,label:'OFFICIAL NCSU: lot geometry and capacity; no live occupancy',fetched_at:new Date().toISOString(),...data});
  } catch (error) {
    return res.status(502).json({error:'Official NCSU endpoint unavailable. Cached map remains usable.',detail:error.message});
  }
};
