/* v1.0.3: quantity formatting, actual pre-main-script rendering, and keyboard rings.
 * Start uvicorn first. Environment overrides match web_smoke.cjs.
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");

(async () => {
  const browser = await chromium.launch({ headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE } : {}) });
  const root = process.env.WISH_WEB_URL || "http://127.0.0.1:8000";
  const artifacts = path.resolve("artifacts/web-v103");
  fs.mkdirSync(artifacts, { recursive: true });
  let checks = 0;
  const errors = [];
  const check = (value, label) => { assert.ok(value, label); checks++; };
  try {
    const client = await browser.newContext();
    const base = await (await client.request.post(root + "/api/calculate", { data: { wish_budget: 240 } })).json();
    // Synthetic display fixture; numerical engine regressions stay in the API suite.
    const data = structuredClone(base);
    data.request.wish_budget = 1200;
    data.expected_wishes = 1234;
    data.conditional_expected_wishes = 1000.25;
    data.thresholds = data.thresholds.map((row, index) => ({ ...row, wishes: index ? 2500 + index : 0 }));
    const record = { schema: 1, id: "format-fixture", date: new Date().toISOString(), data };
    const frames = page => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    for (const language of ["en", "zh"]) {
      for (const precision of [0, 2, 10]) {
        const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
        await context.addInitScript(({ language, precision, record }) => {
          localStorage.setItem("wishlab.settings.v1", JSON.stringify({ language, precision, animations: false }));
          localStorage.setItem("wishlab.history.v1", JSON.stringify([record]));
        }, { language, precision, record });
        const page = await context.newPage();
        page.on("pageerror", error => errors.push(error.message));
        await page.goto(root);
        check((await page.locator(".history-item").textContent()).includes("1,200"), "history uses grouped count");
        await page.locator(".history-item").click();
        check((await page.locator("#result-target").textContent()).includes("1,200"), "summary uses same grouped count");
        check(await page.locator("#expected-wishes").textContent() === "1,234.0", "average always has one decimal");
        check(await page.locator("#conditional-wishes").textContent() === "1,000.3", "conditional average rounds to one decimal");
        check(await page.locator("#threshold-wishes").textContent() === "2,503", "threshold count has no decimals");
        check((await page.locator("#confidence-slider").getAttribute("aria-valuetext")).includes("2,503"), "range accessible text uses grouped count");
        check((await page.locator("#confidence-explanation").textContent()).includes("1,303"), "budget difference uses grouped count");
        const formatted = await page.evaluate(() => ({
          zero: count(0), count: count(1200), missing: average(null), infinity: average(Infinity),
          average: average(162), normal: percent(.123456), low: percent(1e-15), high: percent(1 - 1e-15),
          exactZero: percent(0), exactOne: percent(1),
          combined: targetSummary({ mode: "combined", target_copies: 2, weapon_target: 1, wish_budget: 1200 }),
          weapon: targetSummary({ mode: "weapon", weapon_target: 1, wish_budget: 1200 })
        }));
        check(formatted.zero === "0" && formatted.count === "1,200" && formatted.average === "162.0", "quantity helpers are precision independent");
        check(formatted.missing === "—" && formatted.infinity === "—", "undefined averages remain a dash");
        check(formatted.normal === (12.3456).toFixed(precision) + "%", "probabilities preserve configured precision");
        const unit = 10 ** -precision;
        check(formatted.low === "<" + unit.toFixed(precision) + "%" && formatted.high === ">" + (100 - unit).toFixed(precision) + "%", "near-zero/one guards preserved");
        check(formatted.exactZero === (0).toFixed(precision) + "%" && formatted.exactOne === (100).toFixed(precision) + "%", "exact zero/one use no inequality guards");
        check(formatted.combined.includes("1,200") && formatted.weapon.includes("1,200"), "all mode summaries share count formatter");
        await page.locator("#open-settings").click();
        const downloadPromise = page.waitForEvent("download");
        await page.locator("#download-history").click();
        const text = fs.readFileSync(await (await downloadPromise).path(), "utf8");
        check(text.includes("1,200") && text.includes("1,234.0") && text.includes("2,503"), "readable export uses the same formatters");
        check(text.includes('"wish_budget": 1200') && text.includes('"expected_wishes": 1234'), "raw JSON export stays lossless");
        await context.close();
      }
    }

    // Hold the entire main script indefinitely: the page must paint correctly already.
    for (const [theme, system, language, font] of [
      ["system", "light", "zh", 18], ["light", "dark", "zh", 20],
      ["dark", "light", "en", 10], ["system", "dark", "en", 14]
    ]) {
      const context = await browser.newContext({ colorScheme: system, viewport: { width: 1440, height: 1000 } });
      await context.addInitScript(settings => {
        localStorage.setItem("wishlab.settings.v1", JSON.stringify(settings));
        window.__paintSamples = [];
        new PerformanceObserver(list => {
          for (const entry of list.getEntries()) if (entry.name === "first-contentful-paint") {
            window.__paintSamples.push({ font: getComputedStyle(document.documentElement).fontSize,
              theme: document.documentElement.dataset.theme, language: document.documentElement.lang,
              headline: document.querySelector("h1")?.textContent });
          }
        }).observe({ type: "paint", buffered: true });
      }, { theme, language, font, animations: false });
      const page = await context.newPage();
      page.on("pageerror", error => errors.push(error.message));
      let release;
      const held = new Promise(resolve => { release = resolve; });
      await page.route("**/static/script.js", async route => { await held; await route.continue(); });
      const cdp = await context.newCDPSession(page);
      await cdp.send("Network.enable");
      await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
      await page.goto(root, { waitUntil: "commit" });
      await page.waitForSelector("#open-settings");
      await frames(page);
      await page.waitForFunction(() => window.__paintSamples.length > 0);
      const expectedTheme = theme === "system" ? system : theme;
      const before = await page.evaluate(() => ({
        samples: window.__paintSamples,
        translations: [...document.querySelectorAll("[data-i18n]")].every(el =>
          el.textContent === WishLabStartup.STRINGS[document.documentElement.lang === "en" ? "en" : "zh"][el.dataset.i18n]),
        animation: document.documentElement.dataset.animations,
        background: getComputedStyle(document.documentElement).backgroundColor
      }));
      check(before.samples.every(s => s.font === font + "px" && s.theme === expectedTheme && s.language === (language === "zh" ? "zh-CN" : "en")), "saved appearance and language hold at first contentful paint");
      check(before.samples.every(s => s.headline.includes(language === "zh" ? "让每一次" : "Make every")), "no English hero flash for Chinese users");
      check(before.translations && before.animation === "off", "all parsed labels translated without main script, animations off");
      check(before.background === (expectedTheme === "light" ? "rgb(236, 240, 246)" : "rgb(8, 11, 20)"), "actual painted palette matches preference");
      await page.screenshot({ path: path.join(artifacts, `first-paint-${theme}-${system}-${language}.png`), fullPage: true });
      release();
      await page.waitForLoadState("load");
      check(await page.locator("html").evaluate(el => getComputedStyle(el).fontSize) === font + "px", "main startup does not change font size");
      await page.reload();
      check(await page.locator("html").getAttribute("lang") === (language === "zh" ? "zh-CN" : "en"), "hard reload keeps language");
      await context.close();
    }

    // Fail-open cases: no hidden page even if storage or JavaScript fails.
    for (const failure of ["disabled", "blocked-main", "blocked-startup", "malformed", "storage-denied"]) {
      const context = await browser.newContext({ javaScriptEnabled: failure !== "disabled", colorScheme: "light" });
      if (failure === "malformed") await context.addInitScript(() => localStorage.setItem("wishlab.settings.v1", "{bad json"));
      if (failure === "storage-denied") await context.addInitScript(() => Object.defineProperty(window, "localStorage", { get() { throw new Error("denied"); } }));
      if (failure.startsWith("blocked-")) await context.route("**/static/" + (failure === "blocked-main" ? "script" : "startup") + ".js", route => route.abort());
      const page = await context.newPage();
      await page.goto(root);
      check(await page.locator("h1").isVisible() && await page.locator("#wish_budget").isVisible(), failure + ": static content remains visible");
      check(await page.locator("html").evaluate(el => getComputedStyle(el).backgroundColor) === "rgb(236, 240, 246)", failure + ": system-light fallback");
      if (failure === "disabled") check(await page.locator("noscript").isVisible(), "no-JS explanation is visible");
      await context.close();
    }

    for (const theme of ["dark", "light"]) {
      const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
      await context.addInitScript(({ theme, record }) => {
        localStorage.setItem("wishlab.settings.v1", JSON.stringify({ theme, animations: false }));
        localStorage.setItem("wishlab.history.v1", JSON.stringify([record]));
      }, { theme, record });
      const page = await context.newPage();
      page.on("pageerror", error => errors.push(error.message));
      await page.goto(root);
      await page.locator(".history-item").click();
      // Keyboard modality before focusing controls; transparent range uses wrapper.
      await page.keyboard.press("Tab");
      for (const selector of ["#wish_budget", "#pity", "#target_copies", "#is_guaranteed", "#calculate", "#confidence-slider", "[data-confidence='90']", "#open-settings", ".advanced summary"]) {
        await page.locator(selector).focus();
        const ring = await page.locator(selector).evaluate(el => {
          const visible = el.matches(":focus-visible");
          const rendered = el.type === "range" ? el.parentElement : el;
          const s = getComputedStyle(rendered);
          return { visible, width: s.outlineWidth, style: s.outlineStyle, color: s.outlineColor, shadow: s.boxShadow };
        });
        check(ring.visible && ring.width === "3px" && ring.style === "solid", theme + ": clear keyboard ring on " + selector);
        check(ring.color === (theme === "dark" ? "rgb(165, 155, 255)" : "rgb(99, 81, 198)"), "opaque theme accent focus color");
        check(ring.shadow === "none" || selector === "#calculate" || selector === "#open-settings", "no competing input glow");
      }
      await page.locator("#open-settings").click();
      await page.keyboard.press("Tab");
      for (const selector of ["#setting-precision", "#setting-history", "#close-settings", "#tab-calculator"]) {
        await page.locator(selector).focus();
        check(await page.locator(selector).evaluate(el => el.matches(":focus-visible") && getComputedStyle(el).outlineWidth === "3px"), theme + ": settings focus " + selector);
      }
      await page.locator("#tab-appearance").click();
      await page.keyboard.press("Tab");
      await page.locator("#setting-theme").focus();
      check(await page.locator("#setting-theme").evaluate(el => getComputedStyle(el).outlineStyle === "solid" && getComputedStyle(el).outlineWidth === "3px"), "select has keyboard ring");
      await page.screenshot({ path: path.join(artifacts, `focus-${theme}.png`), fullPage: true });
      // WCAG relative luminance: compare opaque ring with panel/input backgrounds.
      const contrast = await page.evaluate(() => {
        const colors = getComputedStyle(document.documentElement);
        function luminance(hex) {
          const rgb = hex.trim().slice(1).match(/../g).map(x => parseInt(x, 16) / 255).map(x => x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4);
          return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722;
        }
        const accent = luminance(colors.getPropertyValue("--accent"));
        return ["--panel", "--input", "--panel-end", "--soft", "--bg"].map(key => {
          const bg = luminance(colors.getPropertyValue(key));
          return (Math.max(accent, bg) + .05) / (Math.min(accent, bg) + .05);
        });
      });
      check(contrast.every(ratio => ratio >= 3), theme + ": ring contrast exceeds 3:1 on surrounding surfaces");
      await context.close();
    }
    check(errors.length === 0, "no unexpected browser errors: " + errors.join("; "));
    console.log(JSON.stringify({ checks, browserErrors: errors, artifacts }, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
