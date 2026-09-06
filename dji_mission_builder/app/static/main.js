(function () {
  "use strict";

  const DEFAULT_VIEW = [50.826, 4.197]; // [lat, lon] -- default map center

  const map = L.map("map").setView(DEFAULT_VIEW, 15);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  const drawnItems = new L.FeatureGroup();
  map.addLayer(drawnItems);

  const previewLayer = new L.FeatureGroup();
  map.addLayer(previewLayer);

  const drawControl = new L.Control.Draw({
    draw: {
      polygon: { allowIntersection: false, showArea: true },
      marker: false,
      polyline: false,
      circle: false,
      circlemarker: false,
      rectangle: false,
    },
    edit: { featureGroup: drawnItems },
  });
  map.addControl(drawControl);

  map.on(L.Draw.Event.CREATED, function (event) {
    drawnItems.clearLayers();
    previewLayer.clearLayers();
    drawnItems.addLayer(event.layer);
    setExportEnabled(false);
    clearIssues("issues");
  });

  map.on(L.Draw.Event.EDITED, function () {
    previewLayer.clearLayers();
    setExportEnabled(false);
    clearIssues("issues");
  });

  // ---- Tabs ----------------------------------------------------------

  function activateTab(tab) {
    const isCreate = tab === "create";
    document.getElementById("tab-create").classList.toggle("active", isCreate);
    document.getElementById("tab-import").classList.toggle("active", !isCreate);
    document.getElementById("section-create").hidden = !isCreate;
    document.getElementById("section-import").hidden = isCreate;
    document.getElementById("stats").hidden = !isCreate;
    document.getElementById("import-stats").hidden = isCreate;
    drawnItems.clearLayers();
    previewLayer.clearLayers();
  }

  document.getElementById("tab-create").addEventListener("click", () => activateTab("create"));
  document.getElementById("tab-import").addEventListener("click", () => activateTab("import"));

  // ---- Shared helpers --------------------------------------------------

  function currentPolygon() {
    const layers = drawnItems.getLayers();
    if (layers.length === 0) return null;
    const latlngs = layers[0].getLatLngs()[0];
    return latlngs.map((p) => [p.lng, p.lat]);
  }

  function currentParams() {
    return {
      altitude_m: parseFloat(document.getElementById("altitude").value),
      front_overlap: parseFloat(document.getElementById("front-overlap").value) / 100,
      side_overlap: parseFloat(document.getElementById("side-overlap").value) / 100,
      direction_deg: parseFloat(document.getElementById("direction").value),
      speed_ms: parseFloat(document.getElementById("speed").value),
      gimbal_pitch_deg: parseFloat(document.getElementById("gimbal-pitch").value),
    };
  }

  function clearIssues(boxId) {
    const box = document.getElementById(boxId);
    box.hidden = true;
    box.innerHTML = "";
  }

  function showIssues(boxId, issues, extraError) {
    const box = document.getElementById(boxId);
    box.innerHTML = "";
    let any = false;
    if (extraError) {
      any = true;
      const div = document.createElement("div");
      div.className = "issue-error";
      div.textContent = extraError;
      box.appendChild(div);
    }
    (issues || []).forEach((issue) => {
      any = true;
      const div = document.createElement("div");
      div.className = issue.severity === "ERROR" ? "issue-error" : "issue-warning";
      div.textContent = (issue.severity === "ERROR" ? "Error: " : "Warning: ") + issue.message;
      box.appendChild(div);
    });
    box.hidden = !any;
  }

  function setExportEnabled(enabled) {
    document.getElementById("btn-export").disabled = !enabled;
  }

  function formatDuration(seconds) {
    const s = Math.round(seconds);
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return `${m}:${String(rem).padStart(2, "0")}`;
  }

  function drawRoute(waypoints, color) {
    previewLayer.clearLayers();
    if (!waypoints || waypoints.length === 0) return;

    const latlngs = waypoints.map((p) => [p[1], p[0]]);
    L.polyline(latlngs, { color, weight: 2 }).addTo(previewLayer);
    latlngs.forEach((ll, i) => {
      const isEndpoint = i === 0 || i === latlngs.length - 1;
      L.circleMarker(ll, {
        radius: isEndpoint ? 5 : 3,
        color: isEndpoint ? "#b3261e" : color,
        fillColor: isEndpoint ? "#b3261e" : color,
        fillOpacity: 1,
      }).addTo(previewLayer);
    });
    map.fitBounds(L.polyline(latlngs).getBounds(), { padding: [30, 30] });
  }

  async function downloadResponse(response) {
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^";]+)"?/);
    const filename = match ? match[1] : "mission.kmz";

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  // ---- New Mapping Mission tab ------------------------------------------

  function updateStats(data, name) {
    document.getElementById("stat-name").textContent = name || "—";
    document.getElementById("stat-altitude").textContent = document.getElementById("altitude").value + " m";
    document.getElementById("stat-front").textContent = document.getElementById("front-overlap").value + "%";
    document.getElementById("stat-side").textContent = document.getElementById("side-overlap").value + "%";
    document.getElementById("stat-waypoints").textContent = data.waypoint_count;
    document.getElementById("stat-distance").textContent = (data.distance_m / 1000).toFixed(2) + " km";
    document.getElementById("stat-photos").textContent = data.photo_count;
    document.getElementById("stat-time").textContent = formatDuration(data.estimated_seconds);
  }

  async function preview() {
    const polygon = currentPolygon();
    if (!polygon) {
      showIssues("issues", [], "Draw an area on the map first using the polygon tool.");
      return;
    }
    const payload = Object.assign({ polygon }, currentParams());

    let response, data;
    try {
      response = await fetch("/api/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      data = await response.json();
    } catch (err) {
      showIssues("issues", [], "Could not connect to the server.");
      return;
    }

    if (!response.ok) {
      showIssues("issues", data.issues, data.error || "Unknown error while computing the mission.");
      setExportEnabled(false);
      return;
    }

    drawRoute(data.waypoints, "#2f6b4f");
    updateStats(data, document.getElementById("mission-name").value);
    showIssues("issues", data.issues, null);
    setExportEnabled(!data.has_errors);
  }

  async function exportMission() {
    const polygon = currentPolygon();
    if (!polygon) return;
    const payload = Object.assign(
      { polygon, name: document.getElementById("mission-name").value },
      currentParams()
    );

    let response;
    try {
      response = await fetch("/api/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch (err) {
      showIssues("issues", [], "Could not connect to the server.");
      return;
    }

    if (!response.ok) {
      const data = await response.json();
      showIssues("issues", data.issues, data.error || "Export failed.");
      return;
    }

    await downloadResponse(response);
  }

  document.getElementById("btn-preview").addEventListener("click", preview);
  document.getElementById("btn-export").addEventListener("click", exportMission);

  // ---- Import Existing Mission tab --------------------------------------

  function formatRange(range, unit) {
    if (!range) return "—";
    return range.uniform
      ? `${range.min} ${unit}`
      : `${range.min}–${range.max} ${unit} (varies)`;
  }

  function updateImportStats(data) {
    document.getElementById("import-stat-source").textContent = data.source_filename || "—";
    const drone = data.mission_config;
    document.getElementById("import-stat-drone").textContent = drone
      ? `enum ${drone.drone_enum_value}/${drone.drone_sub_enum_value}`
      : "—";
    document.getElementById("import-stat-waypoints").textContent = data.waypoint_count;
    document.getElementById("import-stat-altitude").textContent = formatRange(data.altitude_m, "m");
    document.getElementById("import-stat-speed").textContent = formatRange(data.speed_ms, "m/s");
    document.getElementById("import-stat-finish").textContent = drone ? drone.finish_action : "—";
    document.getElementById("import-stat-distance").textContent = (data.distance_m / 1000).toFixed(2) + " km";
    document.getElementById("import-stat-photos").textContent = data.photo_count;
    document.getElementById("import-stat-time").textContent = formatDuration(data.estimated_seconds);
  }

  async function analyzeImport() {
    const fileInput = document.getElementById("import-file");
    const file = fileInput.files[0];
    if (!file) {
      showIssues("import-issues", [], "Choose a .kmz file first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    let response, data;
    try {
      response = await fetch("/api/import", { method: "POST", body: formData });
      data = await response.json();
    } catch (err) {
      showIssues("import-issues", [], "Could not connect to the server.");
      return;
    }

    if (!response.ok) {
      showIssues("import-issues", data.issues, data.error || "Could not analyze this file.");
      document.getElementById("btn-import-export").disabled = true;
      document.getElementById("import-edit-fields").hidden = true;
      return;
    }

    drawRoute(data.waypoints, "#3b6ea5");
    updateImportStats(data);
    showIssues("import-issues", data.issues, null);
    document.getElementById("import-edit-fields").hidden = false;
    document.getElementById("btn-import-export").disabled = data.has_errors;
  }

  async function exportImportedMission() {
    const fileInput = document.getElementById("import-file");
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("name", document.getElementById("import-name").value);
    formData.append("mission_type", document.getElementById("import-mission-type").value);
    const altitude = document.getElementById("import-altitude").value;
    const speed = document.getElementById("import-speed").value;
    if (altitude) formData.append("altitude_m", altitude);
    if (speed) formData.append("speed_ms", speed);

    let response;
    try {
      response = await fetch("/api/import/export", { method: "POST", body: formData });
    } catch (err) {
      showIssues("import-issues", [], "Could not connect to the server.");
      return;
    }

    if (!response.ok) {
      const data = await response.json();
      showIssues("import-issues", data.issues, data.error || "Export failed.");
      return;
    }

    await downloadResponse(response);
  }

  document.getElementById("btn-analyze").addEventListener("click", analyzeImport);
  document.getElementById("btn-import-export").addEventListener("click", exportImportedMission);
})();
