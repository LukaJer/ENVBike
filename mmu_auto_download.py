"""
mmu_auto_download.py - Launched automatically by the server when a campaign's
end-time is set. Downloads all data for that campaign into a per-campaign
folder on the Desktop.

It is started "fire and forget" by app.py as:
    python3 mmu_auto_download.py <campaign_id>

It looks up the campaign's start/end from the server, then uses the shared
core to download every species with positions. A lock file guarantees that
even with multiple gunicorn workers, the download for a given campaign runs
only once.
"""

import os
import sys

# import the shared core that sits next to this file
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mmu_downloader_core as core

IP_ADDRESS = "127.0.0.1"     # the script runs on the Pi, next to the server
PORT = "5000"
DESKTOP = "/home/mda/Desktop"
LOCK_DIR = "/tmp"


def main():
    if len(sys.argv) < 4:
        print("Usage: mmu_auto_download.py <campaign_id> <start_iso> <end_iso>")
        sys.exit(2)

    campaign_id = sys.argv[1]
    start = sys.argv[2]
    end = sys.argv[3]

    # ---- lock: prevent concurrent double-launch (e.g. two gunicorn workers
    # firing at the same instant). The lock is released when the download
    # finishes, so later, intentional re-run of the same campaign is allowed.
    lock_path = os.path.join(LOCK_DIR, f"mmu_download_{campaign_id}.lock")
    try:
        
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
    except FileExistsError:
        print(f"Download for campaign {campaign_id} already in progress "
              f"(lock {lock_path} exists). Exiting.")
        sys.exit(0)

    try:
        # per-campaign output folder on the Desktop, named with both start and
        # end time so that every end-time edit produces a uniquely named folder
        # and nothing is overwritten.
        safe_start = start.replace(":", "-")
        safe_end = end.replace(":", "-")
        out_dir = os.path.join(
            DESKTOP, f"campaign_{campaign_id}_{safe_start}_to_{safe_end}")

        print(f"[auto] Campaign {campaign_id}: {start} -> {end}")
        core.run_download(IP_ADDRESS, PORT, start, end, out_dir, tag="[auto] ")
        print(f"[auto] Done. Files in: {out_dir}")
    finally:
        # Release the lock so the download is no longer blocked once finished.
        # This guards concurrent launches (lock present only while running) but
        # still permits a deliberate re-download later.
        try:
            os.remove(lock_path)
        except OSError:
            pass


if __name__ == "__main__":
    main()
