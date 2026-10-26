/* Real-browser integration check. Start uvicorn, then run with Playwright.
 * PLAYWRIGHT_MODULE / PLAYWRIGHT_CHROMIUM_EXECUTABLE optionally select local
 * installations. WISH_WEB_URL defaults to http://127.0.0.1:8000.
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");

(async () => {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE } : {})
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 }, colorScheme: "dark", acceptDownloads: true });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  let checks = 0;
  function check(value, label) { assert.ok(value, label); checks++; }
  async function calculate() {
    const response = page.waitForResponse(r => r.url().endsWith("/api/calculate") && r.request().method() === "POST");
    await page.locator("#calculate").click();
    check((await response).ok(), "API responds successfully");
    await page.waitForFunction(() => !document.getElementById("calculate").disabled);
  }
  const root = process.env.WISH_WEB_URL || "http://127.0.0.1:8000";
  const artifacts = path.resolve("artifacts/web-v101");
  fs.mkdirSync(artifacts, { recursive: true });
  try {
    await page.goto(root);
    check(!(await page.locator(".results-column").isVisible()), "initial view has only the plan card");
    const initialPlan = await page.locator(".planner-panel").boundingBox();
    check(initialPlan.width >= 650, "initial plan is wider than the result-layout card");
    check(Math.abs(initialPlan.x + initialPlan.width / 2 - 720) < 2, "initial plan is centered");
    check(await page.locator("#mode-caption").evaluate(el => el.closest(".mode-switch") !== null), "mode instructions are inside selector");
    await page.screenshot({ path: path.join(artifacts, "desktop-initial.png"), fullPage: true });
    check(await page.locator('[data-mode]').count() === 3, "three calculation modes");
    await page.locator("#open-settings").click();
    check(await page.locator("#setting-history").isChecked(), "history defaults on");
    check(await page.locator("#setting-precision").inputValue() === "2", "precision defaults to two");
    check(await page.locator("#setting-outcomes").inputValue() === "3", "outcomes default to three");
    check(await page.locator("#setting-theme").inputValue() === "system", "system theme default");
    check(await page.locator("#setting-font").inputValue() === "14", "default font is 14 px");
    check(await page.locator("#setting-font option").count() === 11, "font dropdown covers every integer 10–20");
    check(await page.locator("#settings-calculator").isVisible(), "settings opens on Calculator Settings");
    check(!(await page.locator("#settings-appearance").isVisible()), "inactive settings page hidden");
    await page.locator("#tab-calculator").focus();
    await page.keyboard.press("ArrowDown");
    check(await page.locator("#settings-appearance").isVisible(), "settings sidebar supports arrow navigation");
    await page.keyboard.press("End");
    check(await page.locator("#settings-help").isVisible(), "settings sidebar End opens Help");
    await page.keyboard.press("Home");
    const closeCenter = await page.locator("#close-settings").evaluate(button => {
      const outer = button.getBoundingClientRect(), icon = button.querySelector("svg").getBoundingClientRect();
      return Math.abs(outer.x + outer.width / 2 - icon.x - icon.width / 2) < 1 &&
        Math.abs(outer.y + outer.height / 2 - icon.y - icon.height / 2) < 1;
    });
    check(closeCenter, "close icon centered on both axes");
    await page.screenshot({ path: path.join(artifacts, "desktop-settings.png"), fullPage: true });
    await page.keyboard.press("Escape");
    check(!(await page.locator("#settings-dialog").isVisible()), "Escape closes settings");

    await calculate();
    check(await page.evaluate(() => document.querySelector(".planner-panel").getAnimations().some(a => a.playState === "running")), "first calculation animates the plan card");
    await page.waitForFunction(() => document.querySelector(".planner-panel").getAnimations().every(a => a.playState !== "running"));
    const settledPlan = await page.locator(".planner-panel").boundingBox();
    const results = await page.locator(".results-column").boundingBox();
    check(settledPlan.x < initialPlan.x && settledPlan.width < initialPlan.width, "plan moves left and narrows after calculation");
    check(results.x > settledPlan.x + settledPlan.width, "result cards appear to the right");
    check(await page.locator("#probability").textContent() === "91.05%", "default character CR regression");
    check(!(await page.locator("#stale-notice").isVisible()), "fresh result not stale");
    await page.locator('[data-mode="weapon"]').click();
    check(await page.locator("#weapon-fields").isVisible(), "weapon state shown");
    check(!(await page.locator("#character-fields").isVisible()), "character state hidden");
    await page.locator("#wish_budget").fill("120");
    await calculate();
    check(await page.locator("#probability").textContent() === "70.67%", "weapon regression");
    check(!(await page.locator("#stale-notice").isVisible()), "hidden fields do not mark weapon result stale");

    await page.locator('[data-mode="combined"]').click();
    await page.locator("#wish_budget").fill("240");
    await calculate();
    check(await page.locator("#probability").textContent() === "45.75%", "combined regression");
    check(await page.locator(".breakdown-row").count() === 3, "three combined outcomes");
    check(await page.locator("#threshold-wishes").textContent() === "332", "90% exact combined threshold");
    check(await page.locator(".confidence-thumb").evaluate(el => getComputedStyle(el).transitionDuration.split(",")[0].trim() !== "0s"), "confidence thumb uses a smooth transition");
    await page.locator('[data-confidence="99"]').click();
    check(await page.locator("#threshold-wishes").textContent() === "403", "99% threshold");
    await page.locator("#confidence-slider").focus();
    await page.keyboard.press("ArrowLeft");
    check(await page.locator("#confidence-percent").textContent() === "95%", "keyboard reaches prior confidence preset");
    check(await page.locator("#threshold-wishes").textContent() === "353", "95% threshold");
    await page.keyboard.press("End");
    check(await page.locator("#threshold-wishes").textContent() === "477", "structural 100% threshold");
    await page.keyboard.press("Home");
    check(await page.locator("#threshold-wishes").textContent() === "0", "zero confidence");
    await page.locator('[data-confidence="90"]').click();
    await page.screenshot({ path: path.join(artifacts, "desktop-dark.png"), fullPage: true });

    // History still loads, while startup remains centered until a record is chosen.
    await page.reload();
    check(!(await page.locator(".results-column").isVisible()), "reload starts with the centered plan");
    check(await page.locator(".history-item").count() === 3, "history loaded on opening");
    const legacyRecord = await page.evaluate(() => JSON.parse(localStorage.getItem("wishlab.history.v1"))[0]);
    legacyRecord.data.version = "1.0.0";
    await page.locator(".history-item").first().click();
    check(await page.locator("#probability").textContent() === "45.75%", "saved result restored on selection");
    check(await page.locator('[data-mode="combined"]').getAttribute("aria-pressed") === "true", "mode restored with history");
    await page.locator("#open-settings").click();
    await page.locator("#setting-precision").fill("4");
    await page.locator("#setting-precision").dispatchEvent("change");
    check(await page.locator("#probability").textContent() === "45.7451%", "precision reformats without recomputation");
    await page.locator("#setting-outcomes").fill("11");
    await page.locator("#setting-outcomes").dispatchEvent("change");
    check(await page.locator("#setting-outcomes").inputValue() === "3", "outcome limit rejects values above ten");
    await page.locator("#setting-outcomes").fill("1");
    await page.locator("#setting-outcomes").dispatchEvent("change");
    await page.locator("#tab-language").click();
    await page.locator("#setting-language").selectOption("zh");
    check(await page.locator("html").getAttribute("lang") === "zh-CN", "Chinese document language");
    check(await page.locator("#settings-title").textContent() === "语言偏好", "settings page heading translated");
    await page.locator("#tab-appearance").click();
    await page.locator("#setting-theme").selectOption("light");
    check(await page.locator("html").getAttribute("data-theme") === "light", "explicit light theme");
    await page.locator("#setting-animations").uncheck();
    check(await page.locator("html").getAttribute("data-animations") === "off", "animations disabled");
    await page.locator("#setting-font").selectOption("20");
    check(await page.evaluate(() => getComputedStyle(document.documentElement).fontSize) === "20px", "20 px font applied");
    const controls = await page.locator("#settings-appearance select").evaluateAll(elements => elements.map(el => el.getBoundingClientRect().height));
    check(controls.every(height => height === controls[0]) && controls[0] === 44, "select controls have equal height");
    await page.locator("#tab-help").click();
    const helpOrder = await page.locator("#settings-help").evaluate(panel => {
      const children = [...panel.children];
      return children[0].querySelector("#app-version") !== null &&
        children[1].querySelector('[data-i18n="terms"]') !== null &&
        children[2].matches("a.help-link");
    });
    check(helpOrder, "help order is About plus version, Terms, then Contact");
    await page.locator("#tab-calculator").click();
    const inputHeight = await page.locator("#setting-precision").evaluate(el => el.getBoundingClientRect().height);
    check(inputHeight === 44, "number inputs match select height");
    const downloadEvent = page.waitForEvent("download");
    await page.locator("#download-history").click();
    const download = await downloadEvent;
    const downloadPath = await download.path();
    const exported = fs.readFileSync(downloadPath, "utf8");
    check(exported.includes('"success_probability"') && exported.includes('"assumptions"'), "download retains raw results and model assumptions");
    check(download.suggestedFilename().endsWith(".txt"), "text export");
    await page.keyboard.press("Escape");
    await page.screenshot({ path: path.join(artifacts, "desktop-light-zh.png"), fullPage: true });

    // A very unlikely target must appear in addition to the top one outcome.
    await page.locator("#wish_budget").fill("0");
    await calculate();
    check(await page.locator(".outcome").count() === 2, "target included outside top N");
    check(await page.locator(".is-target .outcome-rank").textContent() === "#2", "requested outcome has exact tied rank");
    for (let i = 1; i <= 5; i++) {
      await page.locator("#wish_budget").fill(String(i));
      await calculate();
    }
    check(await page.locator(".history-item").count() === 5, "history capped at five records");
    await page.locator(".history-item").last().click();
    check(await page.locator("#wish_budget").inputValue() === "1", "history restores selected inputs");
    await page.locator("#open-settings").click();
    check(await page.locator("#settings-calculator").isVisible(), "reopening resets to Calculator Settings");
    await page.locator("#setting-history").uncheck();
    check(!(await page.locator(".history-section").isVisible()), "history off hides the entire main history section");
    check(!(await page.locator("#download-history").isVisible()), "history off hides download");
    check(await page.evaluate(() => JSON.parse(localStorage.getItem("wishlab.history.v1")).length) === 0, "history off removes persisted records");
    await page.keyboard.press("Escape");
    await calculate();
    check(await page.locator(".history-item").count() === 0, "history off does not save calculations");
    await page.reload();
    check(!(await page.locator(".results-column").isVisible()), "no result restored when history disabled");
    await page.locator("#open-settings").click();
    check(!(await page.locator("#setting-history").isChecked()), "settings persist after reload");
    await page.locator("#tab-appearance").click();
    await page.locator("#setting-theme").selectOption("system");
    await page.emulateMedia({ colorScheme: "dark" });
    check(await page.locator("html").getAttribute("data-theme") === "dark", "follows system changes");
    await page.keyboard.press("Escape");

    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator('[data-mode="combined"]').click();
    await calculate();
    check(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), "mobile has no horizontal overflow with large font");
    await page.locator("#open-settings").click();
    await page.locator("#setting-precision").fill("10");
    await page.locator("#setting-precision").dispatchEvent("change");
    await page.keyboard.press("Escape");
    check(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), "maximum precision has no mobile horizontal overflow");
    await page.locator("#open-settings").click();
    await page.locator("#setting-precision").fill("4");
    await page.locator("#setting-precision").dispatchEvent("change");
    await page.keyboard.press("Escape");
    await page.screenshot({ path: path.join(artifacts, "mobile-dark-zh.png"), fullPage: true });
    await page.locator("#open-settings").click();
    await page.screenshot({ path: path.join(artifacts, "mobile-settings.png"), fullPage: true });
    await page.keyboard.press("Escape");
    // A failed request must leave an actionable message, not erase valid results.
    await page.route("**/api/calculate", route => route.abort("failed"));
    await page.locator("#calculate").click();
    await page.waitForFunction(() => !document.getElementById("calculate").disabled);
    check((await page.locator("#form-status").textContent()).includes("无法连接"), "network failure is translated and understandable");
    check(await page.locator("#result-content").isVisible(), "last good result retained on error");
    const migratedContext = await browser.newContext({ reducedMotion: "reduce" });
    await migratedContext.addInitScript(({ record }) => {
      localStorage.setItem("wishlab.settings.v1", JSON.stringify({ font: "large" }));
      localStorage.setItem("wishlab.history.v1", JSON.stringify([record]));
    }, { record: legacyRecord });
    const migrated = await migratedContext.newPage();
    await migrated.goto(root);
    check(await migrated.locator("#setting-font").inputValue() === "18", "legacy named font migrates to equivalent pixels");
    check(await migrated.locator(".history-item").count() === 1, "v1.0.0 history remains readable");
    await migrated.locator(".history-item").first().click();
    check(await migrated.locator("#probability").textContent() === "45.75%", "legacy saved result can still be selected");
    check(await migrated.locator(".planner-panel").evaluate(el => el.getAnimations().length === 0), "reduced motion suppresses layout animations");
    check(await migrated.locator(".confidence-thumb").evaluate(el => getComputedStyle(el).transitionDuration === "0s"), "reduced motion suppresses slider animation");
    await migratedContext.close();
    // Corrupt saved records must never prevent loading a usable page.
    await page.evaluate(() => {
      localStorage.setItem("wishlab.history.v1", JSON.stringify([{ schema: 1, data: "invalid" }]));
      localStorage.setItem("wishlab.settings.v1", "{broken");
    });
    await page.reload();
    check(!(await page.locator(".results-column").isVisible()), "corrupt storage recovers to a clean page");
    check(await page.locator("#calculate").isEnabled(), "form usable after corrupt storage");
    const blockedContext = await browser.newContext({ viewport: { width: 390, height: 844 } });
    await blockedContext.addInitScript(() => {
      Storage.prototype.getItem = () => { throw new Error("Storage blocked"); };
      Storage.prototype.setItem = () => { throw new Error("Storage blocked"); };
    });
    const blocked = await blockedContext.newPage();
    await blocked.goto(root);
    await blocked.locator("#open-settings").click();
    check((await blocked.locator("#settings-status").textContent()).includes("unavailable"), "blocked storage shows session-only notice");
    await blocked.keyboard.press("Escape");
    await blocked.locator("#wish_budget").fill("0");
    await blocked.locator("#calculate").click();
    await blocked.waitForFunction(() => document.getElementById("probability").textContent !== "—");
    check((await blocked.locator("#probability").textContent()).includes("0.00%"), "calculations work when browser storage is blocked");
    await blockedContext.close();
    check(errors.length === 0, "no JavaScript page errors: " + errors.join("; "));
    console.log(JSON.stringify({ checks, browserErrors: errors, artifacts }, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
