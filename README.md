# EnvBike (Mobile Data Acquisition Unit)

EnvBike is a mobile environmental monitoring system (Mobile Data Acquisition Unit / MDAU) designed to collect, store, visualize, and export geolocated air-quality and meteorological measurements from a bicycle or mobile platform (typically running on a Raspberry Pi).

## Repository Structure

```text
EnvBike/
├── devices.json             # Central device enable/disable, connection & interval config
├── mda-publishers/          # Sensor acquisition & HTTP publishers (git submodule)
├── mda-server/              # Flask backend, SQLite storage & Leaflet web UI (git submodule)
├── mmu_downloader_core.py   # Chunked data exporter with GPS timestamp matching
├── mmu_auto_download.py     # Automated per-campaign exporter
├── data_downloader_v3.py    # Manual backup exporter using mmu_downloader_core.py
├── data_downloader.py       # Legacy single-request downloader
├── data_downloader_V2.py    # Legacy offset-based downloader
└── gps_sync_time_utc.sh     # Syncs system UTC clock from GPS NMEA ($GNRMC)
```

---

## Configuration (`devices.json`)

All instruments are configured in [`devices.json`](devices.json) at the workspace root:
- Set `"enabled": true` or `"enabled": false` per device (`AC32e`, `O342e`, `CO12e`, `Grimm11D`, `Picarro`, `GPS`, `Wind`).
- `mda-publishers/main.py` only starts enabled devices.
- The dashboard (`http://127.0.0.1:5000`) only displays enabled devices (while the map view shows whatever species exist in a campaign's recorded data).
- `mda-server/mock_measurements.py` also respects `devices.json`.

---

## Setup & Virtual Environments

### 1. Server (`mda-server/`)

```bash
cd mda-server
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

> **Arch Linux / Python 3.13+ note**: If `pip install -r requirements.txt` fails compiling older pinned packages (like `matplotlib==3.9.2`), install the direct dependencies unpinned so `pip` uses prebuilt wheels:
> ```bash
> ./venv/bin/pip install flask flask-sqlalchemy gunicorn matplotlib numpy scipy requests windrose pytest
> ```

### 2. Publishers (`mda-publishers/`)

```bash
cd mda-publishers
python3 -m venv venv
./venv/bin/pip install -r requirements.txt pymodbus
```

*(Note: `pymodbus` is required for the Envea Modbus/TCP analyzers.)*

---

## Running the System

### Start the Server

```bash
cd mda-server
./venv/bin/python app.py
```

The web UI and API will be available at **`http://127.0.0.1:5000`** (or `http://<device-ip>:5000` on the local network).

For production (systemd / `mdau_server.service`):
```bash
cd mda-server
./venv/bin/gunicorn --workers 2 --bind 0.0.0.0:5000 'app:create_app()'
```

### Start the Publishers (Real Hardware)

```bash
cd mda-publishers
./venv/bin/python main.py
```

For the legacy `config.ini`-driven setup (Picarro / LI-7810 / Wind / GPS):
```bash
cd mda-publishers
./venv/bin/python publish.py
```

### Run with Mock Measurements (Testing Without Hardware)

In a second terminal (while `app.py` is running):
```bash
cd mda-server
./venv/bin/python mock_measurements.py
```

---

## Supported Sensors

- **Envea Gas Analyzers** (Modbus/TCP or serial stream):
  - `AC32e`: `NO`, `NO2`, `NOx` (ppb)
  - `O342e`: `O3` (ppb)
  - `CO12e`: `CO` (ppm)
- **Grimm 11-D** (`Grimm11D`, RS-232 over USB): `PM10`, `PM4`, `PM2.5`, `PM1` (µg/m³)
- **Picarro CRDS** (TCP `:51020`): `CH4`, `CO2` (ppm), `H2O` (%)
- **LI-COR LI-7810** (MQTT `:1883`): `CH4-LI`, `CO2-LI`
- **Wind & GPS**: Lufft UMB serial wind sensor and NMEA GPS receiver (also provides `gps_time` synchronization).

---

## Frontend Build (`mda-server/static/`)

If you edit TypeScript/CSS files in `mda-server/static/src/`, rebuild `mda-server/static/dist/bundle.js`:

```bash
cd mda-server/static
npm install
npm run build
```

---

## Exporting Campaign Data

- **Web Dashboard**: Click **JSON** or **CSV** next to any campaign on `http://127.0.0.1:5000` (exports all gas/PM measurements matched to the nearest GPS fix within 15 seconds).
- **CLI Backup (`data_downloader_v3.py`)**: Edit `START_TIME` and `END_TIME` in `data_downloader_v3.py` and run:
  ```bash
  python3 data_downloader_v3.py
  ```
- **GPS Clock Sync**:
  ```bash
  bash gps_sync_time_utc.sh
  ```
