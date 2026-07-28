/**
 * email-extractor.js
 *
 * Reads the currently open Gmail message from the DOM and returns a
 * structured object matching the backend's /analyze request schema.
 *
 * Gmail's DOM structure is not officially documented and changes over
 * time, so these selectors are best-effort and may need updating if
 * Gmail's layout changes (documented as a known limitation).
 *
 * Nothing here sends data anywhere or opens any link — extraction only.
 */

function getOpenEmailContainer() {
  // Gmail wraps an open message in a div with role="listitem" inside the
  // message view; .adn / .a3s are common (if unstable) content classes.
  return document.querySelector('div[role="listitem"] .adn.ads') ||
         document.querySelector('div[role="listitem"]');
}

function extractSubject() {
  const el = document.querySelector('h2.hP') || document.querySelector('[data-thread-perm-id] h2');
  return el ? el.innerText.trim() : "";
}

function extractSenderInfo(container) {
  // The sender <span> typically carries the display name and the address
  // in an "email" data attribute or a title attribute.
  const senderEl = container?.querySelector('span.gD') || document.querySelector('span.gD');
  if (!senderEl) return { from_address: "", display_name: "" };
  const address = senderEl.getAttribute("email") || "";
  const displayName = senderEl.getAttribute("name") || senderEl.innerText || "";
  return { from_address: address, display_name: displayName.trim() };
}

function extractBodyHtml(container) {
  const bodyEl = container?.querySelector('.a3s') || document.querySelector('.a3s');
  return bodyEl ? bodyEl.innerHTML : "";
}

function extractBodyText(container) {
  const bodyEl = container?.querySelector('.a3s') || document.querySelector('.a3s');
  return bodyEl ? bodyEl.innerText.trim() : "";
}

function extractLinks(container) {
  const scope = container?.querySelector('.a3s') || document;
  return Array.from(scope.querySelectorAll("a[href]")).map(a => ({
    visible_text: a.innerText.trim(),
    href: a.getAttribute("href") || "",
  })).filter(l => l.href && !l.href.startsWith("mailto:"));
}

function extractImages(container) {
  const scope = container?.querySelector('.a3s') || document;
  return Array.from(scope.querySelectorAll("img")).map(img => {
    const style = (img.getAttribute("style") || "").replace(/\s/g, "").toLowerCase();
    const hidden = style.includes("display:none") || style.includes("visibility:hidden");
    return {
      src: img.getAttribute("src") || "",
      width: img.width || parseInt(img.getAttribute("width")) || null,
      height: img.height || parseInt(img.getAttribute("height")) || null,
      hidden,
    };
  }).filter(i => i.src.startsWith("http"));
}

function extractButtons(container) {
  const scope = container?.querySelector('.a3s') || document;
  const buttonLike = Array.from(scope.querySelectorAll('a, button'));
  return buttonLike
    .map(el => ({ text: el.innerText.trim(), target: el.getAttribute("href") || "" }))
    .filter(b => b.text.length > 0 && b.text.length < 40);
}

function extractFormsPresent(container) {
  const scope = container?.querySelector('.a3s') || document;
  return scope.querySelectorAll("form, input[type=password]").length > 0;
}

/**
 * Main extraction entry point. Returns null if no open email is found.
 */
function extractOpenGmailMessage() {
  const container = getOpenEmailContainer();
  if (!container) return null;

  const sender = extractSenderInfo(container);

  return {
    subject: extractSubject(),
    body: extractBodyText(container),
    html_content: extractBodyHtml(container),
    from_address: sender.from_address,
    reply_to_address: "",   // Gmail's visible DOM does not expose Reply-To directly
    return_path: "",        // not available without raw headers ("Show original")
    message_id: "",         // not available without raw headers
    auth_results: { spf: null, dkim: null, dmarc: null }, // optional / best-effort
    links: extractLinks(container),
    images: extractImages(container),
    buttons: extractButtons(container),
    forms_present: extractFormsPresent(container),
  };
}

// Expose to gmail-content.js (both are loaded as classic content scripts,
// sharing the same global scope in Manifest V3 content script contexts)
window.__mailshieldExtract = extractOpenGmailMessage;
