# EnvBike (Mobile Data Acquisition Unit)

EnvBike is a mobile environmental monitoring system (Mobile Data Acquisition Unit / MDAU) designed to collect, store, visualize, and export geolocated air-quality and meteorological measurements from a bicycle or mobile platform (typically running on a Raspberry Pi).

## Repository Structure

```text
EnvBike/
├── mda-publishers/          # Sensor acquisition & HTTP publishers (git repo)
├── mda-server/              # Flask backend, SQLite storage & Leaflet web UI (git repo)
├── mmu_downloader_core.py   # Chunked data exporter with GPS timestamp matching
├── mmu_auto_download.py     # Automated per-campaign exporter triggered by server
├── data_downloader_v3.py    # Manual backup exporter using mmu_downloader_core.py
├── data_downloader.py       # Legacy single-request downloader
├── data_downloader_V2.py    # Legacy offset-based downloader
└── gps_sync_time_utc.sh     # Syncs system UTC clock from GPS NMEA ($GNRMC)
```

## Components

### 1. `mda-publishers/`
Python multi-threaded publisher service (`BasePublisher`) that reads from environmental sensors and `POST`s JSON measurements to `http://127.0.0.1:5000/measurement/{gas,wind,location}`.

- **Supported Sensors**:
  - **Envea Gas Analyzers** (Modbus/TCP or serial stream):
    - `AC32e`: `NO`, `NO2`, `NOx` (ppb)
    - `O342e`: `O3` (ppb)
    - `CO12e`: `CO` (ppm)
  - **Grimm 11-D** (`Grimm11D`, RS-232 over USB): `PM10`, `PM4`, `PM2.5`, `PM1` (µg/m³)
  - **Picarro CRDS** (TCP `:51020`): `CH4`, `CO2`, `H2O`
  - **LI-COR LI-7810** (MQTT `:1883`): `CH4-LI`, `CO2-LI`
  - **Wind & GPS**: Serial wind sensor and NMEA GPS receiver (also provides `gps_time` synchronization for other publishers).
- **Entry Points**:
  - `main.py` / `publishers/main.py`: Runs Envea (Modbus/TCP), Grimm 11-D, GPS, and Wind publishers.
  - `publish.py`: Config-driven runner using `config.ini` (Picarro, LI-7810, Wind, GPS).
- **Systemd & Deployment**: Includes `mdau_pub.service` and `sync.sh` for deploying to a Raspberry Pi (`mda@<ip>:/home/mda/repos/mda-publishers`).

### 2. `mda-server/`
Web server and live map interface for viewing real-time and historical campaign data.

- **Backend**: SQLAlchemy models (`mda-server/models/`) backed by SQLite (`mda-server/instance/measurements.db`) and request helpers (`mda-server/util/`).
- **Frontend**: TypeScript + Leaflet application (`mda-server/static/src/`) featuring:
  - Live and historical gas/PM trace plotting (`gas-measurement-plotter.ts`)
  - Wind vector and windrose visualization (`wind-measurement-plotter.ts`, `windrose.ts`)
  - Interactive species selector, time slider, numeric readout, and local/online OpenStreetMap tile layers (`osm_grayscale`, `osm`, online OSM).
- **Building the Frontend**:
  ```bash
  cd mda-server/static
  npm install
  npm run build   # outputs static/dist/bundle.js
  ```

### 3. Data Downloaders & Utilities
- **`mmu_downloader_core.py`**: Downloads all gas species reported by `/gas-types` along with `/measurement/location`, automatically subdividing time windows when the server's 5,000-row cap is reached, and attaches the nearest GPS position (within 15 seconds) to each gas measurement. Outputs one JSON file per species.
- **`mmu_auto_download.py`**: Launched automatically when a campaign end-time is set; uses a `/tmp/mmu_download_<campaign_id>.lock` lock file to prevent duplicate concurrent runs.
- **`data_downloader_v3.py`**: Manual backup script. Edit `START_TIME` and `END_TIME` in the file and run:
  ```bash
  python3 data_downloader_v3.py
  ```
- **`gps_sync_time_utc.sh`**: Waits for a valid `$GNRMC` fix on `/dev/ttyACM0` and sets the system UTC clock.
