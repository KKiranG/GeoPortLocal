"use strict";

const $ = (id) => document.getElementById(id);
const TILE_SIZE = 256;
const MAX_MERCATOR_LAT = 85.05112878;

const ui = {
  message: $("message"),
  stateDot: $("state-dot"),
  stateLabel: $("state-label"),
  deviceSelect: $("device-select"),
  deviceDetail: $("device-detail"),
  refreshDevices: $("refresh-devices"),
  connectDevice: $("connect-device"),
  disconnectDevice: $("disconnect-device"),
  latitude: $("latitude"),
  longitude: $("longitude"),
  activeLocation: $("active-location"),
  setLocation: $("set-location"),
  clearLocation: $("clear-location"),
  fuelRegion: $("fuel-region"),
  fuelType: $("fuel-type"),
  fuelQuote: $("fuel-quote"),
  fuelFreshness: $("fuel-freshness"),
  map: $("map"),
  mapTiles: $("map-tiles"),
  mapMarker: $("map-marker"),
  mapZoomIn: $("map-zoom-in"),
  mapZoomOut: $("map-zoom-out"),
  mapFallback: $("map-fallback"),
};

const state = {
  snapshot: { state: "disconnected", device: null, location: null, last_error: null },
  devices: [],
  pollTimer: null,
  operationInFlight: false,
  map: {
    centerLat: -33.8688,
    centerLon: 151.2093,
    zoom: 11,
    markerLat: -33.8688,
    markerLon: 151.2093,
  },
};

class ApiError extends Error {
  constructor(message, code = "REQUEST_FAILED", retryable = false) {
    super(message);
    this.code = code;
    this.retryable = retryable;
  }
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch (_) {
    payload = null;
  }

  if (!response.ok) {
    const error = payload && payload.error;
    throw new ApiError(
      error && error.message ? error.message : `Request failed with HTTP ${response.status}.`,
      error && error.code ? error.code : "REQUEST_FAILED",
      Boolean(error && error.retryable),
    );
  }
  return payload;
}

function humanState(value) {
  return String(value || "disconnected")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function stateClass(value) {
  if (value === "ready") return "ready";
  if (value === "simulating") return "simulating";
  if (["connecting", "discovering", "setting_location", "clearing", "disconnecting"].includes(value)) {
    return "busy";
  }
  if (value === "error") return "error";
  return "";
}

function isBusy(value) {
  return ["connecting", "discovering", "setting_location", "clearing", "disconnecting"].includes(value);
}

function hasValidCoordinates() {
  const latitude = Number(ui.latitude.value);
  const longitude = Number(ui.longitude.value);
  return Number.isFinite(latitude)
    && Number.isFinite(longitude)
    && latitude >= -90
    && latitude <= 90
    && longitude >= -180
    && longitude <= 180;
}

function renderSnapshot(snapshot) {
  state.snapshot = snapshot;
  const current = snapshot.state || "disconnected";

  ui.stateLabel.textContent = humanState(current);
  ui.stateDot.className = `state-dot ${stateClass(current)}`.trim();

  if (snapshot.device) {
    const pieces = [
      snapshot.device.name || "iOS device",
      snapshot.device.ios_version ? `iOS ${snapshot.device.ios_version}` : null,
      snapshot.device.connection ? snapshot.device.connection.toUpperCase() : null,
    ].filter(Boolean);
    ui.deviceDetail.textContent = pieces.join(" · ");
    ui.deviceDetail.classList.remove("muted");
  } else {
    ui.deviceDetail.textContent = "No active device session.";
    ui.deviceDetail.classList.add("muted");
  }

  if (snapshot.location) {
    ui.activeLocation.textContent = `Active: ${snapshot.location.latitude.toFixed(6)}, ${snapshot.location.longitude.toFixed(6)}`;
    ui.activeLocation.classList.remove("muted");
  } else {
    ui.activeLocation.textContent = "No simulated location is recorded by this session.";
    ui.activeLocation.classList.add("muted");
  }

  const connected = Boolean(snapshot.device);
  const busy = isBusy(current) || state.operationInFlight;
  ui.deviceSelect.disabled = connected || busy;
  ui.refreshDevices.disabled = connected || busy;
  ui.connectDevice.disabled = connected || busy || !ui.deviceSelect.value;
  ui.disconnectDevice.disabled = !connected || busy;
  ui.setLocation.disabled = busy
    || !hasValidCoordinates()
    || !["ready", "simulating"].includes(current);
  ui.clearLocation.disabled = busy || !["ready", "simulating"].includes(current);

  if (snapshot.last_error) {
    showMessage(`${snapshot.last_error.code}: ${snapshot.last_error.message}`, "error");
  }

  scheduleStatusPoll();
}

function showMessage(message, kind = "info") {
  ui.message.textContent = message;
  ui.message.className = `message ${kind}`.trim();
  ui.message.hidden = !message;
}

function clearMessage() {
  ui.message.hidden = true;
  ui.message.textContent = "";
  ui.message.className = "message";
}

function describeDevice(device) {
  const name = device.name || device.product_type || "iOS device";
  const ios = device.ios_version ? `iOS ${device.ios_version}` : "iOS version unavailable";
  const connection = device.connection ? device.connection.toUpperCase() : "UNKNOWN";
  const suffix = device.identifier ? device.identifier.slice(-6) : "";
  return `${name} · ${ios} · ${connection}${suffix ? ` · …${suffix}` : ""}`;
}

async function refreshDevices({ quiet = false } = {}) {
  if (!quiet) clearMessage();
  ui.refreshDevices.disabled = true;
  try {
    const payload = await requestJson("/api/devices");
    state.devices = payload.devices || [];
    const previous = ui.deviceSelect.value;
    ui.deviceSelect.replaceChildren();

    if (state.devices.length === 0) {
      ui.deviceSelect.append(new Option("No connected iOS device found", ""));
    } else {
      for (const device of state.devices) {
        ui.deviceSelect.append(new Option(describeDevice(device), device.identifier));
      }
      if (state.devices.some((device) => device.identifier === previous)) {
        ui.deviceSelect.value = previous;
      }
    }
    await refreshStatus({ quiet: true });
  } catch (error) {
    ui.deviceSelect.replaceChildren(new Option("Device discovery unavailable", ""));
    if (!quiet) reportError(error);
  } finally {
    renderSnapshot(state.snapshot);
  }
}

async function connectDevice() {
  const identifier = ui.deviceSelect.value;
  if (!identifier) return;
  await runOperation(async () => {
    const snapshot = await requestJson("/api/device/connect", {
      method: "POST",
      body: JSON.stringify({ identifier }),
    });
    renderSnapshot(snapshot);
    showMessage("Device connection established and ready.", "success");
  });
}

async function disconnectDevice() {
  await runOperation(async () => {
    const snapshot = await requestJson("/api/device/disconnect", { method: "POST" });
    renderSnapshot(snapshot);
    showMessage("Device session closed.", "success");
    await refreshDevices({ quiet: true });
  });
}

async function setLocation() {
  if (!hasValidCoordinates()) {
    showMessage("Enter finite latitude and longitude values within their valid ranges.", "error");
    return;
  }
  const latitude = Number(ui.latitude.value);
  const longitude = Number(ui.longitude.value);

  await runOperation(async () => {
    const snapshot = await requestJson("/api/location", {
      method: "POST",
      body: JSON.stringify({ latitude, longitude }),
    });
    renderSnapshot(snapshot);
    showMessage("The iOS location-simulation request completed successfully.", "success");
  });
}

async function clearLocation() {
  await runOperation(async () => {
    const snapshot = await requestJson("/api/location", { method: "DELETE" });
    renderSnapshot(snapshot);
    showMessage("The iOS clear-location request completed successfully.", "success");
  });
}

async function runOperation(operation) {
  if (state.operationInFlight) return;
  state.operationInFlight = true;
  clearMessage();
  renderSnapshot(state.snapshot);
  try {
    await operation();
  } catch (error) {
    reportError(error);
    await refreshStatus({ quiet: true });
  } finally {
    state.operationInFlight = false;
    renderSnapshot(state.snapshot);
  }
}

function reportError(error) {
  if (error instanceof ApiError) {
    showMessage(`${error.code}: ${error.message}`, "error");
  } else {
    showMessage(
      "Unexpected browser-side failure. The server state has not been assumed successful.",
      "error",
    );
  }
}

async function refreshStatus({ quiet = false } = {}) {
  try {
    const snapshot = await requestJson("/api/device/status");
    const wasConnected = Boolean(state.snapshot.device);
    renderSnapshot(snapshot);
    if (wasConnected && !snapshot.device && !quiet) {
      showMessage(
        "The selected device is no longer present. The local session was invalidated.",
        "error",
      );
    }
  } catch (error) {
    if (!quiet) reportError(error);
  }
}

function scheduleStatusPoll() {
  if (state.pollTimer) {
    clearTimeout(state.pollTimer);
    state.pollTimer = null;
  }
  if (!state.snapshot.device) return;

  state.pollTimer = setTimeout(async () => {
    state.pollTimer = null;
    await refreshStatus({ quiet: false });
  }, 2500);
}

function coordinatesChanged() {
  renderSnapshot(state.snapshot);
  if (!hasValidCoordinates()) return;
  setMapMarker(Number(ui.latitude.value), Number(ui.longitude.value), false);
}

function coordinatesCommitted() {
  if (!hasValidCoordinates()) return;
  setMapMarker(Number(ui.latitude.value), Number(ui.longitude.value), true);
}

function setCoordinates(latitude, longitude, { center = true } = {}) {
  ui.latitude.value = Number(latitude).toFixed(6);
  ui.longitude.value = Number(longitude).toFixed(6);
  setMapMarker(Number(latitude), Number(longitude), center);
  renderSnapshot(state.snapshot);
}

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function normalizeLongitude(longitude) {
  return ((longitude + 180) % 360 + 360) % 360 - 180;
}

function latLonToWorld(latitude, longitude, zoom) {
  const lat = clamp(latitude, -MAX_MERCATOR_LAT, MAX_MERCATOR_LAT);
  const lon = normalizeLongitude(longitude);
  const scale = TILE_SIZE * (2 ** zoom);
  const sinLatitude = Math.sin(lat * Math.PI / 180);
  return {
    x: ((lon + 180) / 360) * scale,
    y: (0.5 - Math.log((1 + sinLatitude) / (1 - sinLatitude)) / (4 * Math.PI)) * scale,
  };
}

function worldToLatLon(x, y, zoom) {
  const scale = TILE_SIZE * (2 ** zoom);
  const longitude = normalizeLongitude((x / scale) * 360 - 180);
  const mercator = Math.PI - (2 * Math.PI * y) / scale;
  const latitude = (180 / Math.PI) * Math.atan(Math.sinh(mercator));
  return { latitude: clamp(latitude, -MAX_MERCATOR_LAT, MAX_MERCATOR_LAT), longitude };
}

function currentMapGeometry() {
  const width = ui.map.clientWidth;
  const height = ui.map.clientHeight;
  const center = latLonToWorld(state.map.centerLat, state.map.centerLon, state.map.zoom);
  return {
    width,
    height,
    center,
    left: center.x - width / 2,
    top: center.y - height / 2,
  };
}

function renderMap() {
  const geometry = currentMapGeometry();
  if (geometry.width <= 0 || geometry.height <= 0) return;

  const zoom = state.map.zoom;
  const tileCount = 2 ** zoom;
  const minTileX = Math.floor(geometry.left / TILE_SIZE);
  const maxTileX = Math.floor((geometry.left + geometry.width) / TILE_SIZE);
  const minTileY = Math.floor(geometry.top / TILE_SIZE);
  const maxTileY = Math.floor((geometry.top + geometry.height) / TILE_SIZE);
  const fragment = document.createDocumentFragment();
  let loadedTiles = 0;
  let failedTiles = 0;

  for (let tileY = minTileY; tileY <= maxTileY; tileY += 1) {
    if (tileY < 0 || tileY >= tileCount) continue;
    for (let tileX = minTileX; tileX <= maxTileX; tileX += 1) {
      const wrappedX = ((tileX % tileCount) + tileCount) % tileCount;
      const image = document.createElement("img");
      image.className = "map-tile";
      image.alt = "";
      image.draggable = false;
      image.decoding = "async";
      image.src = `https://tile.openstreetmap.org/${zoom}/${wrappedX}/${tileY}.png`;
      image.style.left = `${Math.round(tileX * TILE_SIZE - geometry.left)}px`;
      image.style.top = `${Math.round(tileY * TILE_SIZE - geometry.top)}px`;
      image.addEventListener("load", () => {
        loadedTiles += 1;
        if (loadedTiles > 0) ui.mapFallback.hidden = true;
      });
      image.addEventListener("error", () => {
        failedTiles += 1;
        if (failedTiles >= 3 && loadedTiles === 0) ui.mapFallback.hidden = false;
      });
      fragment.append(image);
    }
  }

  ui.mapTiles.replaceChildren(fragment);
  positionMapMarker(geometry);
}

function positionMapMarker(geometry = currentMapGeometry()) {
  const world = latLonToWorld(state.map.markerLat, state.map.markerLon, state.map.zoom);
  const worldWidth = TILE_SIZE * (2 ** state.map.zoom);
  let markerX = world.x;

  while (markerX - geometry.center.x > worldWidth / 2) markerX -= worldWidth;
  while (geometry.center.x - markerX > worldWidth / 2) markerX += worldWidth;

  const left = markerX - geometry.left;
  const top = world.y - geometry.top;
  ui.mapMarker.style.left = `${left}px`;
  ui.mapMarker.style.top = `${top}px`;
  ui.mapMarker.hidden = left < -20
    || top < -20
    || left > geometry.width + 20
    || top > geometry.height + 20;
}

function setMapMarker(latitude, longitude, center) {
  state.map.markerLat = clamp(latitude, -MAX_MERCATOR_LAT, MAX_MERCATOR_LAT);
  state.map.markerLon = normalizeLongitude(longitude);
  if (center) {
    state.map.centerLat = state.map.markerLat;
    state.map.centerLon = state.map.markerLon;
    renderMap();
  } else {
    positionMapMarker();
  }
}

function initMap() {
  renderMap();

  ui.map.addEventListener("click", (event) => {
    if (event.target.closest(".map-controls")) return;
    const rect = ui.map.getBoundingClientRect();
    const geometry = currentMapGeometry();
    const worldX = geometry.left + event.clientX - rect.left;
    const worldY = geometry.top + event.clientY - rect.top;
    const point = worldToLatLon(worldX, worldY, state.map.zoom);
    setCoordinates(point.latitude, point.longitude, { center: false });
  });

  ui.mapZoomIn.addEventListener("click", () => {
    state.map.zoom = clamp(state.map.zoom + 1, 3, 18);
    renderMap();
  });
  ui.mapZoomOut.addEventListener("click", () => {
    state.map.zoom = clamp(state.map.zoom - 1, 3, 18);
    renderMap();
  });

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    if (resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(renderMap, 120);
  });
}

function setFuelFreshness(stale) {
  ui.fuelFreshness.hidden = false;
  ui.fuelFreshness.textContent = stale ? "Stale cache" : "Fresh";
  ui.fuelFreshness.className = `status-tag ${stale ? "stale" : "fresh"}`;
}

function fuelUnavailable(message) {
  ui.fuelQuote.textContent = message;
  ui.fuelQuote.classList.add("muted");
  ui.fuelFreshness.hidden = true;
}

async function loadFuelRegions() {
  try {
    const payload = await requestJson("/api/fuel/regions");
    const regions = payload.regions || [];
    ui.fuelRegion.replaceChildren();
    if (regions.length === 0) {
      ui.fuelRegion.append(new Option("No regions available", ""));
      ui.fuelType.disabled = true;
      fuelUnavailable("No fuel-price regions were returned.");
      return;
    }
    for (const region of regions) ui.fuelRegion.append(new Option(region, region));
    setFuelFreshness(Boolean(payload.stale));
    await loadFuelTypes();
  } catch (error) {
    ui.fuelRegion.replaceChildren(new Option("Fuel data unavailable", ""));
    ui.fuelType.replaceChildren(new Option("—", ""));
    ui.fuelType.disabled = true;
    fuelUnavailable(error instanceof ApiError ? error.message : "Fuel data is unavailable.");
  }
}

async function loadFuelTypes() {
  const region = ui.fuelRegion.value;
  if (!region) return;
  ui.fuelType.disabled = true;
  try {
    const payload = await requestJson(`/api/fuel/types?region=${encodeURIComponent(region)}`);
    const types = payload.types || [];
    ui.fuelType.replaceChildren();
    if (types.length === 0) {
      ui.fuelType.append(new Option("No fuel types", ""));
      fuelUnavailable(`No fuel-price records are available for ${region}.`);
      return;
    }
    for (const type of types) ui.fuelType.append(new Option(type, type));
    ui.fuelType.disabled = false;
    setFuelFreshness(Boolean(payload.stale));
    await loadFuelQuote();
  } catch (error) {
    fuelUnavailable(error instanceof ApiError ? error.message : "Fuel data is unavailable.");
  }
}

async function loadFuelQuote() {
  const region = ui.fuelRegion.value;
  const fuelType = ui.fuelType.value;
  if (!region || !fuelType) return;
  try {
    const payload = await requestJson(
      `/api/fuel/quote?region=${encodeURIComponent(region)}&type=${encodeURIComponent(fuelType)}`,
    );
    const quote = payload.quote;
    if (!quote) {
      fuelUnavailable(`No ${fuelType} quote is available for ${region}.`);
      return;
    }

    setFuelFreshness(Boolean(quote.stale));
    const place = [quote.suburb, quote.state].filter(Boolean).join(", ") || quote.region;
    ui.fuelQuote.classList.remove("muted");
    ui.fuelQuote.replaceChildren();

    const price = document.createElement("strong");
    price.textContent = `${Number(quote.price).toFixed(1)} c/L`;
    const details = document.createElement("div");
    details.textContent = `${quote.type} · ${place}`;
    const coordinates = document.createElement("div");
    coordinates.className = "hint";
    coordinates.textContent = `${Number(quote.lat).toFixed(6)}, ${Number(quote.lng).toFixed(6)}`;
    ui.fuelQuote.append(price, details, coordinates);

    setCoordinates(quote.lat, quote.lng, { center: true });
  } catch (error) {
    fuelUnavailable(error instanceof ApiError ? error.message : "Fuel quote is unavailable.");
  }
}

ui.refreshDevices.addEventListener("click", () => refreshDevices());
ui.connectDevice.addEventListener("click", connectDevice);
ui.disconnectDevice.addEventListener("click", disconnectDevice);
ui.setLocation.addEventListener("click", setLocation);
ui.clearLocation.addEventListener("click", clearLocation);
ui.deviceSelect.addEventListener("change", () => renderSnapshot(state.snapshot));
ui.latitude.addEventListener("input", coordinatesChanged);
ui.longitude.addEventListener("input", coordinatesChanged);
ui.latitude.addEventListener("change", coordinatesCommitted);
ui.longitude.addEventListener("change", coordinatesCommitted);
ui.fuelRegion.addEventListener("change", loadFuelTypes);
ui.fuelType.addEventListener("change", loadFuelQuote);

window.addEventListener("DOMContentLoaded", async () => {
  initMap();
  renderSnapshot(state.snapshot);
  await refreshStatus({ quiet: true });
  await refreshDevices({ quiet: true });
  void loadFuelRegions();
});