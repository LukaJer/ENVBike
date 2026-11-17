# Architecture Rewrite Evaluation: Mosquitto + Telegraf + InfluxDB + Grafana

This document evaluates replacing the current custom `mda-publishers` + `mda-server` + `mmu_downloader_core.py` stack with a standard **Mosquitto (MQTT) + Telegraf + InfluxDB + Grafana** pipeline.

## Feasibility Summary

**Yes, this replacement is feasible and well-suited for EnvBike's time-series sensor data**, with two important caveats:
1. Custom/proprietary sensor protocols (Grimm 11-D, Picarro CRDS, Lufft UMB wind, NMEA GPS) still require lightweight reader scripts publishing to Mosquitto (or Telegraf `execd` plugins).
2. Grafana's Geomap panel can replace the Leaflet map for route/concentration visualization, but bespoke UI features (live rotated heading marker, baseline-relative `CH4`/`CO2` color scaling, and one-click campaign auto-export) will require either small helper scripts or accepting Grafana's native workflows.

---

## Component-by-Component Mapping

| Current Component | Proposed Replacement | Feasibility & Notes |
|---|---|---|
| HTTP `POST` to `127.0.0.1:5000/measurement/{gas,wind,location}` | **Mosquitto** (MQTT broker) | Decouples sensor readers from database storage. `LI7810Publisher` already uses MQTT (`:1883`). |
| Envea analyzers (`AC32e`, `O342e`, `CO12e`) over Modbus/TCP (`:502`) | **Telegraf** (`inputs.modbus`) | Telegraf natively supports Modbus/TCP polling and word-swapped `FLOAT32` registers. |
| `Grimm11D`, `Picarro`, `UMB` (wind), `GPS` (NMEA) | Thin Python sensor scripts → **Mosquitto** | Telegraf has no built-in drivers for Grimm's `N`/`M`/`K` serial lines, Picarro's TCP `:51020` interface, or Lufft UMB RS-485 framing. Keeping minimal Python drivers that publish JSON to Mosquitto is the cleanest approach. |
| `gps_time` & `gps_sync_time_utc.sh` | `gpsd` + `chrony` (or `gps_sync_time_utc.sh`) | Telegraf timestamps incoming data using the host system clock, so disciplining the Raspberry Pi's clock from GPS (`gpsd` + `chrony`) ensures accurate timestamps without internet. |
| `mda-server` SQLite (`measurements.db`) + `mmu_downloader_core.py` | **InfluxDB** + Telegraf (`inputs.mqtt_consumer` → `outputs.influxdb_v2`) | Eliminates SQLite lock contention, the 5,000-row API cap, and the chunked-download workaround. InfluxDB provides native time-range queries and CSV/JSON exports. |
| `mda-server` Leaflet frontend (`static/src/`) | **Grafana** (Geomap + Time Series + Windrose plugins) | Grafana Geomap supports lat/lon route plotting colored by gas/PM values and can point to a local tile server (e.g. nginx serving `mda-server/static/tiles/osm_grayscale/`) for offline field use. |

---

## Key Design Considerations & Trade-offs

### 1. Joining Gas/Wind Measurements with GPS Coordinates
- **Current behavior**: `mda-server` (`Interpolator`) and `mmu_downloader_core.py` (`merge_positions`) store gas, wind, and location separately and join them by timestamp at read/export time.
- **InfluxDB options**:
  - **Option A (Edge enrichment)**: A small Python/Telegraf processor caches the latest GPS fix (`lat`, `lon`, `heading`, `speed`) and attaches it to each gas/PM MQTT message before InfluxDB ingestion. This makes Grafana Geomap queries trivial.
  - **Option B (Query-time join)**: Store `gas`, `wind`, and `location` as separate InfluxDB measurements and join them by timestamp window in Flux (InfluxDB v2) or SQL (InfluxDB v3).

### 2. Campaign Management & Auto-Export
- Grafana does not have a built-in "Create Campaign / Set End Time → launch `mmu_auto_download.py`" workflow.
- **Replacement**: Use Grafana dashboard time ranges and annotations to mark campaigns, and use an InfluxDB CLI/API export script (or a lightweight Flask/FastAPI endpoint) when per-campaign JSON/CSV dumps are needed.

### 3. Custom Map Features
- Grafana Geomap covers most spatial visualization needs, but features like the **live rotating heading marker** (`live-location-marker.ts`) and **baseline-relative concentration scaling** (`gas-measurement-plotter.ts` + `campaign-statistics.ts`) are harder to replicate 1:1 without custom Flux queries or a custom Grafana panel.

---

## Recommended Migration Path
1. Install **Mosquitto**, **InfluxDB**, **Telegraf**, and **Grafana** on the Raspberry Pi (plus `gpsd` + `chrony` for clock sync).
2. Configure Telegraf `inputs.modbus` for `AC32e` (`169.254.169.1`), `O342e` (`169.254.169.2`), and `CO12e` (`169.254.169.3`).
3. Refactor `Grimm11D`, `GPS`, `UMB`, and `Picarro` publishers to publish JSON to Mosquitto topics (e.g. `envbike/pm`, `envbike/gps`, `envbike/wind`, `envbike/gas`) instead of HTTP `POST`ing to Flask.
4. Configure Telegraf `inputs.mqtt_consumer` → `outputs.influxdb_v2`.
5. Serve `mda-server/static/tiles/osm_grayscale/` locally via nginx/lighttpd and configure Grafana Geomap + Time Series dashboards.
