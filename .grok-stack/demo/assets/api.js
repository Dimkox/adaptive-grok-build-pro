const REQUEST_TIMEOUT_MS = 8000;

async function request(path, options = {}) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(path, {
      ...options,
      cache: "no-store",
      credentials: "same-origin",
      signal: controller.signal,
    });
    const payload = await response.json();
    if (!response.ok) {
      const error = new Error(payload.error?.message || "The local demo request failed.");
      error.code = payload.error?.code || "request_failed";
      error.retryable = Boolean(payload.error?.retryable);
      throw error;
    }
    return payload;
  } finally {
    window.clearTimeout(timer);
  }
}

export function getSnapshot() {
  return request("/api/v1/snapshot");
}

export function previewPrompt(prompt) {
  return request("/api/v1/preview", {
    method: "POST",
    headers: {"Content-Type": "application/json", "X-Adaptive-Demo": "1"},
    body: JSON.stringify({schema_version: 1, prompt}),
  });
}
