/**
 * GitHub UI G1 visual QA — opens admin preview, captures screenshots.
 */
import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE = process.env.PW_BASE_URL || 'http://localhost:3000';
const OUT = path.resolve('C:/Users/eminb/Projects/investhome-os/artifacts/github-ui-g1');
const EMAIL = 'superadmin@investhome.demo';
const PASS = 'Demo123!';

fs.mkdirSync(OUT, { recursive: true });

const results = {
  login_ok: false,
  route_ok: false,
  tabs: { sales: false, projects: false, marketing: false },
  drawer_ok: false,
  screenshots: [],
  errors: [],
};

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.locator('input[type="email"]').first().fill(EMAIL);
  await page.locator('input[type="password"]').first().fill(PASS);
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/dashboard/, { timeout: 60000 });
  results.login_ok = true;
}

async function shot(page, name) {
  const file = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: file, fullPage: false });
  results.screenshots.push(file);
  return file;
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  locale: 'tr-TR',
});
const page = await context.newPage();
page.on('pageerror', (err) => results.errors.push(String(err)));

try {
  await login(page);

  await page.goto(`${BASE}/dashboard/admin/github-ui-preview`, {
    waitUntil: 'networkidle',
    timeout: 90000,
  });
  await page.waitForSelector('[data-testid="github-ui-preview"]', { timeout: 30000 });
  results.route_ok = true;

  // Sales pipeline (default tab)
  await page.waitForSelector('[data-testid="g1-sales-pipeline"]', { timeout: 15000 });
  results.tabs.sales = true;
  await shot(page, 'pipeline-1440');
  await shot(page, 'pipeline');

  // Open opportunity drawer
  await page.locator('[data-testid^="g1-opp-"]').first().click();
  await page.waitForSelector('[data-testid="g1-opp-drawer"]', { timeout: 10000 });
  results.drawer_ok = true;
  await shot(page, 'opportunity-drawer-1440');
  await shot(page, 'opportunity-drawer');
  await page.locator('[data-testid="g1-opp-drawer"] .g1-drawer__close').click();
  await page.waitForSelector('[data-testid="g1-opp-drawer"]', { state: 'detached', timeout: 10000 });

  // Project operations
  await page.locator('[data-testid="g1-tab-projects"]').click();
  await page.waitForSelector('[data-testid="g1-project-ops"]', { timeout: 15000 });
  results.tabs.projects = true;
  await shot(page, 'project-operations-1440');
  await shot(page, 'project-operations');

  // Marketing analytics
  await page.locator('[data-testid="g1-tab-marketing"]').click();
  await page.waitForSelector('[data-testid="g1-marketing"]', { timeout: 15000 });
  results.tabs.marketing = true;
  await shot(page, 'marketing-analytics-1440');
  await shot(page, 'marketing-analytics');

  // 1280 viewport
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.locator('[data-testid="g1-tab-sales"]').click();
  await page.waitForSelector('[data-testid="g1-sales-pipeline"]');
  await shot(page, 'pipeline-1280');
  await page.locator('[data-testid="g1-tab-projects"]').click();
  await page.waitForSelector('[data-testid="g1-project-ops"]');
  await shot(page, 'project-operations-1280');
  await page.locator('[data-testid="g1-tab-marketing"]').click();
  await page.waitForSelector('[data-testid="g1-marketing"]');
  await shot(page, 'marketing-analytics-1280');

  const pass =
    results.login_ok &&
    results.route_ok &&
    results.tabs.sales &&
    results.tabs.projects &&
    results.tabs.marketing &&
    results.drawer_ok;

  fs.writeFileSync(path.join(OUT, 'qa-result.json'), JSON.stringify({ pass, ...results }, null, 2));
  console.log(JSON.stringify({ pass, ...results }, null, 2));
  if (!pass) process.exit(1);
} catch (err) {
  results.errors.push(String(err));
  fs.writeFileSync(path.join(OUT, 'qa-result.json'), JSON.stringify({ pass: false, ...results }, null, 2));
  console.error(err);
  process.exit(1);
} finally {
  await browser.close();
}
