/**
 * gmail-content.js
 *
 * Injects a "Analyze with MailShield AI" button above open Gmail messages,
 * calls the local backend via the service worker, and renders the result.
 * Also auto-analyzes newly opened messages in the background and lets the
 * service worker fire a notification if the result is Suspicious/High Risk.
 *
 * MVP SCOPE: this displays findings only. It does not disable links, hide
 * ads, or modify the email content — that is Phase 12/13, a stretch goal.
 */

const BUTTON_ID = "mailshield-analyze-btn";
const PANEL_ID = "mailshield-result-panel";
const analyzedMessageIds = new Set();

function injectAnalyzeButton() {
  const subjectEl = document.querySelector("h2.hP");
  if (!subjectEl) return;

  if (!document.getElementById(BUTTON_ID)) {
    const btn = document.createElement("button");
    btn.id = BUTTON_ID;
    btn.textContent = "🛡 Analyze with MailShield AI";
    btn.className = "mailshield-analyze-btn";
    btn.addEventListener("click", () => handleAnalyzeClick({ auto: false }));
    subjectEl.insertAdjacentElement("afterend", btn);
  }

  autoAnalyzeIfNew();
}

function currentMessageKey() {
  const subject = document.querySelector("h2.hP")?.innerText.trim() || "";
  const sender = document.querySelector("span.gD")?.getAttribute("email") || "";
  return `${sender}::${subject}`;
}

function autoAnalyzeIfNew() {
  const key = currentMessageKey();
  if (!key || analyzedMessageIds.has(key)) return;
  analyzedMessageIds.add(key);
  handleAnalyzeClick({ auto: true });
}

function renderPanel(html) {
  let panel = document.getElementById(PANEL_ID);
  if (!panel) {
    panel = document.createElement("div");
    panel.id = PANEL_ID;
    panel.className = "mailshield-panel";
    const btn = document.getElementById(BUTTON_ID);
    btn.insertAdjacentElement("afterend", panel);
  }
  panel.innerHTML = html;
}

function riskClass(level) {
  if (level === "High Risk") return "mailshield-risk-high";
  if (level === "Suspicious") return "mailshield-risk-suspicious";
  return "mailshield-risk-low";
}

function renderResult(result) {
  const findingsHtml = result.findings.map(f => `<li>${escapeHtml(f)}</li>`).join("");
  const actions = result.blocking_actions || {};
  const recommendedActions = Object.entries(actions)
    .filter(([, v]) => v)
    .map(([k]) => k.replace(/_/g, " "));
  const actionsHtml = recommendedActions.length
    ? `<p class="mailshield-actions"><strong>Recommended protections:</strong> ${recommendedActions.join(", ")}
       <br><em>(Display only in this build — active blocking is a stretch-goal feature.)</em></p>`
    : "";

  renderPanel(`
    <div class="mailshield-header ${riskClass(result.risk_level)}">
      <strong>${escapeHtml(result.classification)}</strong>
      <span>Risk: ${escapeHtml(result.risk_level)} (${result.risk_score}/100)</span>
      <span>Confidence: ${(result.confidence * 100).toFixed(0)}%</span>
    </div>
    <ul class="mailshield-findings">${findingsHtml}</ul>
    ${actionsHtml}
  `);
}

function renderError(message) {
  renderPanel(`<div class="mailshield-header mailshield-risk-error">
    <strong>Analysis failed</strong><span>${escapeHtml(message)}</span>
  </div>`);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function handleAnalyzeClick({ auto = false } = {}) {
  const btn = document.getElementById(BUTTON_ID);
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Analyzing…";
  }

  const emailData = window.__mailshieldExtract ? window.__mailshieldExtract() : null;
  if (!emailData) {
    if (!auto) renderError("Could not find an open email to analyze.");
    if (btn) resetButton(btn);
    return;
  }

  chrome.runtime.sendMessage({ type: "MAILSHIELD_ANALYZE", payload: emailData, auto }, (response) => {
    if (btn) resetButton(btn);
    if (chrome.runtime.lastError) {
      if (!auto) renderError(chrome.runtime.lastError.message);
      return;
    }
    if (!response || !response.ok) {
      if (!auto) renderError(response?.error || "Unknown error contacting the backend.");
      return;
    }
    renderResult(response.data);
  });
}

function resetButton(btn) {
  btn.disabled = false;
  btn.textContent = "🛡 Analyze with MailShield AI";
}

// Gmail is a single-page app; re-check periodically for a newly opened email.
const observer = new MutationObserver(() => injectAnalyzeButton());
observer.observe(document.body, { childList: true, subtree: true });
injectAnalyzeButton();