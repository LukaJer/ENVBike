# TODO

- [ ] **Device Configuration & Service Control from UI**
  - Edit `devices.json` settings directly from the web UI (enable/disable devices, ports/IPs, intervals, stale/offline thresholds).
  - Add controls to restart the publisher and server processes from the UI (or embed a web terminal in the UI).

- [ ] **High Concentration Alerts & Peak/Hotspot Markers**
  - Add a dedicated Alerts/Thresholds tab in the UI.
  - Configure threshold limits for each measured species/value, with a per-species enable/disable toggle.
  - Configure trigger duration or consecutive measurement count before an alert fires.
  - Flash the instrument card/box (or whole UI) when an alert is active, and display the alert on the map view as well.
  - Show peak/hotspot and threshold-exceedance markers for the selected species on `/map/<id>` with a "Jump to Peak" button.

- [x] **Auto-Fit Map to Finished Campaign Route**
  - When viewing a finished campaign on `/map/<id>`, automatically fit the map bounds (`map.fitBounds(...)`) to the recorded route instead of centering on the default coordinates.

- [x] **Map Layer Caching Settings**
  - Add settings to configure which map layers (e.g. `OSM`, `Local`, `LocalG`) and zoom/bounding-box regions are cached locally for offline use.

- [ ] **Campaign Start & Map Readiness Warnings**
  - Show warnings on the map view and when starting a campaign if any enabled instruments or GPS are not ready yet (e.g., disconnected, warming up, reference zero, or no GPS fix).

- [ ] **Real-Time Push Updates (SSE)**
  - Replace `/api/live` polling in `campaigns.html` (and optionally map live updates) with Server-Sent Events (`EventSource`) pushed immediately when `POST /measurement/<type>` receives new data.

