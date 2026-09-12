import {getSnapshot, previewPrompt} from "./api.js";
import {announce, renderLoading, renderSnapshot} from "./render.js";

const form = document.getElementById("preview-form");
const prompt = document.getElementById("prompt");
const promptError = document.getElementById("prompt-error");
const promptCount = document.getElementById("prompt-count");
const submitButton = document.getElementById("submit-button");
const alternateButton = document.getElementById("alternate-button");
const retryButton = document.getElementById("retry-button");
const connectionBanner = document.getElementById("connection-banner");
const connectionLabel = document.getElementById("connection-label");
const resultsHeading = document.getElementById("results-heading");

let lastGood = null;
let alternatePrompt = "Review the project documentation for clarity and broken links";

function connection(online) {
  connectionBanner.hidden = online;
  connectionLabel.textContent = online ? "Local engine connected" : "Local engine unavailable";
}

function validate() {
  const value = prompt.value;
  const valid = value.length >= 1 && value.length <= 4000;
  promptError.hidden = valid;
  prompt.setAttribute("aria-invalid", valid ? "false" : "true");
  if (!valid) announce("Prompt must contain 1 to 4000 characters.");
  return valid;
}

function complete(snapshot, userInitiated) {
  lastGood = snapshot;
  renderSnapshot(snapshot);
  connection(true);
  announce(snapshot.mode === "computed_preview" ? "Draft route/spec preview — verification not run" : "Local sample evidence loaded");
  if (userInitiated) resultsHeading.focus({preventScroll: false});
}

function failed() {
  connection(false);
  if (lastGood) {
    renderSnapshot(lastGood, {stale: true});
    announce("Stale — local server unavailable. Retry when the local server is running.");
  } else {
    document.getElementById("overall-status").textContent = "Offline";
    resultsHeading.textContent = "Local server unavailable";
    announce("Start with python3 scripts/grok_demo.py, then Retry.");
  }
}

async function load() {
  renderLoading();
  try {
    const snapshot = await getSnapshot();
    alternatePrompt = snapshot.scenario?.alternate_prompt || alternatePrompt;
    alternateButton.textContent = snapshot.scenario?.alternate_action_label || "Use contrasting scenario";
    if (!prompt.value) prompt.value = snapshot.scenario?.primary_prompt || "";
    promptCount.textContent = `${prompt.value.length} / 4000`;
    complete(snapshot, false);
  } catch (_error) {
    failed();
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!validate()) return;
  submitButton.disabled = true;
  announce("Computing route and draft specification preview");
  try {
    complete(await previewPrompt(prompt.value), true);
  } catch (error) {
    if (error.code === "invalid_prompt") {
      promptError.hidden = false;
      prompt.setAttribute("aria-invalid", "true");
      announce("Prompt must contain 1 to 4000 characters.");
    } else {
      failed();
    }
  } finally {
    submitButton.disabled = false;
  }
});

prompt.addEventListener("input", () => {
  promptCount.textContent = `${prompt.value.length} / 4000`;
  if (!promptError.hidden) validate();
});

prompt.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.ctrlKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

alternateButton.addEventListener("click", () => {
  prompt.value = alternatePrompt;
  promptCount.textContent = `${prompt.value.length} / 4000`;
  form.requestSubmit();
});

retryButton.addEventListener("click", load);
load();
