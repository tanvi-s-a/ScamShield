const statusEl = document.getElementById("status");
const adBlockToggle = document.getElementById("ad-block-toggle");
const adBlockState = document.getElementById("ad-block-state");
const adBlockMessage = document.getElementById("ad-block-message");
const AD_RULESET_ID = "ad_rules";

chrome.runtime.sendMessage({ type: "MAILSHIELD_HEALTH" }, (response) => {
  if (chrome.runtime.lastError) {
    statusEl.textContent = "❌ Could not reach backend.";
    statusEl.className = "status status-error";
    return;
  }
  if (response && response.ok) {
    const loaded = response.data.model_loaded;
    statusEl.textContent = loaded
      ? "✅ Backend connected, model loaded"
      : "⚠️ Backend connected, but no model is trained yet";
    statusEl.className = loaded ? "status status-ok" : "status status-warn";
  } else {
    statusEl.textContent = `❌ ${response?.error || "Backend unavailable"}`;
    statusEl.className = "status status-error";
  }
});

function updateAdBlockUi(networkEnabled, cosmeticEnabled) {
  const allEnabled = networkEnabled && cosmeticEnabled;
  const anyEnabled = networkEnabled || cosmeticEnabled;
  adBlockToggle.checked = allEnabled;
  adBlockToggle.indeterminate = anyEnabled && !allEnabled;

  if (allEnabled) {
    adBlockState.textContent = "On — network and cosmetic blocking";
    adBlockState.className = "subtext enabled";
  } else if (anyEnabled) {
    adBlockState.textContent = networkEnabled
      ? "Partial — network blocking only"
      : "Partial — cosmetic blocking only";
    adBlockState.className = "subtext partial";
  } else {
    adBlockState.textContent = "Off — ads are allowed";
    adBlockState.className = "subtext disabled";
  }
}

async function loadAdBlockStatus() {
  try {
    const enabledRulesets = await chrome.declarativeNetRequest.getEnabledRulesets();
    const stored = await chrome.storage.local.get({ cosmeticBlockerEnabled: true });
    const networkEnabled = enabledRulesets.includes(AD_RULESET_ID);
    const cosmeticEnabled = stored.cosmeticBlockerEnabled !== false;
    await chrome.storage.local.set({ networkBlockerEnabled: networkEnabled });
    updateAdBlockUi(networkEnabled, cosmeticEnabled);
  } catch (error) {
    console.error("Could not read ad blocker status:", error);
    adBlockToggle.disabled = true;
    adBlockState.textContent = "Status unavailable";
    adBlockMessage.textContent = "Could not control the ad blocker.";
  }
}

adBlockToggle.addEventListener("change", async () => {
  const enabled = adBlockToggle.checked;
  adBlockToggle.indeterminate = false;
  adBlockToggle.disabled = true;
  adBlockMessage.textContent = "Updating…";

  try {
    await chrome.declarativeNetRequest.updateEnabledRulesets({
      enableRulesetIds: enabled ? [AD_RULESET_ID] : [],
      disableRulesetIds: enabled ? [] : [AD_RULESET_ID]
    });
    await chrome.storage.local.set({
      adBlockerEnabled: enabled,
      networkBlockerEnabled: enabled,
      cosmeticBlockerEnabled: enabled
    });
    updateAdBlockUi(enabled, enabled);
    adBlockMessage.textContent = enabled
      ? "All ad blocking enabled. Refresh open pages if needed."
      : "All ad blocking disabled. Refresh open pages to restore hidden ads.";
  } catch (error) {
    console.error("Could not update ad blocker:", error);
    adBlockMessage.textContent = "Could not update the ad blocker.";
    await loadAdBlockStatus();
  } finally {
    adBlockToggle.disabled = false;
  }
});

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName !== "local") return;
  if (changes.networkBlockerEnabled || changes.cosmeticBlockerEnabled) {
    loadAdBlockStatus();
  }
});

document.getElementById("settings-btn").addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});

loadAdBlockStatus();
