/* Global keyboard shortcut for search */
document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    document.querySelector(".header .search input")?.focus();
  }
});

function ensureAdminLoadingOverlay() {
  let overlay = document.querySelector("[data-admin-loading]");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.className = "admin-loading";
    overlay.setAttribute("data-admin-loading", "");
    overlay.setAttribute("role", "status");
    overlay.setAttribute("aria-live", "polite");
    overlay.innerHTML = '<div class="admin-loading-card"><span class="admin-loading-spinner" aria-hidden="true"></span><strong>Working...</strong><span data-admin-loading-message>Saving changes...</span></div>';
    document.body.appendChild(overlay);
  }
  return overlay;
}

function adminLoadingMessage(form) {
  if (form.dataset.loadingMessage) return form.dataset.loadingMessage;
  if (form.enctype && form.enctype.indexOf("multipart/form-data") >= 0) return "Uploading files...";
  if (form.closest(".payment-action-form")) return "Updating payment status...";
  if (form.action && form.action.indexOf("/action/") >= 0) return "Updating admin action...";
  return "Saving changes...";
}

function setAdminButtonLoading(button, label) {
  if (!button || button.dataset.loadingActive === "true") return;
  button.dataset.loadingActive = "true";
  button.dataset.originalHtml = button.innerHTML;
  if (button.name) button.setAttribute("aria-disabled", "true");
  else button.disabled = true;
  button.classList.add("is-loading");
  button.innerHTML = '<span class="admin-btn-spinner" aria-hidden="true"></span><span>' + (label || "Please wait...") + '</span>';
}

let lastAdminSubmitter = null;
document.addEventListener("click", (e) => {
  const button = e.target.closest('button[type="submit"], input[type="submit"]');
  if (button && button.form) lastAdminSubmitter = button;
}, true);

document.addEventListener("submit", (e) => {
  const form = e.target;
  if (!(form instanceof HTMLFormElement) || form.dataset.loadingSkip === "true") return;
  setTimeout(() => {
    if (e.defaultPrevented || form.dataset.loadingStarted === "true") return;
    form.dataset.loadingStarted = "true";
    const message = adminLoadingMessage(form);
    const submitter = e.submitter || (lastAdminSubmitter && lastAdminSubmitter.form === form ? lastAdminSubmitter : null) || form.querySelector('button[type="submit"], input[type="submit"]');
    setAdminButtonLoading(submitter, message);
    const overlay = ensureAdminLoadingOverlay();
    const messageEl = overlay.querySelector("[data-admin-loading-message]");
    if (messageEl) messageEl.textContent = message;
    overlay.classList.add("is-visible");
    document.documentElement.classList.add("has-admin-loading");
  }, 0);
});
