"use strict";

const $ = (id) => document.getElementById(id);

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
  mapFallback: $("map-fallback"),
};

const state = {
  snapshot: { state: "disconnected", device: null, location: null, last_error: null },
  devices: [],
  map: null,
  marker: null,
  pollTimer: null,
  operationInFlight: false,
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
  if (["ready"].includes(value)) return "ready";
  if (["simulating"].includes(value)) return "simulating";
  if (["connecting", "discovering", "setting_location", "clearing", "disconnecting"].includes(value)) return "busy";
  if (["error"].includes(value)) return "error";
  return "";
}

function isBusy(value) {
  return ["connecting", "discovering", "setting_location", "clearing", "disconnecting"].includes(value);
}

function hasValidCoordinates() {
  const latitude = Number(ui.latitude.value);
  const longitude = Number(ui.longitude.value);
  return Number.isFinite(latitude) && Number.isFinite(longitude)
    && latitude >= -90 && latitude <= 90
    && longitude >= -180 && longitude <= 180;
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
  ui.setLocation.disabled = busy || !hasValidCoordinates() || !["ready", "simulating"].includes(current);
  ui.clearLocation.disabled = busy || current !== "simulating";

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
    showMessage("The simulated location was cleared from the active session.", "success");
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
    showMessage("Unexpected browser-side failure. The server state has not been assumed successful.", "error");
  }
}

async function refreshStatus({ quiet = false } = {}) {
  try {
    const snapshot = await requestJson("/api/device/status");
    const wasConnected = Boolean(state.snapshot.device);
    renderSnapshot(snapshot);
    if (wasConnected && !snapshot.device && !quiet) {
      showMessage("The selected device is no longer present. The local session was invalidated.", "error");
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
  const latitude = Number(ui.latitude.value);
  const longitude = Number(ui.longitude.value);
  placeMarker(latitude, longitude, false);
}

function setCoordinates(latitude, longitude, { center = true } = {}) {
  ui.latitude.value = Number(latitude).toFixed(6);
  ui.longitude.value = Number(longitude).toFixed(6);
  placeMarker(Number(latitude), Number(longitude), center);
  renderSnapshot(state.snapshot);
}

function initMap() {
  if (!window.L) {
    ui.map.hidden = true;
    ui.mapFallback.hidden = false;
    return;
  }

  try {
    state.map = L.map("map", { zoomControl: true }).setView([-33.8688, 151.2093], 11);
    const tiles = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    });
    tiles.on("tileerror", () => {
      ui.mapFallback.hidden = false;
      ui.mapFallback.textContent = "Map tiles could not be loaded. Coordinate and device controls remain available.";
    });
    tiles.addTo(state.map);
    state.map.on("click", (event) => {
      setCoordinates(event.latlng.lat, event.latlng.lng, { center: false });
    });
    placeMarker(-33.8688, 151.2093, false);
  } catch (_) {
    ui.map.hidden = true;
    ui.mapFallback.hidden = false;
  }
}

function placeMarker(latitude, longitude, center = true) {
  if (!state.map || !window.L || !Number.isFinite(latitude) || !Number.isFinite(longitude)) return;
  if (!state.marker) {
    state.marker = L.marker([latitude, longitude]).addTo(state.map);
  } else {
    state.marker.setLatLng([latitude, longitude]);
  }
  if (center) state.map.setView([latitude, longitude], Math.max(state.map.getZoom(), 13));
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
    const payload = await requestJson(`/api/fuel/quote?region=${encodeURIComponent(region)}&type=${encodeURIComponent(fuelType)}`);
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
ui.fuelRegion.addEventListener("change", loadFuelTypes);
ui.fuelType.addEventListener("change", loadFuelQuote);

window.addEventListener("DOMContentLoaded", async () => {
  initMap();
  renderSnapshot(state.snapshot);
  await refreshStatus({ quiet: true });
  await refreshDevices({ quiet: true });
  void loadFuelRegions();
});
