
"""
data_downloader_v3.py - MANUAL backup downloader for the Mobile Measurement Unit.

Use this if the automatic download (triggered when a campaign end-time is set)
did not run, or to re-download a time window by hand. It uses the same
download logic as the automatic path:
   downloads every species (new pollutants + legacy gases)
   fetches ALL data dynamically via pagination (no manual splitting)
   attaches a GPS position to every measurement 
   writes one JSON file per species

HOW TO USE

1. Open terminal:        cd ~/Desktop
2. Edit START_TIME / END_TIME below to your campaign window.
3. Run:                     python3 data_downloader_v3.py

Files are written into a folder on the Desktop named after the time window.
This script requires mmu_downloader_core.py to be in the same folder (Desktop).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mmu_downloader_core as core


# CONFIGURATION  --  adjust these

START_TIME = "2026-06-30T11:21:00"
END_TIME   = "2026-06-30T14:27:00"

# Leave SPECIES = None to download every species the server reports
SPECIES = None

# Connection. When running on the Pi itself, 127.0.0.1 works. From another
# machine on the WebApp network, use the Pi's address (e.g. 192.168.0.101).
IP_ADDRESS = "127.0.0.1"
PORT = "5000"

# Where to put the files
DESKTOP = "/home/mda/Desktop"


def main():
    safe_start = START_TIME.replace(":", "-")
    out_dir = os.path.join(DESKTOP, f"manual_download_{safe_start}")
    core.run_download(IP_ADDRESS, PORT, START_TIME, END_TIME, out_dir,
                      species=SPECIES, tag="")
    print(f"\nFiles written to: {out_dir}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted by user.")
        sys.exit(1)
