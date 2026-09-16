// One form request streams the extracted profile, then the server-rendered results.
const form = document.querySelector("#funding-form");
const button = document.querySelector("#submit-button");
const textarea = document.querySelector("#description");
const progress = document.querySelector("#matching-progress");
const status = document.querySelector("#loading-status");
const highlighted = document.querySelector("#highlighted-description");
const chips = document.querySelector("#profile-chips");
const comparison = document.querySelector("#comparison-note");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
let busy = false;

const pause = () => new Promise(resolve => setTimeout(resolve, reducedMotion.matches ? 0 : 350));
const humanize = value => String(value).replaceAll("_", " ").replace(/^./, letter => letter.toUpperCase());

function setStage(step, message) {
  progress.querySelectorAll("[data-step]").forEach(item => {
    item.classList.toggle("is-current", Number(item.dataset.step) === step);
    item.classList.toggle("is-complete", Number(item.dataset.step) < step);
    if (Number(item.dataset.step) === step) item.setAttribute("aria-current", "step");
    else item.removeAttribute("aria-current");
  });
  status.textContent = message;
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
  for (const phrase of phrases) {
    const source = description.toLowerCase();
    const search = phrase.toLowerCase();
    let start = source.indexOf(search);
    while (start !== -1) {
      const end = start + phrase.length;
      if (!spans.some(span => start < span.end && end > span.start)) spans.push({start, end});
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

  const values = [profile.country, profile.industry && humanize(profile.industry),
    profile.company_size, profile.employees != null ? `${profile.employees} employees` : null,
    profile.project_type && humanize(profile.project_type)];
  if (profile.project_budget != null) {
    values.push(`${profile.currency === "EUR" ? "€" : (profile.currency || "Budget") + " "}${Number(profile.project_budget).toLocaleString("en-US")}`);
  }
  chips.replaceChildren();
  for (const value of values.filter(Boolean)) {
    const chip = document.createElement("span");
    chip.className = "profile-chip";
    chip.textContent = value;
    chips.append(chip);
  }
}

if (window.fetch && window.ReadableStream) form?.addEventListener("submit", async event => {
  event.preventDefault();
  if (busy) return;
  const description = textarea.value;
  setBusy(true);
  progress.hidden = false;
  progress.classList.remove("has-error");
  chips.hidden = true;
  comparison.hidden = true;
  highlighted.textContent = description;
  document.querySelector("#matching-output").hidden = true;
  setStage(1, "Reading your description to understand your company and project…");
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
          setStage(1, "Key details found in your description.");
          await pause();
          chips.hidden = false;
          setStage(2, "Your company and project profile is ready.");
          await pause();
          comparison.hidden = false;
          setStage(3, "Checking requirements and assessing how well each programme fits…");
        } else if (update.type === "complete") {
          const page = new DOMParser().parseFromString(update.html, "text/html");
          const output = page.querySelector("#matching-output");
          if (!output) throw new Error("Missing results");
          if (update.status === 200) await pause();
          document.querySelector("#matching-output").replaceWith(output);
          completed = true;
          if (update.status === 200) {
            setStage(4, "Your ranked shortlist is ready.");
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
    progress.hidden = false;
    progress.classList.add("has-error");
    status.textContent = "Matching was interrupted. Your description is saved above; please try again.";
    comparison.hidden = true;
    if (reader) await reader.cancel().catch(() => {});
  } finally {
    setBusy(false);
  }
});

window.addEventListener("pageshow", event => {
  if (event.persisted) { setBusy(false); progress.hidden = true; }
});
