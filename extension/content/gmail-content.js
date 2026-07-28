/**
 * gmail-content.js
 *
 * Injects a "Analyze with MailShield AI" button above open Gmail messages,
 * calls the local backend via the service worker, and renders the result.
 *
 * MVP SCOPE: this displays findings only. It does not disable links, hide
 * ads, or modify the email content — that is Phase 12/13, a stretch goal.
 */

const BUTTON_ID = "mailshield-analyze-btn";
const PANEL_ID = "mailshield-result-panel";

function injectAnalyzeButton() {
  if (document.getElementById(BUTTON_ID)) return;

  const subjectEl = document.querySelector("h2.hP");
  if (!subjectEl) return;

  const btn = document.createElement("button");
  btn.id = BUTTON_ID;
  btn.textContent = "🛡 Analyze with MailShield AI";
  btn.className = "mailshield-analyze-btn";
  btn.addEventListener("click", handleAnalyzeClick);

  subjectEl.insertAdjacentElement("afterend", btn);
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

function handleAnalyzeClick() {
  const btn = document.getElementById(BUTTON_ID);
  btn.disabled = true;
  btn.textContent = "Analyzing…";

  const emailData = window.__mailshieldExtract ? window.__mailshieldExtract() : null;
  if (!emailData) {
    renderError("Could not find an open email to analyze.");
    resetButton(btn);
    return;
  }

  chrome.runtime.sendMessage({ type: "MAILSHIELD_ANALYZE", payload: emailData }, (response) => {
    resetButton(btn);
    if (chrome.runtime.lastError) {
      renderError(chrome.runtime.lastError.message);
      return;
    }
    if (!response || !response.ok) {
      renderError(response?.error || "Unknown error contacting the backend.");
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
