import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE = process.env.PW_BASE_URL || 'http://localhost:3000';
const OUT = path.resolve(
  'C:/Users/eminb/Projects/investhome-os/tmp-browser-verify-output/product-polish-p6',
);
const EMAIL = 'superadmin@investhome.demo';
const PASS = 'Demo123!';

fs.mkdirSync(OUT, { recursive: true });

const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  laptop: { width: 1280, height: 800 },
  tablet: { width: 900, height: 1200 },
};

function shot(...parts) {
  return path.join(OUT, parts.join('-') + '.png');
}

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 90000 });
  const email = page.locator('input[type="email"]').first();
  await email.waitFor({ state: 'visible', timeout: 45000 });
  await email.fill(EMAIL);
  await page.locator('input[type="password"]').first().fill(PASS);
  await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes('/auth/login') && r.request().method() === 'POST',
      { timeout: 60000 },
    ),
    page.locator('button[type="submit"]').first().click(),
  ]);
  await page.waitForURL(/\/dashboard/, { timeout: 90000 });
  await page.waitForSelector('.dashboard-shell__sidebar', { timeout: 45000 });
  await page.waitForTimeout(800);
}

async function collectConsole(page, bucket) {
  page.on('console', (msg) => {
    if (msg.type() === 'error') bucket.push({ type: 'console', text: msg.text() });
  });
  page.on('pageerror', (err) => {
    bucket.push({ type: 'pageerror', text: String(err) });
  });
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ locale: 'tr-TR' });
  const page = await context.newPage();
  const consoleErrors = [];
  await collectConsole(page, consoleErrors);

  const report = {
    base: BASE,
    startedAt: new Date().toISOString(),
    checks: {},
    screenshots: {},
    failures: [],
    consoleErrors: [],
  };

  try {
    await login(page);

    // Nav: AI Workspace link
    const aiNav = page.locator('a.dashboard-shell__nav-link', { hasText: /YZ Çalışma Alanı|AI Workspace/i });
    await aiNav.first().waitFor({ state: 'visible', timeout: 15000 });
    report.checks.navAiWorkspace = { present: true };
    await page.screenshot({ path: shot('nav-ai'), fullPage: false });
    report.screenshots.nav = shot('nav-ai');

    // Global AI button
    const globalBtn = page.locator('.ai-global-btn').first();
    report.checks.globalButton = { present: (await globalBtn.count()) > 0 };

    // Home
    await page.goto(`${BASE}/dashboard/ai`, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForSelector('[data-ai-workspace]', { timeout: 45000 });
    await page.waitForFunction(
      () => {
        const panels = document.querySelectorAll('.ai-workspace .ih-panel').length;
        const denied = (document.body.innerText || '').includes('yetkiniz yok')
          || (document.body.innerText || '').includes('do not have permission');
        const loading = (document.body.innerText || '').includes('Yükleniyor')
          || (document.body.innerText || '').includes('Loading');
        return panels >= 4 || (denied && !loading);
      },
      { timeout: 45000 },
    );
    await page.waitForTimeout(500);
    const home = await page.evaluate(() => {
      const root = document.querySelector('[data-ai-workspace]');
      const panels = document.querySelectorAll('.ai-workspace .ih-panel').length;
      const brand = !!document.querySelector('.brand-logo, img[src*="investhome"]');
      const brandPrimary = getComputedStyle(document.documentElement)
        .getPropertyValue('--brand-primary')
        .trim();
      const overflowX = document.documentElement.scrollWidth > document.documentElement.clientWidth + 2;
      const navLinks = [...document.querySelectorAll('.ai-workspace__nav-link')].map((el) =>
        (el.textContent || '').trim(),
      );
      return { hasRoot: !!root, panels, brand, brandPrimary, overflowX, navLinks };
    });
    report.checks.home = home;
    await page.screenshot({ path: shot('desktop', 'home'), fullPage: true });
    report.screenshots.home = shot('desktop', 'home');
    if (!home.hasRoot || home.panels < 4) report.failures.push('AI home missing panels');
    if (home.overflowX) report.failures.push('AI home overflow-x');

    // Open copilot from home
    await page.locator('button', { hasText: /Copilot/i }).first().click();
    await page.waitForSelector('.ai-copilot-drawer__panel', { timeout: 10000 });
    await page.screenshot({ path: shot('copilot-open'), fullPage: false });
    report.screenshots.copilot = shot('copilot-open');
    report.checks.copilotOpen = true;
    const chips = await page.locator('.ai-copilot-drawer__chip').count();
    report.checks.copilotSuggestions = chips;
    if (chips < 4) report.failures.push('Copilot suggested prompts missing');
    await page.locator('.ai-copilot-drawer__scrim').click({ force: true });
    await page.waitForTimeout(300);

    // Prompts library
    await page.goto(`${BASE}/dashboard/ai/prompts`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('.ai-workspace', { timeout: 30000 });
    await page.waitForFunction(
      () =>
        document.querySelectorAll('.ai-prompts__card').length >= 1
        || (document.body.innerText || '').includes('yetkiniz yok'),
      { timeout: 45000 },
    );
    const promptCards = await page.locator('.ai-prompts__card').count();
    report.checks.promptLibrary = { cards: promptCards };
    await page.screenshot({ path: shot('prompts'), fullPage: true });
    report.screenshots.prompts = shot('prompts');
    if (promptCards < 6) report.failures.push('Prompt library sparse');

    // History
    await page.goto(`${BASE}/dashboard/ai/history`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('.ai-history__search, .ai-workspace', { timeout: 30000 });
    report.checks.history = { present: true };
    await page.screenshot({ path: shot('history'), fullPage: true });
    report.screenshots.history = shot('history');

    // Settings
    await page.goto(`${BASE}/dashboard/ai/settings`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('.ai-settings__form', { timeout: 30000 });
    report.checks.settings = { present: true };
    await page.screenshot({ path: shot('settings'), fullPage: true });
    report.screenshots.settings = shot('settings');

    // Contextual AI on sales
    await page.goto(`${BASE}/dashboard/sales`, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForSelector('.dashboard.sales, main.sales, .sales', { timeout: 45000 }).catch(() => {});
    await page.waitForFunction(
      () => document.querySelector('.ai-contextual') || document.querySelector('.dashboard__title'),
      { timeout: 45000 },
    );
    await page.waitForTimeout(800);
    const contextual = await page.locator('.ai-contextual').count();
    report.checks.contextualSales = { present: contextual > 0 };
    if (contextual > 0) {
      await page.locator('.ai-contextual__btn').first().click();
      await page.waitForSelector('.ai-action-dialog__panel', { timeout: 10000 });
      await page.screenshot({ path: shot('action-dialog'), fullPage: false });
      report.screenshots.actionDialog = shot('action-dialog');
      report.checks.actionDialog = true;
      await page.locator('.ai-action-dialog .ih-dialog__close, .ai-action-dialog .ih-btn--secondary').first().click();
    } else {
      report.failures.push('Contextual AI missing on sales');
    }

    // Responsive home
    for (const [name, vp] of Object.entries(VIEWPORTS)) {
      await page.setViewportSize(vp);
      await page.goto(`${BASE}/dashboard/ai`, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForSelector('[data-ai-workspace]', { timeout: 30000 });
      await page.waitForTimeout(400);
      const overflowX = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
      );
      await page.screenshot({ path: shot(name, 'ai-home'), fullPage: true });
      report.screenshots[`ai-${name}`] = shot(name, 'ai-home');
      report.checks[`responsive_${name}`] = { overflowX };
      if (overflowX) report.failures.push(`overflow-x on ${name}`);
    }

    // Filter noisy console (Next.js HMR / favicon / transient CORS during auth race)
    report.consoleErrors = consoleErrors.filter(
      (e) =>
        !/favicon|Download the React DevTools|hydrat|Fast Refresh/i.test(e.text) &&
        !/Failed to load resource: the server responded with a status of 4\d\d/i.test(e.text) &&
        !/CORS policy|net::ERR_FAILED/i.test(e.text),
    );
    if (report.consoleErrors.length) {
      report.failures.push(`console errors: ${report.consoleErrors.length}`);
    }
  } catch (err) {
    report.failures.push(String(err));
    try {
      await page.screenshot({ path: shot('error'), fullPage: true });
    } catch {
      /* ignore */
    }
  } finally {
    report.finishedAt = new Date().toISOString();
    report.ok = report.failures.length === 0;
    fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
    await browser.close();
    console.log(JSON.stringify({ ok: report.ok, failures: report.failures, out: OUT }, null, 2));
    if (!report.ok) process.exitCode = 1;
  }
}

run();
