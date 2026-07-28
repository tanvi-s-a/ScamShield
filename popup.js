const masterToggle = document.getElementById("masterToggle");
const adBlockToggle = document.getElementById("adBlockToggle");
const phishingToggle = document.getElementById("phishingToggle");

const statusText = document.getElementById("statusText");
const blockedCount = document.getElementById("blockedCount");
const detailsButton = document.getElementById("detailsButton");
const message = document.getElementById("message");

/**
 * Loads saved extension settings.
 */
async function loadSettings() {
  try {
    const settings = await chrome.storage.local.get({
      protectionEnabled: true,
      adBlockEnabled: true,
      phishingEnabled: true,
      blockedItems: 0
    });

    masterToggle.checked = settings.protectionEnabled;
    adBlockToggle.checked = settings.adBlockEnabled;
    phishingToggle.checked = settings.phishingEnabled;
    blockedCount.textContent = settings.blockedItems;

    updateInterface();
  } catch (error) {
    console.error("Could not load settings:", error);
    message.textContent = "Could not load settings.";
  }
}

/**
 * Updates visible UI based on toggle states.
 */
function updateInterface() {
  const isEnabled = masterToggle.checked;

  if (isEnabled) {
    statusText.textContent = "Active";
    statusText.classList.add("active");
    statusText.classList.remove("inactive");
  } else {
    statusText.textContent = "Paused";
    statusText.classList.add("inactive");
    statusText.classList.remove("active");
  }

  adBlockToggle.disabled = !isEnabled;
  phishingToggle.disabled = !isEnabled;
}

/**
 * Saves the current settings.
 */
async function saveSettings() {
  try {
    await chrome.storage.local.set({
      protectionEnabled: masterToggle.checked,
      adBlockEnabled: adBlockToggle.checked,
      phishingEnabled: phishingToggle.checked
    });

    updateInterface();

    message.textContent = "Settings saved.";

    window.setTimeout(() => {
      message.textContent = "";
    }, 1200);
  } catch (error) {
    console.error("Could not save settings:", error);
    message.textContent = "Could not save settings.";
  }
}

masterToggle.addEventListener("change", saveSettings);
adBlockToggle.addEventListener("change", saveSettings);
phishingToggle.addEventListener("change", saveSettings);

detailsButton.addEventListener("click", () => {
  message.textContent =
    "The details page will be added later.";
});

loadSettings();