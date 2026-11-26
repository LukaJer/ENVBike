# AGENTS.md

This file provides guidance for AI coding agents working in the `/home/luka/Code/EnvBike` workspace.

> **Living Documentation**: Keep [SUMMARY.md](file:///home/luka/Code/EnvBike/SUMMARY.md), [TODO.md](file:///home/luka/Code/EnvBike/TODO.md), and [bugs.md](file:///home/luka/Code/EnvBike/bugs.md) updated as features are implemented, bugs are found/fixed, or architecture changes.

## Workspace Layout

The root directory is a git repository (branch `HAL`) with two git submodules (`mda-server` and `mda-publishers`), shared configuration files, and utility scripts:

- **`mda-publishers/`** (git submodule): Python sensor publishers that read data from gas, particulate matter (PM), wind, and GPS sensors and `POST` measurements to the local server (`http://127.0.0.1:5000/measurement/...`).
- **`mda-server/`** (git submodule): Flask + SQLAlchemy backend and TypeScript/Leaflet/MapLibre frontend (`static/src/`) for storing, visualizing, and serving campaign measurements.
- **Root configuration & documentation**:
  - `devices.json`: Authoritative device configuration (enabled flags, serial `/dev/serial/by-id/...` paths, Modbus IPs/ports, polling intervals, stale/offline thresholds) shared by `mda-publishers/main.py` and `mda-server/app.py`.
  - `settings.json`: Server & map settings (`map.default_layer`, `map.color_palette`, `map.active_mbtiles`, `map.mbtiles_descriptions`, etc.) read/written by `/api/settings`.
  - `SUMMARY.md`: Running summary of implemented features, fixes, and current system state.
  - `TODO.md`: Prioritized backlog with completion status and effort estimates.
  - `bugs.md`: Code review findings and fix status across all components.
- **Root scripts**:
  - `mmu_downloader_core.py`: Shared chunked-download and GPS-matching library.
  - `mmu_auto_download.py`: Fire-and-forget campaign export script (expects `<campaign_id> <start_iso> <end_iso>`).
  - `data_downloader_v3.py`: Manual backup downloader wrapping `mmu_downloader_core.py`.
  - `data_downloader.py`, `data_downloader_V2.py`: Legacy single-window / offset downloaders.
  - `gps_sync_time_utc.sh`: Reads `$GNRMC`/`$GPRMC` from the u-blox `/dev/serial/by-id/...` device (fallback `/dev/ttyACM0`) and sets system UTC time via `sudo date -u -s`.
  - `install.sh`: Idempotent setup script for new PCs/Raspberry Pis (system packages, submodules, both Python venvs, directories, and Webpack frontend build).

## Architecture & Data Flow

1. **Time Synchronization & GPS Glitch Filtering**:
   - Publishers rely on `mda-publishers/publishers/gps_time.py` (`gps_time`), initialized by `GpsPublisher` from NMEA `$GNRMC` sentences (`LocationMeasurementMessage.create_from_NMEA_RMC` outputs naive local `datetime`) and extrapolated via `time.monotonic()`.
   - `EnveaPublisher` and `GrimmPublisher` block on `gps_time.wait_for_gps_initialization()` during `start_up()`.
   - `GPS._is_plausible_fix()` (`mda-publishers/sensors/gps.py`) rejects `NaN`/out-of-bounds, `(0.0, 0.0)`, and `>100 m/s` jump spikes (recovering after 3 consistent fixes).
   - `Interpolator.filter_plausible_locations()` (`mda-server/util/interplator.py`) applies the same sanity filter when serving historical campaign data.
2. **Sensor Ingestion (`mda-publishers/`)**:
   - **Device-config driven (`main.py` / `publishers/main.py`)**: Reads `devices.json` and instantiates enabled publishers: `AC32ePublisher` (`NO`, `NO2`, `NOx`), `O342ePublisher` (`O3`), `CO12ePublisher` (`CO`) over Modbus/TCP (port `502`, `pymodbus`), `GrimmPublisher` (`Grimm11D` over serial for `PM10`, `PM4`, `PM2.5`, `PM1`), `GpsPublisher`, `WindPublisher` (`UMB`), and optional `GasPublisher` (Picarro CRDS).
   - **Legacy / `config.ini`-driven (`publish.py`)**: Reads `config.ini` and starts `GasPublisher`, `LI7810Publisher` (MQTT `:1883`), `WindPublisher`, and `GpsPublisher`.
   - All publishers inherit from `BasePublisher` (`threading.Thread`) and `POST` JSON payloads from `messages/` to `http://127.0.0.1:5000/measurement/{gas,wind,location,log}`.
3. **Server & Frontend (`mda-server/`)**:
   - Models live in `mda-server/models/` (`Campaign`, gas/wind/location/log models, `db` in `base_model.py`). SQLite DB (`mda-server/instance/measurements.db`) runs with `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000`.
   - `mdau_server.service` runs Gunicorn `--workers 1 --threads 8` with `MDA_ENABLE_TERMINAL=1` so in-process `live_cache` and recording state are shared across requests.
   - Dashboard UI (`templates/campaigns.html`) includes **Campaigns**, **Live**, **Diagnostics** (`/api/logs`, `/api/terminal`), and **Settings** (`/api/settings`, `/api/offline-maps`).
   - Map UI (`templates/index.html`, `static/src/`) uses Leaflet (`leaflet`, `leaflet-rotatedmarker`) and `maplibre-gl` (`4.7.1`) + `@maplibre/maplibre-gl-leaflet` to render online `OSM` tiles, optional PNG caches (`Local`/`LocalG`), and offline `.mbtiles` vector/raster maps (`MBTiles`/`MBTilesG` served from `static/maps/` via `/tiles/mbtiles/...`).
   - Supported species, ranges, units, and track color palettes (`default`, `plasma`, `turbo`) live in `mda-server/static/src/index.ts`, `gas-measurement-plotter.ts`, and `templates/index.html`.
4. **Data Export (`mmu_downloader_core.py`)**:
   - Splits `[start, end]` into 15-minute whole-second-aligned chunks (`INITIAL_CHUNK`) and recursively halves chunks hitting `ROW_CAP = 5000` (down to `MIN_CHUNK = 10s`), deduplicating by `(datetime, type)`.
   - Fetches gas and location rows separately (`/measurement/gas`, `/measurement/location` with `±15s` boundary padding) and merges client-side within `MAX_MATCH_SECONDS = 15`.

## Common Commands

- **Bootstrap on a new PC / Raspberry Pi**:
  ```bash
  ./install.sh                  # Full install (apt, venvs, npm build)
  ./install.sh --no-apt         # Skip apt-get; use existing system Python/Node
  ```
- **Frontend type-check & build (`mda-server`)**:
  ```bash
  cd mda-server/static && ./node_modules/.bin/tsc --noEmit && npm run build
  ```
- **Run publishers (`mda-publishers`)**:
  ```bash
  cd mda-publishers && venv/bin/python main.py      # devices.json-driven (Envea + Grimm + GPS + Wind)
  cd mda-publishers && venv/bin/python publish.py   # Legacy config.ini-driven (Picarro / LI-7810 / GPS / Wind)
  ```
- **Manual data download**:
  ```bash
  python3 mmu_downloader_core.py <start_iso> <end_iso> <out_dir> [ip] [port]
  python3 data_downloader_v3.py
  ```
- **Git status checks**:
  Check root repo and submodules before committing:
  ```bash
  git status && git -C mda-server status && git -C mda-publishers status
  ```

## Conventions & Notes

- **Adding a new gas/PM species**:
  1. Ensure the sensor driver emits `GasMeasurement` with the exact `type` string and `unit`.
  2. Add the species to `SPECIES` in `mda-server/static/src/index.ts` and `all_species` in `mda-server/templates/index.html`, then rebuild `bundle.js` (`npm run build`).
  3. Update the fallback list in `mmu_downloader_core.py:get_species_list` if `/gas-types` is unavailable.
- **Offline `.mbtiles` maps**: Drop `.mbtiles` files into `mda-server/static/maps/` (gitignored) and select the active map + `MBTiles`/`MBTilesG` layer in the **Settings** tab. Note `maplibre-gl` must stay on `4.7.x` (UMD/CJS) for `@maplibre/maplibre-gl-leaflet` compatibility in Webpack.
- **Modbus drivers (`EnveaAnalyzer`)**: `AC32e`, `CO12e`, and `O342e` subclass `EnveaAnalyzer` (`mda-publishers/sensors/envea_analyzer.py`) and configure `MODBUS_FIELDS` with `MODBUS_WORD_SWAP = True`. `pymodbus` is imported lazily inside `EnveaAnalyzer.connect()`.
- **Keep submodule commits scoped**: Commit inside `mda-server/` and `mda-publishers/` first, then update the submodule pointers in the root `EnvBike` repository.
