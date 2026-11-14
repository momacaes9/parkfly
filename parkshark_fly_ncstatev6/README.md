# Park Shark x Fly Brain - NC State (Hack Day, Nov 14 2026)

A hungry fly (the real 139k-neuron FlyWire connectome) hunting the sweetest
parking spot at NC State. Park Shark's estimator turns each lot into tastes;
the fly brain decides eat / back off / flee.

## Run
1. `python3 build_ncstate.py`  -> web/data.json + senses.json
2. Open web/index.html (or `python3 -m http.server` inside web/)
3. In Colab: run the organizers' fly_brain_starter.ipynb, then our
   fly_decides_parking.ipynb cells. Upload senses.json, download decisions.json,
   drop it into web/ and refresh: the fly's verdicts appear on every lot.

## Real data
Save this as ncstate_parking_raw.geojson next to build_ncstate.py and rebuild:
https://gismaps.oit.ncsu.edu/arcgis/rest/services/Transportation/Transportation_OnlineCampusMap/MapServer/1/query?where=1%3D1&outFields=*&outSR=4326&f=geojson
(Official NCSU lots: name, SPACES, zone, deck/lot, per-permit space counts, HC, EV.)
Until then a SEED set is used and flagged everywhere.

## Honesty
No sensors exist yet: occupancy is an assumed hour-template estimate with a band,
permit rules are simplified, and the fly is a fixed filter judged against a dumb
baseline. Park Shark floor sensors later replace the estimate; senses sharpen.
