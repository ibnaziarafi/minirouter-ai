"use strict";

const ROUTE_NAMES = {
  coding: "Coding",
  reasoning: "Reasoning",
  search: "Search",
  database: "Database",
  no_llm: "No LLM",
};

const CAPABILITY_NAMES = {
  coding: "Coding",
  reasoning: "Reasoning",
  search: "Search",
  database: "Database",
};

const SAMPLES = {
  coding: {
    text: "Fix this Python function so it returns the sum: def add(a, b): return a - b",
    context: "",
  },
  reasoning: {
    text: "A store sold 18 notebooks on Monday and twice as many on Tuesday. How many notebooks were sold in total?",
    context: "",
  },
  search: {
    text: "Find the latest official Python release notes.",
    context: "Target: Python stable release announcements.",
  },
  database: {
    text: "Retrieve the delivery status for order ORD-1042 from my authorized account.",
    context: "Authorized read-only orders workflow. Schema: orders(order_id, delivery_status).",
  },
  calculator: {
    text: "calc: (25 * 80) / 100",
    context: "",
  },
  unsupported: {
    text: "Rewrite this note to sound warmer: Please send the report by Friday.",
    context: "",
  },
};

const form = document.querySelector("#route-form");
const promptInput = document.querySelector("#request-text");
const contextInput = document.querySelector("#context-text");
const submitButton = document.querySelector("#submit-button");
const formError = document.querySelector("#form-error");
const resultLive = document.querySelector("#result-live");
const emptyState = document.querySelector("#empty-state");
const loadingState = document.querySelector("#loading-state");
const successState = document.querySelector("#success-state");
const decisionStatus = document.querySelector("#decision-status");
let latestResponse = null;

function setModelState(text, state) {
  document.querySelector("#model-state").textContent = text;
  const dot = document.querySelector(".status-dot");
  dot.classList.toggle("is-ready", state === "ready");
  dot.classList.toggle("is-error", state === "error");
}

function setDecisionStatus(text, state) {
  decisionStatus.textContent = text;
  decisionStatus.className = `decision-status status-${state}`;
}

function showFormError(message) {
  formError.textContent = message;
  formError.hidden = !message;
}

function setView(view) {
  emptyState.hidden = view !== "empty" && view !== "error";
  loadingState.hidden = view !== "loading";
  successState.hidden = view !== "success";
  resultLive.setAttribute("aria-busy", view === "loading" ? "true" : "false");
  if (view === "empty") setDecisionStatus("Ready", "ready");
  if (view === "loading") setDecisionStatus("Working", "ready");
  if (view === "error") setDecisionStatus("Error", "error");
}

function displayName(value, names) {
  if (typeof value !== "string" || !value) return "Unspecified";
  return names[value] || value.replace(/_/g, " ");
}

function percent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return null;
  return Math.round(Math.min(1, Math.max(0, number)) * 100);
}

function renderScoreRows(container, values, names, selected) {
  container.replaceChildren();
  if (!values || typeof values !== "object" || Array.isArray(values)) {
    const unavailable = document.createElement("p");
    unavailable.className = "field-hint";
    unavailable.textContent = "Scores were not returned for this request.";
    container.append(unavailable);
    return;
  }

  const entries = Object.entries(values).filter(([, value]) => percent(value) !== null);
  if (!entries.length) {
    const unavailable = document.createElement("p");
    unavailable.className = "field-hint";
    unavailable.textContent = "Scores were not returned for this request.";
    container.append(unavailable);
    return;
  }

  for (const [key, rawValue] of entries) {
    const value = percent(rawValue);
    const row = document.createElement("div");
    row.className = "score-row";
    if (key === selected) row.classList.add("is-selected");

    const label = document.createElement("span");
    label.className = "score-label";
    label.textContent = displayName(key, names);

    const track = document.createElement("span");
    track.className = "score-track";
    track.setAttribute("role", "img");
    track.setAttribute("aria-label", `${displayName(key, names)} score ${value}%`);
    const fill = document.createElement("span");
    fill.className = "score-fill";
    fill.style.width = `${value}%`;
    track.append(fill);

    const score = document.createElement("span");
    score.className = "score-value";
    score.textContent = `${value}%`;

    row.append(label, track, score);
    container.append(row);
  }
}

function addDetail(text, warning = false) {
  const chip = document.createElement("span");
  chip.className = warning ? "detail-chip detail-chip-warning" : "detail-chip";
  chip.textContent = text;
  document.querySelector("#decision-details").append(chip);
}

function renderResponse(data) {
  latestResponse = data;
  const isAbstain = data.status === "abstain";
  const route = isAbstain ? null : data.route;
  const routeTitle = isAbstain ? "Abstain" : displayName(route, ROUTE_NAMES);
  const routeName = document.querySelector("#route-name");
  routeName.textContent = routeTitle;
  routeName.setAttribute("aria-label", `Recommendation: ${routeTitle}`);
  document.querySelector("#decision-kicker").textContent = isAbstain ? "Review this request" : "Recommended next route";

  const confidence = percent(data.confidence);
  const confidenceBadge = document.querySelector("#confidence-badge");
  confidenceBadge.textContent = confidence === null ? "Confidence unavailable" : `${confidence}% confidence`;
  confidenceBadge.hidden = confidence === null;

  const explanation = isAbstain
    ? (data.abstain_reason || data.error || "The model could not make a confident recommendation.")
    : "This is a recommendation for the next step. MiniRouter has not run the destination.";
  document.querySelector("#decision-explanation").textContent = explanation;

  const details = document.querySelector("#decision-details");
  details.replaceChildren();
  if (isAbstain && data.abstain_reason) addDetail(`Reason: ${String(data.abstain_reason).replace(/_/g, " ")}`, true);
  if (Array.isArray(data.requires)) {
    for (const need of data.requires) addDetail(`May need ${displayName(need, CAPABILITY_NAMES)}`, true);
  }
  if (data.eligible_handler) addDetail(`Eligible handler: ${String(data.eligible_handler)}`);
  if (Number.isFinite(Number(data.latency_ms))) addDetail(`${Number(data.latency_ms).toFixed(1)} ms local inference`);
  if (data.token_count != null && Number.isFinite(Number(data.token_count))) addDetail(`${data.token_count} input tokens`);
  if (data.context_truncated) addDetail("Input shortened to fit the model limit", true);

  renderScoreRows(document.querySelector("#primary-scores"), data.probabilities, ROUTE_NAMES, route);
  renderScoreRows(document.querySelector("#capability-scores"), data.capability_scores, CAPABILITY_NAMES, null);
  document.querySelector("#json-output").textContent = JSON.stringify(data, null, 2);
  document.querySelector("#copy-status").textContent = "";
  setView("success");
  setDecisionStatus(isAbstain ? "Review" : "Recommendation", isAbstain ? "abstain" : "route");
}

function formatBytes(value) {
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes <= 0) return "Unavailable";
  return `${(bytes / 1_000_000).toFixed(2)} MB (${bytes.toLocaleString()} bytes)`;
}

async function loadMetadata() {
  try {
    const response = await fetch("/api/meta", { headers: { Accept: "application/json" } });
    const metadata = await response.json();
    if (!response.ok) throw new Error(metadata.error || `Metadata request failed (${response.status})`);

    setModelState(metadata.state || "Local model · ready", "ready");
    document.querySelector("#model-version").textContent = metadata.model_version || metadata.state || "Experimental V3";
    document.querySelector("#bundle-size").textContent = formatBytes(metadata.bundle_bytes);
    const parameterCount = Number(metadata.parameters);
    document.querySelector("#parameter-count").textContent = Number.isFinite(parameterCount) && parameterCount > 0
      ? parameterCount.toLocaleString()
      : "Unavailable";
    document.querySelector("#calibration-state").textContent = metadata.calibration || "Unavailable";
  } catch (error) {
    setModelState("Local model · unavailable", "error");
    document.querySelector("#model-version").textContent = "Experimental V3";
    document.querySelector("#bundle-size").textContent = "Unavailable";
    document.querySelector("#parameter-count").textContent = "Unavailable";
    document.querySelector("#calibration-state").textContent = "Unavailable";
    showFormError(`Could not read model information: ${error.message}. Start the local MiniRouter preview and reload this page.`);
  }
}

for (const button of document.querySelectorAll("[data-sample]")) {
  button.addEventListener("click", () => {
    const sample = SAMPLES[button.dataset.sample];
    if (!sample) return;
    promptInput.value = sample.text;
    contextInput.value = sample.context;
    document.querySelector("#char-count").textContent = `${sample.text.length} characters`;
    showFormError("");
    promptInput.focus();
  });
}

promptInput.addEventListener("input", () => {
  document.querySelector("#char-count").textContent = `${promptInput.value.length} characters`;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showFormError("");
  const text = promptInput.value.trim();
  if (!text) {
    showFormError("Enter a request or choose a sample before routing.");
    promptInput.focus();
    return;
  }

  submitButton.disabled = true;
  submitButton.querySelector("span:first-child").textContent = "Routing request…";
  setView("loading");

  const context = contextInput.value.trim();
  const payload = {
    text,
    context: context ? [context] : [],
    available_capabilities: [...document.querySelectorAll('input[name="capability"]:checked')].map((input) => input.value),
    calculator: document.querySelector("#calculator-enabled").checked,
    locale: "en",
    context_complete: true,
  };

  try {
    const response = await fetch("/api/route", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
    });
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error(`The local service returned an invalid response (${response.status}).`);
    }
    if (!response.ok) throw new Error(data.error || `Routing failed (${response.status}).`);
    if (!data || (data.status !== "route" && data.status !== "abstain")) {
      throw new Error("The local service response did not contain a routing decision.");
    }
    renderResponse(data);
  } catch (error) {
    latestResponse = null;
    successState.hidden = true;
    emptyState.hidden = false;
    emptyState.querySelector("h3").textContent = "Could not get a recommendation";
    emptyState.querySelector("p").textContent = "Check that the local model is running, then try again.";
    setView("error");
    showFormError(error.message);
    setDecisionStatus("Error", "error");
  } finally {
    submitButton.disabled = false;
    submitButton.querySelector("span:first-child").textContent = "Get a recommendation";
  }
});

form.addEventListener("reset", () => {
  window.setTimeout(() => {
    latestResponse = null;
    showFormError("");
    document.querySelector("#char-count").textContent = "0 characters";
    emptyState.querySelector("h3").textContent = "Waiting for a request";
    emptyState.querySelector("p").textContent = "Your recommendation and route scores will appear here.";
    setView("empty");
  }, 0);
});

document.querySelector("#copy-json").addEventListener("click", async () => {
  if (!latestResponse) return;
  const status = document.querySelector("#copy-status");
  try {
    await navigator.clipboard.writeText(JSON.stringify(latestResponse, null, 2));
    status.textContent = "JSON copied.";
  } catch {
    status.textContent = "Copy unavailable. Select the JSON above and copy it manually.";
  }
});

loadMetadata();
