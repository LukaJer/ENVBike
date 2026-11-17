# Code Review & Known Bugs (`bugs.md`)

This document lists verified bugs and reliability issues found during a code review of `mda-server/`, `mda-publishers/`, and the root utility scripts.

---

## Root Scripts

### 1. Typo in `requests` exception class (`AttributeError`)
- **Files**: [data_downloader.py](file:///home/luka/Code/EnvBike/data_downloader.py#L47), [data_downloader_V2.py](file:///home/luka/Code/EnvBike/data_downloader_V2.py#L67)
- **Issue**: Both scripts catch `requests.exception.RequestException` instead of `requests.exceptions.RequestException`. If any HTTP/network error occurs, Python raises `AttributeError` instead of handling the error.

### 2. Undefined variables & broken pagination loop in `data_downloader_V2.py`
- **File**: [data_downloader_V2.py](file:///home/luka/Code/EnvBike/data_downloader_V2.py#L60-L61)
- **Issue**: `offset += limit` references undefined local variables `offset` and `limit` (they only exist as string keys in `query_params`), raising `NameError` on the first iteration. Additionally, `query_params["offset"]` is never updated in the loop.

### 3. `mmu_auto_download.py` CLI mismatch & unused server hook
- **File**: [mmu_auto_download.py](file:///home/luka/Code/EnvBike/mmu_auto_download.py#L6-L35)
- **Issue**: The docstring states `app.py` launches it as `python3 mmu_auto_download.py <campaign_id>`, but `main()` requires 3 arguments (`len(sys.argv) < 4`: `<campaign_id> <start_iso> <end_iso>`). Furthermore, [mda-server/app.py](file:///home/luka/Code/EnvBike/mda-server/app.py) does not invoke `mmu_auto_download.py` anywhere.

### 4. `/gas-types` endpoint missing & 1-second chunk boundary truncation
- **File**: [mmu_downloader_core.py](file:///home/luka/Code/EnvBike/mmu_downloader_core.py#L91-L170)
- **Issue**:
  - `get_species_list()` requests `GET /gas-types`, which does not exist in `mda-server/app.py`, so it always falls back to the hardcoded list.
  - `_fetch_all_chunked` advances `cur = chunk_end + datetime.timedelta(microseconds=1000)`, but `_fmt(dt)` formats timestamps at 1-second resolution (`%Y-%m-%dT%H:%M:%S`), dropping sub-second precision on chunk boundaries (partially mitigated by deduplicating `(datetime, type)`).

---

## `mda-server/`

### 5. `serialize` decorator returns HTTP `200 OK` on unhandled exceptions
- **File**: [mda-server/app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L50-L51)
- **Issue**: `except Exception as error: return {"error": str(error)}` omits a status code, so Flask returns `200 OK` with an error JSON object instead of `500` or `400`.

### 6. `POST /measurement/<type>` ignores `ACCEPT_MEASUREMENT_DATA` and misses validation errors
- **File**: [mda-server/app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L73-L84), [mda-server/app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L243-L249)
- **Issue**:
  - `/enable-measurements/<int:enable>` toggles `app.config["ACCEPT_MEASUREMENT_DATA"]`, but `post_measurement()` never checks this flag.
  - `post_measurement()` only catches `KeyError`, so malformed ISO timestamps or non-numeric values (`ValueError`, `TypeError`) cause unhandled `500` errors.

### 7. `Campaign.serialize()` references non-existent attributes
- **File**: [mda-server/models/campaign_model.py](file:///home/luka/Code/EnvBike/mda-server/models/campaign_model.py#L27-L33)
- **Issue**: `Campaign.serialize()` accesses `self.datetime`, `self.type`, `self.concentration`, and `self.unit` (copy-pasted from `GasMeasurement`), which do not exist on `Campaign` and raise `AttributeError` if called.

### 8. `POST /campaign` crashes on empty `id` or invalid `start`
- **File**: [mda-server/app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L164-L165)
- **Issue**: `int(request.form.get('id', 0))` raises `ValueError` if `id` is submitted as an empty string `""`.

### 9. Division by zero, empty-sequence crashes, and hardcoded personal path in stats
- **Files**: [mda-server/app.py](file:///home/luka/Code/EnvBike/mda-server/app.py#L266-L268), [mda-server/util/campaign_statistics.py](file:///home/luka/Code/EnvBike/mda-server/util/campaign_statistics.py#L26-L34), [mda-server/util/campaign_statistics.py](file:///home/luka/Code/EnvBike/mda-server/util/campaign_statistics.py#L71-L116)
- **Issue**:
  - `/stats` divides by `len(concentrations)` without checking for an empty list (`ZeroDivisionError`).
  - `get_campaign_statistics_for_gas()` calls `min()`/`max()` on `concentrations` without an empty-list guard (`ValueError`).
  - `plot_baselines()` hardcodes `range(1, 11)` campaign IDs (crashes if fewer than 10 campaigns exist) and writes to a hardcoded personal path (`/home/christoph/Documents/.../background_vs_percentage_normalized.eps`), which raises `FileNotFoundError` on any other machine.

### 10. `Interpolator` crashes on `< 2` locations and wraps heading angles incorrectly
- **File**: [mda-server/util/interplator.py](file:///home/luka/Code/EnvBike/mda-server/util/interplator.py#L30-L54)
- **Issue**:
  - If `locations` is empty, `_measurement_is_within_interpolation_region()` raises `ValueError: zero-size array` on `time_distances.min()`. If `len(locations) == 1`, `scipy.interpolate.interp1d` raises `ValueError` (requires at least 2 points).
  - `interpolate_heading` linearly interpolates degrees (`0..360`), causing wrap-around artifacts across `359° -> 1°` (interpolating through `180°` instead of `0°`).

---

## `mda-publishers/`

### 11. `GPS` crashes when there is no satellite fix (`RMC` with `None` fields)
- **Files**: [mda-publishers/sensors/gps.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/gps.py#L34-L40), [mda-publishers/messages/location_measurement_message.py](file:///home/luka/Code/EnvBike/mda-publishers/messages/location_measurement_message.py#L27-L46)
- **Issue**:
  - `get_location_measurement()` does not check `msg.is_valid` / `msg.status == 'A'` or `rmc.datestamp is None` / `rmc.timestamp is None` before calling `datetime.combine(rmc.datestamp, rmc.timestamp)`, raising `TypeError` when the GPS has no fix.
  - `GPS._utc_offset` is cached once in `__init__` and never updated across DST transitions.
  - `LocationMeasurementMessage.__str__()` prints `speed={self.heading}` instead of `speed={self.speed}`.

### 12. `BasePublisher._try_post_measurement_to_server` has no HTTP timeout and ignores non-`ConnectionError` failures
- **File**: [mda-publishers/publishers/base_publisher.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/base_publisher.py#L42-L46)
- **Issue**: `requests.post(...)` is called without a `timeout`, so a stalled server can block the publisher thread indefinitely. It also only catches `requests.ConnectionError` (missing `requests.Timeout` / `RequestException`) and never checks `response.ok` / `status_code`.

### 13. `EnveaAnalyzer` does not reconnect on Modbus/TCP drop
- **File**: [mda-publishers/sensors/envea_analyzer.py](file:///home/luka/Code/EnvBike/mda-publishers/sensors/envea_analyzer.py#L98-L118)
- **Issue**: `_modbus_client` is only initialized in `connect()`. If a Modbus/TCP connection drops mid-run, `_read_modbus()` logs the error every cycle without attempting to reconnect.

### 14. Packaging, config duplication, and systemd drift
- **Files**: [mda-publishers/main.py](file:///home/luka/Code/EnvBike/mda-publishers/main.py), [mda-publishers/publishers/main.py](file:///home/luka/Code/EnvBike/mda-publishers/publishers/main.py), [mda-publishers/requirements.txt](file:///home/luka/Code/EnvBike/mda-publishers/requirements.txt), [mda-publishers/mdau_pub.service](file:///home/luka/Code/EnvBike/mda-publishers/mdau_pub.service)
- **Issue**:
  - `main.py` and `publishers/main.py` are nearly identical copies with different hardcoded serial ports (`GPS_PORT` / `WIND_PORT`).
  - `pymodbus` is required by `EnveaAnalyzer` (`mode="modbus"`) but is missing from `requirements.txt`.
  - `mdau_pub.service` still points `ExecStart` to `publish.py` rather than `main.py`.
