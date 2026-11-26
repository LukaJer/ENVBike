# EnvBike Development Summary (`HAL` Branch)

Running summary of implemented features, bug fixes, and architectural changes across `EnvBike` (root), `mda-server`, and `mda-publishers`.

---

## 1. Dashboard, Live Monitoring & Diagnostics (`mda-server`)
- **Live Instrument Dashboard & `devices.json` Integration**:
  - Replaced legacy campaign listing with a tabbed dashboard ([campaigns.html](file:///home/luka/Code/EnvBike/mda-server/templates/campaigns.html)) featuring **Campaigns**, **Live**, **Diagnostics**, and **Settings** tabs.
  - Added `/api/live` (`live_cache` + DB fallback) with per-instrument status badges (`OK`, `Warming up`, `Reference zero`, `ERROR`, `Disconnected`) and automatic hiding of stale values when status is not `OK`.
- **Diagnostics Tab**:
  - Added live log viewer (`/api/logs`) with source filtering, error-only toggle, and DB size indicator.
  - Added embedded web shell (`/api/terminal`), enabled on LAN via `MDA_ENABLE_TERMINAL=1` in [mdau_server.service](file:///home/luka/Code/EnvBike/mda-server/mdau_server.service).
- **Date & Mobile UI Polish**:
  - Standardized date notation to `YYYY.MM.DD` across campaign cards, edit forms, and windrose overlays.
  - Improved mobile campaign card layout and start→end arrow alignment.

## 2. Map Visualization, Offline Maps & GPS Quality (`mda-server`)
- **Map UX & Auto-Fit / Focus**:
  - Live campaigns default to **Focus** mode enabled; finished campaigns auto-fit (`map.fitBounds`) to the recorded track.
  - Live campaigns expose all configured species pills without requiring a page reload as slower sensors come online.
- **Offline `.mbtiles` Vector & Raster Map Support**:
  - Added `mda-server/static/maps/` folder with Munich map (`planet_11.337_48.047_b531ac7e.mbtiles`, `20.88 MB`, `z0–z14` PBF).
  - Added `GET /api/offline-maps` and `GET /tiles/mbtiles/<map>/<z>/<x>/<y>.<ext>` in [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py).
  - Integrated `maplibre-gl@4.7.1` + `@maplibre/maplibre-gl-leaflet` ([mbtiles-style.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/mbtiles-style.ts), [index.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/index.ts)) for offline **Color (`MBTiles`)** and **Grayscale (`MBTilesG`)** layers with smooth overzooming up to `z19`.
- **Settings Tab & Track Contrast**:
  - Added `settings.json` persistence (`/api/settings`) for default map layer, active `.mbtiles` selection with size/tile-count/editable descriptions, and track color palettes (`default`, `plasma`, `turbo`).
  - Added a dark track outline (`drop-shadow` in [livemap.css](file:///home/luka/Code/EnvBike/mda-server/static/src/livemap.css)) so yellow/amber concentration segments stay legible over street lines.
- **GPS Glitch Filtering**:
  - Added `GPS._is_plausible_fix()` ([gps.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/gps.py)) and `Interpolator.filter_plausible_locations()` ([interplator.py](file:///home/luka/Code/EnvBike/mda-server/util/interplator.py)) to reject `(0.0, 0.0)`, `NaN`/out-of-bounds, and `>100 m/s` jump spikes (with 3-fix recovery) for both live recording and historical campaign playback.

## 3. Sensor Publishers & Hardware Support (`mda-publishers`)
- **Envea + Grimm + UMB + Picarro Support**:
  - Added `devices.json`-driven startup ([main.py](file:///home/luka/Code/EnvBike/mda-publishers/main.py)) with `/dev/serial/by-id/...` paths, `EnveaAnalyzer` Modbus/TCP (`AC32e`, `O342e`, `CO12e`) warmup/reference-zero status reporting, `Grimm11D` PM parsing, and `UMB` wind sensor improvements.
  - Added `GPS` → system clock sync (`sudo -n date -s`) and `time.monotonic()` extrapolation in `gps_time.py`.

## 4. Code Review & Critical/High Bug Fixes
- Conducted full multi-agent code review documented in [bugs.md](file:///home/luka/Code/EnvBike/bugs.md) and resolved **all 7 Critical and 18 High** bugs:
  - **Backend**: Gated `/api/terminal`, disabled default `debug=True`, switched Gunicorn to `--workers 1 --threads 8` + SQLite `WAL`/`busy_timeout=5000`, uncapped `LocationMeasurement` queries during interpolation, fixed final wind-averaging bucket & circular heading mean, fixed `campaign_stats` / `plot_baselines` crashes on live/empty campaigns, and normalized timezone-aware ISO datetimes.
  - **Frontend**: Prevented hidden `GasMeasurementPlotter` instances from mutating the shared marker, fixed dropped first measurements & sub-second batch truncation, fixed screenshot mode on live campaigns / failed `/wind-mean`, and fixed MapLibre UMD bundling in Webpack.
  - **Publishers**: Stripped UTC `tzinfo` from local NMEA timestamps, eliminated 60s–6min blocking in `Grimm11D.read_measurements()`, hardened `LI7810Publisher` MQTT JSON parsing/reconnect/shutdown, added `GasPublisher` TCP reconnect + `\r\n` framing fix, and made all `connect()` loops `stop_event`-interruptible with `SIGTERM` handling in `publish.py`.
  - **Root Scripts**: Fixed `data_downloader.py` / `data_downloader_V2.py` crashes, fixed `gps_sync_time_utc.sh` UTC flag (`date -u -s`) + serial reading, and fixed `mmu_downloader_core.py` whole-second chunk alignment, `±15s` GPS buffer, and `"H2O-LI"` fallback.

## 5. Performance Optimizations & Real-Time Push Updates (SSE)
- **Frontend (`mda-server/static/`)**:
  - Switched map species polling to **lazy / active-only** creation & polling ([index.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/index.ts)), pausing hidden plotters and only fetching `getBaseConcentration()` when a baseline species is selected.
  - Replaced per-segment `L.geoJson()` SVG layers + CSS `drop-shadow` with Leaflet's **Canvas renderer** (`L.canvas()`), lightweight `L.polyline` + dark casing polyline, and lazy click popups ([gas-measurement-plotter.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/gas-measurement-plotter.ts), [livemap.css](file:///home/luka/Code/EnvBike/mda-server/static/src/livemap.css)).
  - Switched Webpack ([webpack.config.js](file:///home/luka/Code/EnvBike/mda-server/static/webpack.config.js)) to **`mode: 'production'`**, shrinking `bundle.js` from `1.59 MiB` to `1020 KiB`.
- **Backend (`mda-server/app.py`)**:
  - Tuned SQLite PRAGMAs (`synchronous=NORMAL`, `cache_size=-16000`, `temp_store=MEMORY` alongside `WAL` and `busy_timeout=5000`).
  - Added thread-local read-only `.mbtiles` connection caching (`_get_mbtiles_conn`) keyed by `(path, mtime_ns)`.
  - Added `ix_log_datetime` and `ix_log_sensor_datetime` indexes on the `log` table.
  - Added batch JSON list ingestion to `POST /measurement/<type>` (single SQLite transaction per batch, backwards-compatible with single-dict payloads).
  - Refactored `/campaign/<id>/download` to stream CSV and JSON via `stream_with_context` + `.yield_per(500)` and skip `WindMeasurement` queries for CSV exports.
  - Added **Server-Sent Events (`GET /api/live/stream`)** backed by `threading.Condition` + `live_cache_version` (coalescing bursts, falling back to 2s `age_seconds` heartbeats) and wired [campaigns.html](file:///home/luka/Code/EnvBike/mda-server/templates/campaigns.html) via `EventSource` with automatic polling fallback.
- **Publishers (`mda-publishers/publishers/`)**:
  - Added `requests.Session()` HTTP Keep-Alive in [base_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/base_publisher.py) (closed cleanly on shutdown) and thread-local `requests.Session()` in [logger.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/logger.py).
  - Added `_try_post_measurements_batch()` in `BasePublisher` and updated `EnveaPublisher`, `GrimmPublisher`, `GasPublisher`, and `LI7810Publisher` to send 1 batch `POST` per cycle.
- **Setup & Packaging**:
  - Added executable [install.sh](file:///home/luka/Code/EnvBike/install.sh) to bootstrap system dependencies (`apt-get`), submodules, both Python virtual environments, required runtime directories, and the Webpack frontend build cleanly on a new machine.
  - Replaced pinned `pip freeze` dumps in [mda-server/requirements.txt](file:///home/luka/Code/EnvBike/mda-server/requirements.txt) and [mda-publishers/requirements.txt](file:///home/luka/Code/EnvBike/mda-publishers/requirements.txt) with direct `>=` minimum dependencies, and added `"webpack": "^5.90.0"` to [package.json](file:///home/luka/Code/EnvBike/mda-server/static/package.json).
