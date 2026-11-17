
"""


module is used by BOTH:
   the automatic download (triggered by app.py when a campaign end-time is set)
   the manual backup script (data_downloader_v3.py)

downloads, for a given time window, EVERY gas species the unit knows about
(new pollutants AND legacy gases), reliably attaches a GPS position to each
measurement, and writes one JSON file per species.

Getting data without 5000-row ceiling)

The server caps a single response at ~5000 rows, and on the interpolating read
path it does not reliably honour an 'offset', so plain offset-paging stops after
the first page. To get the COMPLETE data set regardless of size, this module does
NOT depend on offset paging. Instead it splits the requested time window into
consecutive sub-windows (chunks) and downloads each separately, then concatenates
them. If any single chunk still hits the row cap, it is split in half and retried,
so the method adapts automatically to high data rates. This scales to tens of
thousands of rows without any fixed limit.

Gas Values and position

Gas values and location fixes are downloaded separately for the same window and
merged locally by timestamp: each gas measurement gets the nearest location fix
within a maximum time tolerance. 

The file is importable and also runnable directly.
"""

import bisect
import datetime
import json
import os
import sys
import requests



ROW_CAP = 5000

INITIAL_CHUNK = datetime.timedelta(minutes=15)
# do not subdivide chunks shorter than this (safety floor against infinite split)
MIN_CHUNK = datetime.timedelta(seconds=10)
# gas measurement matched to the nearest location within this many seconds
MAX_MATCH_SECONDS = 15
# Network timeout per request.
HTTP_TIMEOUT = 60


def _base(ip, port):
    return f"http://{ip}:{port}"


# datetime helpers

ISO_OUT = "%Y-%m-%dT%H:%M:%S"

def _parse_dt(s):
    """Parse server datetime strings and ISO inputs. Returns datetime or None."""
    if s is None:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return datetime.datetime.fromisoformat(s)
    except ValueError:
        return None


def _fmt(dt):
    """Format a datetime for a request (second resolution, ISO 'T' form)."""
    return dt.strftime(ISO_OUT)


# species list 

def get_species_list(ip, port, explicit=None, timeout=10):
    """Species to download: explicit list if given, else ask /gas-types,
    else a built-in new+legacy fallback."""
    if explicit:
        return list(explicit)
    try:
        r = requests.get(f"{_base(ip, port)}/gas-types", timeout=timeout)
        r.raise_for_status()
        types = r.json()
        if isinstance(types, dict) and types:
            return list(types.keys())
        if isinstance(types, list) and types:
            return list(types)
    except requests.exceptions.RequestException as e:
        print(f"  (could not reach /gas-types: {e}; using built-in fallback list)")
    return ["NO", "NO2", "NOx", "O3", "CO", "PM10", "PM4", "PM2.5", "PM1",
            "CH4", "CH4-LI", "CO2", "CO2-LI", "H2O"]


# low-level single-window fetch

def _fetch_window(url, params_base, start_dt, end_dt):
    """Fetch one [start, end] window in a single request. Returns the list of
    rows (possibly empty). Raises requests exceptions on transport errors."""
    params = dict(params_base)
    params["start"] = _fmt(start_dt)
    params["end"] = _fmt(end_dt)
    params["limit"] = str(ROW_CAP)
    resp = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
    if resp.status_code == 412:        # "No measurements available"
        return []
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        if "error" in data:
            return []
        data = data.get("results", [])
    return data if isinstance(data, list) else []


def _fetch_window_complete(url, params_base, start_dt, end_dt, depth=0):
    """Fetch a window completely, subdividing if the row cap is hit.

    If a single request returns ROW_CAP rows, we assume it was truncated and
    split the window in half, recursing into each half. This guarantees we never
    silently lose rows beyond the cap, and it adapts to the local data rate.
    """
    rows = _fetch_window(url, params_base, start_dt, end_dt)

    if len(rows) < ROW_CAP:
        return rows                   

    
    span = end_dt - start_dt
    if span <= MIN_CHUNK:
        
        print(f"      warning: row cap hit on a {span} window that cannot be "
              f"split further; some rows in this slice may be missing.")
        return rows

    mid = start_dt + span / 2
    
    left = _fetch_window_complete(url, params_base, start_dt, mid, depth + 1)
    right = _fetch_window_complete(
        url, params_base, mid + datetime.timedelta(microseconds=1000), end_dt, depth + 1)
    return left + right


def _fetch_all_chunked(url, params_base, start_dt, end_dt):
    """Fetch the whole [start, end] range by walking it in INITIAL_CHUNK steps,
    fetching each chunk completely, and de-duplicating by datetime.
    Returns rows sorted by datetime."""
    seen = set()
    out = []
    cur = start_dt
    while cur < end_dt:
        chunk_end = min(cur + INITIAL_CHUNK, end_dt)
        rows = _fetch_window_complete(url, params_base, cur, chunk_end)
        for r in rows:
            
            key = (r.get("datetime"), r.get("type"))
            if key not in seen:
                seen.add(key)
                out.append(r)
        cur = chunk_end + datetime.timedelta(microseconds=1000)
    out.sort(key=lambda r: r.get("datetime") or "")
    return out


# locations + merge

def fetch_locations(ip, port, start, end):
    """Download all location fixes in the window (chunked), sorted by time.
    Returns (times_list, loc_list) with times_list sorted."""
    url = f"{_base(ip, port)}/measurement/location"
    start_dt, end_dt = _parse_dt(start), _parse_dt(end)
    raw = _fetch_all_chunked(url, {}, start_dt, end_dt)
    pairs = []
    for loc in raw:
        t = _parse_dt(loc.get("datetime"))
        if t is not None:
            pairs.append((t, loc))
    pairs.sort(key=lambda p: p[0])
    return [p[0] for p in pairs], [p[1] for p in pairs]


def _nearest_location(t, times, locs):
    """Nearest location dict to time t within MAX_MATCH_SECONDS, else None."""
    if not times or t is None:
        return None
    i = bisect.bisect_left(times, t)
    best, best_dt = None, None
    for j in (i - 1, i):
        if 0 <= j < len(times):
            delta = abs((times[j] - t).total_seconds())
            if best_dt is None or delta < best_dt:
                best_dt, best = delta, locs[j]
    if best is not None and best_dt is not None and best_dt <= MAX_MATCH_SECONDS:
        return best
    return None


def fetch_gas(ip, port, species, start, end):
    """Download all gas rows for one species over the whole window (chunked)."""
    url = f"{_base(ip, port)}/measurement/gas"
    start_dt, end_dt = _parse_dt(start), _parse_dt(end)
    return _fetch_all_chunked(url, {"type": species}, start_dt, end_dt)


def merge_positions(gas_rows, times, locs):
    """Attach latitude/longitude from the nearest location fix. Rows without a
    location inside the tolerance are kept with null position (no data dropped)."""
    merged, matched = [], 0
    for row in gas_rows:
        t = _parse_dt(row.get("datetime"))
        loc = _nearest_location(t, times, locs)
        out = dict(row)
        if loc is not None:
            out["latitude"] = loc.get("latitude")
            out["longitude"] = loc.get("longitude")
            matched += 1
        else:
            out["latitude"] = None
            out["longitude"] = None
        merged.append(out)
    return merged, matched


def safe_filename(species, start_time):
    safe_species = species.replace("/", "-").replace(" ", "_")
    safe_date = start_time.replace(":", "-")
    return f"mmu_{safe_species}_{safe_date}.json"


# main entry point

def run_download(ip, port, start, end, out_dir, species=None, tag=""):
    """Download all species over [start, end] into out_dir (one JSON per species).
    Returns a summary list of (species, count, matched)."""
    os.makedirs(out_dir, exist_ok=True)

    species_list = get_species_list(ip, port, species)
    print(f"{tag}Downloading {len(species_list)} species from {start} to {end}")
    print(f"{tag}Output dir: {out_dir}")
    print(f"{tag}Species: {', '.join(species_list)}")

    try:
        times, locs = fetch_locations(ip, port, start, end)
        print(f"{tag}Loaded {len(times)} location fixes for matching.")
    except requests.exceptions.RequestException as e:
        print(f"{tag}WARNING: could not load locations ({e}); "
              f"files will have null positions.")
        times, locs = [], []

    summary = []
    for sp in species_list:
        try:
            gas_rows = fetch_gas(ip, port, sp, start, end)
        except requests.exceptions.RequestException as e:
            print(f"{tag}  {sp}: download failed: {e}")
            summary.append((sp, "ERROR", 0))
            continue

        if not gas_rows:
            print(f"{tag}  {sp}: no data in window (skipped).")
            summary.append((sp, 0, 0))
            continue

        merged, matched = merge_positions(gas_rows, times, locs)
        fname = os.path.join(out_dir, safe_filename(sp, start))
        try:
            with open(fname, "w") as f:
                json.dump(merged, f, indent=1)
        except OSError as e:
            print(f"{tag}  {sp}: could not write file: {e}")
            summary.append((sp, "WRITE-ERROR", 0))
            continue

        print(f"{tag}  {sp}: saved {len(merged)} rows "
              f"({matched} with position) -> {os.path.basename(fname)}")
        summary.append((sp, len(merged), matched))

    print(f"{tag}==================== SUMMARY ====================")
    for sp, count, matched in summary:
        if isinstance(count, int):
            print(f"{tag}  {sp:8} : {count} rows, {matched} positioned")
        else:
            print(f"{tag}  {sp:8} : {count}")
    print(f"{tag}================================================")
    return summary


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: mmu_downloader_core.py <start_iso> <end_iso> <out_dir> [ip] [port]")
        sys.exit(2)
    a_start, a_end, a_out = sys.argv[1], sys.argv[2], sys.argv[3]
    a_ip = sys.argv[4] if len(sys.argv) > 4 else "127.0.0.1"
    a_port = sys.argv[5] if len(sys.argv) > 5 else "5000"
    run_download(a_ip, a_port, a_start, a_end, a_out)
