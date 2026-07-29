/**
 * service-worker.js
 *
 * Receives messages from the content script and popup, calls the local
 * FastAPI backend, and returns structured results. Also stores the
 * backend address / settings in chrome.storage.
 * Testing
 */

const DEFAULT_SETTINGS = {
  backendUrl: "http://127.0.0.1:8000",
  mode: "analyze_only", // analyze_only | warn_and_disable | safe_preview  (modes beyond analyze_only are stretch goals)
};

async function getSettings() {
  const stored = await chrome.storage.sync.get(DEFAULT_SETTINGS);
  return { ...DEFAULT_SETTINGS, ...stored };
}

async function callAnalyze(emailData) {
  const settings = await getSettings();
  const url = `${settings.backendUrl.replace(/\/$/, "")}/analyze`;

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(emailData),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Backend returned ${response.status}: ${text || response.statusText}`);
  }
  return response.json();
}

async function callHealth() {
  const settings = await getSettings();
  const url = `${settings.backendUrl.replace(/\/$/, "")}/health`;
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Backend returned ${response.status}`);
  return response.json();
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "MAILSHIELD_ANALYZE") {
    callAnalyze(message.payload)
      .then((data) => sendResponse({ ok: true, data }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true; // keep the message channel open for the async response
  }

  if (message.type === "MAILSHIELD_HEALTH") {
    callHealth()
      .then((data) => sendResponse({ ok: true, data }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true;
  }
});
