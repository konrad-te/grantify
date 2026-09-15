// The server does the matching. This script only updates the form while it waits.
const form = document.querySelector("#funding-form");
const submitButton = document.querySelector("#submit-button");
const buttonLabel = submitButton?.querySelector(".button-label");
const loadingStatus = document.querySelector("#loading-status");

/** Restore the button and hide the waiting message, including after Back navigation. */
function resetLoadingState() {
  if (!submitButton || !buttonLabel || !loadingStatus) return;

  submitButton.disabled = false;
  submitButton.classList.remove("is-loading");
  submitButton.removeAttribute("aria-busy");
  buttonLabel.textContent = "Find funding";
  loadingStatus.hidden = true;
}

// Show progress and prevent repeat clicks. The browser still submits a normal POST.
form?.addEventListener("submit", () => {
  if (!submitButton || !buttonLabel || !loadingStatus) return;

  submitButton.disabled = true;
  submitButton.classList.add("is-loading");
  submitButton.setAttribute("aria-busy", "true");
  buttonLabel.textContent = "Finding funding…";
  loadingStatus.hidden = false;
});

// Browsers can restore a page from their back/forward cache with the button still disabled.
window.addEventListener("pageshow", resetLoadingState);
