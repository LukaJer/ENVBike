# Code Review & Known Bugs (`bugs.md`)

Comprehensive code review of `mda-server/`, `mda-publishers/`, and root utility scripts on branch `HAL` (`EnvBike` `456c031`, `mda-server` `ba66818`, `mda-publishers` `7a33539`).

Statuses: **`[Open]`**, **`[Partially Fixed]`**, **`[Fixed]`**.

---

## Summary of Open / Partially Fixed Issues

| Area | Critical | High | Medium | Low |
|---|---:|---:|---:|---:|
| `mda-server/` Backend | 0 | 0 | 11 | 3 |
| `mda-server/` Frontend & Templates | 0 | 0 | 9 | 4 |
| `mda-publishers/` Publishers & Sensors | 0 | 0 | 5 | 0 |
| Root Scripts & Config | 0 | 0 | 7 | 2 |

---

## `mda-server/` — Backend (`app.py`, `models/`, `util/`)

### B1. `[Fixed]` `[Critical]` Unauthenticated Remote Command Execution (`POST /api/terminal`) & `debug=True` on `0.0.0.0`
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L588-L629), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L1079-L1083), [mdau_server.service](file:///home/luka/Code/EnvBike/mda-server/mdau_server.service#L10)
- **Status**: Fixed — `api_terminal` now returns `403` unless `MDA_ENABLE_TERMINAL=1` or `request.remote_addr` is loopback (`127.0.0.1` / `::1`), validates `isinstance(payload, dict)` and string `command` (`400`), and `app.run()` defaults `debug` to `os.environ.get("FLASK_DEBUG") == "1"`.

### B2. `[Fixed]` `[High]` Per-Process Mutable State & Missing SQLite Concurrency Config Break Under `--workers 2`
- **Files**: [mdau_server.service](file:///home/luka/Code/EnvBike/mda-server/mdau_server.service#L10), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L123-L165), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L211-L218), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L408-L527), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L588-L608), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L711-L849), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L1021-L1027)
- **Status**: Fixed — `mdau_server.service` switched to `--workers 1 --threads 8`, SQLite `connect` listener enables `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000`, and `post_measurement` wraps `db.session.commit()` with `db.session.rollback()` + 500 JSON error.

### B3. `[Fixed]` `[High]` `LocationMeasurement.get_data` Cap Truncates Locations Before Gas/Wind End Time
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L241-L275), [location_measurement_model.py](file:///home/luka/Code/EnvBike/mda-server/models/location_measurement_model.py#L50-L68)
- **Status**: Fixed — `LocationMeasurement.get_data` supports `apply_limit=False` with explicit `start_datetime`/`end_datetime`; `get_gas_measurements` and `get_wind_measurements` now query uncapped locations over `[measurements[0].datetime - 5s, measurements[-1].datetime + 5s]`.

### B4. `[Fixed]` `[High]` `AverageWindMeasurementWithLocation` Drops Final Bucket & Linearly Averages Angles
- **Files**: [average_wind_measurement_with_location.py](file:///home/luka/Code/EnvBike/mda-server/models/average_wind_measurement_with_location.py#L26-L61)
- **Status**: Fixed — `calculate_average_measurements` flushes `sub_group` after the loop and handles single-point buckets; `create_from_list` computes circular mean heading via `math.sin`/`math.cos` + `math.atan2` normalized to `[0, 360)`.

### B5. `[Fixed]` `[High]` `campaign_stats` and `plot_baselines` Crash on Live/Empty/Non-CH4 Campaigns & Hardcoded Path
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L965-L975), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L1057-L1059), [campaign_statistics.py](file:///home/luka/Code/EnvBike/mda-server/util/campaign_statistics.py#L12-L34), [campaign_statistics.py](file:///home/luka/Code/EnvBike/mda-server/util/campaign_statistics.py#L67-L118)
- **Status**: Fixed — `get_campaign_statistics_for_gas` uses `campaign.end or datetime.now()`, guards empty `concentrations` / `n_base_samples == 0`, and casts outputs to Python `float`; `plot_baselines` queries existing campaigns dynamically, guards empty lists/`int(R) <= 0`, and writes EPS output to `tempfile.gettempdir()`.

### B6. `[Fixed]` `[High]` Tile Cache Worker Crashes Silently on Corrupt Responses, Leaves Partial Files & Lacks Coordinate Validation
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L722-L838)
- **Status**: Fixed — `api_map_tiles_cache` validates dict payloads and finite Web Mercator bounds (`[-85.0511, 85.0511]`, `[-180, 180]`, `min <= max`); `worker()` reuses a `requests.Session()`, validates images via `with Image.open(...) as im:` (`im.load()`) before atomic `.tmp` + `os.replace()` writes, and handles per-tile exceptions cleanly.

### B7. `[Partially Fixed]` `[Medium]` Timezone-Aware ISO Datetimes & Non-Finite Floats (`NaN`/`Inf`) Crash `/api/live`, JSON, and `Interpolator`
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L195-L218), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L426-L519), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L650-L660), [gas_measurement_model.py](file:///home/luka/Code/EnvBike/mda-server/models/gas_measurement_model.py#L18-L24), [location_measurement_model.py](file:///home/luka/Code/EnvBike/mda-server/models/location_measurement_model.py#L20-L28), [wind_measurement_model.py](file:///home/luka/Code/EnvBike/mda-server/models/wind_measurement_model.py#L17-L22), [log_model.py](file:///home/luka/Code/EnvBike/mda-server/models/log_model.py#L17-L22), [interplator.py](file:///home/luka/Code/EnvBike/mda-server/util/interplator.py#L59-L78)
- **Status**:
  - **Fixed**: `ApiHelper.parse_iso_datetime` now normalizes offset-aware ISO datetimes to naive local time in all `create_from_json` methods and `Request.get_datetime`.
  - **Still Open**: Non-finite floats (`NaN`/`Infinity`) and non-string field validation in `create_from_json` / `api_post_settings` / `Interpolator`.

### B8. `[Open]` `[Medium]` `Campaign.serialize()` and `Campaign.create_from_json()` Crash on Wrong/Nullable Fields
- **Files**: [campaign_model.py](file:///home/luka/Code/EnvBike/mda-server/models/campaign_model.py#L17-L33)
- **Issue**: `Campaign.serialize()` references non-existent attributes (`self.datetime`, `self.type`, `self.concentration`, `self.unit`), raising `AttributeError`. `Campaign.create_from_json()` calls `datetime.fromisoformat(json["end"])` unconditionally even though `end` is `nullable=True`, raising `TypeError` when `end` is `None`.
- **Fix**: Serialize `id`, `start`, `end`, `name`, `author`, `description`, and allow `json.get("end") is None`.

### B9. `[Open]` `[Medium]` Invalid Query/Form Parameters Cause `500`s, Negative `limit` Bypasses Cap, and Bad `end` Silently Reopens Campaigns
- **Files**: [api_helper.py](file:///home/luka/Code/EnvBike/mda-server/util/api_helper.py#L9-L42), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L346-L354), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L998-L1055)
- **Issue**:
  - Missing `start` in `Request` raises raw `Exception` (`500`), malformed `start`/`end`/`limit`/`t` raises `ValueError` (`500`), and `limit=-1` is passed to SQLite `.limit(-1)`, which means **no limit** (bypassing `DEFAULT_LIMIT = 2000`).
  - In `POST /campaign`, non-numeric `id` raises `ValueError` (`500`), and a non-empty malformed `end` string causes `ApiHelper.get_datetime_if_set` to return `None`, silently clearing `edit_campaign.end = None`.
  - `/windrose`, `/wind-mean`, and `/stats` pass missing/invalid `start`/`end` directly to `datetime.strptime` (`500`), and `/stats` raises `ValueError`/`ZeroDivisionError` when no `CH4` rows exist.
- **Fix**: Raise `HttpException(..., 400)` for missing/invalid params, clamp `1 <= limit <= MAX_LIMIT` and `t >= 0`, reject unparseable non-empty `end` in `POST /campaign`, and handle empty results in `/stats`.

### B10. `[Open]` `[Medium]` `/windrose` and `/wind-mean`: Upstream Query Injection, No Timeout, Desynced Filtering, Linear Mean & Figure Leak
- **Files**: [windrose.py](file:///home/luka/Code/EnvBike/mda-server/util/windrose.py#L11-L78), [campaign_statistics.py](file:///home/luka/Code/EnvBike/mda-server/util/campaign_statistics.py#L102-L118)
- **Issue**:
  - `get_meteo_data` interpolates raw `station` directly into the upstream URL without validation/encoding and calls `requests.get(url)` with no `timeout`.
  - `get_wind_speed_and_direction` filters `wind_speed` and `wind_direction` independently, misaligning arrays and crashing `ax.bar(...)` with `ValueError` whenever one series has an error value (`>500.0`) and the other does not (or `TypeError` on `None`).
  - `get_average_wind_speed_and_direction` uses linear `np.mean(wind_direction)` on circular degrees (and returns `NaN` on empty arrays).
  - `create_windrose` calls `plt.figure()` and then `WindroseAxes.from_ax()` (creating a second figure); `plt.close()` only closes the second figure, leaking the first on every request. Global `plt.rcParams` mutation and `pyplot` state are not thread-safe.
  - Hardcodes `- timedelta(hours=1)` instead of DST-aware local-to-UTC conversion (off by 1 hour in CEST).
- **Fix**: Validate `station_id`, pass `params=...` and `timeout=10`, filter `(speed, direction)` pairs together, compute circular/vector mean, use OO `Figure` (`WindroseAxes.from_ax(fig=fig)` + `plt.close(fig)`), and convert via `zoneinfo("Europe/Berlin")`.

### B11. `[Open]` `[Medium]` `GET /api/live` DB Fallback Drops Slower Sensors (`limit(300)`) and Compares Timestamp Strings
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L413-L428), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L484-L519)
- **Issue**: `api_live` scans only the latest `300` `GasMeasurement` rows (~30–40s with 10–12 species at 1 Hz), causing slower or briefly idle sensors (<120s `offline_after`) to vanish when `live_cache` is cold or across workers. Timestamps are also compared lexicographically as ISO strings (`cached["datetime"].isoformat() >= db_entry["datetime"]`).
- **Fix**: Query the latest row per `GasMeasurement.type` (`GROUP BY type` / `MAX(id)`) and compare `datetime` objects directly.

### B12. `[Open]` `[Medium]` Non-Atomic Read-Modify-Write Race in `settings.json` (`POST /api/settings`)
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L88-L105), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L634-L671)
- **Issue**: `save_settings` overwrites `settings.json` directly with `open(SETTINGS_PATH, "w")` without locking or atomic replacement; concurrent POSTs can lose updates and concurrent readers can see a truncated file and fall back to defaults.
- **Fix**: Guard writes with a lock and write to a temp file in the same directory followed by `os.replace()`.

### B13. `[Open]` `[Low]` Destructive / State-Mutating Routes Exposed via `GET` & Multiple Active Campaigns Allowed
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L377-L390), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L1014-L1027)
- **Issue**: `/campaign/delete/<int:campaign_id>` and `/enable-measurements/<int:enable>` mutate state via `GET` without CSRF protection, and `/campaign/start` allows starting multiple simultaneous active (`end=None`) campaigns.
- **Fix**: Switch state-mutating routes to `@app.post(...)` and guard `/campaign/start` against duplicate active campaigns.

### B14. `[Fixed]` `[Low]` Wasted DB Query & Unbounded In-Memory Buffering in `campaign_download`
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py)
- **Status**: Fixed — skips `WindMeasurement` queries when `format=csv` and streams both CSV and JSON via `stream_with_context` + `.yield_per(500)` in 500-row chunks.

### B15. `[Fixed]` `[Critical]` Gunicorn Thread Pool Exhaustion in `GET /api/live/stream`
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py), [mdau_server.service](file:///home/luka/Code/EnvBike/mda-server/mdau_server.service#L11)
- **Status**: Fixed — `api_live_stream()` enforces `sse_semaphore = threading.BoundedSemaphore(4)` (returning `503` when full so clients fall back to polling), releases in `finally:`, and caps each stream at `SSE_MAX_LIFETIME_SECONDS = 90.0` so stale sockets recycle and `EventSource` transparently reconnects.

### B16. `[Fixed]` `[High]` `GET /api/live/stream` Holds a SQLAlchemy `QueuePool` Connection and SQLite WAL Snapshot Indefinitely
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py)
- **Status**: Fixed — `event_stream()` wraps `_build_live_payload(include_db=True)` in `try ... finally: db.session.remove()` before entering the SSE loop, immediately releasing the SQLAlchemy connection and WAL read snapshot.

### B17. `[Fixed]` `[High]` Unhandled `ValueError` in `GET /api/live/stream` (`allow_nan=False`) Triggers Infinite Reconnect-Crash Loop
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py)
- **Status**: Fixed — shared `_finite_float()` sanitizes `concentration`, `latitude`, `longitude`, `speed`, and `heading` in `_build_live_payload()` (both DB and `live_cache` paths) so `NaN`/`Inf` serialize cleanly as `null`.

### B18. `[Open]` `[Medium]` `serve_mbtiles_tile` Unhandled `OverflowError` (`500`) & `_get_mbtiles_conn` `OSError` / FD Leak
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L100-L135), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L927-L944)
- **Issue**: `<int:z>` matches `z >= 64`, causing `(1 << z) - 1 - y` (or oversized `x`/`y >= 2^63`) to raise `OverflowError` on `sqlite3.Connection.execute` (`500`). `_get_mbtiles_conn` also calls `os.stat(path)` outside the `try` block (`FileNotFoundError` race `500`), and deleted `.mbtiles` files keep cached SQLite handles open per thread.
- **Fix**: Reject `z` outside `0..24` or out-of-range `x`/`y` with `404`, catch `OSError` alongside `sqlite3.Error`, and call `_evict_mbtiles_conn(path)` when a file is absent.

### B19. `[Open]` `[Medium]` Batch `POST /measurement/<type>` & `_update_live_cache` Overwrite Newer `live_cache` Entries with Older Timestamps
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L292-L357), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L731)
- **Issue**: `_update_live_cache()` overwrites entries unconditionally without checking `m.datetime >= existing["datetime"]`. An out-of-order or backfill batch overwrites `live_cache` with older readings, which `_build_live_payload(include_db=False)` then pushes to SSE clients.
- **Fix**: Only update cached entries when `existing is None` or `m.datetime >= existing["datetime"]`.

### B20. `[Open]` `[Medium]` `POST /api/settings` Crashes with `TypeError` (`500`) on Unhashable `default_layer` / `color_palette`
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L866-L874)
- **Issue**: `m.get("default_layer") in valid_layers` and `m.get("color_palette") in valid_palettes` test set membership without checking `isinstance(..., str)`, raising `TypeError: unhashable type` (`500`) on JSON lists/objects.
- **Fix**: Validate `isinstance(val, str)` first (and return `400` on invalid `default_layer`).

### B21. `[Open]` `[Medium]` `campaign_download` Matches Measurements Against Unfiltered GPS Glitches
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L1281-L1377)
- **Issue**: `campaign_download()` fetches raw `LocationMeasurement` rows without calling `Interpolator.filter_plausible_locations(locs)`, so exported CSV/JSON files match gas points to `(0, 0)` and jump spikes that map views filter out.
- **Fix**: Pass `locs` through `Interpolator.filter_plausible_locations(locs)` before building `loc_times`.

### B22. `[Open]` `[Medium]` `Interpolator.filter_plausible_locations` Permanently Accepts an Initial-Fix Glitch & Drops Short Post-Glitch Sequences
- **Files**: [interplator.py](file:///home/luka/Code/EnvBike/mda-server/util/interplator.py#L50-L79)
- **Issue**: The first in-bounds non-`(0, 0)` fix is accepted unconditionally into `filtered`. If the first fix is a spatial glitch, 3+ valid fixes trigger `candidate` recovery while leaving the glitch in `filtered[0]`; if only 1–2 valid fixes follow in the query window, only the glitch is returned.
- **Fix**: Drop an unconfirmed `filtered[0]` when `len(filtered) == 1` triggers recovery, or require confirmation before committing the initial fix.

### B23. `[Open]` `[Low]` `screenshot` Route Omits Offline Map Metadata from `map_settings`
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L479-L496), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L1454-L1473)
- **Issue**: `screenshot()` passes raw `load_settings()["map"]` without `active_mbtiles_info`, `has_local_png`, or `has_local_gray_png`, forcing screenshots to fall back to online `OSM` tiles instead of configured offline `MBTiles`/`Local` layers.
- **Fix**: Extract a shared helper for enriching `map_settings` and call it in both `campaign_map()` and `screenshot()`.

### B24. `[Open]` `[Low]` `_set_sqlite_pragma` Runs `PRAGMA journal_mode=WAL;` Before `PRAGMA busy_timeout=5000;`
- **Files**: [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L1546-L1553)
- **Issue**: Setting `journal_mode=WAL` before `busy_timeout=5000` can fail immediately with `database is locked` if another process holds a lock before WAL is enabled.
- **Fix**: Execute `PRAGMA busy_timeout=5000;` first in `_set_sqlite_pragma`.

---

## `mda-server/` — Frontend & Templates (`templates/`, `static/src/`)

### F1. `[Fixed]` `[High]` All `GasMeasurementPlotter` Instances Mutate a Single Shared `marker` Concurrently
- **Files**: [index.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/index.ts#L107), [index.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/index.ts#L125-L145), [gas-measurement-plotter.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/gas-measurement-plotter.ts#L51-L65)
- **Status**: Fixed (`bundle.js` rebuilt) — `GasMeasurementPlotter` tracks `is_visible`, guards `updateMarkerPosition()` with `if (this.is_visible)`, and syncs `marker` + `gas_display` on species switch.

### F2. `[Fixed]` `[High]` First Measurement Dropped & 1-Second Batch-Boundary Truncation in `MeasurementPlotter` / `WindMeasurementPlotter`
- **Files**: [measurement-plotter.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/measurement-plotter.ts#L71-L110), [wind-measurement-plotter.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/wind-measurement-plotter.ts#L55-L77), [gas-measurement-plotter.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/gas-measurement-plotter.ts), [api_helper.py](file:///home/luka/Code/EnvBike/mda-server/util/api_helper.py#L23-L28)
- **Status**: Fixed (`bundle.js` rebuilt) — `MeasurementPlotter` and `WindMeasurementPlotter` draw the first measurement and advance `start_datetime`; `GasMeasurementPlotter` renders a `circleMarker` for single-point starts; `formatToISODateTime()` preserves milliseconds and `Request.get_datetime` parses ISO strings with fractional seconds via `ApiHelper.parse_iso_datetime`.

### F3. `[Fixed]` `[High]` Live Campaign Species List Is Frozen at Page-Load DB State
- **Files**: [index.html](file:///home/luka/Code/EnvBike/mda-server/templates/index.html#L178-L202), [index.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/index.ts#L174-L181), [app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L304-L309)
- **Status**: Fixed (`bundle.js` rebuilt) — live campaigns (`campaign.end is none`) expose all `all_species` pills/plotters without requiring a page reload, and finished campaigns filter unknown species safely.

### F4. `[Fixed]` `[High]` Tile Cache Progress UI Cannot Resume After Reload & Permanently Stalls on Transient Fetch Error
- **Files**: [campaigns.html](file:///home/luka/Code/EnvBike/mda-server/templates/campaigns.html#L1250-L1318)
- **Status**: Fixed — `loadSettingsUI()` calls `pollTileCacheStatus()` to reattach to running downloads, avoids reload loops via `wasActive`, and reschedules `tileCacheTimer` on transient `!resp.ok` or network errors.

### F5. `[Fixed]` `[High]` Screenshot Mode Crashes with Unhandled `TypeError` on Live Campaigns or Failed `/wind-mean`
- **Files**: [windrose.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/windrose.ts#L4-L55), [index.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/index.ts#L215-L217)
- **Status**: Fixed (`bundle.js` rebuilt) — defaults `campaign.end` to `new Date()`, wraps `fetchWindMeanData` in `try/catch` with `Number.isFinite` fallback (`"Wind mean N/A"`), and attaches `.catch(...)` in `index.ts`.

### F6. `[Partially Fixed]` `[Medium]` Settings Tab Shows Generic Error on Save Failure
- **Files**: [campaigns.html](file:///home/luka/Code/EnvBike/mda-server/templates/campaigns.html#L1453-L1457)
- **Status**:
  - **Fixed / Removed**: The `deg2num()` / PNG tile downloader UI was removed from `campaigns.html`.
  - **Still Open**: `#map-settings-form` submit handler still displays generic `'Failed to save'` on non-OK `POST /api/settings` responses instead of surfacing `res.error`.

### F7. `[Open]` `[Medium]` `loadSettingsUI()` Overwrites Unsaved Settings Edits After Tile Caching or Tab Switching
- **Files**: [campaigns.html](file:///home/luka/Code/EnvBike/mda-server/templates/campaigns.html#L1187-L1189), [campaigns.html](file:///home/luka/Code/EnvBike/mda-server/templates/campaigns.html#L1268-L1283)
- **Issue**: When tile caching finishes or when switching back to the Settings tab, `loadSettingsUI()` re-fetches `/api/settings` and calls `populateSettingsForm()`, silently wiping unsaved edits in the form.
- **Fix**: Separate `/api/map-tiles/status` refresh from `/api/settings` form population, and avoid overwriting dirty form fields.

### F8. `[Open]` `[Medium]` Diagnostics & Live Polling Race Conditions and `<select>` Dropdown Reset
- **Files**: [campaigns.html](file:///home/luka/Code/EnvBike/mda-server/templates/campaigns.html#L1067-L1174), [campaigns.html](file:///home/luka/Code/EnvBike/mda-server/templates/campaigns.html#L1370-L1375)
- **Issue**: `pollDiagnostics()` and `pollLive()` do not cancel superseded in-flight fetches (`AbortController` / request sequence ID), allowing stale responses to overwrite newer filtered output. `pollDiagnostics()` also unconditionally reassigns `#diag-sensor.innerHTML` every 3s even when `data.sensors` hasn't changed, closing the native dropdown while the user is selecting an option.
- **Fix**: Use `AbortController` or a monotonic request ID in both pollers, guard DOM updates with `activeTab === 'diagnostics'`, and only rebuild `#diag-sensor` when `data.sensors` changes.

### F9. `[Fixed]` `[Medium]` `onFinished` Auto-Fit Reads Mutable `active_plotter` After Species Switch
- **Files**: [index.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/index.ts#L209-L219)
- **Status**: Fixed (`bundle.js` rebuilt) — `plotter.onFinished` closes over `const plotter`, checks `active_plotter === plotter`, and validates `bounds && bounds.isValid()`. (See `F21` for remaining `hasFittedInitialBounds` ordering.)

### F10. `[Open]` `[Medium]` `Slider` (`gas-slider.ts`): Negative `max`, `null`/`NaN` Crashes, Stuck Popup & Focus Conflict
- **Files**: [gas-slider.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/gas-slider.ts#L16-L69)
- **Issue**: `updateSliderMax()` sets `max = "-1"` when `data_map.size === 0`. `updatePopup()` calls `data.concentration.toFixed(3)` and passes `[data.latitude, data.longitude]` to Leaflet without `Number.isFinite` checks. `updateGasType()` neither resets `slider_element.value` nor closes an open popup. Releasing the pointer outside the slider or `touchcancel` leaves the popup open, and `map.panTo(...)` conflicts with Focus mode.
- **Fix**: Clamp `max` to `Math.max(0, size - 1)`, reset value and call `hidePopup()` in `updateGasType()`, guard `Number.isFinite`, handle `change`/`touchcancel`, and suspend Focus panning while dragging.

### F11. `[Open]` `[Medium]` Plotter & `NumericDisplay` Crash on `NaN`/`null` Values or Zero Span
- **Files**: [gas-measurement-plotter.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/gas-measurement-plotter.ts#L117-L156), [wind-measurement-plotter.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/wind-measurement-plotter.ts#L36-L51), [numeric-display.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/numeric-display.ts#L17-L21)
- **Issue**: `getColor(NaN)` or `min === max` (`?span=0`) produces `undefined` colors and crashes `hex.slice(1)`. `WindMeasurementPlotter` with `speed = NaN` passes `{ icon: undefined }` to `L.marker`, crashing Leaflet's `Marker._initIcon()`. `NumericDisplay.updateValue(null)` throws `TypeError` on `.toFixed()`.
- **Fix**: Guard `Number.isFinite` (and `range <= 0` in `getColor`) at the entry of all three methods, and verify `icon` exists before constructing `L.marker`.

### F12. `[Open]` `[Medium]` Edit Campaign Form (`campaign.html`) Silently Truncates Seconds from `start` and `end`
- **Files**: [campaign.html](file:///home/luka/Code/EnvBike/mda-server/templates/campaign.html#L92-L96)
- **Issue**: `campaign.start` and `campaign.end` are prefilled with `strftime('%Y.%m.%d %H:%M')`, dropping seconds. Editing a campaign's name or description and saving silently truncates up to 59 seconds off `start` and `end`.
- **Fix**: Format both inputs with `'%Y.%m.%d %H:%M:%S'`.

### F13. `[Open]` `[Low]` Unescaped HTML in Map Popups/Legend & Falsy `0` Check in Legend Grades
- **Files**: [gas-measurement-plotter.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/gas-measurement-plotter.ts#L93), [gas-measurement-plotter.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/gas-measurement-plotter.ts#L193-L197), [gas-slider.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/gas-slider.ts#L55)
- **Issue**: `datetime`, `type`/`gas_name`, and `unit` are interpolated into HTML strings without escaping. `grades[i + 1] ? ... : '+'` treats `0` as falsy and renders `+` instead of `–0`.
- **Fix**: Escape interpolated values (or use `textContent`) and check `i + 1 < grades.length`.

### F14. `[Open]` `[Low]` `url-helper.ts`: `extractCampaignIdFromCurrentUrl()` Returns `0` on `/map/<id>`, Wrong `Campaign.end` Type & Unchecked `Date` Parsing
- **Files**: [url-helper.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/url-helper.ts#L14-L48)
- **Issue**: Regex `/\/map\/(\d+)\/screenshot/` fails on normal `/map/<id>` routes; `Campaign.end` is typed `Date` instead of `Date | null`; invalid `start`/`end` query params produce `"NaN-NaN-NaNTNaN:NaN:NaN"`.
- **Fix**: Match `/\/map\/(\d+)/`, type `end: Date | null`, and validate `!Number.isNaN(parsed.getTime())`.

### F15. `[Open]` `[Low]` `<a href="#">` Missing `preventDefault()` & `livemap.css` Override Order
- **Files**: [focus-control.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/focus-control.ts#L20-L36), [wind-control.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/wind-control.ts#L19-L35), [livemap.css](file:///home/luka/Code/EnvBike/mda-server/static/src/livemap.css#L8-L53)
- **Issue**: `FocusControl` and `WindControl` click handlers omit `L.DomEvent.preventDefault(e)`, mutating `location.hash` to `#`. `livemap.css` is injected by `style-loader` *after* `index.html`'s `<style>` block, overriding `#control-panel` `line-height` and `height`.
- **Fix**: Call `L.DomEvent.preventDefault(e)` in both handlers and remove obsolete `#control-panel` / `.slider` rules from `livemap.css`.

### F16. `[Fixed]` `[High]` Duplicate Polling Loops & Stale UI/State Mutations on Rapid Species Switching
- **Files**: [measurement-plotter.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/measurement-plotter.ts), [gas-measurement-plotter.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/gas-measurement-plotter.ts)
- **Status**: Fixed (`bundle.js` rebuilt) — `MeasurementPlotter` tracks `pollGeneration` and `AbortController` (aborting & bumping generation in `stopPlotting()`), ignores `AbortError`, and checks generation before `plotData()`, `onFinished?.()`, or `setTimeout`; `GasMeasurementPlotter.drawMeasurement()` guards slider and numeric display updates with `this.is_visible`.

### F17. `[Fixed]` `[High]` `sseFailCount` Not Reset in `startLiveStream()`, Unguarded Closed `EventSource` Handlers & `pollLive()` Race
- **Files**: [campaigns.html](file:///home/luka/Code/EnvBike/mda-server/templates/campaigns.html)
- **Status**: Fixed — `startLiveStream()` resets `sseFailCount = 0` and guards `onopen`/`onmessage`/`onerror` with `src === liveSource`; `stopLiveStream()` detaches handlers and aborts `liveFetchController`; `pollLive()` uses `AbortController` and verifies `ctrl === liveFetchController && !liveSource` before updating DOM or rescheduling.

### F18. `[Open]` `[Medium]` Raster MBTiles Shares One `L.tileLayer` Instance Across `"MBTiles"` and `"MBTilesG"`
- **Files**: [index.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/index.ts#L124-L138)
- **Issue**: For raster `.mbtiles` (`png`/`jpg`/`webp`), the same `rasterLayer` instance is assigned to both `tile_layers["MBTiles"]` and `tile_layers["MBTilesG"]`. Leaflet keys layers by `L.stamp(layer)`, causing both radio buttons to appear checked, forcing full tile reloads on click, and not rendering `"MBTilesG"` in grayscale.
- **Fix**: Omit `"MBTilesG"` for raster `.mbtiles` (falling back `"MBTilesG"` -> `"MBTiles"`) or use a distinct `L.tileLayer` instance with CSS grayscale.

### F19. `[Open]` `[Medium]` Early Species Pill Clicks Dropped While `await getOrCreatePlotter(start_key)` Is Pending
- **Files**: [index.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/index.ts#L239-L258)
- **Issue**: `main()` awaits `getOrCreatePlotter(start_key)` before registering `#gas-selector`'s `'change'` listener. Clicking a `.gas-pill` while initial baseline stats are loading updates the pill highlight and fires `'change'` before any listener exists, leaving the active pill out of sync with the plotted species.
- **Fix**: Register the `#gas-selector` `'change'` listener before `await getOrCreatePlotter(start_key)` (or sync `selector.value` after startup).

### F20. `[Open]` `[Medium]` Saving Map Settings Before `/api/offline-maps` Loads Wipes `active_mbtiles`
- **Files**: [campaigns.html](file:///home/luka/Code/EnvBike/mda-server/templates/campaigns.html#L880-L882), [campaigns.html](file:///home/luka/Code/EnvBike/mda-server/templates/campaigns.html#L1381-L1459)
- **Issue**: Submitting `#map-settings-form` before `loadSettingsUI()` finishes fetching `/api/offline-maps` (or after a failed fetch) reads empty `#mbtiles-list` inputs and sends `active_mbtiles: ""` and `mbtiles_descriptions: {}`, wiping saved settings.
- **Fix**: Track whether `#mbtiles-list` has loaded successfully and omit `active_mbtiles` / `mbtiles_descriptions` from `collectMapSettingsPayload()` until populated.

### F21. `[Open]` `[Low]` `hasFittedInitialBounds` Set Before Checking `bounds.isValid()`
- **Files**: [index.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/index.ts#L210-L219)
- **Issue**: `hasFittedInitialBounds = true;` executes before checking `bounds && bounds.isValid()`, preventing `fitBounds` from running on a subsequent species if the initial species has no valid GPS-matched points.
- **Fix**: Move `hasFittedInitialBounds = true;` inside `if (bounds && bounds.isValid())`.

---

## `mda-publishers/` — Publishers & Sensors

### P1. `[Fixed]` `[Critical]` NMEA RMC Timestamps Keep UTC `tzinfo` After Adding Local Offset, Corrupting `gps_time` & Crashing `/api/live`
- **Files**: [location_measurement_message.py](file:///home/luka/Code/EnvBike/mda-publishers/messages/location_measurement_message.py#L27-L37), [gps.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/gps.py#L44-L56)
- **Status**: Fixed — `create_from_NMEA_RMC` converts the GNSS UTC datetime via `astimezone().replace(tzinfo=None)` (or adds explicit `utc_offset` to naive datetime), producing naive local timestamps without relying on `time.localtime().tm_isdst`.

### P2. `[Fixed]` `[Critical]` `Grimm11D.read_measurements()` Blocks for 60s on Serial Timeouts & Up to ~6 Minutes While Zeroing
- **Files**: [grimm_11d.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/grimm_11d.py#L45-L69)
- **Status**: Fixed — returns `[]` immediately on `raw == ""` (serial timeout), zero lines (`_skip_zero`), and `NA` mass lines after updating `self.last_status`.

### P3. `[Fixed]` `[High]` `LI7810Publisher` Crashes Paho's Network Thread on Bad Payloads, Dies on Startup Connect Failure & Stops Loop Before `disconnect()`
- **Files**: [li7810_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/li7810_publisher.py#L30-L89)
- **Status**: Fixed — switched to `json.loads` with full exception handling in `on_message`, added stop-aware `connect()` retry loop in `start_up()`, and ordered `disconnect()` before `loop_stop()` in `shutdown()`.

### P4. `[Fixed]` `[High]` `GasPublisher` Dies on Transient Startup Errors, Never Reconnects on TCP Drop & `Picarro.Meas_GetBuffer()` Breaks on `\r\n`
- **Files**: [gas_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/gas_publisher.py#L23-L60), [picarro.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/picarro.py#L146-L176)
- **Status**: Fixed — `Meas_GetBuffer()` strips `";\r\n "`, `GasPublisher.start_up()` catches transient startup errors, and `measurement_routine()` reconnects on `(ConnectionError, OSError, TimeoutError)`.

### P5. `[Fixed]` `[High]` Uninterruptible `connect()` Loops Hang `publish.py` & Prevent Clean `shutdown()` in `main.py`
- **Files**: [connection_strategy.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/connection_strategy.py#L38-L107), [gps.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/gps.py#L22-L33), [umb.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/umb.py#L110-L121), [envea_analyzer.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/envea_analyzer.py#L55), [grimm_11d.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/grimm_11d.py#L32-L33), [picarro.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/picarro.py#L106-L107), [publish.py](file:///home/luka/Code/EnvBike/mda-publishers/publish.py#L67-L77)
- **Status**: Fixed — threaded `stop_event=self._stopping` into all `connect()` methods, guarded `is_open` before `serial.open()`, and added `SIGINT`/`SIGTERM` handling + daemon threads + bounded `join()` to `publish.py`.

### P6. `[Partially Fixed]` `[Medium]` Serial Drivers (`GPS`, `UMB`, `Grimm11D`) & `EnveaAnalyzer` (Stream/Poll) Never Reconnect Mid-Run
- **Files**: [gps.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/gps.py#L35-L48), [umb.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/umb.py#L123-L176), [grimm_11d.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/grimm_11d.py#L35-L52), [envea_analyzer.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/envea_analyzer.py#L65-L75)
- **Issue**: Unlike `EnveaAnalyzer._read_modbus()`, these drivers only connect once in `start_up()`. A USB-serial unplug/reset or stream drop leaves them failing on a dead descriptor forever.
- **Fix**: Close and reopen the port/connection with `stop_event`-aware backoff on `SerialException`/`OSError`/`ConnectionError`.

### P7. `[Open]` `[Medium]` Non-Finite IEEE-754 Floats (`NaN`/`Inf`) from Modbus or UMB Cause HTTP `500` on `mda-server`
- **Files**: [envea_analyzer.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/envea_analyzer.py#L152-L154), [umb.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/umb.py#L228-L231)
- **Issue**: Unpacked `>f` / `<f` / `<d` values are not checked with `math.isfinite()`. `NaN` from an analyzer serializes to `NaN` -> SQLite `NULL`, violating `NOT NULL` constraints on `mda-server`.
- **Fix**: Skip publishing samples where `not math.isfinite(value)` and set an appropriate status/log.

### P8. `[Open]` `[Medium]` `EnveaAnalyzer` Crashes with `AttributeError` in Non-Modbus Mode Without `connection`
- **Files**: [envea_analyzer.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/envea_analyzer.py#L30-L63), [envea_gas_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/envea_gas_publisher.py#L45-L68)
- **Issue**: `EnveaAnalyzer.__init__` defaults `connection=None` and `mode="stream"`. Calling `connect()`, `close()`, or `_read_text()` without a `ConnectionStrategy` raises `AttributeError` (including in `finally` shutdown).
- **Fix**: Validate `if self._mode != "modbus" and self._connection is None: raise ValueError(...)` and guard `if self._connection is not None:` in `close()`.

### P9. `[Fixed]` `[High]` Thread-Unsafe `requests.Session` Shared Across `BasePublisher` & `LI7810Publisher` Paho Thread (+ Shutdown Stall)
- **Files**: [base_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/base_publisher.py), [li7810_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/li7810_publisher.py)
- **Status**: Fixed — `BasePublisher` uses thread-local sessions closed via `_close_sessions()`, orders `self.shutdown()` before the `timeout=1.0` `"Disconnected"` log in `finally:`, and `LI7810Publisher.on_message()` enqueues batches onto `self._queue` drained by `measurement_routine()`.

### P10. `[Fixed]` `[High]` `LI7810Publisher.on_message` Misses `OverflowError`/`OSError`, Accepts `NaN`/`Inf` & Stays Stuck `"Unconnected"`
- **Files**: [li7810_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/li7810_publisher.py)
- **Status**: Fixed — catches `(OverflowError, OSError)` alongside parse/type errors, rejects non-finite timestamps/concentrations via `math.isfinite()`, and posts `"OK"` / error status from `measurement_routine()`.

### P11. `[Fixed]` `[High]` `GPS._is_plausible_fix` Unconditionally Accepts First-Fix Glitches & Clamps Backward Clock Jumps to `dt_s = 0.0`
- **Files**: [gps.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/gps.py)
- **Status**: Fixed — `_is_plausible_fix()` computes `dt_s` from `time.monotonic()` (immune to backward wall-clock/DST jumps) and requires `RECOVERY_CONSECUTIVE_FIXES` (`3`) consistent fixes before establishing the initial `_last_valid_fix`.

### P12. `[Open]` `[Medium]` `Logger` Leaks Thread-Local `requests.Session` Objects & Ignores HTTP Error Statuses
- **Files**: [logger.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/logger.py#L13-L28), [gps_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/gps_publisher.py#L27-L43)
- **Issue**: `Logger._get_session()` creates unclosed `requests.Session()` instances per calling thread (including short-lived threads like `_sync_system_time_once`) and discards the `Response` without checking `not resp.ok`.
- **Fix**: Track sessions in `Logger` for cleanup on shutdown (or avoid keep-alive in ephemeral threads) and warn on `not resp.ok`.

### P13. `[Open]` `[Medium]` Unchunked `BasePublisher._try_post_measurements_batch` Risks Dropping Large Picarro Buffers on 5s Timeout
- **Files**: [base_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/base_publisher.py#L72-L88), [gas_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/gas_publisher.py#L42-L50)
- **Issue**: `GasPublisher` drains the Picarro buffer and submits all rows in one HTTP `POST` with `timeout=5.0`; large backlogs can time out on a Raspberry Pi and lose the cleared buffer.
- **Fix**: Chunk large batches (e.g., 200–500 measurements per `POST`) and/or scale timeout with payload size.

---

## Root Scripts & Config

### R1. `[Fixed]` `[Critical]` `data_downloader_V2.py`: Crash on `data.get(...)` (`list` Returned by Server)
- **Files**: [data_downloader_V2.py](file:///home/luka/Code/EnvBike/data_downloader_V2.py)
- **Status**: Fixed — handles `list` vs `dict` responses (`isinstance(data, dict)`) and closes `]` in a `finally:` block.

### R2. `[Fixed]` `[Critical]` `data_downloader_V2.py`: Undefined `offset`/`limit` (`NameError`) & Unsupported Server `offset` Pagination
- **Files**: [data_downloader_V2.py](file:///home/luka/Code/EnvBike/data_downloader_V2.py)
- **Status**: Fixed — defined `limit`/`offset`, updated `query_params["offset"]`, and breaks out when `isinstance(data, list)` or `len(items) < limit`.

### R3. `[Fixed]` `[Critical]` `data_downloader.py` & `data_downloader_V2.py`: `AttributeError` Typo (`requests.exception`)
- **Files**: [data_downloader.py](file:///home/luka/Code/EnvBike/data_downloader.py#L47), [data_downloader_V2.py](file:///home/luka/Code/EnvBike/data_downloader_V2.py#L74)
- **Status**: Fixed — updated to `requests.exceptions.RequestException` in both files.

### R4. `[Fixed]` `[Critical]` `gps_sync_time_utc.sh`: `sudo date -s` Sets UTC Time as Local Timezone & Locale-Dependent Month
- **Files**: [gps_sync_time_utc.sh](file:///home/luka/Code/EnvBike/gps_sync_time_utc.sh)
- **Status**: Fixed — now runs locale-independent `sudo date -u -s "${YYYY}-${MO}-${DD} ${HH}:${MM}:${SS}"`.

### R5. `[Fixed]` `[High]` `mmu_downloader_core.py`: 1 ms Boundary Drift Skips 1s Every 1,000 Chunks & Sub-Second Split Overlaps
- **Files**: [mmu_downloader_core.py](file:///home/luka/Code/EnvBike/mmu_downloader_core.py)
- **Status**: Fixed — `_align_window()` aligns boundaries to whole seconds, `_fetch_window_complete()` splits on integer seconds, and `_fetch_all_chunked()` handles `start_dt == end_dt` cleanly.

### R6. `[Fixed]` `[High]` `mmu_downloader_core.py`: `fetch_locations` Omits `±15s` Boundary Buffer for GPS Matching
- **Files**: [mmu_downloader_core.py](file:///home/luka/Code/EnvBike/mmu_downloader_core.py)
- **Status**: Fixed — `fetch_locations()` pads `[start_dt, end_dt]` by `±MAX_MATCH_SECONDS`.

### R7. `[Fixed]` `[High]` `mmu_downloader_core.py`: Missing `"H2O-LI"` in Species Fallback & Missing `/gas-types` Endpoint
- **Files**: [mmu_downloader_core.py](file:///home/luka/Code/EnvBike/mmu_downloader_core.py)
- **Status**: Fixed — added `"H2O-LI"` to `get_species_list()` fallback list.

### R8. `[Fixed]` `[High]` `gps_sync_time_utc.sh`: `head -n 1` Hangs Past `TIMEOUT`, Spins on Missing Device & Lacks NMEA Validation
- **Files**: [gps_sync_time_utc.sh](file:///home/luka/Code/EnvBike/gps_sync_time_utc.sh)
- **Status**: Fixed — checks `[ -r "$DEVICE" ]`, configures `stty raw -echo`, opens fd 3 once with `IFS= read -r -t 2 LINE <&3`, strips `\r`, matches `$GNRMC`/`$GPRMC`, and validates `TIME`/`DATE` formats.

### R9. `[Fixed]` `[High]` `gps_sync_time_utc.sh` vs `devices.json`: Hardcoded `/dev/ttyACM0` & Serial Port Contention
- **Files**: [gps_sync_time_utc.sh](file:///home/luka/Code/EnvBike/gps_sync_time_utc.sh)
- **Status**: Fixed — defaults to `/dev/serial/by-id/usb-u-blox_AG_-_www.u-blox.com_u-blox_GNSS_receiver-if00` when present (falling back to `/dev/ttyACM0`, overridable via `$1`).

### R10. `[Open]` `[Medium]` `mmu_downloader_core.py`: Unchecked `None` on Bad `start`/`end` & Timezone Stripping
- **Files**: [mmu_downloader_core.py](file:///home/luka/Code/EnvBike/mmu_downloader_core.py#L61-L80), [mmu_downloader_core.py](file:///home/luka/Code/EnvBike/mmu_downloader_core.py#L160-L210)
- **Issue**: `_parse_dt()` returns `None` on invalid strings, crashing with `TypeError` inside `_fetch_all_chunked()`; aware ISO datetimes silently have their offset dropped by `_fmt()`.
- **Fix**: Validate `start_dt`/`end_dt` (`not None`, `start_dt <= end_dt`) up front and normalize/reject aware datetimes explicitly.

### R11. `[Open]` `[Medium]` `mmu_auto_download.py`: Stale Lock File on `SIGTERM`/`SIGKILL` Permanently Blocks Runs
- **Files**: [mmu_auto_download.py](file:///home/luka/Code/EnvBike/mmu_auto_download.py#L40-L70)
- **Issue**: Uses `O_CREAT | O_EXCL` on `/tmp/mmu_download_{campaign_id}.lock` with cleanup only in `finally:`; abnormal termination leaves a stale lock file that blocks future downloads for that campaign.
- **Fix**: Use `fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)` so the kernel releases the lock on exit.

### R12. `[Open]` `[Medium]` `mmu_auto_download.py`: Docstring / CLI Mismatch & Unused Server Hook
- **Files**: [mmu_auto_download.py](file:///home/luka/Code/EnvBike/mmu_auto_download.py#L6-L35)
- **Issue**: Docstring claims `app.py` invokes it with `<campaign_id>`, but `main()` requires 3 arguments (`<campaign_id> <start_iso> <end_iso>`) and `mda-server/app.py` never calls it.
- **Fix**: Align the docstring with the 3-arg CLI (or implement the campaign lookup).

### R13. `[Open]` `[Medium]` `mmu_downloader_core.py`: Exported `latitude`/`longitude` Are Strings Instead of Floats
- **Files**: [mmu_downloader_core.py](file:///home/luka/Code/EnvBike/mmu_downloader_core.py#L222-L225)
- **Issue**: Copies formatted coordinate strings from `LocationMeasurement.serialize()` verbatim instead of floats (inconsistent with `/campaign/<id>/download` and `with-location=1`).
- **Fix**: Convert `latitude`/`longitude` via `float(...)` in `merge_positions()`.

### R14. `[Open]` `[Medium]` `data_downloader_v3.py`: Output Directory Omits `END_TIME` (Silent Overwrite)
- **Files**: [data_downloader_v3.py](file:///home/luka/Code/EnvBike/data_downloader_v3.py#L48-L51)
- **Issue**: `manual_download_{safe_start}` omits `END_TIME`, overwriting previous exports with the same `START_TIME`.
- **Fix**: Include `safe_end` in the directory name.

### R15. `[Partially Fixed]` `[Medium]` `mdau_pub.service` Ignores `devices.json` & `LI7810` Missing from `devices.json`
- **Files**: [mdau_pub.service](file:///home/luka/Code/EnvBike/mda-publishers/mdau_pub.service#L11), [devices.json](file:///home/luka/Code/EnvBike/devices.json#L1-L78), [main.py](file:///home/luka/Code/EnvBike/mda-publishers/main.py#L27-L89)
- **Issue**: `mdau_pub.service` still executes `publish.py` (`config.ini`) instead of `main.py` (`devices.json`), and `LI7810` has no entry in `devices.json` / `main.py`.
- **Fix**: Point `mdau_pub.service` to `main.py` and optionally add an `"enabled": false` `LI7810` entry to `devices.json`.

### R16. `[Open]` `[Low]` Hardcoded `/home/mda/Desktop` & Partial Filename Sanitization
- **Files**: [mmu_auto_download.py](file:///home/luka/Code/EnvBike/mmu_auto_download.py#L24-L58), [data_downloader_v3.py](file:///home/luka/Code/EnvBike/data_downloader_v3.py#L44), [mmu_downloader_core.py](file:///home/luka/Code/EnvBike/mmu_downloader_core.py#L233-L236)
- **Issue**: Hardcoded `/home/mda/Desktop` fails under other usernames; `safe_filename()` only replaces `:`, not `/` or `..`.
- **Fix**: Use `os.path.expanduser("~/Desktop")` and sanitize `/`.

### R17. `[Open]` `[Low]` `data_downloader.py`: Missing Request `timeout` & Silent Truncation
- **Files**: [data_downloader.py](file:///home/luka/Code/EnvBike/data_downloader.py#L21-L34)
- **Issue**: `requests.get(..., stream=True)` has no `timeout`, and `limit=5050` / `with-location=1` silently truncates large windows or drops points >5s from a GPS fix.
- **Fix**: Add `timeout=60` or retire in favor of `data_downloader_v3.py`.

### R18. `[Fixed]` `[High]` `install.sh` Installs `apt` `nodejs`/`npm` (`< 20.9.0`) Incompatible with `webpack-cli@^7.3.1`
- **Files**: [install.sh](file:///home/luka/Code/EnvBike/install.sh), [package.json](file:///home/luka/Code/EnvBike/mda-server/static/package.json#L26)
- **Status**: Fixed — updated `"webpack-cli"` to `"^5.1.4"` (Node 18+ compatible) in `package.json` and added a Node.js `>= 18` version check in `install.sh`.

### R19. `[Open]` `[Medium]` `install.sh` Unbound `$USER` (`set -u`), Unconditional `sudo`, and Unrecoverable Partial `venv`s
- **Files**: [install.sh](file:///home/luka/Code/EnvBike/install.sh#L2), [install.sh](file:///home/luka/Code/EnvBike/install.sh#L53-L54), [install.sh](file:///home/luka/Code/EnvBike/install.sh#L88-L115)
- **Issue**: `id -nG "$USER"` fails with `USER: unbound variable` when `$USER` is unset; `sudo` fails in minimal `root` containers lacking `sudo`; and if `python3 -m venv` previously failed mid-creation leaving `bin/python` without `pip`, re-runs skip venv creation and crash.
- **Fix**: Resolve `TARGET_USER="${SUDO_USER:-${USER:-$(id -un)}}"`, skip `sudo` when `EUID == 0`, and check `[[ ! -x "$venv_dir/bin/pip" ]]` using `python3 -m venv --clear`.

---

## Previously Fixed Items (History)

- **`[Fixed]`** `serialize` decorator returning HTTP `200` on unhandled exceptions (`mda-server/app.py`).
- **`[Fixed]`** `POST /measurement/<type>` validation (`ACCEPT_MEASUREMENT_DATA`, `415`, non-dict `400`, parse errors `400`).
- **`[Fixed]`** `Interpolator` heading wrap-around (`np.unwrap`), empty/duplicate/single-location finite checks (`mda-server/util/interplator.py`).
- **`[Fixed]`** Infinite `0ms` polling loop for Wind on finished campaigns (`wind-measurement-plotter.ts`).
- **`[Fixed]`** Initial gas selection race (`index.html` / `index.ts`) and `FocusControl` crash when `"NO"` has no data.
- **`[Fixed]`** `gas-slider.ts` popup null dereference before `if (!data) return`.
- **`[Fixed]`** Dashboard `pollLive` null-dereference, stale values on `ERROR`, and unescaped `devices.json` `innerHTML` (`campaigns.html`).
- **`[Fixed]`** `GPS` DST refresh per sample & `LocationMeasurementMessage.__str__` `speed` typo.
- **`[Fixed]`** `BasePublisher` HTTP `timeout=5.0` & non-2xx warning logging.
- **`[Fixed]`** `EnveaAnalyzer._read_modbus()` reconnect on silent socket drop.
- **`[Fixed]`** `Logger.log()` `:log` suffix separation, `gps_time.now`, and `timeout=5.0`.
- **`[Fixed]`** `UMBError` subclassing `Exception`, `time.monotonic()`, `reset_input_buffer()`, and `UMBStatus` validation (`umb.py`).
- **`[Fixed]`** `Grimm11D.read_measurements()` resetting stale `"OK"` status on silent scans (`grimm_11d.py`).
- **`[Fixed]`** `TcpConnectionStrategy.read()` raising `ConnectionError` on EOF (eliminating 100% CPU spin) and socket `settimeout(5.0)`.
- **`[Fixed]`** `_GnssTime` using `time.monotonic()` instead of wall-clock `time.time()`.
