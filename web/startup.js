"use strict";

// Parser-blocking startup: no dependency on the deferred calculator script.
// Translations and settings validation have one shared definition.
(() => {
const STRINGS = {
  en: {
    exactEngine: "EXACT PROBABILITY ENGINE", eyebrow: "GENSHIN IMPACT · WISH PLANNER",
    headline: "Make every wish count.", intro: "Know your odds. Set your target. Plan your next pull with confidence.",
    modeLabel: "Calculation mode", characterMode: "Character", weaponMode: "Weapon", combinedMode: "Character + Weapon",
    characterCaption: "Featured characters, with Capturing Radiance taken into account.",
    weaponCaption: "Your charted weapon, with the one-Fate-Point Epitomized Path.",
    combinedCaption: "Character first. Then your weapon, using the wishes left over.",
    yourPlan: "Your wish plan", stopAtTarget: "STOP AT TARGET", budget: "Available wishes", wishes: "wishes",
    budgetHint: "One shared budget. Every unused wish stays yours.", characterState: "Character banner", weaponState: "Weapon banner",
    currentPity: "Current pity", targetCopies: "Target copies", characterPityHint: "0–89 since your last 5-star", weaponPityHint: "0–79 since your last 5-star",
    targetHint: "Additional featured copies", weaponTargetHint: "Copies of your charted weapon",
    featuredGuaranteed: "Guaranteed featured 5-star", featuredHint: "Your last non-guaranteed 5-star was a loss",
    promotedGuaranteed: "Guaranteed promoted 5-star", promotedHint: "A promoted weapon, not necessarily your target",
    advancedCR: "Capturing Radiance counter", crCounter: "Assumed hidden counter",
    crHint: "Community assumption. Starts at C1; leave unchanged if unknown.",
    fatePoint: "Epitomized Path · Fate Point", fateHint: "Chart your desired weapon first. Fate Points reset between banners.",
    characterModel: "Community soft pity + community Capturing Radiance. These are modeling assumptions, not official per-wish formulas.",
    weaponModel: "Community weapon soft pity + one-Fate-Point Epitomized Path. The soft-pity curve is a modeling assumption.",
    combinedModel: "Community soft pity on both banners, with character Capturing Radiance. Character first; each target stops its banner.",
    calculate: "Calculate probability", calculating: "Calculating your plan…",
    cancelCalculation: "Cancel", retryCalculation: "Retry calculation",
    loadingResult: "Calculating exact probabilities… Previous numbers are hidden until this attempt finishes.",
    cancelledCalculation: "Calculation cancelled. You can change your plan or retry.",
    timedOutCalculation: "The calculation took longer than 30 seconds. Please retry or try a smaller plan.",
    previousResult: "Last successful result — not a result of this attempt.",
    previousResultStatus: "PREVIOUS RESULT", calculationFailed: "NOT COMPLETED",
    versionUnavailable: "unavailable", versionHeader: "Version {version}",
    recentCalculations: "Recent calculations", clear: "Clear", noHistory: "Your last five plans will appear here.",
    historyDisabled: "History is off. Calculations are not stored.", restoreHistory: "Restore calculation",
    yourOdds: "Your odds", emptyTitle: "A little foresight goes a long way.",
    emptyBody: "Choose your banner, enter your plan, and let the probabilities do the rest.",
    exactNotSimulation: "EXACT CALCULATION · NO SIMULATION", ready: "CALCULATED", updated: "RECALCULATE",
    successWithinBudget: "chance of reaching your target within budget",
    expectedCompletion: "Average wishes to target", unconditional: "E[T] · without a budget limit",
    conditionalCompletion: "Average when successful", conditional: "E[T | success within budget]",
    stale: "Inputs changed. Calculate again to update these results.",
    success: "Target reached", unfinished: "Target not reached", both: "Both goals completed",
    character_only: "Character completed, weapon unfinished", character_failed: "Character unfinished",
    likelyOutcomes: "Most likely outcomes", outcomesHint: "Copies at the end of your plan. Pulling stops at each target.",
    targetAlwaysShown: "Your requested outcome is always shown, even outside the top list. Ties share a rank.",
    yourTarget: "YOUR TARGET", topCount: "TOP {n}", characterOutcome: "{n} character copies", weaponOutcome: "{n} weapon copies",
    combinedOutcome: "{c} character + {w} weapon copies",
    targetSummaryCharacter: "Target: {c} character copies · {n} wishes",
    targetSummaryWeapon: "Target: {w} weapon copies · {n} wishes",
    targetSummaryCombined: "Target: {c} character + {w} weapon copies · {n} wishes",
    planConfidence: "Plan for your confidence", confidenceTarget: "target success probability",
    minimumTotal: "minimum total wishes", confidenceSlider: "Desired probability from 0% to 100%", confidencePresets: "Confidence presets",
    confidenceExplanation: "Exact minimum budget, not an average wait. Drag to a preset or choose a button. 100% uses the model’s finite guarantee.",
    budgetDelta: "{n} more wishes than your current budget.", budgetEnough: "Your current budget meets this confidence level.",
    footer: "A clearer view of chance. Built for Travelers.", versionFooter: "VERSION {version}",
    settings: "Settings", openSettings: "Open settings", closeSettings: "Close settings", makeItYours: "MAKE IT YOURS",
    calculatorSettings: "Calculator settings", historySetting: "Calculation history",
    historyHint: "Store the latest 5 calculations on this device.", historyOffHint: "Turning history off removes saved records from this browser.",
    downloadHistory: "Download calculation data (.txt)", precision: "Probability decimal places", precisionHint: "Probabilities only. Averages use one decimal; counts use whole numbers. Calculations keep full precision.",
    outcomesSetting: "Outcomes list", outcomesSettingHint: "Top N outcomes (1–10), plus your target.",
    appearance: "Appearance", colorTheme: "Color theme", systemTheme: "Follow system", darkTheme: "Dark", lightTheme: "Light",
    fontSize: "Font size", smallFont: "Small", normalFont: "Default", largeFont: "Large",
    animations: "CSS animations", animationsHint: "Your system’s reduced-motion preference is respected.",
    languagePreferences: "Language preferences", language: "Language", helpCenter: "Help center", about: "About the calculator",
    settingsCategories: "Settings categories", settingsBrandCaption: "A clearer view of chance.",
    aboutText: "We track every possible pity, guarantee, and counter state using exact dynamic programming. Combined mode uses completion-time distributions to plan characters first, then weapons. Community soft pity and the community Capturing Radiance counter are assumed, not official per-wish formulas. Results depend on those assumptions.",
    version: "Version", contact: "Contact author / report an issue", terms: "Terms and policies",
    termsText: "This independent fan-made tool is for learning and planning. It is not affiliated with HoYoverse and does not guarantee in-game results. No account, purchase, or wish-history upload is required. Form inputs are sent only to the calculator backend. Settings and up to five calculations stay in your browser; this app does not save calculation history on the server or use analytics. Local server request logs may record request metadata. You can clear history at any time. Exported files are under your control.",
    storageError: "Browser storage is unavailable. Settings and history will last only for this session.",
    networkError: "Could not reach the calculator. Start the backend and open this page through its localhost address.",
    apiError: "Calculation failed. Please try again.", invalidRequest: "Check your inputs. Wishes: 0–2000; target copies: 0–10; character pity: 0–89; weapon pity: 0–79.",
    settingsInvalid: "Enter a whole number in the allowed range.", noSavedData: "No saved calculations to download.",
    dataDownloaded: "Calculation data downloaded.", historyCleared: "Saved history cleared.", phase1: "PHASE 1", phase2: "PHASE 2",
    notDefined: "—", successAnnounce: "Calculation complete. Success probability: {p}.",
    savingOff: "History is off; this result is not saved."
  },
  zh: {
    exactEngine: "精确概率计算引擎", eyebrow: "原神 · 祈愿规划工具", headline: "让每一次祈愿，心中有数。",
    intro: "了解概率，设定目标，为下一次祈愿做好准备。",
    modeLabel: "计算模式", characterMode: "角色祈愿", weaponMode: "武器祈愿", combinedMode: "角色 + 武器",
    characterCaption: "计算限定角色获取概率，包含捕获明光机制。",
    weaponCaption: "计算定轨武器获取概率，采用 1 命定值的神铸定轨规则。",
    combinedCaption: "先抽角色，再用剩余祈愿抽取武器。",
    yourPlan: "你的祈愿计划", stopAtTarget: "达成目标即停止", budget: "可用祈愿数", wishes: "抽",
    budgetHint: "共用一份预算，剩余的每一抽都会保留。",
    characterState: "角色活动祈愿", weaponState: "武器活动祈愿", currentPity: "当前垫抽", targetCopies: "目标数量",
    characterPityHint: "上次五星后的连续祈愿数，0–89", weaponPityHint: "上次五星后的连续祈愿数，0–79",
    targetHint: "本次需要新增的限定角色数量", weaponTargetHint: "本次需要新增的定轨武器数量",
    featuredGuaranteed: "下个五星必为限定角色", featuredHint: "上次非大保底的五星未获得限定角色",
    promotedGuaranteed: "下个五星必为当期 UP 武器", promotedHint: "保证为 UP 武器，但不一定是你的目标",
    advancedCR: "捕获明光计数器", crCounter: "假定的隐藏计数",
    crHint: "社区推测模型，初始值为 C1。不确定时保留默认值。",
    fatePoint: "神铸定轨 · 命定值", fateHint: "请先为目标武器定轨。命定值不跨武器祈愿期继承。",
    characterModel: "默认采用社区软保底曲线和捕获明光计数模型。这些属于建模假设，并非官方公布的逐抽公式。",
    weaponModel: "默认采用社区武器软保底曲线和 1 命定值定轨规则。软保底曲线属于建模假设。",
    combinedModel: "两种祈愿均采用社区软保底，角色包含捕获明光。先角色后武器，各自达标即停止。",
    calculate: "计算获取概率", calculating: "正在计算你的计划…",
    cancelCalculation: "取消", retryCalculation: "重新计算",
    loadingResult: "正在计算精确概率……本次计算完成前将隐藏上次的数值。",
    cancelledCalculation: "已取消计算。你可以修改计划或重新计算。",
    timedOutCalculation: "计算已超过 30 秒。请重试或尝试较小的计划。",
    previousResult: "上次成功的计算结果，并非本次尝试的结果。",
    previousResultStatus: "上次的结果", calculationFailed: "未完成",
    versionUnavailable: "暂不可用", versionHeader: "版本 {version}",
    recentCalculations: "最近计算", clear: "清空", noHistory: "最近五次计算将显示在这里。",
    historyDisabled: "历史记录已关闭，计算结果不会保存。", restoreHistory: "恢复此次计算",
    yourOdds: "你的获取概率", emptyTitle: "多一点了解，多一份从容。",
    emptyBody: "选择祈愿类型，输入你的计划，即可查看精确概率。",
    exactNotSimulation: "精确计算 · 非随机模拟", ready: "已计算", updated: "待重新计算",
    successWithinBudget: "在预算内达成目标的概率",
    expectedCompletion: "平均达标祈愿数", unconditional: "E[T] · 不限制预算",
    conditionalCompletion: "成功时的平均达标抽数", conditional: "E[T | 在预算内成功]",
    stale: "输入已变更，请重新计算以更新结果。",
    success: "已达成目标", unfinished: "未达成目标", both: "角色与武器均达标",
    character_only: "角色达标，武器未达标", character_failed: "角色未达标",
    likelyOutcomes: "最可能出现的结果", outcomesHint: "计划结束时新增的数量，各祈愿在达标后立即停止。",
    targetAlwaysShown: "你的指定结果始终显示，即使未进入前列。概率相同的结果共享排名。",
    yourTarget: "你的目标", topCount: "前 {n} 项", characterOutcome: "{n} 个角色", weaponOutcome: "{n} 把武器",
    combinedOutcome: "{c} 个角色 + {w} 把武器",
    targetSummaryCharacter: "目标：{c} 个角色 · {n} 抽",
    targetSummaryWeapon: "目标：{w} 把武器 · {n} 抽",
    targetSummaryCombined: "目标：{c} 个角色 + {w} 把武器 · {n} 抽",
    planConfidence: "按把握规划预算", confidenceTarget: "目标成功概率", minimumTotal: "所需的最少总抽数",
    confidenceSlider: "目标概率，从 0% 到 100%", confidencePresets: "成功概率预设",
    confidenceExplanation: "这里是精确的最少预算，不是平均等待抽数。拖动至预设位置或点击按钮。100% 使用模型的有限保底上界。",
    budgetDelta: "比当前预算还需 {n} 抽。", budgetEnough: "当前预算已达到此成功概率。",
    footer: "看清概率，安心规划。为旅行者而作。", versionFooter: "版本 {version}",
    settings: "设置", openSettings: "打开设置", closeSettings: "关闭设置", makeItYours: "按照你的偏好",
    calculatorSettings: "计算器设置", historySetting: "计算历史", historyHint: "在此设备上保存最近 5 次计算。",
    historyOffHint: "关闭历史记录将移除此浏览器中已保存的计算。",
    downloadHistory: "下载计算数据（.txt）", precision: "概率小数位数", precisionHint: "仅调整概率显示。平均值保留一位小数，数量显示整数，计算仍保留完整精度。",
    outcomesSetting: "结果列表", outcomesSettingHint: "显示概率最高的前 N 项（1–10），另加你的目标。",
    appearance: "外观", colorTheme: "颜色主题", systemTheme: "跟随系统", darkTheme: "深色模式", lightTheme: "浅色模式",
    fontSize: "字号", smallFont: "较小", normalFont: "默认", largeFont: "较大",
    animations: "CSS 动画", animationsHint: "同时遵循系统的减弱动态效果偏好。",
    languagePreferences: "语言偏好", language: "语言", helpCenter: "帮助中心", about: "关于计算器",
    settingsCategories: "设置分类", settingsBrandCaption: "看清概率，安心规划。",
    aboutText: "计算器使用精确动态规划，追踪每一种垫抽、保底及计数器状态。组合模式通过达标时间分布实现先角色后武器。社区软保底和捕获明光隐藏计数均为建模假设，并非官方逐抽概率公式。结果依赖所采用的假设。",
    version: "版本", contact: "联系作者 / 反馈问题", terms: "条款与政策",
    termsText: "本工具由玩家独立制作，用于学习和规划，与 HoYoverse 无隶属关系，也不保证游戏中的实际结果。无需账号、购买或上传祈愿历史。表单输入仅发送至计算后端。设置及最多五次计算保存在浏览器中，本应用不在服务器保存计算历史，也不使用分析追踪。 本地服务器请求日志可能记录请求元数据。你可以随时清空历史；导出的文件由你自行保管。",
    storageError: "浏览器存储不可用。设置与历史仅在当前会话中保留。",
    networkError: "无法连接计算器。请启动后端，并通过其 localhost 地址打开页面。",
    apiError: "计算失败，请重试。", invalidRequest: "请检查输入：祈愿数 0–2000；目标数量 0–10；角色垫抽 0–89；武器垫抽 0–79。",
    settingsInvalid: "请输入允许范围内的整数。", noSavedData: "暂无可下载的计算记录。",
    dataDownloaded: "计算数据已下载。", historyCleared: "已清空历史记录。", phase1: "第一阶段", phase2: "第二阶段",
    notDefined: "—", successAnnounce: "计算完成，目标成功概率为 {p}。",
    savingOff: "历史记录已关闭，此结果不会保存。"
  }
};

const DEFAULTS = { history: true, precision: 2, outcomes: 3, theme: "system", font: 14, animations: true, language: "en" };
function validateSettings(value) {
  const s = { ...DEFAULTS };
  if (!value || typeof value !== "object") return s;
  for (const key of ["history", "animations"]) if (typeof value[key] === "boolean") s[key] = value[key];
  if (Number.isInteger(value.precision) && value.precision >= 0 && value.precision <= 10) s.precision = value.precision;
  if (Number.isInteger(value.outcomes) && value.outcomes >= 1 && value.outcomes <= 10) s.outcomes = value.outcomes;
  for (const [key, values] of Object.entries({ theme: ["system", "dark", "light"], language: ["en", "zh"] })) {
    if (values.includes(value[key])) s[key] = value[key];
  }
  const legacyFonts = { small: 14, normal: 16, large: 18 };
  const font = typeof value.font === "string" ? legacyFonts[value.font] : value.font;
  if (Number.isInteger(font) && font >= 10 && font <= 20) s.font = font;
  return s;
}
  function applyAppearance(settings) {
    const root = document.documentElement;
    root.dataset.theme = settings.theme === "system"
      ? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light") : settings.theme;
    root.dataset.animations = settings.animations ? "on" : "off";
    root.dataset.longNumbers = settings.precision > 4 ? "true" : "false";
    root.style.setProperty("--size", settings.font + "px");
  }
  let saved;
  try { saved = JSON.parse(localStorage.getItem("wishlab.settings.v1")); }
  catch { /* Invalid/blocked storage uses the same defaults as the main app. */ }
  const settings = validateSettings(saved);
  applyAppearance(settings);
  document.documentElement.lang = settings.language === "zh" ? "zh-CN" : "en";
  const title = settings.language === "zh" ? "Wish Lab · 原神祈愿概率计算器" : "Wish Lab · Genshin Wish Probability Calculator";

  // Translate parser additions in microtasks, before the browser can paint them.
  // Never hide the document: static HTML remains readable if either script fails.
  const selector = "[data-i18n], [data-i18n-aria]";
  function translate(element) {
    const text = STRINGS[settings.language][element.dataset.i18n];
    if (text !== undefined && element.textContent !== text) element.textContent = text;
    const label = STRINGS[settings.language][element.dataset.i18nAria];
    if (label !== undefined) element.setAttribute("aria-label", label);
  }
  const observer = new MutationObserver(records => {
    const elements = new Set();
    for (const record of records) {
      const target = record.target.nodeType === Node.ELEMENT_NODE ? record.target : record.target.parentElement;
      const owner = target?.closest(selector);
      if (owner) elements.add(owner);
      for (const node of record.addedNodes) {
        if (node.nodeType !== Node.ELEMENT_NODE) continue;
        if (node.matches(selector)) elements.add(node);
        node.querySelectorAll(selector).forEach(element => elements.add(element));
      }
    }
    elements.forEach(translate);
    if (document.title !== title) document.title = title;
  });
  observer.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
  document.addEventListener("DOMContentLoaded", () => observer.disconnect(), { once: true });
  window.WishLabStartup = { STRINGS, DEFAULTS, validateSettings, applyAppearance };
})();
