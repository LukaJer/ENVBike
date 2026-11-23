# Code Review & Known Bugs (`bugs.md`)

This document lists verified bugs and reliability issues found during code reviews of `mda-server/`, `mda-publishers/`, and the root utility scripts, updated for the `HAL` branch (`mda-server` `315321c`, `mda-publishers` `568729e`, `EnvBike` `deb3a3e`) and subsequent high-impact fixes.

Statuses are marked **`[Open]`**, **`[Partially Fixed]`**, or **`[Fixed]`**.

---

## Root Scripts

### 1. `[Open]` Typo in `requests` exception class (`AttributeError`)
- **Files**: [data_downloader.py](file:///home/luka/Code/EnvBike/data_downloader.py#L47), [data_downloader_V2.py](file:///home/luka/Code/EnvBike/data_downloader_V2.py#L67)
- **Issue**: Both scripts catch `requests.exception.RequestException` instead of `requests.exceptions.RequestException`. If any HTTP/network error occurs, Python raises `AttributeError` instead of handling the error.

### 2. `[Open]` Undefined variables & broken pagination loop in `data_downloader_V2.py`
- **File**: [data_downloader_V2.py](file:///home/luka/Code/EnvBike/data_downloader_V2.py#L60-L61)
- **Issue**: `offset += limit` references undefined local variables `offset` and `limit` (they only exist as string keys in `query_params`), raising `NameError` on the first iteration. Additionally, `query_params["offset"]` is never updated in the loop.

### 3. `[Open]` `mmu_auto_download.py` CLI mismatch & unused server hook
- **File**: [mmu_auto_download.py](file:///home/luka/Code/EnvBike/mmu_auto_download.py#L6-L35), [mda-server/app.py](file:///home/luka/Code/EnvBike/mda-server/app.py)
- **Issue**: The docstring states `app.py` launches it as `python3 mmu_auto_download.py <campaign_id>`, but `main()` requires 3 arguments (`len(sys.argv) < 4`: `<campaign_id> <start_iso> <end_iso>`). Furthermore, `mda-server/app.py` does not invoke `mmu_auto_download.py` anywhere.

### 4. `[Open]` `/gas-types` endpoint missing & 1-second chunk boundary truncation
- **File**: [mmu_downloader_core.py](file:///home/luka/Code/EnvBike/mmu_downloader_core.py#L91-L170)
- **Issue**:
  - `get_species_list()` requests `GET /gas-types`, which does not exist in `mda-server/app.py`, so it always falls back to the hardcoded list.
  - `_fetch_all_chunked` advances `cur = chunk_end + datetime.timedelta(microseconds=1000)`, but `_fmt(dt)` formats timestamps at 1-second resolution (`%Y-%m-%dT%H:%M:%S`), dropping sub-second precision on chunk boundaries (partially mitigated by deduplicating `(datetime, type)`).

---

## `mda-server/` — Existing Items

### 5. `[Fixed]` `serialize` decorator returns HTTP `200 OK` on unhandled exceptions
- **File**: [mda-server/app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L56-L57)
- **Status**: Fixed — `except Exception as error:` in `serialize` now returns HTTP `500` (`{"error": str(error)}, 500`).

### 6. `[Fixed]` `POST /measurement/<type>` validation gaps
- **File**: [mda-server/app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L152-L166)
- **Status**: Fixed — `ACCEPT_MEASUREMENT_DATA` is enforced, unknown types return `415`, non-dict JSON bodies return `400`, and `(KeyError, ValueError, TypeError)` return `400`.

### 7. `[Open]` `Campaign.serialize()` references non-existent attributes
- **File**: [mda-server/models/campaign_model.py](file:///home/luka/Code/EnvBike/mda-server/models/campaign_model.py#L27-L33)
- **Issue**: `Campaign.serialize()` accesses `self.datetime`, `self.type`, `self.concentration`, and `self.unit` (copy-pasted from `GasMeasurement`), which do not exist on `Campaign` and raise `AttributeError` if called.

### 8. `[Fixed]` `POST /campaign` crash on empty `id` or invalid `start`
- **File**: [mda-server/app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L292-L295)
- **Status**: Fixed using `int(request.form.get('id') or 0)` and returning `400` when `ApiHelper.get_datetime_if_set(...)` returns `None`.
- **Minor residual**: A non-integer `id` string still raises `ValueError` (`500`).

### 9. `[Open]` Division by zero, empty-sequence crashes, and hardcoded personal path in stats
- **Files**: [mda-server/app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L642-L644), [mda-server/util/campaign_statistics.py](file:///home/luka/Code/EnvBike/mda-server/util/campaign_statistics.py#L16-L34), [mda-server/util/campaign_statistics.py](file:///home/luka/Code/EnvBike/mda-server/util/campaign_statistics.py#L71-L116)
- **Issue**:
  - `/stats` divides by `len(concentrations)` without checking for an empty list (`ZeroDivisionError`).
  - `get_campaign_statistics_for_gas()` calls `min()`/`max()` on `concentrations` without an empty-list guard (`ValueError`), and fails on live campaigns where `campaign.end` is `None` (`campaign_statistics.py#L16`).
  - `plot_baselines()` hardcodes `range(1, 11)` campaign IDs (crashes if fewer than 10 campaigns exist) and writes to a hardcoded personal path (`/home/christoph/Documents/.../background_vs_percentage_normalized.eps`), raising `FileNotFoundError` on any other machine.

### 10. `[Fixed]` `Interpolator` heading wrap-around & single-location finite check
- **File**: [mda-server/util/interplator.py](file:///home/luka/Code/EnvBike/mda-server/util/interplator.py#L22-L70)
- **Status**: Fixed — `Interpolator` handles empty/duplicate/single-location inputs, checks `np.isfinite()` in the `len(unique_locs) == 1` branch, and performs circular heading interpolation via `np.unwrap(np.deg2rad(...))`.

---

## `mda-server/` — New Bugs Found on `HAL`

### 15. `[Fixed]` Infinite `0ms` polling loop for Wind on finished campaigns
- **Files**: [mda-server/static/src/wind-measurement-plotter.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/wind-measurement-plotter.ts#L55-L68), [mda-server/static/src/measurement-plotter.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/measurement-plotter.ts#L39-L51)
- **Status**: Fixed (`bundle.js` rebuilt) — `WindMeasurementPlotter.plotData()` tracks `new_measurements` and throws `"No new data available."` when none were added, stopping polling on finished campaigns.

### 16. `[Fixed]` Race condition on initial gas selection in map view (`index.html` vs `index.ts`)
- **Files**: [mda-server/templates/index.html](file:///home/luka/Code/EnvBike/mda-server/templates/index.html#L229-L238), [mda-server/static/src/index.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/index.ts#L115-L164)
- **Status**: Fixed (`bundle.js` rebuilt) — `index.html` exposes `availableSpecies` and marks `active_list[0]` as selected server-side with `setActivePill(selector.value)`; `index.ts` reads `#gas-selector` directly on init without any `window.load` race.

### 17. `[Fixed]` Map polls all 14 species simultaneously & `FocusControl` crashes when `"NO"` has no data
- **Files**: [mda-server/static/src/index.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/index.ts#L115-L143), [mda-server/static/src/gas-measurement-plotter.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/gas-measurement-plotter.ts#L105-L113)
- **Status**: Fixed (`bundle.js` rebuilt) — `index.ts` only creates/polls plotters for `availableSpecies`, binds `FocusControl` to `active_plotter` (carrying focus state across species switches), and `GasMeasurementPlotter.setFocus()` guards `previous_measurement` and finite coordinates.

### 18. `[Fixed]` Slider popup dereferences `data` before null check (`gas-slider.ts`)
- **File**: [mda-server/static/src/gas-slider.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/gas-slider.ts#L48-L67)
- **Status**: Fixed (`bundle.js` rebuilt) — `updatePopup()` checks `if (!data) return;` before calling `data.concentration.toFixed(3)`.

### 19. `[Open]` 1st point skipped & 1-second batch-boundary truncation in `MeasurementPlotter`
- **File**: [mda-server/static/src/measurement-plotter.ts](file:///home/luka/Code/EnvBike/mda-server/static/src/measurement-plotter.ts#L71-L110)
- **Issue**: `plotData()` never calls `drawMeasurement()` for the first measurement (`previous_measurement === null`), and `formatToISODateTime()` truncates `start_datetime` to whole seconds (`YYYY-MM-DDTHH:MM:SS`), risking skipped or re-fetched rows at 2,000-row batch boundaries.

### 20. `[Fixed]` Dashboard `pollLive` null-dereference, stale values shown on `ERROR`, and unescaped `innerHTML`
- **Files**: [mda-server/templates/campaigns.html](file:///home/luka/Code/EnvBike/mda-server/templates/campaigns.html)
- **Status**: Fixed — `campaigns.html` escapes `devices.json` strings via `escapeHtml()`, checks `Number.isFinite(...)` before `.toFixed()`, and separates `active` from `showData` in `resolveStatus()` / `updateTelemetry()` so stale values are hidden during `ERROR:` / `Disconnected`.

### 21. `[Partially Fixed]` `live_cache` concurrency/multi-worker issues, commit ordering, and `server_started_at` clock-skew bug
- **Files**: [mda-server/app.py](file:///home/luka/Code/EnvBike/mda-server/app.py)
- **Status**:
  - **Fixed**: Added `live_cache_lock`, moved `_update_live_cache()` after `db.session.commit()`, and replaced `server_started_at` with `startup_max_ids` primary-key watermarks (immune to clock skew).
  - **Still Open**: In-process `live_cache` and `ACCEPT_MEASUREMENT_DATA` remain per-worker if run under multi-worker Gunicorn (`mdau_server.service` uses `--workers 2`).

### 22. `[Partially Fixed]` Backend reliability, memory, & mock script issues
- **Files**: [mda-server/app.py](file:///home/luka/Code/EnvBike/mda-server/app.py), [mda-server/tests/mock/measurement_mock.py](file:///home/luka/Code/EnvBike/mda-server/tests/mock/measurement_mock.py), [mda-server/tests/mock/location_measurement_mock.py](file:///home/luka/Code/EnvBike/mda-server/tests/mock/location_measurement_mock.py)
- **Status**:
  - **Fixed**: Replaced `.scalars().one()` with `.scalar()` + 404/redirect, passed `available_species` in `screenshot()`, sanitized non-finite floats (`allow_nan=False`) in `campaign_download()`, fixed CWD-relative `config.ini` and `mock_location_measurements.xml`, and added `timeout=5.0` + `RequestException` handling to `MeasurementMock`.
  - **Still Open**: `/campaign/<id>/download` buffers ORM rows and CSV/JSON in memory (OOM risk on huge campaigns), `/campaign/delete/<id>` and `/enable-measurements/<enable>` mutate state via `GET`, and `/campaign/start` allows multiple simultaneous active (`end=None`) campaigns.

---

## `mda-publishers/` — Existing Items

### 11. `[Fixed]` `GPS` DST caching & `__str__` typo
- **Files**: [mda-publishers/sensors/gps.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/gps.py), [mda-publishers/messages/location_measurement_message.py](file:///home/luka/Code/EnvBike/mda-publishers/messages/location_measurement_message.py#L46)
- **Status**: Fixed — `GPS` guards invalid/missing-fix `RMC` sentences, refreshes `_get_utc_offset()` per measurement, sets `timeout=1.0`, and `LocationMeasurementMessage.__str__()` prints `speed={self.speed}`.

### 12. `[Fixed]` `BasePublisher` HTTP timeout & status checking
- **File**: [mda-publishers/publishers/base_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/base_publisher.py)
- **Status**: Fixed — uses `timeout=5.0`, catches `requests.RequestException`, and logs a warning on non-2xx (`not resp.ok`).

### 13. `[Fixed]` `EnveaAnalyzer` Modbus reconnect on silent socket drop
- **File**: [mda-publishers/sensors/envea_analyzer.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/envea_analyzer.py)
- **Status**: Fixed — `_read_modbus()` closes and resets `self._modbus_client = None` on Modbus errors/exceptions so half-open sockets reconnect on the next cycle.

### 14. `[Partially Fixed]` Packaging, entrypoint wrapper, and systemd drift
- **Files**: [mda-publishers/publishers/main.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/main.py), [mda-publishers/requirements.txt](file:///home/luka/Code/EnvBike/mda-publishers/requirements.txt), [mda-publishers/mdau_pub.service](file:///home/luka/Code/EnvBike/mda-publishers/mdau_pub.service#L11)
- **Status**:
  - **Fixed**: `publishers/main.py` is a thin wrapper with parent `sys.path` insertion, and `pymodbus` is now listed in `requirements.txt`.
  - **Still Open**: `mdau_pub.service` still executes `publish.py` rather than `main.py`.

---

## `mda-publishers/` — New Bugs Found on `HAL`

### 23. `[Fixed]` `Logger.log()` collides with structured dashboard status logs and has no HTTP timeout
- **Files**: [mda-publishers/publishers/logger.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/logger.py)
- **Status**: Fixed — `Logger` appends `:log` suffix to `sensor_name` so debug logs never overwrite structured `live_cache["logs"]` entries, stamps `gps_time.now`, uses `timeout=5.0`, and catches `requests.RequestException`.

### 24. `[Partially Fixed]` Shutdown races prevent `shutdown()` and `"Disconnected"` logs from running
- **Files**: [mda-publishers/main.py](file:///home/luka/Code/EnvBike/mda-publishers/main.py), [mda-publishers/publishers/base_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/base_publisher.py), [mda-publishers/publishers/envea_gas_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/envea_gas_publisher.py), [mda-publishers/publishers/grimm_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/grimm_publisher.py), [mda-publishers/publishers/gas_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/gas_publisher.py), [mda-publishers/publishers/wind_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/wind_publisher.py), [mda-publishers/publishers/li7810_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/li7810_publisher.py), [mda-publishers/sensors/connection_strategy.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/connection_strategy.py), [mda-publishers/sensors/gps.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/gps.py)
- **Status**:
  - **Fixed**: Replaced `time.sleep` with `self._stopping.wait(...)` across publishers, added `timeout=1.0` to serial ports, wrapped `BasePublisher.run()` in `try/except/finally` so `shutdown()` and `"Disconnected"` run, added `stop_event` support in `ConnectionStrategy.connect()`, and added `loop_stop()` to `LI7810Publisher.shutdown()`.
  - **Still Open**: `GPS.connect()` / `UMB.connect()` retry loops still default to `retries=0` without passing `self._stopping`.

### 25. `[Partially Fixed]` Infinite CPU spin on TCP disconnect & missing mid-run reconnects
- **Files**: [mda-publishers/sensors/connection_strategy.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/connection_strategy.py), [mda-publishers/publishers/gps_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/gps_publisher.py), [mda-publishers/publishers/base_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/base_publisher.py)
- **Status**:
  - **Fixed**: `TcpConnectionStrategy.read()` raises `ConnectionError` on EOF (eliminating the 100% CPU spin) and `connect()` recreates sockets with `settimeout(5.0)`; `GpsPublisher` waits `1.0s` on error; `BasePublisher.run()` catches startup failures cleanly.
  - **Still Open**: Mid-run serial reconnect on USB unplug for `GPS`, `UMB`, and `Grimm11D`.

### 26. `[Partially Fixed]` `gps_time` uses wall-clock `time.time()` & mixes naive local / analyzer timestamps
- **Files**: [mda-publishers/publishers/gps_time.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/gps_time.py), [mda-publishers/sensors/picarro.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/picarro.py#L156)
- **Status**:
  - **Fixed**: `_GnssTime` uses `time.monotonic()` for elapsed-time extrapolation.
  - **Still Open**: Naive local timestamps vs Picarro analyzer clock without timezone awareness.

### 27. `[Fixed]` UMB wind driver error handling & protocol issues
- **Files**: [mda-publishers/sensors/umb.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/umb.py)
- **Status**: Fixed — `UMBError` subclasses `Exception`, `read_from_serial()` uses `time.monotonic()`, and `send_request()` flushes stale input bytes (`reset_input_buffer()`) before writing and validates `UMBStatus` (raising `UMBError` on non-zero status) before unpacking payload bytes.

### 28. `[Fixed]` `Grimm11D.read_measurements()` leaves `last_status` stale on silent scans
- **File**: [mda-publishers/sensors/grimm_11d.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/grimm_11d.py)
- **Status**: Fixed — sets `self.last_status = "Waiting for new data..."` when `_MAX_SCAN_LINES` finishes without a valid mass line if previously `"OK"`.
