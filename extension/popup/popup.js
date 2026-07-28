const statusEl = document.getElementById("status");

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

document.getElementById("settings-btn").addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});
