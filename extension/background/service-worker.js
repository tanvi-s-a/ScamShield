/**
 * service-worker.js
 *
 * Receives messages from the content script and popup, calls the local
 * FastAPI backend, and returns structured results. Also stores the
 * backend address / settings in chrome.storage. Fires a notification and
 * badge when an auto-scan finds a Suspicious/High Risk email.
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

// --- Notification + badge helpers -----------------------------------

const notificationTabMap = new Map();

function notifyIfRisky(result, tabId) {
  if (!result) return;

  if (result.risk_level === "High Risk" || result.risk_level === "Suspicious") {
    const notificationId = `mailshield-${Date.now()}`;
    chrome.notifications.create(notificationId, {
      type: "basic",
      iconUrl: "extension/icons/icon128.png",
      title: result.risk_level === "High Risk"
        ? "⚠️ High-risk email detected"
        : "⚠️ Suspicious email detected",
      message: `${result.classification} (${result.risk_score}/100). ${result.findings[0] || ""}`,
      priority: result.risk_level === "High Risk" ? 2 : 1,
    });
    if (tabId) notificationTabMap.set(notificationId, tabId);
  }

  updateBadge(result, tabId);
}

function updateBadge(result, tabId) {
  if (!tabId) return;
  if (result.risk_level === "High Risk") {
    chrome.action.setBadgeText({ text: "!", tabId });
    chrome.action.setBadgeBackgroundColor({ color: "#d32f2f", tabId });
  } else if (result.risk_level === "Suspicious") {
    chrome.action.setBadgeText({ text: "?", tabId });
    chrome.action.setBadgeBackgroundColor({ color: "#f9a825", tabId });
  } else {
    chrome.action.setBadgeText({ text: "", tabId });
  }
}

// Clicking a notification focuses the Gmail tab it came from.
chrome.notifications.onClicked.addListener((notificationId) => {
  const tabId = notificationTabMap.get(notificationId);
  if (tabId) chrome.tabs.update(tabId, { active: true });
  chrome.notifications.clear(notificationId);
  notificationTabMap.delete(notificationId);
});

// --- Message handling --------------------------------------------------

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "MAILSHIELD_ANALYZE") {
    callAnalyze(message.payload)
      .then((data) => {
        sendResponse({ ok: true, data });
        // Auto-scans (not manual button clicks) trigger notifications.
        if (message.auto) {
          notifyIfRisky(data, sender.tab?.id);
        }
      })
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
// --- Ad-block statistics -----------------------------------------------
// onRuleMatchedDebug is available for unpacked extensions and records each
// request blocked by the declarative network ruleset.
let pendingNetworkBlocks = 0;
let networkCountFlushTimer = null;

async function flushNetworkBlockCount() {
  const amountToAdd = pendingNetworkBlocks;
  pendingNetworkBlocks = 0;
  if (amountToAdd <= 0) return;

  try {
    const stored = await chrome.storage.local.get({ networkBlockedCount: 0 });
    await chrome.storage.local.set({
      networkBlockedCount: Number(stored.networkBlockedCount || 0) + amountToAdd,
    });
  } catch (error) {
    console.warn("MailShield could not update network block counter:", error);
  }
}

if (chrome.declarativeNetRequest.onRuleMatchedDebug) {
  chrome.declarativeNetRequest.onRuleMatchedDebug.addListener(() => {
    pendingNetworkBlocks += 1;
    clearTimeout(networkCountFlushTimer);
    networkCountFlushTimer = setTimeout(flushNetworkBlockCount, 250);
  });
}

// Keep the stored network setting synchronized with the enabled ruleset.
chrome.runtime.onInstalled.addListener(async () => {
  const enabledRulesets = await chrome.declarativeNetRequest.getEnabledRulesets();
  await chrome.storage.local.set({
    networkBlockerEnabled: enabledRulesets.includes("ad_rules"),
  });
});
