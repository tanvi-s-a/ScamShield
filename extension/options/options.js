const DEFAULTS = { backendUrl: "http://127.0.0.1:8000", mode: "analyze_only" };

function load() {
  chrome.storage.sync.get(DEFAULTS, (settings) => {
    document.getElementById("backend-url").value = settings.backendUrl;
    document.getElementById("mode").value = settings.mode;
  });
}

function save() {
  const backendUrl = document.getElementById("backend-url").value.trim() || DEFAULTS.backendUrl;
  const mode = document.getElementById("mode").value;
  chrome.storage.sync.set({ backendUrl, mode }, () => {
    const status = document.getElementById("save-status");
    status.textContent = "Saved.";
    setTimeout(() => (status.textContent = ""), 1500);
  });
}

document.addEventListener("DOMContentLoaded", load);
document.getElementById("save-btn").addEventListener("click", save);
