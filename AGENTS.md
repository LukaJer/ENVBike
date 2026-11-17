# AGENTS.md

This file provides guidance for AI coding agents working in the `/home/luka/Code/EnvBike` workspace.

## Workspace Layout

The root directory is **not** a git repository; it contains standalone utility scripts and two independent git subrepositories:

- **`mda-publishers/`** (git repo): Python sensor publishers that read data from gas, particulate matter (PM), wind, and GPS sensors and `POST` measurements to the local server (`http://127.0.0.1:5000/measurement/...`).
- **`mda-server/`** (git repo): Flask + SQLAlchemy backend and TypeScript/Leaflet frontend (`static/src/`) for storing, visualizing, and serving campaign measurements.
- **Root scripts**:
  - `mmu_downloader_core.py`: Shared chunked-download and GPS-matching library.
  - `mmu_auto_download.py`: Fire-and-forget campaign export script (expects `<campaign_id> <start_iso> <end_iso>`).
  - `data_downloader_v3.py`: Manual backup downloader wrapping `mmu_downloader_core.py`.
  - `data_downloader.py`, `data_downloader_V2.py`: Legacy single-window / offset downloaders.
  - `gps_sync_time_utc.sh`: Reads `$GNRMC` from `/dev/ttyACM0` and sets system UTC time via `sudo date -s`.

> **Important Workspace State (`mda-server`)**: At the time of writing, `mda-server` has unstaged deletions in its working tree for several tracked root files (`app.py`, `requirements.txt`, `config.ini`, `mdau_server.service`, `tests/`, etc.), alongside unstaged edits in `static/src/`, `templates/index.html`, and `util/api_helper.py`. Do not assume `app.py` or `tests/` exist on disk without checking first; inspect `git -C mda-server status` before modifying `mda-server`.

## Architecture & Data Flow

1. **Time Synchronization**: Publishers rely on `publishers/gps_time.py` (`gps_time`), which is initialized by `GpsPublisher` from NMEA sentences. `EnveaPublisher` and `GrimmPublisher` block on `gps_time.wait_for_gps_initialization()` during `start_up()`.
2. **Sensor Ingestion (`mda-publishers/`)**:
   - **Legacy / Config-driven (`publish.py`)**: Reads `config.ini` and starts `GasPublisher` (Picarro CRDS over TCP `:51020`), `LI7810Publisher` (LI-COR over MQTT `:1883`), `WindPublisher` (serial), and `GpsPublisher` (serial).
   - **Envea + Grimm setup (`main.py` / `publishers/main.py`)**: Instantiates `AC32ePublisher` (`NO`, `NO2`, `NOx`), `O342ePublisher` (`O3`), `CO12ePublisher` (`CO`) over Modbus/TCP (port `502`, `pymodbus`), `GrimmPublisher` (`Grimm11D` over serial RS-232/USB for `PM10`, `PM4`, `PM2.5`, `PM1`), plus `GpsPublisher` and `WindPublisher`.
   - All publishers inherit from `BasePublisher` (`threading.Thread`) and `POST` JSON payloads from `messages/` to `http://127.0.0.1:5000/measurement/{gas,wind,location}`.
3. **Server & Frontend (`mda-server/`)**:
   - Models live in `mda-server/models/` (`Campaign`, gas/wind/location measurement models, `db` in `base_model.py`). SQLite DB is stored in `mda-server/instance/measurements.db`.
   - Frontend source is TypeScript in `mda-server/static/src/` using `leaflet` and `leaflet-rotatedmarker`, compiled with Webpack to `mda-server/static/dist/bundle.js`.
   - Supported species and their display ranges/units are configured in `mda-server/static/src/index.ts` (`SPECIES`) and `mda-server/templates/index.html` (`#gas-selector`).
4. **Data Export (`mmu_downloader_core.py`)**:
   - The server caps responses at ~5000 rows (`ROW_CAP = 5000`) and does not reliably honor `offset` on interpolated reads.
   - `mmu_downloader_core.py` works around this by splitting `[start, end]` into 15-minute chunks (`INITIAL_CHUNK`) and recursively halving any chunk that returns `ROW_CAP` rows (down to `MIN_CHUNK = 10s`), then deduplicating by `(datetime, type)`.
   - Gas and location rows are fetched separately (`/measurement/gas`, `/measurement/location`) and merged client-side by nearest timestamp within `MAX_MATCH_SECONDS = 15`.

## Common Commands

- **Frontend build (`mda-server`)**:
  ```bash
  cd mda-server/static && npm run build
  ```
  (Runs `webpack --config webpack.config.js` using `tsconfig.json`.)
- **Run publishers (`mda-publishers`)**:
  ```bash
  cd mda-publishers && python3 main.py      # Envea (Modbus/TCP) + Grimm + GPS + Wind
  cd mda-publishers && python3 publish.py   # Legacy config.ini-driven (Picarro / LI-7810 / GPS / Wind)
  ```
- **Manual data download**:
  ```bash
  python3 mmu_downloader_core.py <start_iso> <end_iso> <out_dir> [ip] [port]
  # Or edit START_TIME / END_TIME in data_downloader_v3.py and run:
  python3 data_downloader_v3.py
  ```
- **Git status checks**:
  Check subrepos individually since the root is not a git repo:
  ```bash
  git -C mda-server status
  git -C mda-publishers status
  ```

## Conventions & Notes

- **Adding a new gas/PM species**:
  1. Ensure the sensor driver emits `GasMeasurement` with the exact `type` string and `unit`.
  2. Add the species to `SPECIES` in `mda-server/static/src/index.ts` and `<option>` in `mda-server/templates/index.html`, then rebuild `bundle.js` (`npm run build`).
  3. Update the fallback list in `mmu_downloader_core.py:get_species_list` if `/gas-types` is unavailable.
- **Modbus drivers (`EnveaAnalyzer`)**: `AC32e`, `CO12e`, and `O342e` subclass `EnveaAnalyzer` (`mda-publishers/sensors/envea_analyzer.py`) and configure `MODBUS_FIELDS` with `MODBUS_WORD_SWAP = True`. Note that `pymodbus` is imported lazily inside `EnveaAnalyzer.connect()` when `mode == "modbus"`.
- **Keep `mda-publishers` and `mda-server` changes scoped**: Always check which subrepository you are editing and verify `git -C <subrepo> status` after changes.
