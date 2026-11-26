# TODO

- [ ] **Device Configuration & Service Control from UI** *(Est. 2–3 hrs)*
  - Edit `devices.json` settings directly from the Settings tab (enable/disable devices, ports/IPs, intervals, stale/offline thresholds).
  - Add dedicated controls to restart the publisher and server processes from the UI *(web terminal already implemented in Diagnostics)*.

- [ ] **High Concentration Alerts & Peak/Hotspot Markers** *(Est. 3–4 hrs)*
  - Add threshold configuration in the Settings tab (per-species limit, enable/disable toggle, trigger duration / consecutive count).
  - Flash the instrument card/box (or whole UI) when an alert is active, and display the alert on the map view as well.
  - Show peak/hotspot and threshold-exceedance markers for the selected species on `/map/<id>` with a "Jump to Peak" button.

- [x] **Auto-Fit Map to Finished Campaign Route**
  - When viewing a finished campaign on `/map/<id>`, automatically fit the map bounds (`map.fitBounds(...)`) to the recorded route instead of centering on the default coordinates.

- [x] **Map Layer Caching Settings**
  - Added Settings tab with default map layer (`OSM`, `MBTiles`, `MBTilesG`, `Local`, `LocalG`) and track color palette (`default`, `plasma`, `turbo`).

- [x] **Offline Maps (Munich MBTiles Support)**
  - Added `static/maps/*.mbtiles` serving (`/tiles/mbtiles/...`, `/api/offline-maps`), `maplibre-gl-leaflet` vector/raster rendering (`MBTiles` / `MBTilesG`), Munich map (`planet_11.337_48.047_b531ac7e.mbtiles`), and Settings selector with size/description.

- [ ] **Campaign Start & Map Readiness Warnings** *(Est. 1–2 hrs)*
  - Show warnings on the map view and when starting a campaign if any enabled instruments or GPS are not ready yet (e.g., disconnected, warming up, reference zero, or no GPS fix).

- [x] **Real-Time Push Updates (SSE)**
  - Replaced `/api/live` polling in `campaigns.html` with Server-Sent Events (`EventSource` on `/api/live/stream` with automatic polling fallback) pushed immediately when `POST /measurement/<type>` or `/enable-measurements/<enable>` updates state.

- [ ] **RTC Battery & GPS Hardware Clock Sync** *(Est. 20–30 mins)*
  - Run `sudo -n hwclock -w` right after `sudo -n date -s` in `GpsPublisher._sync_system_time_once()` (`mda-publishers/publishers/gps_publisher.py`) so the RPi RTC hardware chip stays synced to GPS.
  - Optionally add a timeout/flag to `gps_time.wait_for_gps_initialization()` so `EnveaPublisher` and `GrimmPublisher` can start using RTC time indoors before a GPS fix arrives.

- [x] **Performance Improvements**
  - Lazy active-only species polling, Leaflet Canvas renderer + dark casing polylines + lazy popups, production Webpack build (`1020 KiB`), SQLite PRAGMA tuning + `log` indexes, thread-local `.mbtiles` connection cache, batch ingestion + `requests.Session` Keep-Alive, streaming exports, and SSE push updates.
