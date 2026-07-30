const DEFAULTS = { backendUrl: "http://127.0.0.1:8000", mode: "analyze_only" };
const AD_RULESET_ID = "ad_rules";

const networkToggle = document.getElementById("network-blocking");
const cosmeticToggle = document.getElementById("cosmetic-blocking");
const networkCountEl = document.getElementById("network-count");
const cosmeticCountEl = document.getElementById("cosmetic-count");
const adblockStatus = document.getElementById("adblock-status");

function formatCount(value) {
  return Number(value || 0).toLocaleString("en-US");
}

async function loadAdBlockSettings() {
  const [enabledRulesets, stored] = await Promise.all([
    chrome.declarativeNetRequest.getEnabledRulesets(),
    chrome.storage.local.get({
      cosmeticBlockerEnabled: true,
      networkBlockedCount: 0,
      cosmeticBlockedCount: 0
    })
  ]);

  const networkEnabled = enabledRulesets.includes(AD_RULESET_ID);
  networkToggle.checked = networkEnabled;
  cosmeticToggle.checked = stored.cosmeticBlockerEnabled !== false;
  networkCountEl.textContent = formatCount(stored.networkBlockedCount);
  cosmeticCountEl.textContent = formatCount(stored.cosmeticBlockedCount);
  await chrome.storage.local.set({ networkBlockerEnabled: networkEnabled });
}

async function setNetworkBlocking(enabled) {
  networkToggle.disabled = true;
  adblockStatus.textContent = "Updating…";
  try {
    await chrome.declarativeNetRequest.updateEnabledRulesets({
      enableRulesetIds: enabled ? [AD_RULESET_ID] : [],
      disableRulesetIds: enabled ? [] : [AD_RULESET_ID]
    });
    await chrome.storage.local.set({ networkBlockerEnabled: enabled });
    adblockStatus.textContent = enabled ? "Network blocking enabled." : "Network blocking disabled.";
  } catch (error) {
    console.error(error);
    networkToggle.checked = !enabled;
    adblockStatus.textContent = "Could not update network blocking.";
  } finally {
    networkToggle.disabled = false;
  }
}

async function setCosmeticBlocking(enabled) {
  cosmeticToggle.disabled = true;
  adblockStatus.textContent = "Updating…";
  try {
    await chrome.storage.local.set({
      cosmeticBlockerEnabled: enabled,
      adBlockerEnabled: enabled
    });
    adblockStatus.textContent = enabled ? "Cosmetic blocking enabled." : "Cosmetic blocking disabled.";
  } catch (error) {
    console.error(error);
    cosmeticToggle.checked = !enabled;
    adblockStatus.textContent = "Could not update cosmetic blocking.";
  } finally {
    cosmeticToggle.disabled = false;
  }
}

function loadBackendSettings() {
  chrome.storage.sync.get(DEFAULTS, (settings) => {
    document.getElementById("backend-url").value = settings.backendUrl;
    document.getElementById("mode").value = settings.mode;
  });
}

function saveBackendSettings() {
  const backendUrl = document.getElementById("backend-url").value.trim() || DEFAULTS.backendUrl;
  const mode = document.getElementById("mode").value;
  chrome.storage.sync.set({ backendUrl, mode }, () => {
    const status = document.getElementById("save-status");
    status.textContent = "Saved.";
    setTimeout(() => (status.textContent = ""), 1500);
  });
}

networkToggle.addEventListener("change", () => setNetworkBlocking(networkToggle.checked));
cosmeticToggle.addEventListener("change", () => setCosmeticBlocking(cosmeticToggle.checked));

document.getElementById("reset-stats-btn").addEventListener("click", async () => {
  await chrome.storage.local.set({ networkBlockedCount: 0, cosmeticBlockedCount: 0 });
  networkCountEl.textContent = "0";
  cosmeticCountEl.textContent = "0";
  adblockStatus.textContent = "Counters reset.";
});

document.getElementById("save-btn").addEventListener("click", saveBackendSettings);

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName !== "local") return;
  if (changes.networkBlockedCount) {
    networkCountEl.textContent = formatCount(changes.networkBlockedCount.newValue);
  }
  if (changes.cosmeticBlockedCount) {
    cosmeticCountEl.textContent = formatCount(changes.cosmeticBlockedCount.newValue);
  }
});

document.addEventListener("DOMContentLoaded", async () => {
  loadBackendSettings();
  try {
    await loadAdBlockSettings();
  } catch (error) {
    console.error(error);
    adblockStatus.textContent = "Could not load ad blocker settings.";
  }
});
