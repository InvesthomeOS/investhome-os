/**
 * D1D.2 mandatory localhost Playwright proof.
 * Writes screenshots under artifacts/dashboard-d1d2/ and a JSON summary.
 *
 * Run from repo root:
 *   node scripts/d1d2-playwright-proof.mjs
 *
 * Requires: playwright installed (apps/web), localhost:3000 serving current build.
 */
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(__dirname, '..');
const OUT = join(repoRoot, 'artifacts', 'dashboard-d1d2');
const BASE = process.env.PW_BASE_URL || 'http://localhost:3000';
const EMAIL = process.env.DEMO_EMAIL || 'superadmin@investhome.demo';
const PASSWORD = process.env.DEMO_PASSWORD || 'Demo123!';

const require = createRequire(join(repoRoot, '.pw-verify', 'package.json'));
const { chromium } = require('playwright');

mkdirSync(OUT, { recursive: true });

const consoleErrors = [];
const css404 = [];
const mutatingMethods = [];
const results = {
  base: BASE,
  startedAt: new Date().toISOString(),
  screenshots: {},
  http: {},
  assertions: {},
  consoleErrors: [],
  css404: [],
  mutatingOnLoad: [],
};

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' });
  await page.fill('input[type="email"]', EMAIL);
  await page.fill('input[type="password"]', PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForSelector('.dashboard-shell', { timeout: 45_000 });
}

async function shot(page, name) {
  const path = join(OUT, `${name}.png`);
  await page.screenshot({ path, fullPage: true });
  results.screenshots[name] = path;
  return path;
}

function trackPage(page) {
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push({ text: msg.text(), url: page.url() });
    }
  });
  page.on('pageerror', (err) => {
    consoleErrors.push({ text: err.message, url: page.url() });
  });
  page.on('response', (resp) => {
    const url = resp.url();
    if (resp.status() === 404 && /\.css(\?|$)/i.test(url)) {
      css404.push(url);
    }
  });
  page.on('request', (req) => {
    const method = req.method().toUpperCase();
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      // Ignore login/auth bootstrap
      if (/\/auth\/|\/login|\/api\/auth/i.test(req.url())) return;
      mutatingMethods.push({ method, url: req.url(), page: page.url() });
    }
  });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  trackPage(page);

  await login(page);

  // Force light theme for unmissable visual comparison
  await page.evaluate(() => {
    localStorage.setItem('investhome-theme', 'light');
    document.documentElement.setAttribute('data-theme', 'light');
  });

  // 1) Prototype route
  const protoResp = await page.goto(`${BASE}/dashboard/admin/design-system/executive-dashboard`, {
    waitUntil: 'networkidle',
    timeout: 60_000,
  });
  results.http.prototype = protoResp?.status() ?? 0;
  await page.waitForSelector('[data-testid="executive-dashboard-prototype"]', { timeout: 30_000 });
  await shot(page, '01-prototype');

  const protoHasMarketing = (await page.locator('[data-testid="exec-proto-marketing-widget"]').count()) > 0;
  const protoTasks = (await page.locator('[data-testid="exec-proto-tasks-widget"]').count()) > 0;
  const protoCal = (await page.locator('[data-testid="exec-proto-calendar-widget"]').count()) > 0;
  const protoAi = (await page.locator('[data-testid="exec-proto-ai-widget"]').count()) > 0;
  const protoComms = (await page.locator('[data-testid="exec-proto-comms-widget"]').count()) > 0;
  results.assertions.prototype = {
    http200: results.http.prototype === 200,
    marketing: protoHasMarketing,
    tasks: protoTasks,
    calendar: protoCal,
    tasksNeCalendar: protoTasks && protoCal,
    ai: protoAi,
    comms: protoComms,
    aiNeComms: protoAi && protoComms,
  };

  // 2) Production default
  mutatingMethods.length = 0;
  const prodResp = await page.goto(`${BASE}/dashboard/executive`, {
    waitUntil: 'networkidle',
    timeout: 60_000,
  });
  results.http.production = prodResp?.status() ?? 0;
  await page.waitForSelector('[data-testid="executive-dashboard-production"]', { timeout: 45_000 });
  const legacyOnDefault = (await page.locator('[data-testid="executive-dashboard-legacy"]').count()) > 0;
  await shot(page, '02-production');
  results.assertions.production = {
    http200: results.http.production === 200,
    isNew: (await page.locator('[data-testid="executive-dashboard-production"]').count()) > 0,
    notLegacy: !legacyOnDefault,
    marketing: (await page.locator('[data-testid="exec-prod-marketing-widget"]').count()) > 0,
    tasks: (await page.locator('[data-testid="exec-prod-tasks-widget"]').count()) > 0,
    calendar: (await page.locator('[data-testid="exec-prod-calendar-widget"]').count()) > 0,
    ai: (await page.locator('[data-testid="exec-prod-ai-widget"]').count()) > 0,
    comms: (await page.locator('[data-testid="exec-prod-comms-widget"]').count()) > 0,
    kpiStrip: (await page.locator('[data-testid="exec-prod-kpi-strip"]').count()) > 0,
    mutatingOnLoad: [...mutatingMethods],
  };

  // 3) Legacy
  const legacyResp = await page.goto(`${BASE}/dashboard/executive?view=legacy`, {
    waitUntil: 'networkidle',
    timeout: 60_000,
  });
  results.http.legacy = legacyResp?.status() ?? 0;
  await page.waitForSelector('[data-testid="executive-dashboard-legacy"]', { timeout: 45_000 });
  const prodOnLegacy = (await page.locator('[data-testid="executive-dashboard-production"]').count()) > 0;
  await shot(page, '03-legacy');
  results.assertions.legacy = {
    http200: results.http.legacy === 200,
    isLegacy: true,
    notProduction: !prodOnLegacy,
  };

  // Unknown view → new
  await page.goto(`${BASE}/dashboard/executive?view=foobar`, {
    waitUntil: 'networkidle',
    timeout: 60_000,
  });
  await page.waitForSelector('[data-testid="executive-dashboard-production"]', { timeout: 45_000 });
  results.assertions.unknownViewIsNew =
    (await page.locator('[data-testid="executive-dashboard-production"]').count()) > 0;

  // 4) Production 1280
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto(`${BASE}/dashboard/executive`, { waitUntil: 'networkidle', timeout: 60_000 });
  await page.waitForSelector('[data-testid="executive-dashboard-production"]', { timeout: 45_000 });
  await shot(page, '04-production-1280');

  // 5) Tablet
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="executive-dashboard-production"]', { timeout: 45_000 });
  await shot(page, '05-tablet');
  const tabletOverflow = await page.evaluate(() => {
    return document.documentElement.scrollWidth > document.documentElement.clientWidth + 2;
  });
  results.assertions.tabletNoHOverflow = !tabletOverflow;

  // 6) Mobile
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="executive-dashboard-production"]', { timeout: 45_000 });
  await shot(page, '06-mobile');
  const mobileOverflow = await page.evaluate(() => {
    return document.documentElement.scrollWidth > document.documentElement.clientWidth + 2;
  });
  results.assertions.mobileNoHOverflow = !mobileOverflow;

  // Design system CSS applied check (production)
  const dsApplied = await page.evaluate(() => {
    const el = document.querySelector('.ds-exec-prod');
    if (!el) return false;
    const styles = getComputedStyle(el);
    return Boolean(styles && styles.display);
  });
  results.assertions.designSystemClassPresent = dsApplied;

  results.consoleErrors = consoleErrors.slice(0, 50);
  results.css404 = [...new Set(css404)];
  results.mutatingOnLoad = results.assertions.production.mutatingOnLoad;
  results.finishedAt = new Date().toISOString();

  const pass =
    results.http.prototype === 200 &&
    results.assertions.prototype.http200 &&
    results.assertions.production.isNew &&
    results.assertions.production.notLegacy &&
    results.assertions.legacy.isLegacy &&
    results.assertions.legacy.notProduction &&
    results.assertions.unknownViewIsNew &&
    results.assertions.production.marketing &&
    results.assertions.production.tasks &&
    results.assertions.production.calendar &&
    results.assertions.production.ai &&
    results.assertions.production.comms &&
    existsSync(join(OUT, '01-prototype.png')) &&
    existsSync(join(OUT, '02-production.png')) &&
    existsSync(join(OUT, '03-legacy.png'));

  results.verdict = pass ? 'PASS' : 'FAIL';
  writeFileSync(join(OUT, 'proof-summary.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results, null, 2));
  console.log(`D1D.2 proof verdict: ${results.verdict}`);

  await browser.close();
  process.exit(pass ? 0 : 1);
})().catch((err) => {
  console.error(err);
  writeFileSync(
    join(OUT, 'proof-summary.json'),
    JSON.stringify({ verdict: 'FAIL', error: String(err) }, null, 2),
  );
  process.exit(1);
});
