// One form request streams the extracted profile, then the server-rendered results.
const form = document.querySelector("#funding-form");
const button = document.querySelector("#submit-button");
const textarea = document.querySelector("#description");
const progress = document.querySelector("#matching-progress");
const status = document.querySelector("#loading-status");
const loadingBar = document.querySelector("#loading-bar");
const loadingFill = document.querySelector("#loading-fill");
let progressTimer;
let progressValue = 0;
let progressCeiling = 42;

function paintProgress(value) {
  progressValue = value;
  loadingFill.style.width = `${value}%`;
}

function stopProgress() {
  clearInterval(progressTimer);
  progressTimer = undefined;
}

function startProgress() {
  stopProgress();
  loadingFill.style.transition = "none";
  paintProgress(0);
  void loadingFill.offsetWidth;
  loadingFill.style.transition = "";
  progressCeiling = 42;
  paintProgress(4);
  // Estimated movement between server events; only a finished search reaches 100%.
  progressTimer = setInterval(() => {
    paintProgress(progressValue + (progressCeiling - progressValue) * 0.018);
  }, 250);
}
const highlighted = document.querySelector("#highlighted-description");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
let busy = false;

const pause = () => new Promise(resolve => setTimeout(resolve, reducedMotion.matches ? 0 : 350));
// A decorative layer paints highlights under the native, editable textarea.
function syncHighlights() {
  highlighted.style.width = `${textarea.clientWidth}px`;
  highlighted.style.height = `${textarea.clientHeight}px`;
  highlighted.scrollTop = textarea.scrollTop;
  highlighted.scrollLeft = textarea.scrollLeft;
}
textarea.addEventListener("scroll", syncHighlights);
function resetChecklist() {
  document.querySelectorAll(".checklist-item").forEach(item => {
    item.classList.remove("is-found");
    item.querySelector(".checklist-icon").textContent = "○";
    item.querySelector(".checklist-status").textContent = "";
  });
  document.querySelector(".checklist-note").textContent = "After your search, checkmarks will show which details we identified.";
}
textarea.addEventListener("input", () => {
  highlighted.replaceChildren();
  resetChecklist();
});
if (window.ResizeObserver) new ResizeObserver(syncHighlights).observe(textarea);
window.addEventListener("resize", syncHighlights);

function setStage(step, message) {
  const floors = [0, 4, 45, 58, 100];
  progressCeiling = [0, 42, 55, 94, 100][step];
  if (step === 4) stopProgress();
  paintProgress(Math.max(progressValue, floors[step]));
  status.textContent = message;
  loadingBar.setAttribute("aria-valuetext", message);
}

function setBusy(value) {
  busy = value;
  button.disabled = value;
  button.classList.toggle("is-loading", value);
  button.setAttribute("aria-busy", String(value));
  button.querySelector(".button-label").textContent = value ? "Finding funding…" : "Find funding";
  textarea.readOnly = value;
}

function showProfile(profile, description) {
  // Mark only excerpts actually present in the submitted text, never invented positions.
  const phrases = [...(profile.source_phrases || []), profile.country, profile.industry,
    profile.company_size, profile.project_type?.replaceAll("_", " ")]
    .filter(value => typeof value === "string" && value.trim().length > 1)
    .sort((a, b) => b.length - a.length);
  const spans = [];
  const source = description.toLowerCase();
  const wordCharacter = character => /[\p{L}\p{N}_]/u.test(character || "");
  for (const phrase of phrases) {
    const search = phrase.toLowerCase();
    let start = source.indexOf(search);
    while (start !== -1) {
      const end = start + phrase.length;
      const wholePhrase = !(wordCharacter(search[0]) && wordCharacter(source[start - 1])) &&
        !(wordCharacter(search.at(-1)) && wordCharacter(source[end]));
      if (wholePhrase && !spans.some(span => start < span.end && end > span.start)) spans.push({start, end});
      start = source.indexOf(search, end);
    }
  }
  highlighted.replaceChildren();
  let position = 0;
  for (const span of spans.sort((a, b) => a.start - b.start)) {
    highlighted.append(document.createTextNode(description.slice(position, span.start)));
    const mark = document.createElement("mark");
    mark.textContent = description.slice(span.start, span.end);
    highlighted.append(mark);
    position = span.end;
  }
  highlighted.append(document.createTextNode(description.slice(position)));
  // Keep a final empty line aligned with the textarea's scrollable content.
  highlighted.append(document.createTextNode("\n"));
  syncHighlights();
}

if (window.fetch && window.ReadableStream) form?.addEventListener("submit", async event => {
  event.preventDefault();
  if (busy) return;
  const description = textarea.value;
  resetChecklist();
  setBusy(true);
  progress.hidden = false;
  progress.classList.remove("has-error");
  highlighted.replaceChildren();
  document.querySelector("#matching-output").hidden = true;
  startProgress();
  setStage(1, "Understanding your project…");
  let completed = false;
  let reader;
  try {
    const response = await fetch(form.action, {
      method: "POST", body: new FormData(form), headers: {Accept: "application/x-ndjson"},
    });
    if (!response.ok || !response.body) throw new Error("Request failed");
    reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const {value, done} = await reader.read();
      buffer += decoder.decode(value, {stream: !done});
      let newline;
      while ((newline = buffer.indexOf("\n")) !== -1) {
        const line = buffer.slice(0, newline);
        buffer = buffer.slice(newline + 1);
        if (!line.trim()) continue;
        const update = JSON.parse(line);
        if (update.type === "profile") {
          showProfile(update.profile, description);
          setStage(2, "Building your profile…");
          await pause();
          setStage(3, "Comparing funding opportunities…");
        } else if (update.type === "complete") {
          const page = new DOMParser().parseFromString(update.html, "text/html");
          const output = page.querySelector("#matching-output");
          if (!output) throw new Error("Missing results");
          if (update.status === 200) {
            setStage(4, "Your ranked shortlist is ready.");
            await pause();
          }
          document.querySelector("#matching-output").replaceWith(output);
          const checklist = page.querySelector("#description-checklist");
          if (checklist) document.querySelector("#description-checklist").replaceWith(checklist);
          completed = true;
          if (update.status === 200) {
            progress.hidden = true;
            output.classList.add("results-reveal");
          } else {
            progress.hidden = true;
          }
          output.focus({preventScroll: true});
          output.scrollIntoView({behavior: reducedMotion.matches ? "instant" : "smooth", block: "start"});
        }
      }
      if (done) break;
    }
    if (!completed) throw new Error("Incomplete response");
  } catch (error) {
    stopProgress();
    progress.hidden = false;
    progress.classList.add("has-error");
    status.textContent = "Matching was interrupted. Your description is saved above; please try again.";
    loadingBar.setAttribute("aria-valuetext", "Search interrupted");
    if (reader) await reader.cancel().catch(() => {});
  } finally {
    stopProgress();
    setBusy(false);
  }
});

window.addEventListener("pagehide", stopProgress);

window.addEventListener("pageshow", event => {
  if (event.persisted) { setBusy(false); progress.hidden = true; }
});

// Result cards arrive after the request, so handle tooltip hover and focus at the document level.
function updateConfidenceTooltip(event) {
  const icon = event.target.closest?.(".confidence-info");
  const tooltip = icon?.nextElementSibling;
  if (!tooltip?.classList.contains("confidence-tooltip")) return;
  const visible = icon.matches(":hover, :focus");
  tooltip.hidden = !visible;
  // Inline visibility also handles browsers still holding the previous stylesheet in cache.
  tooltip.style.visibility = visible ? "visible" : "";
  tooltip.style.opacity = visible ? "1" : "";
}

for (const type of ["pointerover", "pointerout", "focusin", "focusout"]) {
  document.addEventListener(type, updateConfidenceTooltip);
}

// Delegation keeps checklist help working after streamed results replace the list.
function closeChecklistHelp() {
  document.querySelectorAll(".checklist-info").forEach(icon => {
    icon.setAttribute("aria-expanded", "false");
    document.getElementById(icon.getAttribute("aria-controls")).hidden = true;
  });
}

function openChecklistHelp(icon) {
  closeChecklistHelp();
  icon.setAttribute("aria-expanded", "true");
  document.getElementById(icon.getAttribute("aria-controls")).hidden = false;
}

document.addEventListener("pointerover", event => {
  const icon = event.target.closest?.(".checklist-info");
  if (icon && event.pointerType !== "touch") openChecklistHelp(icon);
});
document.addEventListener("pointerout", event => {
  const item = event.target.closest?.(".checklist-item");
  if (item && !item.contains(event.relatedTarget) && !item.contains(document.activeElement)) closeChecklistHelp();
});
document.addEventListener("focusin", event => {
  const icon = event.target.closest?.(".checklist-info");
  if (icon) openChecklistHelp(icon);
  else closeChecklistHelp();
});
document.addEventListener("click", event => {
  const icon = event.target.closest?.(".checklist-info");
  if (icon) openChecklistHelp(icon);
  else if (!event.target.closest?.(".checklist-help")) closeChecklistHelp();
});
document.addEventListener("keydown", event => {
  if (event.key === "Escape") closeChecklistHelp();
});
