"use strict";

const { STRINGS, DEFAULTS, validateSettings } = window.WishLabStartup;
const $ = (id) => document.getElementById(id);
const SETTINGS_KEY = "wishlab.settings.v1";
const HISTORY_KEY = "wishlab.history.v1";
let storageAvailable = true;
function readStorage(key, fallback) {
  try { const raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : fallback; }
  catch { storageAvailable = false; return fallback; }
}
function writeStorage(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); }
  catch { storageAvailable = false; $("settings-status").textContent = t("storageError"); }
}
let settings = validateSettings(readStorage(SETTINGS_KEY, DEFAULTS));
function validRecord(record) {
  const r = record?.data, q = r?.request;
  return record?.schema === 1 && typeof record.id === "string" && typeof record.date === "string" && Number.isFinite(Date.parse(record.date))
    && typeof r?.version === "string" && r.version.length > 0 && r.version.length <= 64
    && ["character", "weapon", "combined"].includes(q?.mode)
    && Number.isInteger(q.wish_budget) && q.wish_budget >= 0 && q.wish_budget <= 2000
    && ["pity", "target_copies", "cr_counter", "weapon_pity", "fate_point", "weapon_target"].every(k => Number.isInteger(q[k]) && q[k] >= 0)
    && q.pity <= 89 && q.target_copies <= 10 && q.cr_counter <= 3 && q.weapon_pity <= 79 && q.fate_point <= 1 && q.weapon_target <= 10
    && typeof q.is_guaranteed === "boolean" && typeof q.weapon_guaranteed === "boolean"
    && Number.isFinite(r.success_probability) && r.success_probability >= 0 && r.success_probability <= 1
    && Array.isArray(r.outcomes) && r.outcomes.length <= 30 && r.outcomes.every(o => Number.isFinite(o.probability) && o.probability >= 0 && Number.isInteger(o.rank) && Number.isInteger(o.character_copies) && Number.isInteger(o.weapon_copies))
    && Array.isArray(r.thresholds) && r.thresholds.length === 7 && r.thresholds.every(o => Number.isFinite(o.probability) && Number.isInteger(o.wishes) && o.wishes >= 0)
    && r.breakdown && typeof r.breakdown === "object";
}
const storedHistory = readStorage(HISTORY_KEY, []);
let history = settings.history && Array.isArray(storedHistory) ? storedHistory.filter(validRecord).slice(0, 5) : [];
if (!settings.history) writeStorage(HISTORY_KEY, []);
const CALCULATION_TIMEOUT_MS = 30_000;
let mode = "character", currentData = null, busy = false;
let activeRequest = null, requestSequence = 0, attentionSequence = 0;
let requestState = { kind: "idle", message: null };
let appVersion = null;
let formStatus = null;
let selectedConfidence = 90;
const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
let layoutAnimations = [];
let activeSettingsPage = "calculator";
function t(key, values = {}) {
  let text = STRINGS[settings.language][key] ?? STRINGS.en[key] ?? key;
  for (const [name, value] of Object.entries(values)) text = text.replaceAll("{" + name + "}", String(value));
  return text;
}
function renderVersion() {
  const version = appVersion ?? t("versionUnavailable");
  document.querySelectorAll("[data-app-version]").forEach(element => { element.textContent = version; });
  $("version-footer").textContent = t("versionFooter", { version });
}
function acceptBackendVersion(value) {
  if (typeof value === "string" && value.trim() && value.length <= 64) {
    appVersion = value;
    renderVersion();
  }
}
async function loadBackendVersion() {
  try {
    const response = await fetch("/api/version", { signal: AbortSignal.timeout(5000) });
    if (response.ok) acceptBackendVersion((await response.json()).version);
  } catch { /* No invented or saved version fallback. Calculations can still work. */ }
  renderVersion();
}
// Quantity-specific display rules; raw API/history data always stays unrounded.
function formatQuantity(value, digits) {
  return value === null || !Number.isFinite(value) ? t("notDefined")
    : new Intl.NumberFormat(settings.language === "zh" ? "zh-CN" : "en-US", {
      minimumFractionDigits: digits, maximumFractionDigits: digits
    }).format(value);
}
function count(value) { return formatQuantity(value, 0); }
function average(value) { return formatQuantity(value, 1); }
function percent(value) {
  const p = value * 100, unit = 10 ** -settings.precision;
  if (value > 0 && p < unit / 2) return "<" + formatQuantity(unit, settings.precision) + "%";
  if (value < 1 && p > 100 - unit / 2) return ">" + formatQuantity(100 - unit, settings.precision) + "%";
  return formatQuantity(p, settings.precision) + "%";
}
function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}
function setFormStatus(key = null, error = false) {
  formStatus = key ? { key, error } : null;
  renderFormStatus();
}
function renderFormStatus() {
  $("form-status").dataset.kind = formStatus?.error ? "error" : "";
  $("form-status").textContent = formStatus ? t(formStatus.key, {
    p: currentData ? percent(currentData.success_probability) : ""
  }) : "";
  if (formStatus?.key === "successAnnounce" && !settings.history) {
    $("form-status").textContent += " " + t("savingOff");
  }
}
function requestData() {
  return {
    mode, wish_budget: Number($("wish_budget").value),
    pity: Number($("pity").value), is_guaranteed: $("is_guaranteed").checked,
    target_copies: Number($("target_copies").value), cr_counter: Number($("cr_counter").value),
    weapon_pity: Number($("weapon_pity").value), weapon_guaranteed: $("weapon_guaranteed").checked,
    fate_point: Number($("fate_point").value), weapon_target: Number($("weapon_target").value)
  };
}
function setMode(next) {
  if (mode !== next) attentionSequence++;
  mode = next;
  document.querySelectorAll("[data-mode]").forEach(button => {
    const active = button.dataset.mode === mode;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  document.querySelector(".mode-tabs").style.setProperty("--mode-index", ["character", "weapon", "combined"].indexOf(mode));
  for (const [id, visible] of [["character-fields", mode !== "weapon"], ["weapon-fields", mode !== "character"]]) {
    $(id).hidden = !visible; $(id).disabled = !visible;
  }
  $("mode-caption").dataset.i18n = mode + "Caption";
  $("mode-caption").textContent = t(mode + "Caption");
  $("model-note").dataset.i18n = mode + "Model";
  $("model-note").textContent = t(mode + "Model");
  $("character-phase").textContent = mode === "combined" ? t("phase1") : "";
  $("weapon-phase").textContent = mode === "combined" ? t("phase2") : "";
  markStale();
}
function markStale() {
  const comparable = q => {
    const fields = ["mode", "wish_budget"];
    if (q.mode !== "weapon") fields.push("pity", "is_guaranteed", "target_copies", "cr_counter");
    if (q.mode !== "character") fields.push("weapon_pity", "weapon_guaranteed", "fate_point", "weapon_target");
    return JSON.stringify(fields.map(key => q[key]));
  };
  const stale = currentData && comparable(currentData.request) !== comparable(requestData());
  $("stale-notice").hidden = !stale;
  $("result-state").textContent = busy ? t("calculating")
    : requestState.kind !== "idle" ? t(currentData ? "previousResultStatus" : "calculationFailed")
    : currentData ? t(stale ? "updated" : "ready") : "";
}
function targetSummary(q) {
  const key = q.mode === "combined" ? "targetSummaryCombined" : q.mode === "weapon" ? "targetSummaryWeapon" : "targetSummaryCharacter";
  return t(key, { c: count(q.target_copies), w: count(q.weapon_target), n: count(q.wish_budget) });
}
function outcomeLabel(outcome, outcomeMode) {
  if (outcomeMode === "combined") return t("combinedOutcome", { c: count(outcome.character_copies), w: count(outcome.weapon_copies) });
  return t(outcomeMode + "Outcome", { n: count(outcomeMode === "character" ? outcome.character_copies : outcome.weapon_copies) });
}
function renderOutcomes() {
  if (!currentData) return;
  const all = currentData.outcomes;
  const visible = all.slice(0, settings.outcomes);
  const target = all.find(row => row.is_target);
  if (target && !visible.includes(target)) visible.push(target);
  $("outcome-count").textContent = t("topCount", { n: count(settings.outcomes) });
  $("outcomes-list").replaceChildren();
  for (const row of visible) {
    const li = node("li", "outcome" + (row.is_target ? " is-target" : ""));
    const content = node("div", "outcome-content"), name = node("div", "outcome-name");
    name.append(node("span", "outcome-rank", "#" + count(row.rank)), node("span", "", outcomeLabel(row, currentData.request.mode)));
    if (row.is_target) name.append(node("span", "target-badge", t("yourTarget")));
    content.append(name, node("span", "outcome-probability", percent(row.probability)));
    const track = node("div", "outcome-track"), fill = node("span");
    fill.style.width = Math.max(0, Math.min(100, row.probability * 100)) + "%";
    track.setAttribute("aria-hidden", "true"); track.append(fill); li.append(content, track);
    $("outcomes-list").append(li);
  }
}
function renderConfidence() {
  if (!currentData) return;
  const threshold = currentData.thresholds.find(row => row.probability === selectedConfidence / 100);
  if (!threshold) return;
  $("confidence-slider").value = String(selectedConfidence);
  document.querySelector(".confidence-axis").style.setProperty("--confidence-position", selectedConfidence + "%");
  // Preset labels remain whole percentages; calculated probabilities use percent().
  const confidence = count(selectedConfidence) + "%";
  $("confidence-slider").setAttribute("aria-valuetext", confidence + " · " + count(threshold.wishes) + " " + t("wishes"));
  $("confidence-percent").textContent = confidence;
  $("threshold-wishes").textContent = count(threshold.wishes);
  document.querySelectorAll("[data-confidence]").forEach(button => button.classList.toggle("active", Number(button.dataset.confidence) === selectedConfidence));
  const delta = threshold.wishes - currentData.request.wish_budget;
  $("confidence-explanation").textContent = t("confidenceExplanation") + " " + (delta > 0 ? t("budgetDelta", { n: count(delta) }) : t("budgetEnough"));
}
function animationsAllowed() {
  return settings.animations && !reducedMotion.matches;
}
function cancelLayoutAnimations() {
  layoutAnimations.forEach(animation => animation.cancel());
  layoutAnimations = [];
}
function setResultLayout(hasResult) {
  const workspace = document.querySelector(".workspace");
  if (workspace.classList.contains("has-results") === hasResult) return;
  const planner = document.querySelector(".planner-panel");
  const before = planner.getBoundingClientRect();
  cancelLayoutAnimations();
  workspace.classList.toggle("has-results", hasResult);
  document.querySelector(".results-column").hidden = !hasResult;
  if (!hasResult || !animationsAllowed()) return;
  const after = planner.getBoundingClientRect();
  // FLIP the actual card width and position without scaling its text. The
  // normal responsive grid is the final layout; animation is only cosmetic.
  if (window.matchMedia("(min-width: 761px)").matches) {
    layoutAnimations.push(planner.animate([
      { transform: `translate(${before.left - after.left}px, ${before.top - after.top}px)`, width: before.width + "px" },
      { transform: "translate(0, 0)", width: after.width + "px" }
    ], { duration: 650, easing: "cubic-bezier(.22, 1, .36, 1)" }));
  }
  document.querySelectorAll(".results-column > .panel").forEach((panel, index) => {
    layoutAnimations.push(panel.animate([
      { opacity: 0, transform: "translate(24px, 12px)" },
      { opacity: 1, transform: "translate(0, 0)" }
    ], { duration: 580, delay: 120 + index * 85, easing: "cubic-bezier(.22, 1, .36, 1)", fill: "backwards" }));
  });
}
async function revealResultIfNeeded(trigger) {
  const sequence = ++attentionSequence;
  // Wait out FLIP/staggered animations and browser scroll anchoring before
  // measuring. A later request/mode/history action invalidates this reveal.
  await Promise.allSettled(layoutAnimations.map(animation => animation.finished));
  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  if (sequence !== attentionSequence) return;
  const settingsDialog = $("settings-dialog");
  if (settingsDialog.open) {
    await new Promise(resolve => settingsDialog.addEventListener("close", resolve, { once: true }));
    if (sequence !== attentionSequence) return;
  }
  const panel = document.querySelector(".result-panel");
  if (document.querySelector(".results-column").hidden) return;
  const rect = panel.getBoundingClientRect();
  // On short screens/tall cards the leading section (title + main readout or
  // feedback) is the visibility target, rather than an impossible full-card fit.
  const leadingHeight = Math.min(rect.height, 360, Math.max(160, window.innerHeight - 48));
  if (rect.top >= 24 && rect.top + leadingHeight <= window.innerHeight - 24) return;
  const focusStillWithAction = document.activeElement === trigger || document.activeElement === document.body;
  window.scrollTo({
    top: Math.max(0, window.scrollY + rect.top - 24),
    behavior: animationsAllowed() ? "smooth" : "instant"
  });
  if (focusStillWithAction && !settingsDialog.open) $("result-title").focus({ preventScroll: true });
}
function renderRequestFeedback() {
  const { kind, message } = requestState;
  const feedback = $("result-feedback");
  feedback.hidden = kind === "idle";
  feedback.dataset.state = kind;
  const error = kind === "error" || kind === "timeout";
  feedback.setAttribute("role", error ? "alert" : "status");
  feedback.setAttribute("aria-live", error ? "assertive" : "polite");
  $("result-feedback-message").textContent = message ? t(message) : "";
  $("result-spinner").hidden = !busy;
  $("loading-placeholder").hidden = !busy;
  document.querySelector(".feedback-actions [data-cancel-calculation]").hidden = !busy;
  $("retry-calculation").hidden = kind === "idle" || busy;
  $("previous-result-note").hidden = !currentData || busy || kind === "idle";
}
function renderResult() {
  const hasResult = Boolean(currentData);
  renderRequestFeedback();
  for (const id of ["result-content", "outcomes-panel", "confidence-panel"]) $(id).hidden = !hasResult || busy;
  setResultLayout(hasResult || requestState.kind !== "idle");
  if (!hasResult) { markStale(); return; }
  $("result-target").textContent = targetSummary(currentData.request);
  $("probability").textContent = percent(currentData.success_probability);
  $("probability-orbit").style.setProperty("--progress", (currentData.success_probability * 100) + "%");
  $("expected-wishes").textContent = average(currentData.expected_wishes);
  $("conditional-wishes").textContent = average(currentData.conditional_expected_wishes);
  $("result-breakdown").replaceChildren();
  for (const [key, value] of Object.entries(currentData.breakdown)) {
    const row = node("div", "breakdown-row");
    row.append(node("span", "", t(key)), node("strong", "", percent(value)));
    $("result-breakdown").append(row);
  }
  renderOutcomes(); renderConfidence(); markStale();
}
function renderHistory() {
  document.querySelector(".history-section").hidden = !settings.history;
  $("history-list").replaceChildren();
  $("clear-history").hidden = !settings.history || !history.length;
  $("download-history").hidden = !settings.history;
  $("download-history").disabled = !history.length;
  if (!settings.history || !history.length) {
    $("history-list").append(node("p", "history-empty", t(settings.history ? "noHistory" : "historyDisabled")));
    return;
  }
  for (const record of history) {
    const button = node("button", "history-item");
    button.type = "button";
    button.disabled = busy;
    button.setAttribute("aria-label", t("restoreHistory") + ": " + targetSummary(record.data.request));
    const label = node("span");
    label.append(node("strong", "", targetSummary(record.data.request)));
    label.append(node("small", "", new Date(record.date).toLocaleString(settings.language === "zh" ? "zh-CN" : "en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })));
    button.append(label, node("span", "history-probability", percent(record.data.success_probability)));
    button.addEventListener("click", () => restoreRecord(record));
    $("history-list").append(button);
  }
}
function restoreRecord(record) {
  if (busy) return;
  const trigger = document.activeElement;
  const q = record.data.request;
  for (const [id, value] of Object.entries(q)) {
    const element = $(id);
    if (!element) continue;
    if (element.type === "checkbox") element.checked = value;
    else element.value = value;
  }
  setMode(q.mode);
  currentData = record.data;
  requestState = { kind: "idle", message: null };
  setFormStatus();
  renderResult();
  void revealResultIfNeeded(trigger);
}
function translatePage() {
  document.documentElement.lang = settings.language === "zh" ? "zh-CN" : "en";
  document.title = settings.language === "zh" ? "Wish Lab · 原神祈愿概率计算器" : "Wish Lab · Genshin Wish Probability Calculator";
  document.querySelectorAll("[data-i18n]").forEach(element => { element.textContent = t(element.dataset.i18n); });
  document.querySelectorAll("[data-i18n-aria]").forEach(element => element.setAttribute("aria-label", t(element.dataset.i18nAria)));
  setMode(mode); renderResult(); renderHistory();
  renderFormStatus();
  $("calculate-label").textContent = t(busy ? "calculating" : "calculate");
  selectSettingsPage(activeSettingsPage);
  renderVersion();
}
function applyAppearance() {
  window.WishLabStartup.applyAppearance(settings);
  if (!animationsAllowed()) cancelLayoutAnimations();
}
function syncSettingsControls() {
  for (const key of Object.keys(DEFAULTS)) {
    const element = $("setting-" + key);
    if (!element) continue;
    if (element.type === "checkbox") element.checked = settings[key];
    else element.value = settings[key];
  }
}
function setBusy(value) {
  busy = value;
  $("calculate").disabled = value;
  $("calculate-label").textContent = t(value ? "calculating" : "calculate");
  document.querySelector(".result-panel").setAttribute("aria-busy", String(value));
  document.querySelectorAll(".history-item").forEach(button => { button.disabled = value; });
  $("request-controls").hidden = !value;
}

document.querySelectorAll("[data-mode]").forEach(button => button.addEventListener("click", () => setMode(button.dataset.mode)));
$("wish_form").addEventListener("input", markStale);
$("wish_form").addEventListener("change", markStale);
$("wish_form").addEventListener("submit", async event => {
  event.preventDefault();
  if (busy || !$("wish_form").reportValidity()) return;
  const payload = requestData();
  // Hidden banner inputs still have stored values. Native validation applies
  // only to the active phase; send valid defaults for inactive fields.
  if (mode === "character") Object.assign(payload, { weapon_pity: 0, weapon_guaranteed: false, fate_point: 0, weapon_target: 1 });
  if (mode === "weapon") Object.assign(payload, { pity: 0, is_guaranteed: false, target_copies: 1, cr_counter: 1 });
  const trigger = document.activeElement;
  attentionSequence++;
  const job = { id: ++requestSequence, controller: new AbortController(), timer: null, trigger };
  activeRequest = job;
  requestState = { kind: "loading", message: "loadingResult" };
  setBusy(true);
  setFormStatus();
  renderResult();
  job.timer = setTimeout(() => { if (activeRequest === job) stopCalculation("timeout"); }, CALCULATION_TIMEOUT_MS);
  try {
    const response = await fetch("/api/calculate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload), signal: job.controller.signal
    });
    if (!response.ok) {
      const error = new Error(response.status === 422 ? "invalidRequest" : "apiError");
      throw error;
    }
    const data = await response.json();
    if (activeRequest !== job) return;
    if (!validRecord({ schema: 1, id: "response", date: new Date().toISOString(), data })) throw new Error("apiError");
    activeRequest = null;
    clearTimeout(job.timer);
    acceptBackendVersion(data.version);
    currentData = data;
    requestState = { kind: "idle", message: null };
    setBusy(false);
    if (settings.history) {
      history.unshift({ schema: 1, id: crypto.randomUUID(), date: new Date().toISOString(), data });
      history = history.slice(0, 5);
      writeStorage(HISTORY_KEY, history);
    }
    renderResult(); renderHistory();
    setFormStatus("successAnnounce");
    void revealResultIfNeeded(trigger);
  } catch (error) {
    if (activeRequest !== job) return;
    activeRequest = null;
    const message = error instanceof TypeError ? "networkError" : error.message in STRINGS.en ? error.message : "apiError";
    requestState = { kind: "error", message };
    setBusy(false);
    setFormStatus(message, true);
    renderResult();
    void revealResultIfNeeded(trigger);
  } finally {
    clearTimeout(job.timer);
  }
});
function stopCalculation(kind = "cancelled") {
  const job = activeRequest;
  if (!job) return;
  activeRequest = null; // Invalidate first: even a late response cannot commit.
  clearTimeout(job.timer);
  job.controller.abort();
  const message = kind === "timeout" ? "timedOutCalculation" : "cancelledCalculation";
  requestState = { kind, message };
  const trigger = document.activeElement;
  setBusy(false);
  setFormStatus(message, kind === "timeout");
  renderResult();
  void revealResultIfNeeded(trigger);
}
document.querySelectorAll("[data-cancel-calculation]").forEach(button => button.addEventListener("click", () => stopCalculation()));
$("retry-calculation").addEventListener("click", () => $("wish_form").requestSubmit());

$("confidence-slider").addEventListener("input", event => {
  const value = Number(event.target.value);
  selectedConfidence = [0, 50, 75, 90, 95, 99, 100].reduce((a, b) => Math.abs(a - value) <= Math.abs(b - value) ? a : b);
  renderConfidence();
});
$("confidence-slider").addEventListener("keydown", event => {
  const presets = [0, 50, 75, 90, 95, 99, 100];
  let index = presets.indexOf(selectedConfidence);
  if (["ArrowRight", "ArrowUp", "PageUp"].includes(event.key)) index++;
  else if (["ArrowLeft", "ArrowDown", "PageDown"].includes(event.key)) index--;
  else if (event.key === "Home") index = 0;
  else if (event.key === "End") index = presets.length - 1;
  else return;
  event.preventDefault();
  selectedConfidence = presets[Math.max(0, Math.min(presets.length - 1, index))];
  renderConfidence();
});
document.querySelectorAll("[data-confidence]").forEach(button => button.addEventListener("click", () => {
  selectedConfidence = Number(button.dataset.confidence); renderConfidence();
}));
$("clear-history").addEventListener("click", () => {
  history = []; writeStorage(HISTORY_KEY, history); renderHistory();
  setFormStatus("historyCleared");
});
const dialog = $("settings-dialog");
function selectSettingsPage(page, focusTab = false) {
  activeSettingsPage = page;
  const titles = { calculator: "calculatorSettings", appearance: "appearance", language: "languagePreferences", help: "helpCenter" };
  $("settings-title").dataset.i18n = titles[page];
  $("settings-title").textContent = t(titles[page]);
  document.querySelectorAll("[data-settings-page]").forEach(tab => {
    const active = tab.dataset.settingsPage === page;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
    tab.tabIndex = active ? 0 : -1;
    $("settings-" + tab.dataset.settingsPage).hidden = !active;
    if (active && focusTab) tab.focus();
  });
  document.querySelector(".settings-body").scrollTop = 0;
}
$("open-settings").addEventListener("click", () => {
  selectSettingsPage("calculator");
  dialog.showModal();
});
document.querySelectorAll("[data-settings-page]").forEach(tab => tab.addEventListener("click", () => selectSettingsPage(tab.dataset.settingsPage)));
document.querySelector(".settings-nav").addEventListener("keydown", event => {
  const pages = ["calculator", "appearance", "language", "help"];
  let index = pages.indexOf(activeSettingsPage);
  if (event.key === "ArrowDown" || event.key === "ArrowRight") index++;
  else if (event.key === "ArrowUp" || event.key === "ArrowLeft") index--;
  else if (event.key === "Home") index = 0;
  else if (event.key === "End") index = pages.length - 1;
  else return;
  event.preventDefault();
  selectSettingsPage(pages[(index + pages.length) % pages.length], true);
});
$("close-settings").addEventListener("click", () => dialog.close());
dialog.addEventListener("click", event => {
  const rect = dialog.getBoundingClientRect();
  if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
});
for (const key of Object.keys(DEFAULTS)) {
  const element = $("setting-" + key);
  if (!element) continue;
  element.addEventListener("change", () => {
    if (element.type === "number") {
      if (!element.value.trim() || !element.checkValidity() || !Number.isInteger(Number(element.value))) {
        $("settings-status").textContent = t("settingsInvalid");
        element.value = settings[key]; return;
      }
      settings[key] = Number(element.value);
    } else settings[key] = element.type === "checkbox" ? element.checked : key === "font" ? Number(element.value) : element.value;
    if (key === "history" && !settings.history) { history = []; writeStorage(HISTORY_KEY, []); }
    writeStorage(SETTINGS_KEY, settings);
    $("settings-status").textContent = storageAvailable ? "" : t("storageError");
    applyAppearance(); translatePage();
  });
}
$("download-history").addEventListener("click", async () => {
  if (!settings.history || !history.length) { $("settings-status").textContent = t("noSavedData"); return; }
  if (!appVersion) await loadBackendVersion();
  const text = ["Wish Lab — calculation data", t("versionHeader", { version: appVersion ?? t("versionUnavailable") }), "Exported: " + new Date().toISOString(),
    "Exact under the supplied community soft-pity / Capturing Radiance assumptions.",
    "Policy: stop at target. Combined mode: character first, then weapons.",
    "", ...history.map((record, i) => [
      "Calculation " + count(i + 1) + " | " + record.date, targetSummary(record.data.request),
      t("success") + ": " + percent(record.data.success_probability),
      t("expectedCompletion") + ": " + average(record.data.expected_wishes),
      t("conditionalCompletion") + ": " + average(record.data.conditional_expected_wishes),
      ...record.data.thresholds.map(row => percent(row.probability) + ": " + count(row.wishes) + " " + t("wishes")),
      "Success probability (unrounded): " + record.data.success_probability,
      JSON.stringify(record.data, null, 2), ""
    ].join("\n"))
  ].join("\n");
  const url = URL.createObjectURL(new Blob(["\uFEFF", text], { type: "text/plain;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url; link.download = "wish-lab-calculations-" + new Date().toISOString().slice(0, 10) + ".txt";
  document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  $("settings-status").textContent = t("dataDownloaded");
});
systemTheme.addEventListener("change", applyAppearance);
reducedMotion.addEventListener("change", () => { if (!animationsAllowed()) cancelLayoutAnimations(); });
syncSettingsControls(); applyAppearance(); translatePage();
// History loads on opening, but the initial view stays on the centered plan.
// Choosing a saved calculation explicitly reveals its result cards.
if (!storageAvailable) $("settings-status").textContent = t("storageError");
void loadBackendVersion();
