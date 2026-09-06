(function () {
  "use strict";

  const LENNIK = [50.826, 4.197]; // [lat, lon] -- default view, matches the real samples' area

  const map = L.map("map").setView(LENNIK, 15);
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
    clearIssues();
  });

  map.on(L.Draw.Event.EDITED, function () {
    previewLayer.clearLayers();
    setExportEnabled(false);
    clearIssues();
  });

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

  function clearIssues() {
    const box = document.getElementById("issues");
    box.hidden = true;
    box.innerHTML = "";
  }

  function showIssues(issues, extraError) {
    const box = document.getElementById("issues");
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
      div.textContent = (issue.severity === "ERROR" ? "Fout: " : "Waarschuwing: ") + issue.message;
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

  function drawPreview(waypoints) {
    previewLayer.clearLayers();
    if (!waypoints || waypoints.length === 0) return;

    const latlngs = waypoints.map((p) => [p[1], p[0]]);
    L.polyline(latlngs, { color: "#2f6b4f", weight: 2 }).addTo(previewLayer);
    latlngs.forEach((ll, i) => {
      const isEndpoint = i === 0 || i === latlngs.length - 1;
      L.circleMarker(ll, {
        radius: isEndpoint ? 5 : 3,
        color: isEndpoint ? "#b3261e" : "#2f6b4f",
        fillColor: isEndpoint ? "#b3261e" : "#2f6b4f",
        fillOpacity: 1,
      }).addTo(previewLayer);
    });
  }

  async function preview() {
    const polygon = currentPolygon();
    if (!polygon) {
      showIssues([], "Teken eerst een gebied op de kaart met de polygoon-tool.");
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
      showIssues([], "Kon geen verbinding maken met de server.");
      return;
    }

    if (!response.ok) {
      showIssues(data.issues, data.error || "Onbekende fout bij het berekenen van de missie.");
      setExportEnabled(false);
      return;
    }

    drawPreview(data.waypoints);
    updateStats(data, document.getElementById("mission-name").value);
    showIssues(data.issues, null);
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
      showIssues([], "Kon geen verbinding maken met de server.");
      return;
    }

    if (!response.ok) {
      const data = await response.json();
      showIssues(data.issues, data.error || "Export mislukt.");
      return;
    }

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

  document.getElementById("btn-preview").addEventListener("click", preview);
  document.getElementById("btn-export").addEventListener("click", exportMission);
})();
