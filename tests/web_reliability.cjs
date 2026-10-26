/* v1.0.2: real viewport/focus checks plus controlled slow/error/version APIs.
 * Start uvicorn first; module/browser overrides match web_smoke.cjs.
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
  const root = process.env.WISH_WEB_URL || "http://127.0.0.1:8000";
  const artifacts = path.resolve("artifacts/web-v102");
  fs.mkdirSync(artifacts, { recursive: true });
  let checks = 0;
  const errors = [];
  const check = (condition, label) => { assert.ok(condition, label); checks++; };
  const client = await browser.newContext();
  const base = await (await client.request.post(root + "/api/calculate", {
    data: { mode: "character", pity: 37, wish_budget: 240, target_copies: 2 }
  })).json();
  const legacy = { schema: 1, id: "saved", date: new Date().toISOString(), data: structuredClone(base) };
  legacy.data.version = "1.0.1";
  async function ready(page) {
    await page.waitForFunction(() => !document.getElementById("calculate").disabled &&
      document.getElementById("result-feedback").hidden &&
      !document.getElementById("result-content").hidden);
  }
  async function inView(page) {
    await page.waitForFunction(() => {
      const rect = document.querySelector(".result-panel").getBoundingClientRect();
      return rect.top >= 18 && rect.top + Math.min(rect.height, 360) <= innerHeight - 18;
    });
    // A smooth scroll may enter the visible area before it reaches rest.
    await page.evaluate(() => { window.__scrollSample = null; });
    await page.waitForFunction(() => {
      const top = document.querySelector(".result-panel").getBoundingClientRect().top;
      const previous = window.__scrollSample;
      const stable = previous && Math.abs(top - previous.top) < .5 ? previous.stable + 1 : 0;
      window.__scrollSample = { top, stable };
      return stable >= 6;
    });
  }
  try {
    for (const [width, height, reduced, animations] of [
      [1440, 700, false, true], [761, 650, false, false],
      [760, 760, true, true], [390, 700, false, true]
    ]) {
      const context = await browser.newContext({ viewport: { width, height }, reducedMotion: reduced ? "reduce" : "no-preference" });
      await context.addInitScript(({ record, animations }) => {
        localStorage.setItem("wishlab.settings.v1", JSON.stringify({ animations }));
        localStorage.setItem("wishlab.history.v1", JSON.stringify(Array.from({ length: 5 }, (_, i) => ({ ...record, id: "saved-" + i }))));
      }, { record: legacy, animations });
      const page = await context.newPage();
      page.on("pageerror", error => errors.push(error.message));
      await page.goto(root);
      await page.locator('[data-mode="combined"]').click();
      await page.locator("#calculate").scrollIntoViewIfNeeded();
      await page.locator("#calculate").click();
      await ready(page);
      await inView(page);
      check(await page.locator("#result-title").evaluate(el => el === document.activeElement), width + ": offscreen result receives focus after scrolling");
      check(await page.locator("#probability").textContent() === "45.75%", width + ": combined regression preserved");
      const beforeLayout = await page.locator(".result-panel").boundingBox();
      await page.waitForTimeout(200);
      const afterLayout = await page.locator(".result-panel").boundingBox();
      check(Math.abs(beforeLayout.y - afterLayout.y) < 2, width + ": result stays visible after animation settles");

      await page.locator(".history-item").last().click();
      await inView(page);
      check(await page.locator("#probability").textContent() === "91.05%", width + ": restored history result is visible");
      if (width >= 761) {
        // Budget input and result headline are both in view. Enter submits
        // without scrolling to the CTA at the bottom of the tall left column.
        await page.evaluate(() => {
          const rect = document.querySelector(".result-panel").getBoundingClientRect();
          window.scrollTo({ top: scrollY + rect.top - 28, behavior: "instant" });
        });
        await page.locator("#wish_budget").focus();
        const y = await page.evaluate(() => scrollY);
        await page.keyboard.press("Enter");
        await ready(page);
        await page.waitForTimeout(150);
        check(Math.abs((await page.evaluate(() => scrollY)) - y) < 2, width + ": comfortable result does not steal scroll");
        check(await page.locator("#wish_budget").evaluate(el => el === document.activeElement), width + ": comfortable result does not steal input focus");
      }
      await page.screenshot({ path: path.join(artifacts, "visible-" + width + ".png") });
      await context.close();
    }

    const context = await browser.newContext({ viewport: { width: 1440, height: 800 }, reducedMotion: "reduce" });
    await context.route("**/api/version", route => route.fulfill({ json: { version: "9.8.7" } }));
    let behavior = "hold";
    const held = [];
    await context.route("**/api/calculate", async route => {
      const response = { ...structuredClone(base), version: "9.8.7", request: route.request().postDataJSON() };
      if (behavior === "hold") await new Promise(resolve => held.push(resolve));
      else if (behavior === "http-error") { await route.fulfill({ status: 500, body: "failure" }); return; }
      else if (behavior === "network-error") { await route.abort("failed"); return; }
      else if (behavior === "invalid-json") { await route.fulfill({ json: {} }); return; }
      try { await route.fulfill({ json: response }); } catch { /* Cancelled requests are deliberately released late. */ }
    });
    const page = await context.newPage();
    page.on("pageerror", error => errors.push(error.message));
    await page.goto(root);
    await page.waitForFunction(() => document.querySelector(".version-tag").textContent === "9.8.7");
    check(await page.locator("#app-version").textContent() === "9.8.7", "About version comes from API");
    check(await page.locator("#version-footer").textContent() === "VERSION 9.8.7", "footer version comes from API");
    await page.locator("#calculate").click();
    await page.waitForFunction(() => document.getElementById("result-feedback").dataset.state === "loading");
    check(await page.locator("#loading-placeholder").isVisible(), "first request shows visible loading skeleton");
    check(!(await page.locator("#result-content").isVisible()), "no numbers presented as a loading result");
    check(await page.locator("#request-controls").isVisible(), "CTA has loading and cancel controls");
    check(await page.locator(".result-panel").getAttribute("aria-busy") === "true", "loading has aria-busy");
    await page.locator("#request-controls [data-cancel-calculation]").click();
    check(await page.locator("#calculate").isEnabled(), "cancel immediately re-enables Calculate");
    check(await page.locator("#result-feedback").getAttribute("data-state") === "cancelled", "cancelled state is explicit");
    check(await page.locator(".history-item").count() === 0, "cancel does not save history");
    await page.locator("#retry-calculation").click();
    await page.waitForFunction(() => document.getElementById("calculate").disabled);
    for (let n = 0; n < 100 && held.length < 2; n++) await page.waitForTimeout(10);
    check(held.length === 2, "retry has its own pending request");
    held[0]();
    await page.waitForTimeout(100);
    check(await page.locator("#calculate").isDisabled(), "late cancelled response cannot end a newer request");
    check(await page.locator(".history-item").count() === 0, "late cancelled response cannot save history");
    held[1]();
    await ready(page);
    check(await page.locator(".history-item").count() === 1, "successful retry saves exactly once");

    behavior = "http-error";
    await page.locator("#calculate").click();
    await page.waitForFunction(() => document.getElementById("result-feedback").dataset.state === "error");
    check(await page.locator("#result-feedback").getAttribute("role") === "alert", "HTTP error is prominent accessible alert");
    check(await page.locator("#previous-result-note").isVisible(), "retained successful numbers are explicitly labeled");
    check(await page.locator("#probability").textContent() === "91.05%", "error preserves last good result");
    check(await page.locator("#calculate").isEnabled(), "HTTP error releases CTA");
    await page.screenshot({ path: path.join(artifacts, "error-desktop.png") });
    await page.locator("#open-settings").click();
    await page.locator("#tab-language").click();
    await page.locator("#setting-language").selectOption("zh");
    await page.keyboard.press("Escape");
    check((await page.locator("#result-feedback-message").textContent()).includes("计算失败"), "error feedback translates");
    check(await page.locator("#version-footer").textContent() === "版本 9.8.7", "language switch preserves API version");
    behavior = "network-error";
    await page.locator("#retry-calculation").click();
    await page.waitForFunction(() => document.getElementById("result-feedback-message").textContent.includes("无法连接"));
    check(await page.locator("#calculate").isEnabled(), "network failure is recoverable");
    behavior = "invalid-json";
    await page.locator("#retry-calculation").click();
    await page.waitForFunction(() => document.getElementById("result-feedback-message").textContent.includes("计算失败"));
    check(await page.locator("#calculate").isEnabled(), "invalid response is recoverable");

    await page.clock.install();
    behavior = "hold";
    await page.locator("#retry-calculation").click();
    await page.waitForFunction(() => document.getElementById("calculate").disabled);
    for (let n = 0; n < 100 && held.length < 3; n++) await page.waitForTimeout(10);
    check(held.length === 3, "timeout scenario has a pending backend request");
    check(!(await page.locator("#result-content").isVisible()), "previous numbers are hidden during recalculation");
    await page.clock.fastForward(30_001);
    await page.waitForFunction(() => document.getElementById("result-feedback").dataset.state === "timeout");
    check(await page.locator("#calculate").isEnabled(), "hung request times out and releases CTA");
    check((await page.locator("#result-feedback-message").textContent()).includes("30"), "timeout explains the deadline");
    check(await page.locator(".history-item").count() === 1, "failed and timed-out attempts do not enter history");
    behavior = "success";
    await page.locator("#retry-calculation").click();
    await ready(page);
    check(!(await page.locator("#previous-result-note").isVisible()), "successful retry clears previous-result warning");
    held[2]();
    await page.waitForTimeout(50);
    check(await page.locator(".history-item").count() === 2, "late timeout response cannot commit");

    await page.locator("#open-settings").click();
    const downloadEvent = page.waitForEvent("download");
    await page.locator("#download-history").click();
    const download = await downloadEvent;
    const exported = fs.readFileSync(await download.path(), "utf8");
    check(exported.split("\n")[1] === "版本 9.8.7", "export header uses the same API version");
    await context.close();

    const unavailable = await browser.newContext();
    await unavailable.addInitScript(record => {
      localStorage.setItem("wishlab.history.v1", JSON.stringify([record]));
    }, legacy);
    await unavailable.route("**/api/version", route => route.abort("failed"));
    const offline = await unavailable.newPage();
    await offline.goto(root);
    await offline.waitForFunction(() => document.querySelector(".version-tag").textContent === "unavailable");
    await offline.locator(".history-item").click();
    check(await offline.locator("#app-version").textContent() === "unavailable", "history cannot overwrite an unavailable live version");
    await offline.locator("#open-settings").click();
    const offlineDownload = offline.waitForEvent("download");
    await offline.locator("#download-history").click();
    const offlineFile = await offlineDownload;
    check(fs.readFileSync(await offlineFile.path(), "utf8").split("\n")[1] === "Version unavailable", "failed version fetch never exports an invented release");
    await unavailable.close();
    check(errors.length === 0, "no JavaScript errors: " + errors.join("; "));
    console.log(JSON.stringify({ checks, errors, artifacts }, null, 2));
  } finally {
    await client.close();
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
