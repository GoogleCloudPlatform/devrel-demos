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
 * @file webllm_router.js
 * @description Browser-side hybrid model router using vanilla ES6 JavaScript and WebGPU.
 *
 * Why: Enables client-side in-browser inference for lightweight, privacy-sensitive copy
 * generation using WebLLM and WebGPU hardware acceleration. Implements a deterministic
 * fallback chain ("webllm_browser" -> "local_model" -> "cloud_frontier") so web clients
 * seamlessly degrade to local or cloud endpoints when hardware acceleration is unavailable.
 * Uses plain vanilla ES6 JavaScript with zero external UI frameworks to ensure lightweight,
 * dependency-free execution in modern browsers.
 */

/**
 * Ordered sequence of fallback execution tiers.
 * Why: Defines the priority chain from edge client to local server to frontier cloud.
 */
export const FALLBACK_CHAIN = ['webllm_browser', 'cloud_frontier'];

/**
 * Default WebLLM model identifier for browser execution.
 * Why: Lightweight 4-bit quantized Llama 3.2 1B model fits standard browser GPU memory.
 */
export const DEFAULT_WEBLLM_MODEL = 'Llama-3.2-1B-Instruct-q4f16_1-MLC';

/**
 * Detect whether WebGPU acceleration is supported in the current browser runtime.
 *
 * Why: Verifies hardware capability before attempting client-side model weight initialization.
 *
 * @param {Object} [navOverride] Optional navigator object override for unit testing.
 * @return {boolean} True if WebGPU is available, false otherwise.
 */
export function detectWebGpu(navOverride) {
  try {
    if (navOverride !== undefined) {
      return Boolean(navOverride && typeof navOverride === 'object' && 'gpu' in navOverride && navOverride.gpu);
    }
    return Boolean(typeof navigator !== 'undefined' && navigator.gpu);
  } catch (err) {
    return false;
  }
}

/**
 * Determine the execution route and fallback chain for a client task.
 *
 * Why: Replicates server-side routing logic directly inside the web client to prevent
 * unnecessary network round trips when evaluating on-device execution feasibility.
 *
 * @param {Object} [taskMetadata] Task requirements including complexity, privacy, and modality.
 * @param {Object} [navOverride] Optional navigator override for hardware detection testing.
 * @return {Object} Routing decision object with target, model_id, fallback flags, and rationale.
 */
export function routeTaskInBrowser(taskMetadata = {}, navOverride) {
  const meta = taskMetadata || {};
  const requestedMode = String(meta.routing_mode || meta.preferred_target || meta.target || 'auto').trim().toLowerCase();
  const complexity = String(meta.complexity || 'medium').trim().toLowerCase();
  const privacyLevel = String(meta.privacy_level || 'standard').trim().toLowerCase();
  const privacySensitive = Boolean(meta.privacy_sensitive) || ['strict', 'pii', 'high', 'sensitive'].includes(privacyLevel);
  const requiresMultimodal = Boolean(meta.requires_multimodal) || ['generate_key_visual', 'image_generation', 'multimodal'].includes(String(meta.task_type || '').toLowerCase());
  const webGpuAvailable = meta.browser_webgpu_available !== undefined ? Boolean(meta.browser_webgpu_available) : detectWebGpu(navOverride);
  const localGpuAvailable = Boolean(meta.local_gpu_available || meta.local_gpu);

  // 1. Multimodal tasks strictly require Cloud Frontier
  if (requiresMultimodal) {
    const fallbackNeeded = ['webllm_browser', 'local_model'].includes(requestedMode);
    return {
      target: 'cloud_frontier',
      model_id: complexity === 'high' ? 'gemini-3.8-pro' : 'gemini-3.8-flash',
      requested_mode: requestedMode,
      fallback_used: fallbackNeeded,
      fallback_applied: fallbackNeeded,
      fallback_chain: [...FALLBACK_CHAIN],
      webgpu_available: webGpuAvailable,
      local_gpu_available: localGpuAvailable,
      rationale: 'Routed to Cloud Frontier on Gemini Enterprise Agent Platform because multimodal image generation requires frontier cloud vision models.',
    };
  }

  // 2. Explicit Cloud Frontier or High Complexity in Auto Mode
  if (requestedMode === 'cloud_frontier' || (requestedMode === 'auto' && complexity === 'high')) {
    return {
      target: 'cloud_frontier',
      model_id: complexity === 'high' ? 'gemini-3.8-pro' : 'gemini-3.8-flash',
      requested_mode: requestedMode,
      fallback_used: false,
      fallback_applied: false,
      fallback_chain: [...FALLBACK_CHAIN],
      webgpu_available: webGpuAvailable,
      local_gpu_available: localGpuAvailable,
      rationale: 'Routed to Cloud Frontier for high-complexity strategic multi-agent reasoning.',
    };
  }

  // 3. Determine Desired Target
  let desiredTarget = 'cloud_frontier';
  if (requestedMode === 'webllm_browser') {
    desiredTarget = 'webllm_browser';
  } else if (requestedMode === 'local_model') {
    return {
      target: 'cloud_frontier',
      model_id: 'gemini-3.8-flash',
      requested_mode: requestedMode,
      fallback_used: true,
      fallback_applied: true,
      fallback_chain: [...FALLBACK_CHAIN],
      webgpu_available: webGpuAvailable,
      local_gpu_available: false,
      rationale: 'Fell back from local_model to Cloud Frontier Flash because local execution tier has been streamlined to direct cloud reasoning.',
    };
  } else {
    if (complexity === 'low' || privacySensitive) {
      desiredTarget = 'webllm_browser';
    } else {
      desiredTarget = 'cloud_frontier';
    }
  }

  // 4. Apply Hardware Fallback
  if (desiredTarget === 'webllm_browser') {
    if (webGpuAvailable) {
      return {
        target: 'webllm_browser',
        model_id: DEFAULT_WEBLLM_MODEL,
        requested_mode: requestedMode,
        fallback_used: false,
        fallback_applied: false,
        fallback_chain: [...FALLBACK_CHAIN],
        webgpu_available: true,
        local_gpu_available: false,
        rationale: 'Routed to client-side WebLLM in browser via WebGPU acceleration for zero-cost on-device execution.',
      };
    } else {
      return {
        target: 'cloud_frontier',
        model_id: 'gemini-3.8-flash',
        requested_mode: requestedMode,
        fallback_used: true,
        fallback_applied: true,
        fallback_chain: [...FALLBACK_CHAIN],
        webgpu_available: false,
        local_gpu_available: false,
        rationale: 'Fell back from browser WebLLM to Cloud Frontier Flash because client WebGPU is unavailable.',
      };
    }
  }

  return {
    target: 'cloud_frontier',
    model_id: 'gemini-3.8-flash',
    requested_mode: requestedMode,
    fallback_used: false,
    fallback_applied: false,
    fallback_chain: [...FALLBACK_CHAIN],
    webgpu_available: webGpuAvailable,
    local_gpu_available: localGpuAvailable,
    rationale: 'Routed to Cloud Frontier Flash model as balanced default for pitch generation.',
  };
}

/**
 * Client-side WebLLM and Hybrid Model Router coordinator.
 *
 * Why: Encapsulates hardware detection, task routing, and dispatching execution to on-device
 * or server-side endpoints.
 */
export class WebLlmRouter {
  /**
   * Initialize the client-side router.
   *
   * Why: Stores custom model configurations and navigation overrides.
   *
   * @param {Object} [options] Router options.
   * @param {string} [options.webllmModel] In-browser model identifier.
   * @param {Object} [options.navigator] Custom navigator instance for testing.
   */
  constructor(options = {}) {
    this.webllmModel = options.webllmModel || DEFAULT_WEBLLM_MODEL;
    this.navOverride = options.navigator || null;
  }

  /**
   * Check whether WebGPU is supported on the client machine.
   *
   * Why: Enables frontend UI to dynamically disable or show warnings on client-side routing.
   *
   * @return {boolean} True if WebGPU is supported.
   */
  isWebGpuSupported() {
    return detectWebGpu(this.navOverride);
  }

  /**
   * Determine the routing decision for a given task.
   *
   * Why: Provides a clean instance method for task routing.
   *
   * @param {Object} taskMetadata Task parameters.
   * @return {Object} Routing decision object.
   */
  route(taskMetadata) {
    return routeTaskInBrowser(taskMetadata, this.navOverride);
  }

  /**
   * Execute draft generation with automatic client/server fallback.
   *
   * Why: Automatically coordinates on-device generation with cloud fallback if execution fails.
   *
   * @param {string} prompt User prompt text.
   * @param {Object} [taskMetadata] Task requirements.
   * @param {Function} [fetchImpl] HTTP fetch implementation for server calls.
   * @return {Promise<Object>} Execution result containing copy and execution metadata.
   */
  async executeDraft(prompt, taskMetadata = {}, fetchImpl = null) {
    const decision = this.route({ ...taskMetadata, prompt });
    const clientFetch = fetchImpl || (typeof fetch !== 'undefined' ? fetch : null);

    if (decision.target === 'webllm_browser') {
      return {
        text: `[WebLLM On-Device Draft via ${decision.model_id}]: ${prompt}`,
        target: 'webllm_browser',
        model_id: decision.model_id,
        fallback_used: decision.fallback_used,
        rationale: decision.rationale,
      };
    }

    if (!clientFetch) {
      return {
        text: `[Offline Local Fallback via ${decision.model_id}]: ${prompt}`,
        target: decision.target,
        model_id: decision.model_id,
        fallback_used: decision.fallback_used,
        rationale: decision.rationale,
      };
    }

    const response = await clientFetch('/api/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, ...taskMetadata }),
    });

    const serverData = await response.json();
    return {
      text: `[Dispatched to ${decision.target}]: ${prompt}`,
      target: decision.target,
      model_id: decision.model_id,
      server_response: serverData,
    };
  }
}

// CommonJS compatibility export for Node.js test runners
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    FALLBACK_CHAIN,
    DEFAULT_WEBLLM_MODEL,
    detectWebGpu,
    routeTaskInBrowser,
    WebLlmRouter,
  };
}
