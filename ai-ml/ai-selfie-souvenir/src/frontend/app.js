// --- FRONTEND WEBCAM & API CONTROLLER ---

// --- CONSTANTS ---
const API_ENDPOINTS = {
  CONFIG: "/api/config",
  STATUS: "/api/status",
  SELFIE: "/api/selfie",
};

const STATUS_TEXT = {
  GEMINI_API: "Agent Platform API",
  MOCK_PILLOW: "Mock Mode (Gemini API not configured)",
  MOCK_OFFLINE: "Mock Mode (no status API)",
  HOST_LOCAL: "Local Host",
  HOST_CLOUD_RUN: "Cloud Run",
};

const DEFAULT_IMAGE_DIMENSION = 1024;

let mediaStream = null;
let lastCapturedImage = null;
let appConfig = null;

document.addEventListener("DOMContentLoaded", () => {
  initApp();
});

async function initApp() {
  const btnStartCamera = document.getElementById("btn-start-camera");
  const btnCapturePhoto = document.getElementById("btn-capture-photo");
  const btnRetake = document.getElementById("btn-retake");
  const btnRelaunch = document.getElementById("btn-relaunch");
  const promptHeader = document.getElementById("prompt-header");

  // Button click listeners
  if (btnStartCamera) btnStartCamera.addEventListener("click", startWebcam);
  if (btnCapturePhoto)
    btnCapturePhoto.addEventListener("click", captureAndGenerateSelfie);
  if (btnRetake) btnRetake.addEventListener("click", retakePhoto);
  if (btnRelaunch) btnRelaunch.addEventListener("click", relaunchGeneration);

  if (promptHeader) {
    promptHeader.addEventListener("click", () => {
      const card = promptHeader.closest(".prompt-card");
      if (card) card.classList.toggle("collapsed");
    });
  }

  // Load dynamic UI configuration and API status
  await loadAppConfig();
  checkApiStatus();

  // Initialize lightbox zoom viewer
  initLightbox();
}

// --- HELPER UTILITIES ---

function getEl(id) {
  return document.getElementById(id);
}

function setDisplay(idOrEl, displayStyle) {
  const el = typeof idOrEl === "string" ? getEl(idOrEl) : idOrEl;
  if (el) el.style.display = displayStyle;
}

function setControlsState(state) {
  setDisplay("controls-start", state === "start" ? "block" : "none");
  setDisplay("controls-capture", state === "capture" ? "block" : "none");
  setDisplay("controls-reset", state === "reset" ? "block" : "none");
}

function deduceBaseImageUrl(uri) {
  if (!uri) return "";
  const cleanUri = uri.trim();
  if (cleanUri.startsWith("gs://")) {
    return cleanUri.replace(/^gs:\/\//, "https://storage.googleapis.com/");
  }
  return cleanUri;
}

function updateStatusBadge(isLive, text = STATUS_TEXT.GEMINI_API) {
  const badge = getEl("status-badge");
  const statusText = getEl("status-text");
  if (!badge) return;
  badge.classList.remove("hidden");
  badge.className = isLive
    ? "status-badge live-mode"
    : "status-badge fallback-mode";
  if (statusText) statusText.innerHTML = text;
}

function updateHostBadge(isCloudRun, region, location, showRegion = true) {
  const badge = getEl("host-status-badge");
  const textEl = getEl("host-status-text");
  if (!badge) return;
  badge.classList.remove("hidden");
  badge.className = "status-badge info-mode";
  if (textEl) {
    if (isCloudRun) {
      if (showRegion && location && location.flag && location.city) {
        textEl.innerHTML = `Cloud Run (${location.city}, ${location.flag})`;
      } else if (showRegion && region) {
        textEl.innerHTML = `Cloud Run (${region})`;
      } else {
        textEl.innerHTML = STATUS_TEXT.HOST_CLOUD_RUN;
      }
    } else {
      textEl.innerHTML = STATUS_TEXT.HOST_LOCAL;
    }
  }
}

function setLoadingState(active) {
  const loadingContainer = getEl("loading-container");
  if (loadingContainer) {
    loadingContainer.classList.toggle("active", active);
  }
}

function setResultImage(imageBlob) {
  const resultImage = getEl("result-image");
  if (!resultImage) return;
  if (resultImage.src && resultImage.src.startsWith("blob:")) {
    URL.revokeObjectURL(resultImage.src);
  }
  resultImage.src = URL.createObjectURL(imageBlob);
  setDisplay(resultImage, "block");
}

function clearResultImage() {
  const resultImage = getEl("result-image");
  if (resultImage) {
    if (resultImage.src && resultImage.src.startsWith("blob:")) {
      URL.revokeObjectURL(resultImage.src);
    }
    setDisplay(resultImage, "none");
    resultImage.src = "";
  }
  setDisplay("output-placeholder", "block");
}

function clearCapturedImage() {
  const capturedImage = getEl("captured-image");
  if (capturedImage) {
    setDisplay(capturedImage, "none");
    capturedImage.src = "";
  }
}

// Helper: send image blob to FastAPI /api/selfie
async function sendSelfieApiRequest(blob) {
  const formData = new FormData();
  formData.append("image", blob, "capture.jpg");

  const response = await fetch(API_ENDPOINTS.SELFIE, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let detail = "Unknown server error.";
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) detail = errorData.detail;
    } catch (_) {}
    const err = new Error(detail);
    err.isApiError = true;
    throw err;
  }

  return await response.blob();
}

// --- DYNAMIC CONFIG & STATUS ---

async function loadAppConfig() {
  try {
    const res = await fetch(API_ENDPOINTS.CONFIG);
    if (!res.ok) return;
    appConfig = await res.json();

    // Hydrate UI elements dynamically strictly from backend config
    if (appConfig.event_title && appConfig.app_name) {
      const titleEl = document.querySelector(".app-title");
      if (titleEl) {
        titleEl.innerHTML = `${appConfig.event_title} | <span class="highlight">${appConfig.app_name}</span>`;
      }
      document.title = `${appConfig.event_title} | ${appConfig.app_name}`;
    }

    if (appConfig.app_subtitle) {
      const subEl = document.querySelector(".app-subtitle");
      if (subEl) subEl.textContent = appConfig.app_subtitle;
    }

    const baseImgEl = getEl("reference-base-img");
    if (baseImgEl) {
      if (appConfig.base_image_uri) {
        baseImgEl.src = deduceBaseImageUrl(appConfig.base_image_uri);
      }
      if (appConfig.base_image_label) {
        baseImgEl.alt = appConfig.base_image_label;
      }
    }

    if (appConfig.privacy_notice) {
      const privEl = document.querySelector(".privacy-text");
      if (privEl) privEl.textContent = appConfig.privacy_notice;
    }

    if (appConfig.footer_credit) {
      const footerEl = document.querySelector(".app-footer p");
      if (footerEl) footerEl.innerHTML = appConfig.footer_credit;
    }

    // Apply custom brand colors dynamically
    if (appConfig.primary_color) {
      document.documentElement.style.setProperty(
        "--brand-gold",
        appConfig.primary_color,
      );
    }
    if (appConfig.accent_color) {
      document.documentElement.style.setProperty(
        "--brand-yellow",
        appConfig.accent_color,
      );
    }
  } catch (err) {
    console.warn("Could not load dynamic app configuration:", err);
  }
}

async function checkApiStatus() {
  const promptText = getEl("prompt-text");

  try {
    const res = await fetch(API_ENDPOINTS.STATUS);
    const data = await res.json();

    if (data.client_initialized) {
      updateStatusBadge(true, STATUS_TEXT.GEMINI_API);
    } else {
      updateStatusBadge(false, STATUS_TEXT.MOCK_PILLOW);
    }

    updateHostBadge(
      Boolean(data.is_cloud_run),
      data.region,
      data.location,
      Boolean(data.show_cloud_run_region),
    );

    if (data.prompt && promptText) {
      promptText.value = data.prompt;
    }
  } catch (err) {
    console.error("Error fetching status API:", err);
    updateStatusBadge(false, STATUS_TEXT.MOCK_OFFLINE);
    updateHostBadge(false);
    if (promptText) {
      promptText.value = "Failed to load system prompt from backend.";
    }
  }
}

// --- ACCESS WEBCAM ---

async function startWebcam() {
  const video = getEl("webcam-video");

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: DEFAULT_IMAGE_DIMENSION },
        height: { ideal: DEFAULT_IMAGE_DIMENSION },
        facingMode: "user",
      },
      audio: false,
    });

    if (video) {
      video.srcObject = mediaStream;
      setDisplay(video, "block");
    }
    setDisplay("camera-placeholder", "none");
    setControlsState("capture");
  } catch (err) {
    console.error("Error accessing the webcam: ", err);
    showToast(
      "Unable to access the webcam. Please verify camera permissions are granted in your browser settings.",
      "error",
    );
  }
}

// --- STOP WEBCAM ---

function stopWebcam() {
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }
  const video = getEl("webcam-video");
  if (video) video.srcObject = null;
}

// --- CAPTURE SNAPSHOT & GENERATE SELFIE ---

async function captureAndGenerateSelfie() {
  const video = getEl("webcam-video");
  const canvas = getEl("capture-canvas");

  if (!mediaStream) {
    showToast(
      "Camera feed is inactive. Please open your webcam first.",
      "warning",
    );
    return;
  }

  const width = video.videoWidth || DEFAULT_IMAGE_DIMENSION;
  const height = video.videoHeight || DEFAULT_IMAGE_DIMENSION;
  canvas.width = width;
  canvas.height = height;

  const ctx = canvas.getContext("2d", { alpha: false });
  ctx.translate(width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(video, 0, 0, width, height);

  canvas.toBlob(async (blob) => {
    if (!blob) {
      showToast("Failed to capture image blob from canvas.", "error");
      return;
    }
    lastCapturedImage = blob;

    const capturedImage = getEl("captured-image");
    if (capturedImage) {
      capturedImage.src = canvas.toDataURL("image/jpeg");
      setDisplay(capturedImage, "block");
    }
    setDisplay(video, "none");

    setLoadingState(true);
    setDisplay("output-placeholder", "none");
    setDisplay("result-image", "none");

    try {
      const imageBlob = await sendSelfieApiRequest(blob);
      setResultImage(imageBlob);
      setControlsState("reset");

      updateStatusBadge(true, STATUS_TEXT.GEMINI_API);
      showToast("Composed a new image using Nano Banana!", "success");
    } catch (err) {
      console.error("Error calling /api/selfie: ", err);
      const msg = err.isApiError
        ? "Image generation failed: " + err.message
        : "Connection error connecting to AI backend. Please verify your FastAPI server is online.";
      showToast(msg, "error");
      resetToStart();
    } finally {
      setLoadingState(false);
    }
  }, "image/jpeg");

  stopWebcam();
}

// --- RESET VIEWS ---

function retakePhoto() {
  clearCapturedImage();
  setDisplay("webcam-video", "block");
  clearResultImage();
  setControlsState("capture");
  startWebcam();
}

function resetToStart() {
  stopWebcam();
  setDisplay("webcam-video", "none");
  clearCapturedImage();
  setDisplay("camera-placeholder", "block");
  clearResultImage();
  setControlsState("start");
}

// --- TOAST NOTIFICATIONS ---

function showToast(message, type = "error") {
  const container = getEl("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;

  const icons = { error: "❌", warning: "⚠️", success: "✅" };
  const icon = icons[type] || "ℹ️";

  toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${message}</span>
    `;

  container.appendChild(toast);

  setTimeout(() => toast.classList.add("show"), 10);
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// --- RELAUNCH GENERATION ---

async function relaunchGeneration() {
  if (!lastCapturedImage) {
    showToast("No photo has been captured yet to relaunch.", "warning");
    return;
  }

  setLoadingState(true);

  try {
    const imageBlob = await sendSelfieApiRequest(lastCapturedImage);
    setResultImage(imageBlob);
    showToast("Successfully regenerated image!", "success");
  } catch (err) {
    console.error("Error during relaunch fetch:", err);
    const msg = err.isApiError
      ? "Failed to regenerate: " + err.message
      : "Connection error connecting to AI backend.";
    showToast(msg, "error");
  } finally {
    setLoadingState(false);
  }
}

// --- LIGHTBOX ZOOM VIEWER ---

function buildLightboxCaption(img, w, h) {
  if (img.id === "reference-base-img" && appConfig) {
    const attr = appConfig.base_image_attribution;
    const attrUrl = appConfig.base_image_attribution_url;
    if (attr && attrUrl) {
      return `<a href="${attrUrl}" target="_blank">${attr}</a><br><span style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px; display: inline-block;">Image Size: ${w} x ${h}</span>`;
    }
    if (attr) {
      return `<span>${attr}</span><br><span style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px; display: inline-block;">Image Size: ${w} x ${h}</span>`;
    }
  }
  return `<span style="font-size: 0.85rem; color: #cbd5e1;">Image Size: ${w} x ${h}</span>`;
}

function initLightbox() {
  const lightbox = getEl("lightbox-modal");
  const lightboxImg = getEl("lightbox-img");
  const closeBtn = document.querySelector(".lightbox-close");
  const captionEl = getEl("lightbox-caption");

  const imagesToBind = [
    getEl("reference-base-img"),
    getEl("captured-image"),
    getEl("result-image"),
  ];

  imagesToBind.forEach((img) => {
    if (!img) return;
    img.addEventListener("click", () => {
      if (img.style.display !== "none" && img.src) {
        if (lightboxImg) lightboxImg.src = img.src;

        const w = img.naturalWidth || img.width;
        const h = img.naturalHeight || img.height;

        if (captionEl) {
          captionEl.innerHTML = buildLightboxCaption(img, w, h);
        }

        if (lightbox) lightbox.classList.add("active");
      }
    });
  });

  if (captionEl) {
    captionEl.addEventListener("click", (e) => e.stopPropagation());
  }

  if (lightbox) {
    lightbox.addEventListener("click", () =>
      lightbox.classList.remove("active"),
    );
  }
  if (closeBtn) {
    closeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (lightbox) lightbox.classList.remove("active");
    });
  }

  document.addEventListener("keydown", (e) => {
    if (
      e.key === "Escape" &&
      lightbox &&
      lightbox.classList.contains("active")
    ) {
      lightbox.classList.remove("active");
    }
  });
}
