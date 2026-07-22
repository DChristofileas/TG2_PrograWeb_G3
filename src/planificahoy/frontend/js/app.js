"use strict";

// PlanificaHoy frontend. Consumes ONLY the backend (FastAPI): /locations, /recommendation.
// Never calls Open-Meteo directly. Never duplicates ACTIVITY_RULES.

const els = {
  input: document.getElementById("location-input"),
  searchBtn: document.getElementById("search-btn"),
  searchStatus: document.getElementById("search-status"),
  candidates: document.getElementById("candidates"),
  activitySection: document.getElementById("activity-section"),
  selectedLocation: document.getElementById("selected-location"),
  evaluateBtn: document.getElementById("evaluate-btn"),
  evaluateStatus: document.getElementById("evaluate-status"),
  resultSection: document.getElementById("result-section"),
  levelBanner: document.getElementById("level-banner"),
  levelIcon: document.getElementById("level-icon"),
  levelText: document.getElementById("level-text"),
  resultSummary: document.getElementById("result-summary"),
  resultReasons: document.getElementById("result-reasons"),
  wLocation: document.getElementById("w-location"),
  wTimestamp: document.getElementById("w-timestamp"),
  wTemp: document.getElementById("w-temp"),
  wPrecip: document.getElementById("w-precip"),
  wWind: document.getElementById("w-wind"),
};

const LEVEL_META = {
  FAVORABLE: { icon: "✅", label: "Favorable" },
  REGULAR: { icon: "⚠️", label: "Regular" },
  UNFAVORABLE: { icon: "⛔", label: "Desfavorable" },
};

const state = {
  selected: null, // chosen LocationCandidate
  searching: false,
  evaluating: false,
};

// ---- Helpers ----------------------------------------------------------------

function setStatus(el, message, isError = false) {
  el.textContent = message || "";
  el.classList.toggle("error", Boolean(isError));
}

// Reads the backend's { "detail": "..." } shape; falls back to a generic message.
async function readError(response) {
  try {
    const data = await response.json();
    if (data && typeof data.detail === "string") return data.detail;
  } catch (_) { /* no JSON body */ }
  return `Error del servidor (código ${response.status}).`;
}

function formatTimestamp(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("es-CR", {
    weekday: "short", day: "numeric", month: "short",
    hour: "2-digit", minute: "2-digit",
  });
}

function locationLabel(c) {
  const region = c.admin_region ? `${c.admin_region}, ` : "";
  return `${c.name} — ${region}${c.country}`;
}

// ---- Step 1: search locations ----------------------------------------------

async function searchLocations() {
  const query = els.input.value.trim();
  if (query.length < 2) {
    setStatus(els.searchStatus, "Escribe al menos 2 caracteres.", true);
    return;
  }
  if (state.searching) return; // avoid double submit

  state.searching = true;
  els.searchBtn.disabled = true;
  els.candidates.innerHTML = "";
  setStatus(els.searchStatus, "Buscando ubicaciones…");

  try {
    const res = await fetch(`/locations?query=${encodeURIComponent(query)}`);
    if (!res.ok) {
      setStatus(els.searchStatus, await readError(res), true);
      return;
    }
    const candidates = await res.json();
    if (!Array.isArray(candidates) || candidates.length === 0) {
      setStatus(els.searchStatus, "No se encontraron ubicaciones. Prueba otro nombre.", true);
      return;
    }
    setStatus(els.searchStatus, `${candidates.length} resultado(s). Elige uno:`);
    renderCandidates(candidates);
  } catch (_) {
    setStatus(els.searchStatus, "No se pudo contactar al servidor. Revisa que el backend esté activo.", true);
  } finally {
    state.searching = false;
    els.searchBtn.disabled = false;
  }
}

function renderCandidates(candidates) {
  els.candidates.innerHTML = "";
  candidates.forEach((c) => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "candidate-btn";
    btn.innerHTML =
      `<strong>${c.name}</strong>` +
      `<small>${c.admin_region ? c.admin_region + ", " : ""}${c.country} · ${c.timezone}</small>`;
    btn.addEventListener("click", () => selectCandidate(c, btn));
    li.appendChild(btn);
    els.candidates.appendChild(li);
  });
}

function selectCandidate(candidate, btn) {
  state.selected = candidate;
  document.querySelectorAll(".candidate-btn").forEach((b) => b.classList.remove("selected"));
  btn.classList.add("selected");

  els.selectedLocation.textContent = `Ubicación seleccionada: ${locationLabel(candidate)}`;
  els.activitySection.classList.remove("is-disabled");
  refreshEvaluateButton();
  els.activitySection.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// ---- Step 2: activity + evaluate -------------------------------------------

function selectedActivity() {
  const checked = document.querySelector('input[name="activity"]:checked');
  return checked ? checked.value : null;
}

function refreshEvaluateButton() {
  els.evaluateBtn.disabled = !(state.selected && selectedActivity());
}

async function evaluate() {
  if (!state.selected) return;
  const activity = selectedActivity();
  if (!activity) {
    setStatus(els.evaluateStatus, "Elige una actividad primero.", true);
    return;
  }
  if (state.evaluating) return;

  state.evaluating = true;
  els.evaluateBtn.disabled = true;
  setStatus(els.evaluateStatus, "Consultando el pronóstico…");

  const { latitude, longitude, timezone } = state.selected;
  const params = new URLSearchParams({ latitude, longitude, timezone, activity });

  try {
    const res = await fetch(`/recommendation?${params.toString()}`);
    if (!res.ok) {
      setStatus(els.evaluateStatus, await readError(res), true);
      els.resultSection.hidden = true;
      return;
    }
    const data = await res.json();
    renderResult(data);
    setStatus(els.evaluateStatus, "");
  } catch (_) {
    setStatus(els.evaluateStatus, "No se pudo contactar al servidor. Intenta de nuevo.", true);
    els.resultSection.hidden = true;
  } finally {
    state.evaluating = false;
    refreshEvaluateButton();
  }
}

function renderResult(data) {
  const { weather, recommendation } = data;
  const meta = LEVEL_META[recommendation.level] || { icon: "•", label: recommendation.level };

  els.levelBanner.className = `level-banner level-${recommendation.level}`;
  els.levelIcon.textContent = meta.icon;
  els.levelText.textContent = meta.label; // text + icon, never color-only
  els.resultSummary.textContent = recommendation.summary;

  els.wLocation.textContent = locationLabel(state.selected);
  els.wTimestamp.textContent = formatTimestamp(weather.timestamp);
  els.wTemp.textContent = `${weather.temperature_celsius} °C`;
  els.wPrecip.textContent = `${weather.precipitation_probability_percent} %`;
  els.wWind.textContent = `${weather.wind_speed_kmh} km/h`;

  els.resultReasons.innerHTML = "";
  (recommendation.reasons || []).forEach((reason) => {
    const li = document.createElement("li");
    li.textContent = reason;
    els.resultReasons.appendChild(li);
  });

  els.resultSection.hidden = false;
  els.resultSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// ---- Wiring -----------------------------------------------------------------

els.searchBtn.addEventListener("click", searchLocations);
els.input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") searchLocations();
});
els.evaluateBtn.addEventListener("click", evaluate);
document.querySelectorAll('input[name="activity"]').forEach((radio) => {
  radio.addEventListener("change", refreshEvaluateButton);
});
