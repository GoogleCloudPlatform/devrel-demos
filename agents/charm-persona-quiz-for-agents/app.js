/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * app.js
 * Static GitHub Pages UI controller, Google Gemini Decision 1 (gemini-decision-1 · /v1beta/decisions)
 * transport router, SVG radar chart renderer, and window.CHARM_AGENT_API harness.
 */

import {
  OCEAN_SCENARIOS,
  PRESET_AGENTS,
  FLOW_FORMAT_C_PERSONAS,
  FLOW_FORMAT_C_BY_CODE,
  buildResponsesForFormatC,
  countWords,
  validateParagraphResponses,
  buildSystemOnePayload,
  parseGradioSsePayload,
  normalizeOceanProfile,
} from "./ocean-core.js";

const GEMINI_DECISIONS_URL = "https://generativelanguage.googleapis.com/v1beta/decisions";

const TRAIT_DISPLAY_META = [
  { trait: "openness", code: "O", title: "Openness to Experience" },
  { trait: "conscientiousness", code: "C", title: "Conscientiousness" },
  { trait: "extraversion", code: "E", title: "Extraversion" },
  { trait: "agreeableness", code: "A", title: "Agreeableness" },
  { trait: "neuroticism", code: "N", title: "Neuroticism / Threat Sensitivity" },
];

let lastResultProfile = null;
let activeQuestionIndex = 0;

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function setActiveQuestionCard(targetIndex) {
  const total = OCEAN_SCENARIOS.length;
  const normalized = ((Number(targetIndex) || 0) % total + total) % total;
  activeQuestionIndex = normalized;

  const stackEl = document.getElementById("question-card-stack");
  if (stackEl) {
    if (stackEl.dataset) stackEl.dataset.activeIndex = String(normalized);
    if (typeof stackEl.setAttribute === "function") {
      stackEl.setAttribute("data-active-index", String(normalized));
    }
  }

  const cards =
    typeof document !== "undefined" && typeof document.querySelectorAll === "function"
      ? Array.from(document.querySelectorAll(".question-deck-card"))
      : [];
  cards.forEach((card, idx) => {
    const cardIdx =
      card.dataset && card.dataset.questionIndex !== undefined
        ? Number(card.dataset.questionIndex)
        : idx;
    const isActive = cardIdx === normalized;
    card.hidden = !isActive;
    if (card.style) {
      card.style.display = isActive ? "flex" : "none";
    }
    if (card.classList) {
      card.classList.toggle("is-active", isActive);
    }
  });

  const indicator = document.getElementById("question-stack-indicator");
  if (indicator) {
    indicator.textContent = `Card ${normalized + 1} of ${total}`;
  }

  const dots =
    typeof document !== "undefined" && typeof document.querySelectorAll === "function"
      ? Array.from(document.querySelectorAll(".stack-dot"))
      : [];
  dots.forEach((dot, idx) => {
    const dotIdx =
      dot.dataset && dot.dataset.stackJump !== undefined
        ? Number(dot.dataset.stackJump)
        : idx;
    const isActive = dotIdx === normalized;
    if (dot.classList) {
      dot.classList.toggle("is-active", isActive);
    }
  });

  return activeQuestionIndex;
}

export function flipQuestionCard(delta) {
  return setActiveQuestionCard(activeQuestionIndex + Number(delta || 0));
}

function setStatusPill(text, tone = "ok") {
  const pill = document.getElementById("transport-status-pill");
  if (!pill) return;
  pill.textContent = text;
  if (tone === "warn") {
    pill.style.background = "#fee2e2";
    pill.style.color = "#991b1b";
    pill.style.borderColor = "#2b211b";
  } else if (tone === "busy") {
    pill.style.background = "#fef3c7";
    pill.style.color = "#92400e";
    pill.style.borderColor = "#2b211b";
  } else {
    pill.style.background = "#e4e5fc";
    pill.style.color = "#3c3e82";
    pill.style.borderColor = "#2b211b";
  }
}

function canUseSameOriginProxy() {
  try {
    if (typeof window !== "undefined" && window.location) {
      const proto = String(window.location.protocol || "").toLowerCase();
      return proto === "http:" || proto === "https:";
    }
  } catch (_) {
    // ignore location access errors
  }
  return false;
}

async function callGeminiDecisionsApi(payload, apiKey = "", timeoutMs = 15000) {
  const cleanKey = String(apiKey || "").trim();
  const useLocalProxy = !cleanKey && canUseSameOriginProxy() && typeof fetch === "function";
  if (!cleanKey && !useLocalProxy) {
    throw new Error(
      "Live Gemini Decision 1 (/v1beta/decisions) is unavailable: missing GEMINI_API_KEY. Heuristic Tier 2 fallback is disabled."
    );
  }

  const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
  const timer = controller ? setTimeout(() => controller.abort(), timeoutMs) : null;
  try {
    const t0 = Date.now();
    const wireBody = {
      model: payload.model || "gemini-decision-1",
      input:
        typeof payload.input === "string"
          ? payload.input
          : JSON.stringify(payload.state || {}, null, 2),
      questions: payload.questions,
    };

    const targetUrl = useLocalProxy ? "/api/decisions" : GEMINI_DECISIONS_URL;
    const headers = { "Content-Type": "application/json" };
    if (!useLocalProxy) {
      headers["x-goog-api-key"] = cleanKey;
    }

    const resp = await fetch(targetUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(wireBody),
      signal: controller ? controller.signal : undefined,
    });
    if (!resp.ok) {
      let detail = "";
      try {
        const errJson = await resp.json();
        if (errJson && errJson.error) detail = ` (${errJson.error})`;
      } catch (_) {
        // ignore JSON parse failure on error body
      }
      throw new Error(
        `Live Gemini Decision 1 (/v1beta/decisions) HTTP ${resp.status}: live model unavailable${detail}`
      );
    }
    const json = await resp.json();
    json.model = json.model || "gemini-decision-1";
    json.latency_ms = json.latency_ms || Number((Date.now() - t0).toFixed(1));
    return {
      rawResponse: json,
      sourceLabel: "Google Gemini Decision 1 (/v1beta/decisions)",
    };
  } finally {
    if (timer) clearTimeout(timer);
  }
}

function resolveBrowserGeminiApiKey(explicitKey = "") {
  if (explicitKey && String(explicitKey).trim()) {
    return String(explicitKey).trim();
  }
  if (typeof window !== "undefined") {
    if (window.GEMINI_API_KEY) return String(window.GEMINI_API_KEY).trim();
    if (window.CHARM_GEMINI_API_KEY) return String(window.CHARM_GEMINI_API_KEY).trim();
  }
  try {
    if (typeof localStorage !== "undefined") {
      const stored = localStorage.getItem("GEMINI_API_KEY");
      if (stored) return String(stored).trim();
    }
  } catch (_) {
    // ignore storage access errors
  }
  return "";
}

export async function runSystemOneEvaluation(payload, mode = "gemini_api", apiKey = "") {
  if (mode === "browser") {
    throw new Error(
      "Tier 2 browser heuristic fallback is disabled. Live Gemini Decision 1 (/v1beta/decisions) is required."
    );
  }
  const resolvedKey = resolveBrowserGeminiApiKey(apiKey);
  return await callGeminiDecisionsApi(payload, resolvedKey, 15000);
}

function readResponsesFromDom() {
  const responses = {};
  for (const scenario of OCEAN_SCENARIOS) {
    const el = document.getElementById(scenario.textareaId);
    responses[scenario.id] = el ? String(el.value || "").trim() : "";
  }
  return responses;
}

function updateWordCounters() {
  const dots =
    typeof document !== "undefined" && typeof document.querySelectorAll === "function"
      ? Array.from(document.querySelectorAll(".stack-dot"))
      : [];

  OCEAN_SCENARIOS.forEach((scenario, idx) => {
    const shortKey = scenario.id;
    const textarea = document.getElementById(scenario.textareaId);
    const counter = document.getElementById(`counter-${shortKey}`);
    if (!textarea || !counter) return;
    const text = String(textarea.value || "").trim();
    const words = countWords(text);
    const chars = text.length;
    counter.textContent = `${words} words · ${chars} chars`;
    const isReady = words >= 8 && chars >= 40;
    if (isReady) {
      counter.classList.add("valid");
    } else {
      counter.classList.remove("valid");
    }
    if (dots[idx] && dots[idx].classList) {
      dots[idx].classList.toggle("is-ready", isReady);
    }
  });
}

function renderValidationErrors(validationResult) {
  const banner = document.getElementById("form-error-banner");
  let firstInvalidIndex = -1;
  OCEAN_SCENARIOS.forEach((scenario, idx) => {
    const shortKey = scenario.id;
    const errEl = document.getElementById(`error-${shortKey}`);
    if (!errEl) return;
    const msg = validationResult.errors[scenario.id];
    if (msg) {
      if (firstInvalidIndex === -1) firstInvalidIndex = idx;
      errEl.textContent = msg;
      errEl.hidden = false;
    } else {
      errEl.textContent = "";
      errEl.hidden = true;
    }
  });

  if (firstInvalidIndex !== -1) {
    setActiveQuestionCard(firstInvalidIndex);
  }

  if (banner) {
    if (!validationResult.valid) {
      banner.textContent =
        "Every OCEAN scenario requires an open-ended paragraph (at least 8 words and 40 characters). Multiple-choice shortcuts are not permitted.";
      banner.hidden = false;
    } else {
      banner.textContent = "";
      banner.hidden = true;
    }
  }
}

function renderRadarSvg(profile) {
  const svg = document.getElementById("ocean-radar-svg");
  if (!svg) return;

  const cx = 150;
  const cy = 154;
  const maxR = 102;
  const order = [
    { key: "openness", label: "O" },
    { key: "conscientiousness", label: "C" },
    { key: "extraversion", label: "E" },
    { key: "agreeableness", label: "A" },
    { key: "neuroticism", label: "N" },
  ];

  function polarToCartesian(angleIdx, radiusFraction) {
    const angle = -Math.PI / 2 + (angleIdx * 2 * Math.PI) / 5;
    const r = maxR * radiusFraction;
    return {
      x: Number((cx + r * Math.cos(angle)).toFixed(1)),
      y: Number((cy + r * Math.sin(angle)).toFixed(1)),
    };
  }

  let ringsHtml = "";
  for (const frac of [0.25, 0.5, 0.75, 1.0]) {
    const pts = [0, 1, 2, 3, 4]
      .map((i) => {
        const p = polarToCartesian(i, frac);
        return `${p.x},${p.y}`;
      })
      .join(" ");
    ringsHtml += `<polygon points="${pts}" fill="none" stroke="#cbd5e1" stroke-width="1.2" />`;
  }

  let axesHtml = "";
  let labelsHtml = "";
  order.forEach((item, idx) => {
    const end = polarToCartesian(idx, 1.0);
    const labelPt = polarToCartesian(idx, 1.24);
    const pct = profile && profile.traits && profile.traits[item.key]
      ? profile.traits[item.key].percentage
      : 50;
    axesHtml += `<line x1="${cx}" y1="${cy}" x2="${end.x}" y2="${end.y}" stroke="#94a3b8" stroke-width="1.2" />`;
    labelsHtml += `<text x="${labelPt.x}" y="${labelPt.y}" fill="#573e2b" font-size="12" font-weight="800" font-family="monospace" text-anchor="middle" dominant-baseline="middle">${item.label} ${pct}%</text>`;
  });

  const dataPts = order.map((item, idx) => {
    const pct = profile && profile.traits && profile.traits[item.key]
      ? profile.traits[item.key].percentage
      : 50;
    return polarToCartesian(idx, Math.max(0.08, pct / 100));
  });
  const polygonPoints = dataPts.map((p) => `${p.x},${p.y}`).join(" ");
  const dotsHtml = dataPts
    .map(
      (p) =>
        `<circle cx="${p.x}" cy="${p.y}" r="4.5" fill="#f59e0b" stroke="#1e292b" stroke-width="1.8" />`
    )
    .join("");

  svg.innerHTML = `
    ${ringsHtml}
    ${axesHtml}
    <polygon points="${polygonPoints}" fill="rgba(165, 166, 246, 0.35)" stroke="#787ac8" stroke-width="2.4" />
    ${dotsHtml}
    ${labelsHtml}
  `;
}

function renderMatchedFormatCCard(profile) {
  const cardSlot = document.getElementById("matched-format-c-card");
  if (!cardSlot) return;

  const fc =
    profile && profile.formatC
      ? profile.formatC
      : FLOW_FORMAT_C_BY_CODE.OcEAn || FLOW_FORMAT_C_PERSONAS[0];

  const prob = typeof fc.probability === "number" && Number.isFinite(fc.probability) ? fc.probability : 0.5;
  const barWidth = Math.max(6, Math.min(100, Math.round(prob * 100)));
  const fcCode = escapeHtml(fc.code || "OcEAn");
  const fcNumber = escapeHtml(fc.number || "");
  const fcArchetype = escapeHtml(fc.archetype || "");
  const fcCritter = escapeHtml(String(fc.critter || "").trim());
  const fcDescription = escapeHtml(fc.description || "");
  const letterPills = String(fc.code || "OcEAn")
    .split("")
    .map((ch) => {
      const safeCh = escapeHtml(ch);
      const safeUpper = escapeHtml(ch.toUpperCase());
      const isHigh = ch === ch.toUpperCase();
      return `<span class="fc-letter ${isHigh ? "fc-high" : "fc-low"}" title="${safeUpper}: ${isHigh ? "High" : "Low"}">${safeCh}</span>`;
    })
    .join("");

  cardSlot.innerHTML = `
    <div
      class="format-c-card is-matched"
      data-format-c="${fcCode}"
      title="Matched Flow Format C #${fcNumber} ${fcCode} (${fcArchetype} · ${fcCritter})"
    >
      <div class="fc-card-top">
        <span class="fc-num">#${fcNumber}</span>
        <span class="fc-code-letters">${letterPills}</span>
        <span class="fc-prob">${(prob * 100).toFixed(1)}%</span>
      </div>
      <div class="fc-card-title">
        <strong>${fcArchetype}</strong>
        <span class="fc-critter">${fcCritter}</span>
      </div>
      <p class="fc-desc">${fcDescription}</p>
      <div class="prob-track fc-prob-track">
        <div class="prob-fill" style="width: ${barWidth}%"></div>
      </div>
    </div>
  `;
}

function renderProfileToDom(profile, requestPayload, sourceLabel = "Gemini Decision 1") {
  lastResultProfile = profile;

  const codeBadge = document.getElementById("ocean-code-badge");
  if (codeBadge) codeBadge.textContent = profile.oceanCode;

  const formatCBadge = document.getElementById("format-c-badge");
  if (formatCBadge && profile.formatC) {
    formatCBadge.textContent = `#${profile.formatC.number} · ${profile.formatC.code}`;
  }

  const metaLine = document.getElementById("results-meta-line");
  if (metaLine) {
    const tokensText = profile.meta && Number.isFinite(Number(profile.meta.inputTokens)) && profile.meta.inputTokens
      ? `${Number(profile.meta.inputTokens)} input tokens`
      : "1 forward pass";
    const latencyText = profile.meta && Number.isFinite(Number(profile.meta.latencyMs)) && profile.meta.latencyMs
      ? `${Number(profile.meta.latencyMs)} ms`
      : "instant";
    metaLine.innerHTML = `<strong>${escapeHtml(sourceLabel)}</strong> · ${escapeHtml(tokensText)} · ${escapeHtml(latencyText)} · 0 text tokens generated`;
  }

  // Archetype & Flow Format C card
  const archBanner = document.getElementById("archetype-banner");
  if (archBanner && archBanner.classList) {
    archBanner.classList.remove("is-awaiting");
  }
  const archTitle = document.getElementById("archetype-title");
  const archTagline = document.getElementById("archetype-tagline");
  const archSummary = document.getElementById("archetype-summary");
  const archConf = document.getElementById("archetype-confidence");
  const archDist = document.getElementById("archetype-distribution");

  if (archTitle) {
    archTitle.textContent = profile.formatC
      ? profile.formatC.archetype
      : profile.archetype.title;
  }
  if (archTagline) {
    archTagline.textContent = profile.formatC
      ? profile.archetype.title
      : profile.archetype.tagline;
  }
  if (archSummary) {
    archSummary.textContent = profile.formatC
      ? profile.formatC.description
      : profile.archetype.summary;
  }
  if (archConf) {
    const confVal = profile.formatC
      ? profile.formatC.probability
      : profile.archetype.confidence;
    archConf.textContent = `${Math.round(confVal * 100)}%`;
  }

  if (archDist) {
    const distItems =
      profile.formatC && Array.isArray(profile.formatC.topCombos)
        ? profile.formatC.topCombos.map((c) => ({
            label: `#${c.number} ${c.code} · ${c.archetype}`,
            title: `${c.code} (${c.archetype} — ${c.critter}): ${c.description}`,
            probability: c.probability,
          }))
        : profile.archetype.distribution.map((item) => ({
            label: item.title,
            title: item.title,
            probability: item.probability,
          }));

    const topProb = distItems.length > 0 ? Math.max(0.01, distItems[0].probability) : 1;

    archDist.innerHTML = distItems
      .map((item, idx) => {
        const itemProb = typeof item.probability === "number" && Number.isFinite(item.probability) ? item.probability : 0;
        const pct = Math.max(0, Math.min(100, (itemProb / topProb) * 100)).toFixed(1);
        const topClass = idx === 0 ? "top" : "";
        const fillClass = idx === 0 ? "prob-fill" : "prob-fill muted";
        return `
          <div class="dist-row">
            <span class="dist-label ${topClass}" title="${escapeHtml(item.title)}">${escapeHtml(item.label)}</span>
            <div class="prob-track"><div class="${fillClass}" style="width: ${pct}%"></div></div>
            <span class="prob-val">${(itemProb * 100).toFixed(0)}%</span>
          </div>
        `;
      })
      .join("");
  }

  // Clear awaiting state on the Trait by the Numbers card
  const chimeraCard = document.getElementById("chimera-breakdown-card");
  if (chimeraCard && chimeraCard.classList) {
    chimeraCard.classList.remove("is-awaiting");
  }

  // Radar SVG
  renderRadarSvg(profile);

  // Noul indicators
  const gamingBadge = document.getElementById("noul-gaming-badge");
  const gamingBar = document.getElementById("noul-gaming-bar");
  if (gamingBadge && gamingBar) {
    const p = profile.flags.rubricGamingProbability;
    gamingBadge.textContent = `${profile.flags.isRubricGaming ? "FLAGGED" : "authentic"} · p=${p.toFixed(2)}`;
    gamingBadge.className = `noul-badge ${profile.flags.isRubricGaming ? "flag-true" : ""}`;
    gamingBar.className = `prob-fill ${profile.flags.isRubricGaming ? "warn" : ""}`;
    gamingBar.style.width = `${Math.min(100, Math.round(p * 100))}%`;
  }

  const reflBadge = document.getElementById("noul-reflection-badge");
  const reflBar = document.getElementById("noul-reflection-bar");
  if (reflBadge && reflBar) {
    const p = profile.flags.selfReflectionProbability;
    reflBadge.textContent = `${profile.flags.isHighSelfReflection ? "HIGH" : "moderate"} · p=${p.toFixed(2)}`;
    reflBadge.className = `noul-badge ${profile.flags.isHighSelfReflection ? "flag-positive" : ""}`;
    reflBar.style.width = `${Math.min(100, Math.round(p * 100))}%`;
  }

  // Found Persona text description inside Traits in Detail card (32 Flow Big Five combinations)
  const wildPersonaCard = document.getElementById("wild-persona-card");
  const wildPersonaName = document.getElementById("wild-persona-name");
  const wildPersonaDesc = document.getElementById("wild-persona-desc");
  const wildPersonaSuperpowers = document.getElementById("wild-persona-superpowers");
  const wildPersonaCryptonite = document.getElementById("wild-persona-cryptonite");
  const wildPersonaMatches = document.getElementById("wild-persona-matches");
  const wildPersonaOpposite = document.getElementById("wild-persona-opposite");
  if (profile.formatC && wildPersonaName && wildPersonaDesc) {
    const fc = profile.formatC;
    if (wildPersonaCard && wildPersonaCard.classList) {
      wildPersonaCard.classList.remove("is-awaiting");
    }
    wildPersonaName.textContent = `${fc.archetype} (${fc.code})`;
    wildPersonaDesc.textContent = fc.description;

    const traitInsights = {
      O: {
        superpower: "creative framing and novel abstractions",
        cryptonite: "over-engineering unfamiliar territory",
      },
      o: {
        superpower: "proven, reliable playbooks",
        cryptonite: "resisting unconventional approaches",
      },
      C: {
        superpower: "methodical execution and thorough verification",
        cryptonite: "getting bogged down in perfectionism",
      },
      c: {
        superpower: "rapid improvisation and adaptability",
        cryptonite: "skipping edge-case checks or structure",
      },
      E: {
        superpower: "energizing collaboration and clear momentum",
        cryptonite: "over-communicating or moving too fast solo",
      },
      e: {
        superpower: "focused, autonomous deep work",
        cryptonite: "under-sharing context with collaborators",
      },
      A: {
        superpower: "diplomatic consensus and team alignment",
        cryptonite: "hesitating to push back on flawed ideas",
      },
      a: {
        superpower: "direct, candid critique",
        cryptonite: "coming across blunt or overly adversarial",
      },
      N: {
        superpower: "early risk and edge-case vigilance",
        cryptonite: "over-hedging or second-guessing under pressure",
      },
      n: {
        superpower: "calm composure under ambiguity",
        cryptonite: "underestimating subtle failure modes",
      },
    };
    const letters = String(fc.code || "").split("");
    const formatList = (items) => {
      if (items.length === 0) return "";
      const joined =
        items.length === 1
          ? items[0]
          : `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
      return joined.charAt(0).toUpperCase() + joined.slice(1) + ".";
    };
    const superpowersList = letters
      .slice(0, 3)
      .map((ch) => traitInsights[ch] && traitInsights[ch].superpower)
      .filter(Boolean);
    const cryptoniteList = [letters[1], letters[3], letters[4]]
      .map((ch) => traitInsights[ch] && traitInsights[ch].cryptonite)
      .filter(Boolean);
    if (wildPersonaSuperpowers) {
      wildPersonaSuperpowers.textContent = formatList(superpowersList);
    }
    if (wildPersonaCryptonite) {
      wildPersonaCryptonite.textContent = formatList(cryptoniteList);
    }
    if (wildPersonaMatches && letters.length === 5) {
      const flip = (ch) => (ch === ch.toUpperCase() ? ch.toLowerCase() : ch.toUpperCase());
      const compCode1 = `${letters[0]}${flip(letters[1])}${letters[2]}${letters[3]}${flip(letters[4])}`;
      const compCode2 = `${flip(letters[0])}${flip(letters[1])}${flip(letters[2])}A${letters[4]}`;
      const match1 = FLOW_FORMAT_C_BY_CODE[compCode1];
      const match2 = FLOW_FORMAT_C_BY_CODE[compCode2];
      const matches = [match1, match2].filter(
        (m, idx, arr) => m && m.code !== fc.code && arr.findIndex((x) => x && x.code === m.code) === idx
      );
      wildPersonaMatches.innerHTML = matches
        .map(
          (m) => {
            const descText = m.description ? m.description.charAt(0).toLowerCase() + m.description.slice(1) : "";
            return `<li><strong>#${escapeHtml(m.number)} ${escapeHtml(m.archetype)} (${escapeHtml(m.code)}):</strong> ${escapeHtml(descText)}</li>`;
          }
        )
        .join("");
    }
    if (wildPersonaOpposite && letters.length === 5) {
      const flip = (ch) => (ch === ch.toUpperCase() ? ch.toLowerCase() : ch.toUpperCase());
      const oppCode = letters.map(flip).join("");
      const opp = FLOW_FORMAT_C_BY_CODE[oppCode];
      if (opp) {
        const oppDesc = opp.description ? opp.description.charAt(0).toLowerCase() + opp.description.slice(1) : "";
        wildPersonaOpposite.innerHTML = `<li><strong>#${escapeHtml(opp.number)} ${escapeHtml(opp.archetype)} (${escapeHtml(opp.code)}):</strong> ${escapeHtml(oppDesc)}</li>`;
      }
    }
  }

  // 5 OCEAN Trait Score Cards + Per-Card Star Footers + Medallion Badges
  const badgeMap = {
    openness: "badge-o-val",
    conscientiousness: "badge-c-val",
    extraversion: "badge-e-val",
    agreeableness: "badge-a-val",
    neuroticism: "badge-n-val",
  };

  for (const scenario of OCEAN_SCENARIOS) {
    const t = profile.traits[scenario.trait];
    if (!t) continue;
    const starsEl = document.getElementById(`stars-${scenario.id}`);
    if (starsEl) {
      starsEl.innerHTML = "";
    }
    const miniEl = document.getElementById(`mini-${scenario.id}`);
    if (miniEl) {
      miniEl.textContent = `Gemini: ${t.percentage}% (${t.rawScore.toFixed(1)}/4)`;
    }
  }

  for (const meta of TRAIT_DISPLAY_META) {
    const t = profile.traits[meta.trait];
    if (!t) continue;
    const starCount = Math.max(1, Math.min(5, Math.round(t.scale1to5)));
    const badgeEl = document.getElementById(badgeMap[meta.trait]);
    if (badgeEl) {
      badgeEl.textContent = `${t.percentage}% (${"★".repeat(starCount)})`;
    }
  }

  const cardsContainer = document.getElementById("trait-cards-container");
  if (cardsContainer) {
    cardsContainer.innerHTML = TRAIT_DISPLAY_META.map((meta) => {
      const t = profile.traits && profile.traits[meta.trait];
      if (!t || !Array.isArray(t.levels) || t.levels.length === 0) return "";
      const topLevelIdx = t.levels.reduce(
        (bestIdx, cur, idx, arr) =>
          (Number(cur.probability) || 0) > (Number(arr[bestIdx].probability) || 0) ? idx : bestIdx,
        0
      );
      const levelRows = t.levels
        .map((lvl) => {
          const isTop = lvl.index === topLevelIdx;
          const lvlProb = typeof lvl.probability === "number" && Number.isFinite(lvl.probability) ? lvl.probability : 0;
          const pct = Math.max(0, Math.min(100, lvlProb * 100)).toFixed(1);
          const safeLabel = escapeHtml(lvl.label);
          return `
            <div class="level-row">
              <span class="dist-label ${isTop ? "top" : ""}" title="${safeLabel}">${Number(lvl.index) || 0}. ${safeLabel}</span>
              <div class="prob-track"><div class="prob-fill ${isTop ? "" : "muted"}" style="width: ${pct}%"></div></div>
              <span class="prob-val">${lvlProb.toFixed(2)}</span>
            </div>
          `;
        })
        .join("");

      const rawScore = typeof t.rawScore === "number" && Number.isFinite(t.rawScore) ? t.rawScore : 0;
      const pctNum = typeof t.percentage === "number" && Number.isFinite(t.percentage) ? Math.round(t.percentage) : 0;
      return `
        <div class="trait-result-card" data-trait="${escapeHtml(t.id)}">
          <div class="trait-result-head">
            <span class="trait-result-title">${escapeHtml(t.code)} · ${escapeHtml(t.title)} <small style="color:#64748b;font-weight:600">(${escapeHtml(t.band)})</small></span>
            <span class="trait-result-metrics">${pctNum}% · ${rawScore.toFixed(2)}/4</span>
          </div>
          <div class="level-bars">${levelRows}</div>
        </div>
      `;
    }).join("");
  }

  // Raw JSON Inspector
  const reqPre = document.getElementById("raw-request-pre");
  const respPre = document.getElementById("raw-response-pre");
  if (reqPre && requestPayload) {
    reqPre.textContent = JSON.stringify(requestPayload, null, 2);
  }
  if (respPre && profile.rawSystemOneResponse) {
    respPre.textContent = JSON.stringify(profile.rawSystemOneResponse, null, 2);
  }

  // Machine-readable JSON output sink for visiting browser agents
  const modelInput = document.getElementById("agent-model");
  const harnessInput = document.getElementById("agent-harness");
  const resultEnvelope = {
    status: "complete",
    protocol: "charm.v1",
    transport: sourceLabel,
    agent_id: profile.agentId,
    agent_model: (modelInput && modelInput.value.trim()) || "",
    agent_harness: (harnessInput && harnessInput.value.trim()) || "",
    profile,
  };
  const sink = document.getElementById("ocean-result-json");
  if (sink) {
    sink.textContent = JSON.stringify(resultEnvelope, null, 2);
  }
  const copyBtn = document.getElementById("copy-result-btn");
  if (copyBtn) {
    copyBtn.disabled = false;
  }
  if (typeof window !== "undefined" && typeof window.dispatchEvent === "function" && typeof CustomEvent === "function") {
    window.dispatchEvent(new CustomEvent("charm:scored", { detail: resultEnvelope }));
  }
  if (isServerApiReachable()) {
    fetch("/api/latest-result", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(resultEnvelope),
    })
      .then((r) => {
        if (r.status === 404) serverApiAvailable = false;
        return r.ok ? r.json() : null;
      })
      .then((data) => {
        if (data && typeof data.version === "number") {
          lastKnownServerVersion = Math.max(lastKnownServerVersion, data.version);
        }
      })
      .catch(() => {
        serverApiAvailable = false;
      });
  }
}

export function fillResponses(
  responsesMap,
  agentId = "",
  agentModel = "",
  agentHarness = ""
) {
  const idInput = document.getElementById("agent-id");
  const modelInput = document.getElementById("agent-model");
  const harnessInput = document.getElementById("agent-harness");
  if (idInput && agentId) idInput.value = agentId;
  if (modelInput && agentModel) modelInput.value = agentModel;
  if (harnessInput && typeof agentHarness === "string" && agentHarness) {
    harnessInput.value = agentHarness;
  }

  for (let idx = 0; idx < OCEAN_SCENARIOS.length; idx++) {
    const scenario = OCEAN_SCENARIOS[idx];
    const qKey = `q${idx + 1}`;
    const qAltKey = `question_${idx + 1}`;
    const el = document.getElementById(scenario.textareaId);
    const val =
      responsesMap &&
      (typeof responsesMap[qKey] === "string"
        ? responsesMap[qKey]
        : typeof responsesMap[qAltKey] === "string"
        ? responsesMap[qAltKey]
        : typeof responsesMap[scenario.id] === "string"
        ? responsesMap[scenario.id]
        : typeof responsesMap[scenario.trait] === "string"
        ? responsesMap[scenario.trait]
        : typeof responsesMap[scenario.trait.charAt(0).toUpperCase()] === "string"
        ? responsesMap[scenario.trait.charAt(0).toUpperCase()]
        : null);
    if (el && typeof val === "string") {
      el.value = val;
    }
  }
  updateWordCounters();
  setStatusPill("Answers Ready · Click 'Score Your Persona!'", "ok");
  const readyBanner = document.getElementById("prefill-ready-banner");
  if (readyBanner) {
    readyBanner.textContent = "🐾 Agent answers loaded — please click Score Your Persona! to evaluate.";
    readyBanner.hidden = false;
  }
}

export function resetMat({ syncServer = true } = {}) {
  lastResultProfile = null;

  const qBadgeReset = {
    openness: ["badge-o-val", "Q1"],
    conscientiousness: ["badge-c-val", "Q2"],
    extraversion: ["badge-e-val", "Q3"],
    agreeableness: ["badge-a-val", "Q4"],
    neuroticism: ["badge-n-val", "Q5"],
  };

  for (const scenario of OCEAN_SCENARIOS) {
    const shortKey = scenario.id;
    const textarea = document.getElementById(scenario.textareaId);
    if (textarea) textarea.value = "";

    const miniEl = document.getElementById(`mini-${shortKey}`);
    if (miniEl) miniEl.textContent = "Gemini: —";

    const starsEl = document.getElementById(`stars-${shortKey}`);
    if (starsEl) starsEl.innerHTML = "";

    const errEl = document.getElementById(`error-${shortKey}`);
    if (errEl) {
      errEl.textContent = "";
      errEl.hidden = true;
    }
  }

  for (const [trait, [badgeId, qLabel]] of Object.entries(qBadgeReset)) {
    const badgeEl = document.getElementById(badgeId);
    if (badgeEl) badgeEl.textContent = qLabel;
  }

  updateWordCounters();
  setActiveQuestionCard(0);
  clearLocalState();
  if (syncServer && isServerApiReachable()) {
    fetch("/api/reset", { method: "POST" })
      .then((r) => {
        if (r.status === 404) serverApiAvailable = false;
      })
      .catch(() => {
        serverApiAvailable = false;
      });
  }

  const banner = document.getElementById("form-error-banner");
  if (banner) {
    banner.textContent = "";
    banner.hidden = true;
  }
  const readyBanner = document.getElementById("prefill-ready-banner");
  if (readyBanner) {
    readyBanner.textContent = "";
    readyBanner.hidden = true;
  }

  // Reset "Your Persona Is" slot
  const archBanner = document.getElementById("archetype-banner");
  if (archBanner && archBanner.classList) {
    archBanner.classList.add("is-awaiting");
  }
  const codeBadge = document.getElementById("ocean-code-badge");
  if (codeBadge) codeBadge.textContent = "O~ C~ E~ A~ N~";
  const formatCBadge = document.getElementById("format-c-badge");
  if (formatCBadge) formatCBadge.textContent = "#—";
  const archTitle = document.getElementById("archetype-title");
  if (archTitle) archTitle.textContent = "Awaiting Score";
  const archTagline = document.getElementById("archetype-tagline");
  if (archTagline) archTagline.textContent = "Summon Gemini Decision 1 to score!";
  const archConf = document.getElementById("archetype-confidence");
  if (archConf) archConf.textContent = "—";
  const radarSvg = document.getElementById("ocean-radar-svg");
  if (radarSvg) radarSvg.innerHTML = "";
  const archSummary = document.getElementById("archetype-summary");
  if (archSummary) archSummary.textContent = "";
  const archDist = document.getElementById("archetype-distribution");
  if (archDist) archDist.innerHTML = "";

  // Reset "CHIMERA TRAIT SPLIT" card
  const chimeraCard = document.getElementById("chimera-breakdown-card");
  if (chimeraCard && chimeraCard.classList) {
    chimeraCard.classList.add("is-awaiting");
  }
  const metaLine = document.getElementById("results-meta-line");
  if (metaLine) metaLine.textContent = "Single forward pass · 0 tokens generated";
  const matchedCard = document.getElementById("matched-format-c-card");
  if (matchedCard) matchedCard.innerHTML = "";
  const cardsContainer = document.getElementById("trait-cards-container");
  if (cardsContainer) cardsContainer.innerHTML = "";

  // Reset "Traits in Detail" card
  const wildPersonaCard = document.getElementById("wild-persona-card");
  if (wildPersonaCard && wildPersonaCard.classList) {
    wildPersonaCard.classList.add("is-awaiting");
  }
  const wildPersonaName = document.getElementById("wild-persona-name");
  if (wildPersonaName) wildPersonaName.textContent = "Awaiting Score";
  const wildPersonaDesc = document.getElementById("wild-persona-desc");
  if (wildPersonaDesc) wildPersonaDesc.textContent = "";
  const wildPersonaSuperpowers = document.getElementById("wild-persona-superpowers");
  if (wildPersonaSuperpowers) wildPersonaSuperpowers.textContent = "";
  const wildPersonaCryptonite = document.getElementById("wild-persona-cryptonite");
  if (wildPersonaCryptonite) wildPersonaCryptonite.textContent = "";
  const wildPersonaMatches = document.getElementById("wild-persona-matches");
  if (wildPersonaMatches) wildPersonaMatches.innerHTML = "";
  const wildPersonaOpposite = document.getElementById("wild-persona-opposite");
  if (wildPersonaOpposite) wildPersonaOpposite.innerHTML = "";

  const copyBtn = document.getElementById("copy-result-btn");
  if (copyBtn) {
    copyBtn.disabled = true;
    copyBtn.textContent = "Copy JSON";
  }

  // Reset Raw JSON inspector & machine-readable sink
  const reqPre = document.getElementById("raw-request-pre");
  if (reqPre) reqPre.textContent = "{}";
  const respPre = document.getElementById("raw-response-pre");
  if (respPre) respPre.textContent = "{}";
  const sink = document.getElementById("ocean-result-json");
  if (sink) {
    sink.textContent = JSON.stringify(
      {
        status: "awaiting_submission",
        protocol: "charm.v1",
        decision_model: "gemini-decision-1",
      },
      null,
      2
    );
  }
}

export function loadPreset(presetKey) {
  const preset = PRESET_AGENTS[presetKey] || PRESET_AGENTS.explorer;
  fillResponses(preset.responses, preset.agentId, preset.label);
  return preset;
}

export function loadFormatCCombo(code) {
  const persona = FLOW_FORMAT_C_BY_CODE[code] || FLOW_FORMAT_C_PERSONAS[0];
  const responses = buildResponsesForFormatC(persona.code);
  const agentId = `flow-${persona.number}-${persona.code}-${persona.archetype.toLowerCase()}`;
  const modelLabel = `Flow #${persona.number} ${persona.code} · ${persona.archetype} (${String(persona.critter || "").trim()})`;
  fillResponses(responses, agentId, modelLabel);
  return { persona, agentId, responses };
}

const CHARM_STORAGE_KEY = "charm.state.v1";
let lastKnownServerVersion = 0;
let serverApiAvailable = true;

function isHttpOriginWithFetch() {
  return (
    typeof fetch === "function" &&
    typeof window !== "undefined" &&
    window.location &&
    String(window.location.origin || "").startsWith("http")
  );
}

function isServerApiReachable() {
  return serverApiAvailable && isHttpOriginWithFetch();
}

async function copyTextWithFeedback(text, btn, defaultLabel, fallbackTitle) {
  if (text && typeof navigator !== "undefined" && navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      btn.textContent = "Copied!";
      setTimeout(() => {
        btn.textContent = defaultLabel;
      }, 1600);
      return;
    } catch {
      // fallback below
    }
  }
  if (typeof window !== "undefined" && typeof window.prompt === "function") {
    window.prompt(fallbackTitle, text);
  }
}

function readLocalState() {
  if (typeof localStorage === "undefined") return null;
  try {
    const raw = localStorage.getItem(CHARM_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}

function saveLocalState(patch) {
  if (typeof localStorage === "undefined" || !patch || typeof patch !== "object") return;
  try {
    const prev = readLocalState() || {};
    localStorage.setItem(CHARM_STORAGE_KEY, JSON.stringify({ ...prev, ...patch }));
  } catch {
    // ignore storage quota / private mode errors
  }
}

function clearLocalState() {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.removeItem(CHARM_STORAGE_KEY);
  } catch {
    // ignore
  }
}

function collectCurrentFormState() {
  const answers = {};
  for (let idx = 0; idx < OCEAN_SCENARIOS.length; idx++) {
    const s = OCEAN_SCENARIOS[idx];
    const el = document.getElementById(s.textareaId);
    if (el && typeof el.value === "string") {
      answers[`q${idx + 1}`] = el.value;
    }
  }
  const idInput = document.getElementById("agent-id");
  const modelInput = document.getElementById("agent-model");
  const harnessInput = document.getElementById("agent-harness");
  return {
    agent_id: idInput ? idInput.value : "",
    agent_model: modelInput ? modelInput.value : "",
    agent_harness: harnessInput ? harnessInput.value : "",
    answers,
  };
}

function applyServerState(state, { isInitialSync = false } = {}) {
  if (!state || typeof state !== "object" || typeof state.version !== "number") return;
  if (state.version <= lastKnownServerVersion) return;
  const prevVersion = lastKnownServerVersion;
  lastKnownServerVersion = state.version;

  const prefill = state.prefill && typeof state.prefill === "object" ? state.prefill : null;
  const result = state.result && typeof state.result === "object" ? state.result : null;

  if (!prefill && result && result.status === "awaiting_submission") {
    if (!isInitialSync && prevVersion > 0) {
      clearLocalState();
    }
    return;
  }

  let appliedAnswers = null;
  let agentId = "";
  let agentModel = "";
  let agentHarness = "";

  const isComplete = Boolean(result && result.status === "complete" && (result.raw_decisions || result.profile));

  if (prefill) {
    const ans = prefill.answers && typeof prefill.answers === "object" ? prefill.answers : prefill;
    if (ans && (ans.q1 || ans.question_1 || ans.openness_scenario || ans.openness)) {
      appliedAnswers = ans;
      agentId = prefill.agent_id || "";
      agentModel = prefill.agent_model || prefill.model || "";
      agentHarness = prefill.agent_harness || prefill.harness || "";
      if (!isComplete) {
        resetMat({ syncServer: false });
      }
      fillResponses(ans, agentId, agentModel, agentHarness);
    }
  }

  if (isComplete) {
    const effectiveAgentId = result.agent_id || agentId || "external-agent";
    const profile = result.raw_decisions
      ? normalizeOceanProfile(result.raw_decisions, effectiveAgentId)
      : result.profile;
    const reqPayload =
      result.request_payload ||
      state.request_payload ||
      (appliedAnswers ? buildSystemOnePayload(effectiveAgentId, appliedAnswers) : {});
    renderProfileToDom(profile, reqPayload, "Gemini Decision 1 (gemini-decision-1)");
    setStatusPill("Scored · Gemini Decision 1", "ok");
    const banner = document.getElementById("form-error-banner");
    if (banner) {
      banner.textContent = "";
      banner.hidden = true;
    }
    const readyBanner = document.getElementById("prefill-ready-banner");
    if (readyBanner) {
      readyBanner.textContent = "";
      readyBanner.hidden = true;
    }
    saveLocalState({
      ...collectCurrentFormState(),
      request_payload: reqPayload,
      raw_decisions: result.raw_decisions || null,
      profile: result.raw_decisions ? null : profile,
      server_version: state.version,
    });
  } else if (appliedAnswers) {
    saveLocalState({
      ...collectCurrentFormState(),
      request_payload: null,
      raw_decisions: null,
      server_version: state.version,
    });
  }
}

export async function handleEvaluateSubmit(event) {
  if (event && typeof event.preventDefault === "function") {
    event.preventDefault();
  }

  const responses = readResponsesFromDom();
  const validation = validateParagraphResponses(responses);
  renderValidationErrors(validation);
  if (!validation.valid) {
    return null;
  }

  const idInput = document.getElementById("agent-id");
  const agentId = (idInput && idInput.value.trim()) || "anonymous-llm-agent";

  const btn = document.getElementById("evaluate-btn");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Scoring...";
  }
  setStatusPill("Running Gemini Decision 1...", "busy");

  const payload = buildSystemOnePayload(agentId, responses);

  try {
    const { rawResponse, sourceLabel } = await runSystemOneEvaluation(
      payload,
      "gemini_api",
      ""
    );
    const banner = document.getElementById("form-error-banner");
    if (banner) {
      banner.textContent = "";
      banner.hidden = true;
    }
    const readyBanner = document.getElementById("prefill-ready-banner");
    if (readyBanner) {
      readyBanner.textContent = "";
      readyBanner.hidden = true;
    }
    const profile = normalizeOceanProfile(rawResponse, agentId);
    renderProfileToDom(profile, payload, "Gemini Decision 1 (gemini-decision-1)");
    setStatusPill(`Scored · ${sourceLabel}`, "ok");
    saveLocalState({
      ...collectCurrentFormState(),
      request_payload: payload,
      raw_decisions: rawResponse,
      server_version: lastKnownServerVersion,
    });
    return profile;
  } catch (err) {
    const errMsg = String((err && err.message) || err);
    const banner = document.getElementById("form-error-banner");
    if (banner) {
      banner.textContent = `Evaluation error: ${errMsg}`;
      banner.hidden = false;
    }
    setStatusPill("Error · Live Model Unavailable", "warn");
    const sink = document.getElementById("ocean-result-json");
    if (sink) {
      sink.textContent = JSON.stringify(
        {
          status: "error",
          protocol: "charm.v1",
          decision_model: "gemini-decision-1",
          error: errMsg,
        },
        null,
        2
      );
    }
    throw err;
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "🐾 Score Your Persona!";
    }
  }
}

function initCharmApp() {
  // Expose programmatic API for autonomous browser agents
  if (typeof window !== "undefined") {
    window.CHARM_AGENT_API = {
      protocol: "charm.v1",
      decisionModel: "gemini-decision-1",
      getQuestions: () =>
        OCEAN_SCENARIOS.map((s) => ({
          id: s.id,
          thread: s.thread,
          title: s.title,
          prompt: s.prompt,
        })),
      getFormatCPersonas: () => FLOW_FORMAT_C_PERSONAS,
      fillResponses,
      loadPreset,
      loadFormatCCombo,
      renderProfileToDom,
      resetMat,
      setActiveQuestionCard,
      flipQuestionCard,
      getActiveQuestionIndex: () => activeQuestionIndex,
      evaluate: () => handleEvaluateSubmit(null),
      getLastResult: () => lastResultProfile,
      getResultJson: () => {
        const sink = document.getElementById("ocean-result-json");
        try {
          return sink ? JSON.parse(sink.textContent || "{}") : null;
        } catch {
          return null;
        }
      },
      waitForResult: () =>
        new Promise((resolve) => {
          const sink = document.getElementById("ocean-result-json");
          try {
            const current = sink ? JSON.parse(sink.textContent || "{}") : null;
            if (current && current.status === "complete") {
              resolve(current);
              return;
            }
          } catch {
            // ignore
          }
          window.addEventListener("charm:scored", (ev) => resolve(ev.detail), { once: true });
        }),
    };
  }

  const copyAgentPromptBtn = document.getElementById("copy-agent-prompt-btn");
  if (copyAgentPromptBtn) {
    copyAgentPromptBtn.addEventListener("click", () => {
      const origin = isHttpOriginWithFetch()
        ? window.location.origin
        : "http://127.0.0.1:8787";
      const promptText = `Take the CHARM personality assessment: read ${origin}/llms.txt, fetch GET ${origin}/api/questions, write honest 2-5 sentence paragraph answers for q1-q15, and POST { agent_id, agent_model, agent_harness, answers: { q1..q15 } } to ${origin}/api/submit.\n\nWhen done, ask a human to click the 'Score Your Persona!' button in the app to reveal your traits!`;
      copyTextWithFeedback(promptText, copyAgentPromptBtn, "Copy Prompt", "Copy agent prompt:");
    });
  }

  const copyBtn = document.getElementById("copy-result-btn");
  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      const sink = document.getElementById("ocean-result-json");
      const text = sink ? sink.textContent : "";
      copyTextWithFeedback(text, copyBtn, "Copy JSON", "Copy scored JSON result:");
    });
  }

  // Default Explorer preset on startup, unless URL/API prefill was provided
  let appliedUrlPrefill = false;
  if (typeof window !== "undefined" && window.location) {
    const params = new URLSearchParams(window.location.search || "");
    const rawAnswers = params.get("answers");
    let prefillMap = null;
    let prefillAgentId = params.get("agent_id") || undefined;
    let prefillModel = params.get("agent_model") || params.get("model") || undefined;
    let prefillHarness = params.get("agent_harness") || params.get("harness") || undefined;

    if (rawAnswers) {
      try {
        const parsed = JSON.parse(rawAnswers);
        if (parsed && typeof parsed === "object") {
          prefillMap = parsed.answers && typeof parsed.answers === "object" ? parsed.answers : parsed;
          prefillAgentId = parsed.agent_id || prefillAgentId;
          prefillModel = parsed.agent_model || parsed.model || prefillModel;
          prefillHarness = parsed.agent_harness || parsed.harness || prefillHarness;
        }
      } catch {
        // ignore malformed answers JSON
      }
    } else {
      const directMap = {};
      for (let idx = 0; idx < OCEAN_SCENARIOS.length; idx++) {
        const s = OCEAN_SCENARIOS[idx];
        const val =
          params.get(`q${idx + 1}`) ||
          params.get(`question_${idx + 1}`) ||
          params.get(s.id) ||
          params.get(s.trait);
        if (typeof val === "string" && val.trim()) {
          directMap[`q${idx + 1}`] = val;
        }
      }
      if (Object.keys(directMap).length > 0) {
        prefillMap = directMap;
      }
    }

    if (prefillMap) {
      fillResponses(prefillMap, prefillAgentId, prefillModel, prefillHarness);
      appliedUrlPrefill = true;
    }
  }

  if (!appliedUrlPrefill) {
    const savedState = readLocalState();
    if (savedState && typeof savedState.server_version === "number") {
      lastKnownServerVersion = savedState.server_version;
    }
    if (savedState && savedState.answers && typeof savedState.answers === "object") {
      fillResponses(
        savedState.answers,
        savedState.agent_id || "",
        savedState.agent_model || "",
        savedState.agent_harness || ""
      );
      if (savedState.raw_decisions || savedState.profile) {
        try {
          const restoredProfile = savedState.raw_decisions
            ? normalizeOceanProfile(savedState.raw_decisions, savedState.agent_id || "saved-agent")
            : savedState.profile;
          renderProfileToDom(
            restoredProfile,
            savedState.request_payload || {},
            "Gemini Decision 1 (gemini-decision-1)"
          );
          setStatusPill("Scored · Restored", "ok");
        } catch {
          // ignore corrupted saved score
        }
      }
    } else {
      resetMat({ syncServer: false });
    }

    const readyBanner = document.getElementById("prefill-ready-banner");
    if (readyBanner) {
      readyBanner.textContent = "";
      readyBanner.hidden = true;
    }
    if (isServerApiReachable()) {
      fetch("/api/state")
        .then((r) => {
          if (r.status === 404) serverApiAvailable = false;
          return r.ok ? r.json() : null;
        })
        .then((state) => applyServerState(state, { isInitialSync: true }))
        .catch(() => {
          serverApiAvailable = false;
        });
    }
  }

  if (typeof setInterval === "function" && isServerApiReachable()) {
    const pollInterval = setInterval(() => {
      if (!isServerApiReachable()) {
        clearInterval(pollInterval);
        return;
      }
      fetch("/api/state")
        .then((r) => {
          if (r.status === 404) {
            serverApiAvailable = false;
            clearInterval(pollInterval);
          }
          return r.ok ? r.json() : null;
        })
        .then((state) => applyServerState(state, { isInitialSync: false }))
        .catch(() => {
          serverApiAvailable = false;
          clearInterval(pollInterval);
        });
    }, 2500);
  }

  const prevBtn = document.getElementById("question-prev-btn");
  if (prevBtn) {
    prevBtn.addEventListener("click", () => flipQuestionCard(-1));
  }
  const nextBtn = document.getElementById("question-next-btn");
  if (nextBtn) {
    nextBtn.addEventListener("click", () => flipQuestionCard(1));
  }
  const dots =
    typeof document !== "undefined" && typeof document.querySelectorAll === "function"
      ? Array.from(document.querySelectorAll(".stack-dot"))
      : [];
  dots.forEach((dot, idx) => {
    dot.addEventListener("click", () => {
      const targetIdx =
        dot.dataset && dot.dataset.stackJump !== undefined
          ? Number(dot.dataset.stackJump)
          : idx;
      setActiveQuestionCard(targetIdx);
    });
  });

  setActiveQuestionCard(0);

  let activeOceanDefIndex = 0;
  const setActiveOceanDefCard = (index) => {
    const cards =
      typeof document !== "undefined" && typeof document.querySelectorAll === "function"
        ? Array.from(document.querySelectorAll("#ocean-def-stack .ocean-def-card"))
        : [];
    const total = cards.length || 5;
    const target = ((Number(index) % total) + total) % total;
    activeOceanDefIndex = target;

    const stack = document.getElementById("ocean-def-stack");
    if (stack && stack.dataset) {
      stack.dataset.activeIndex = String(target);
    }

    cards.forEach((card, idx) => {
      const isCurrent = idx === target;
      if (card.classList) {
        card.classList.toggle("is-active", isCurrent);
      }
      if (card.style) {
        card.style.display = isCurrent ? "flex" : "none";
      }
    });

    const tabs =
      typeof document !== "undefined" && typeof document.querySelectorAll === "function"
        ? Array.from(document.querySelectorAll(".ocean-def-tab"))
        : [];
    tabs.forEach((tab, idx) => {
      const isCurrent = idx === target;
      if (tab.classList) {
        tab.classList.toggle("is-active", isCurrent);
      }
      if (typeof tab.setAttribute === "function") {
        tab.setAttribute("aria-selected", isCurrent ? "true" : "false");
      }
    });
  };

  const oceanDefPrev = document.getElementById("ocean-def-prev-btn");
  if (oceanDefPrev) {
    oceanDefPrev.addEventListener("click", () => setActiveOceanDefCard(activeOceanDefIndex - 1));
  }
  const oceanDefNext = document.getElementById("ocean-def-next-btn");
  if (oceanDefNext) {
    oceanDefNext.addEventListener("click", () => setActiveOceanDefCard(activeOceanDefIndex + 1));
  }
  const oceanDefTabs =
    typeof document !== "undefined" && typeof document.querySelectorAll === "function"
      ? Array.from(document.querySelectorAll(".ocean-def-tab"))
      : [];
  oceanDefTabs.forEach((tab, idx) => {
    tab.addEventListener("click", () => {
      const targetIdx =
        tab.dataset && tab.dataset.oceanDefJump !== undefined
          ? Number(tab.dataset.oceanDefJump)
          : idx;
      setActiveOceanDefCard(targetIdx);
    });
  });
  setActiveOceanDefCard(0);

  const personaTypeStack = document.getElementById("persona-type-stack");
  if (personaTypeStack && Array.isArray(FLOW_FORMAT_C_PERSONAS)) {
    personaTypeStack.innerHTML = FLOW_FORMAT_C_PERSONAS.map(
      (p, idx) => `
        <article class="ocean-def-card persona-type-card ${idx === 0 ? "is-active" : ""}" data-persona-type-index="${idx}" style="display: ${idx === 0 ? "flex" : "none"};">
          <div class="ocean-def-head">
            <span class="medallion-mini">${escapeHtml(p.number)}</span>
            <strong>${escapeHtml(p.archetype)}</strong>
            <small class="persona-code-pill">${escapeHtml(p.code)}</small>
          </div>
          <p class="ocean-def-desc">${escapeHtml(p.description)}</p>
        </article>
      `
    ).join("");
  }

  const personaTypeTabs = document.getElementById("persona-type-tabs");
  if (personaTypeTabs && Array.isArray(FLOW_FORMAT_C_PERSONAS)) {
    personaTypeTabs.innerHTML = FLOW_FORMAT_C_PERSONAS.map(
      (p, idx) =>
        `<button type="button" class="persona-type-tab ${idx === 0 ? "is-active" : ""}" data-persona-type-jump="${idx}" aria-selected="${idx === 0 ? "true" : "false"}" title="#${escapeHtml(p.number)} ${escapeHtml(p.archetype)} (${escapeHtml(p.code)})">${escapeHtml(p.number)}</button>`
    ).join("");
  }

  let activePersonaTypeIndex = 0;
  const setActivePersonaTypeCard = (index) => {
    const cards =
      typeof document !== "undefined" && typeof document.querySelectorAll === "function"
        ? Array.from(document.querySelectorAll("#persona-type-stack .persona-type-card"))
        : [];
    const total = cards.length || FLOW_FORMAT_C_PERSONAS.length || 32;
    const target = ((Number(index) % total) + total) % total;
    activePersonaTypeIndex = target;

    if (personaTypeStack && personaTypeStack.dataset) {
      personaTypeStack.dataset.activeIndex = String(target);
    }

    cards.forEach((card, idx) => {
      const isCurrent = idx === target;
      if (card.classList) {
        card.classList.toggle("is-active", isCurrent);
      }
      if (card.style) {
        card.style.display = isCurrent ? "flex" : "none";
      }
    });

    const tabs =
      typeof document !== "undefined" && typeof document.querySelectorAll === "function"
        ? Array.from(document.querySelectorAll("#persona-type-tabs .persona-type-tab"))
        : [];
    tabs.forEach((tab, idx) => {
      const isCurrent = idx === target;
      if (tab.classList) {
        tab.classList.toggle("is-active", isCurrent);
      }
      if (typeof tab.setAttribute === "function") {
        tab.setAttribute("aria-selected", isCurrent ? "true" : "false");
      }
    });
  };

  if (personaTypeTabs && typeof document !== "undefined" && typeof document.querySelectorAll === "function") {
    Array.from(document.querySelectorAll("#persona-type-tabs .persona-type-tab")).forEach(
      (tab, idx) => {
        tab.addEventListener("click", () => {
          const targetIdx =
            tab.dataset && tab.dataset.personaTypeJump !== undefined
              ? Number(tab.dataset.personaTypeJump)
              : idx;
          setActivePersonaTypeCard(targetIdx);
        });
      }
    );
  }

  const personaPrevBtn = document.getElementById("persona-type-prev-btn");
  if (personaPrevBtn) {
    personaPrevBtn.addEventListener("click", () =>
      setActivePersonaTypeCard(activePersonaTypeIndex - 1)
    );
  }
  const personaNextBtn = document.getElementById("persona-type-next-btn");
  if (personaNextBtn) {
    personaNextBtn.addEventListener("click", () =>
      setActivePersonaTypeCard(activePersonaTypeIndex + 1)
    );
  }
  setActivePersonaTypeCard(0);

  for (const scenario of OCEAN_SCENARIOS) {
    const textarea = document.getElementById(scenario.textareaId);
    if (textarea) {
      textarea.addEventListener("input", () => {
        updateWordCounters();
        saveLocalState(collectCurrentFormState());
      });
    }
  }
  for (const metaId of ["agent-id", "agent-model", "agent-harness"]) {
    const metaEl = document.getElementById(metaId);
    if (metaEl) {
      metaEl.addEventListener("input", () => {
        saveLocalState(collectCurrentFormState());
      });
    }
  }

  const presetIds = [
    ["preset-explorer", "explorer"],
    ["preset-sentinel", "sentinel"],
    ["preset-diplomat", "diplomat"],
    ["preset-adversarial", "adversarial"],
  ];
  for (const [domId, key] of presetIds) {
    const btn = document.getElementById(domId);
    if (btn) {
      btn.addEventListener("click", () => {
        loadPreset(key);
        handleEvaluateSubmit(null).catch(() => {});
      });
    }
  }

  const clearBtn = document.getElementById("clear-btn");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => resetMat({ syncServer: true }));
  }

  const form = document.getElementById("ocean-questionnaire-form");
  if (form) {
    form.addEventListener("submit", (evt) => {
      handleEvaluateSubmit(evt).catch(() => {});
    });
  }
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCharmApp);
  } else {
    initCharmApp();
  }
}
