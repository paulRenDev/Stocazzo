# Vendored third-party libraries

Vendored (not loaded from a CDN) so the app works without any external
JS/CSS dependency at load time — only the map tile images themselves
need internet access.

- **Leaflet** 1.9.4 — BSD-2-Clause — https://leafletjs.com
- **Leaflet.draw** 1.0.4 — MIT — https://github.com/Leaflet/Leaflet.draw

Fetched via `npm install leaflet@1.9.4 leaflet-draw@1.0.4` and copied
from each package's `dist/` folder. To update, repeat with a newer
version and re-copy `leaflet.js`/`leaflet.css`/`leaflet.draw.js`/
`leaflet.draw.css` and their `images/` folders.
