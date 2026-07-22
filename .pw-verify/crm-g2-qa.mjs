/**
 * CRM G2 visual QA — login + route screenshots.
 */
import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE = process.env.PW_BASE_URL || 'http://localhost:3000';
const OUT = path.resolve('C:/Users/eminb/Projects/investhome-os/artifacts/crm-g2');
const EMAIL = 'superadmin@investhome.demo';
const PASS = 'Demo123!';

fs.mkdirSync(OUT, { recursive: true });

const results = {
  login_ok: false,
  routes: {},
  drawer_ok: false,
  screenshots: [],
  errors: [],
};

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.locator('input[type="email"]').first().fill(EMAIL);
  await page.locator('input[type="password"]').first().fill(PASS);
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/dashboard|workspaces/, { timeout: 60000 });
  results.login_ok = true;
}

async function shot(page, name) {
  const file = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: file, fullPage: false });
  results.screenshots.push(file);
  console.log('shot', name);
  return file;
}

async function visit(page, route, key) {
  await page.goto(`${BASE}${route}`, { waitUntil: 'networkidle', timeout: 90000 });
  await page.waitForTimeout(800);
  results.routes[key] = { url: page.url(), ok: true };
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

  // Leads — desktop / laptop / tablet
  await visit(page, '/workspaces/crm/leads', 'leads');
  await page.waitForSelector('[data-testid="crm-g2-leads"], .crm-g2-leads, main', { timeout: 30000 });
  await shot(page, 'leads-1440');

  await page.setViewportSize({ width: 1280, height: 800 });
  await page.waitForTimeout(400);
  await shot(page, 'leads-1280');

  await page.setViewportSize({ width: 768, height: 1024 });
  await page.waitForTimeout(400);
  await shot(page, 'leads-768');

  // Pipeline board + drawer
  await page.setViewportSize({ width: 1440, height: 900 });
  await visit(page, '/workspaces/crm/pipeline', 'pipeline');
  await page.waitForSelector('[data-testid="crm-g2-pipeline"], .crm-g2-pipeline, main', { timeout: 30000 });
  // Prefer board view
  const boardBtn = page.locator('button').filter({ hasText: /board|pano|Board|Pano/i }).first();
  if (await boardBtn.count()) {
    try { await boardBtn.click({ timeout: 3000 }); } catch {}
  }
  await page.waitForTimeout(500);
  await shot(page, 'pipeline-board-1440');

  const card = page.locator('.crm-g2-card, [data-testid^="crm-g2-opp"], [role="listitem"] button, .crm-g2-board .crm-g2-card').first();
  if (await card.count()) {
    await card.click();
    await page.waitForSelector('[data-testid="crm-g2-drawer"], .crm-g2-drawer, [role="dialog"]', { timeout: 15000 });
    results.drawer_ok = true;
    await page.waitForTimeout(400);
    await shot(page, 'pipeline-drawer-1440');
  } else {
    results.errors.push('No pipeline card found to open drawer');
    await shot(page, 'pipeline-drawer-1440-MISSING');
  }

  // Contacts / companies / dashboard
  await visit(page, '/workspaces/crm/contacts', 'contacts');
  await page.waitForTimeout(600);
  await shot(page, 'contacts-1440');

  await visit(page, '/workspaces/crm/companies', 'companies');
  await page.waitForTimeout(600);
  await shot(page, 'companies-1440');

  await visit(page, '/workspaces/crm/dashboard', 'dashboard');
  await page.waitForTimeout(600);
  await shot(page, 'dashboard-1440');

  const pass = results.login_ok && results.drawer_ok && results.screenshots.length >= 7;
  fs.writeFileSync(path.join(OUT, 'qa-result.json'), JSON.stringify({ pass, ...results }, null, 2));
  console.log(JSON.stringify({ pass, login_ok: results.login_ok, drawer_ok: results.drawer_ok, count: results.screenshots.length, errors: results.errors, routes: results.routes }, null, 2));
  if (!pass) process.exit(1);
} catch (err) {
  results.errors.push(String(err));
  fs.writeFileSync(path.join(OUT, 'qa-result.json'), JSON.stringify({ pass: false, ...results }, null, 2));
  console.error(err);
  process.exit(1);
} finally {
  await browser.close();
}
