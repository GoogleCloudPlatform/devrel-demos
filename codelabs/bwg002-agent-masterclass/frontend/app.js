"use strict";

/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * @file app.js
 * @description Vanilla ES6 JavaScript client for the Agentic Pitch Generator starter web UI.
 *
 * Why: Connects the plain HTML5 interface to the FastAPI backend endpoints
 * (`/api/health`, `/api/config`, `/api/pitch`, and
 * `/a2a/pitch_generator/.well-known/agent-card.json`) without third-party UI libraries.
 * Uses strictly safe DOM APIs (`document.createElement`, `textContent`, `replaceChildren`)
 * to prevent DOM-based cross-site scripting.
 */

/**
 * Create a DOM element with safe attribute assignment and plain text content.
 *
 * Why: Constructing elements exclusively via `document.createElement` and `textContent`
 * guarantees that untrusted model outputs or user briefs are never parsed as executable
 * HTML markup.
 *
 * @param {string} tagName HTML tag name to create.
 * @param {Object<string, string>} attributes Key-value map of element attributes.
 * @param {string} textValue Optional text content assigned via `textContent`.
 * @return {HTMLElement} Newly created DOM element.
 */
function createSafeElement(tagName, attributes, textValue) {
  const el = document.createElement(tagName);
  if (attributes && typeof attributes === "object") {
    Object.keys(attributes).forEach((key) => {
      if (attributes[key] !== undefined && attributes[key] !== null) {
        el.setAttribute(key, String(attributes[key]));
      }
    });
  }
  if (textValue !== undefined && textValue !== null) {
    el.textContent = String(textValue);
  }
  return el;
}

/**
 * Display a non-blocking status message in `#status-banner`.
 *
 * Why: Avoids blocking browser modal dialogs and updates an ARIA live region
 * (`role="alert"`) for screen-reader accessibility.
 *
 * @param {string} message Notification message to display (empty string hides banner).
 * @param {string} level Severity indicator (`"info"`, `"warn"`, or `"error"`).
 * @return {void}
 */
function setBanner(message, level) {
  if (typeof document === "undefined") {
    return;
  }
  const banner = document.getElementById("status-banner");
  if (!banner) {
    return;
  }
  if (!message) {
    banner.hidden = true;
    banner.textContent = "";
    return;
  }
  banner.hidden = false;
  banner.setAttribute("data-level", level || "info");
  banner.textContent = String(message);
}

/**
 * Render the step-by-step agent execution trace list inside `#workflow-trace-list`.
 *
 * Why: Uses `replaceChildren` and `createSafeElement("li", ...)` so learners can
 * inspect which specialist nodes (`creative_director`, `copywriter`, `assemble`,
 * `package`) ran during the workflow.
 *
 * @param {Array<string>} traceSteps Ordered list of executed workflow node names.
 * @return {void}
 */
function renderWorkflowTrace(traceSteps) {
  if (typeof document === "undefined") {
    return;
  }
  const listEl = document.getElementById("workflow-trace-list");
  if (!listEl) {
    return;
  }
  const steps =
    Array.isArray(traceSteps) && traceSteps.length > 0
      ? traceSteps
      : ["creative_director", "copywriter", "assemble", "package"];
  const items = steps.map((stepName) =>
    createSafeElement("li", {}, `Executed node: ${stepName}`)
  );
  listEl.replaceChildren(...items);
}

/**
 * Update the DOM cards in `#pitch-result-card` with the workflow response payload.
 *
 * Why: Populates the starter Creative Director concept and Copywriter social copy,
 * and dynamically reveals Art Direction or Key Visual cards once the learner adds
 * `visual_director` in Module 1.
 *
 * @param {Object} data Parsed JSON response from `/api/pitch`.
 * @return {void}
 */
function renderPitchResult(data) {
  if (typeof document === "undefined" || !data) {
    return;
  }
  const statusEl = document.getElementById("pitch-status");
  const conceptEl = document.getElementById("pitch-concept");
  const copyEl = document.getElementById("pitch-copy");
  const brandCard = document.getElementById("brand-strategy-card");
  const brandEl = document.getElementById("pitch-brand-strategy");
  const artCard = document.getElementById("art-direction-card");
  const artEl = document.getElementById("pitch-art-direction");
  const visualCard = document.getElementById("key-visual-card");
  const visualEl = document.getElementById("pitch-key-visual");
  const visualImgEl = document.getElementById("pitch-key-visual-img");

  const statusText = String(data.status || "completed");
  if (statusEl) {
    statusEl.textContent = statusText;
    statusEl.className =
      statusText === "completed" ? "badge badge-ok" : "badge badge-warn";
  }
  if (conceptEl) {
    conceptEl.textContent = data.concept || "No concept generated.";
  }
  if (copyEl) {
    copyEl.textContent = data.copy || "No social copy generated.";
  }
  if (brandCard && brandEl) {
    if (data.brand_strategy) {
      brandCard.hidden = false;
      brandEl.textContent = data.brand_strategy;
    } else {
      brandCard.hidden = true;
    }
  }
  if (artCard && artEl) {
    if (data.art_direction) {
      artCard.hidden = false;
      artEl.textContent = data.art_direction;
    } else {
      artCard.hidden = true;
    }
  }
  if (visualCard && visualEl) {
    if (data.key_visual_uri) {
      visualCard.hidden = false;
      const rawUri = String(data.key_visual_uri);
      const sessionId = encodeURIComponent(
        String(data.session_id || "default").trim() || "default"
      );
      const resolvedImgUrl =
        data.key_visual_url ||
        (rawUri.startsWith("gs://")
          ? `/api/artifacts/${sessionId}/key_visual.png`
          : rawUri);
      if (visualImgEl) {
        visualImgEl.src = resolvedImgUrl;
        visualImgEl.hidden = false;
      }
      visualEl.textContent = `Artifact URI: ${rawUri}`;
    } else {
      visualCard.hidden = true;
      if (visualImgEl) {
        visualImgEl.removeAttribute("src");
        visualImgEl.hidden = true;
      }
    }
  }

  renderWorkflowTrace(data.trace);
}

/**
 * Execute an HTTP request using the standard Fetch API (`fetch(url, options)`).
 *
 * Why: Provides a default `fetch(` implementation while allowing unit tests to inject
 * a custom `fetchImpl` mock when running offline outside a browser.
 *
 * @param {string} url Request URL or relative path.
 * @param {Object} [options] Optional Fetch API request options.
 * @return {Promise<Response>} Fetch API response promise.
 */
function defaultFetch(url, options) {
  return fetch(url, options);
}

/**
 * Fetch service health (`/api/health`) and public configuration (`/api/config`).
 *
 * Why: Verifies backend connectivity on page load and displays active project,
 * region, and Gemini Enterprise Agent Platform model in the header summary.
 *
 * @param {Function} fetchImpl Optional fetch implementation for dependency injection.
 * @return {Promise<Object>} Resolved health and config objects.
 */
async function fetchHealthAndConfig(fetchImpl) {
  const fetcher = fetchImpl || defaultFetch;
  const [healthResp, configResp] = await Promise.all([
    fetcher("/api/health"),
    fetcher("/api/config"),
  ]);
  const health = await healthResp.json();
  const cfg = await configResp.json();

  if (typeof document !== "undefined") {
    const healthBadge = document.getElementById("health-badge");
    if (healthBadge) {
      healthBadge.textContent = `Service: ${health.status || "ok"}`;
      healthBadge.className = "badge badge-ok";
    }
    const summaryEl = document.getElementById("config-summary");
    if (summaryEl) {
      const modelName = (cfg.models && cfg.models.flash) || "gemini-3.8-flash";
      summaryEl.textContent =
        `Project: ${cfg.project_id} | Region: ${cfg.region} | ` +
        `Model: ${modelName} | Enterprise Agent Platform: ${cfg.use_enterprise ? "Enabled" : "Disabled"}`;
    }
  }
  return { health, config: cfg };
}

/**
 * Toggle the loading state and spinner on `#btn-generate-pitch`.
 *
 * Why: Disables the submit button and renders an accessible inline spinner while
 * the multi-agent workflow executes so users do not accidentally submit duplicate
 * requests and have clear visual feedback that work is in progress.
 *
 * @param {boolean} isLoading True while the pitch request is in flight.
 * @return {void}
 */
function setGenerateButtonLoading(isLoading) {
  if (typeof document === "undefined") {
    return;
  }
  const btn = document.getElementById("btn-generate-pitch");
  const statusEl = document.getElementById("pitch-status");
  if (!btn) {
    return;
  }
  if (isLoading) {
    btn.disabled = true;
    btn.setAttribute("aria-busy", "true");
    const spinnerEl = createSafeElement("span", {
      class: "spinner",
      "aria-hidden": "true",
    });
    const labelEl = createSafeElement("span", {}, "Generating Pitch...");
    btn.replaceChildren(spinnerEl, labelEl);
    if (statusEl) {
      statusEl.textContent = "Generating...";
      statusEl.className = "badge badge-warn";
    }
  } else {
    btn.disabled = false;
    btn.removeAttribute("aria-busy");
    btn.textContent = "Generate Campaign Pitch";
  }
}

/**
 * Submit a campaign brief to `POST /api/pitch` and render the resulting pitch package.
 *
 * Why: Drives the primary campaign generation workflow using Gemini Enterprise Agent
 * Platform cloud models while locking the submit button until completion.
 *
 * @param {Object} payload Request dictionary with `brief` and `session_id`.
 * @param {Function} fetchImpl Optional fetch implementation for testing.
 * @return {Promise<Object>} Workflow execution response.
 */
async function submitPitchRequest(payload, fetchImpl) {
  if (typeof document !== "undefined") {
    const btn = document.getElementById("btn-generate-pitch");
    if (btn && btn.disabled) {
      return null;
    }
  }
  const fetcher = fetchImpl || fetch;
  setBanner("", "info");
  setGenerateButtonLoading(true);
  try {
    const resp = await fetcher("/api/pitch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!resp.ok) {
      setBanner(data.error || "Failed to generate pitch.", "error");
      const statusEl =
        typeof document !== "undefined"
          ? document.getElementById("pitch-status")
          : null;
      if (statusEl) {
        statusEl.textContent = "error";
        statusEl.className = "badge badge-warn";
      }
      return data;
    }
    renderPitchResult(data);
    return data;
  } catch (err) {
    setBanner(`Failed to generate pitch: ${err.message || err}`, "error");
    const statusEl =
      typeof document !== "undefined"
        ? document.getElementById("pitch-status")
        : null;
    if (statusEl) {
      statusEl.textContent = "error";
      statusEl.className = "badge badge-warn";
    }
    throw err;
  } finally {
    setGenerateButtonLoading(false);
  }
}

/**
 * Fetch and display the A2A Agent Card from `/a2a/pitch_generator/.well-known/agent-card.json`.
 *
 * Why: Allows learners to inspect the published A2A v0.3 discovery metadata directly
 * in the web UI.
 *
 * @param {Function} fetchImpl Optional fetch implementation for testing.
 * @return {Promise<Object>} Parsed A2A Agent Card JSON.
 */
async function inspectA2aAgentCard(fetchImpl) {
  const fetcher = fetchImpl || fetch;
  const resp = await fetcher("/a2a/pitch_generator/.well-known/agent-card.json");
  const card = await resp.json();
  if (typeof document !== "undefined") {
    const section = document.getElementById("a2a-card-section");
    const panel = document.getElementById("a2a-card-panel");
    if (section && panel) {
      section.hidden = false;
      panel.textContent = JSON.stringify(card, null, 2);
    }
  }
  return card;
}

/**
 * Attach DOM event listeners for form submission and A2A Agent Card inspection.
 *
 * Why: Centralizes UI initialization when `DOMContentLoaded` fires in the browser.
 *
 * @return {void}
 */
function initPitchGeneratorApp() {
  if (typeof document === "undefined") {
    return;
  }
  fetchHealthAndConfig().catch((err) => {
    setBanner(`Unable to load service configuration: ${err.message}`, "warn");
  });

  const form = document.getElementById("pitch-form");
  if (form) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const briefInput = document.getElementById("brief-input");
      const sessionInput = document.getElementById("session-id-input");

      submitPitchRequest({
        brief: briefInput ? briefInput.value : "",
        session_id: sessionInput ? sessionInput.value : "default",
      });
    });
  }

  const a2aBtn = document.getElementById("btn-inspect-a2a");
  if (a2aBtn) {
    a2aBtn.addEventListener("click", () => {
      inspectA2aAgentCard();
    });
  }
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", initPitchGeneratorApp);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    createSafeElement,
    setBanner,
    renderWorkflowTrace,
    renderPitchResult,
    fetchHealthAndConfig,
    setGenerateButtonLoading,
    submitPitchRequest,
    inspectA2aAgentCard,
    initPitchGeneratorApp,
  };
}
