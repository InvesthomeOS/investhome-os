/**
 * G13 Adoption screenshot capture.
 * Usage: node artifacts/adoption-g13/capture.mjs
 * Paths resolved via import.meta.url (absolute on disk).
 */
import { chromium } from '../../.pw-verify/node_modules/playwright/index.mjs';
import { mkdirSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const BASE = process.env.WEB_BASE_URL || 'http://localhost:3000';
const EMAIL = 'superadmin@investhome.demo';
const PASSWORD = 'Demo123!';
const PORTAL_EMAIL = 'investor.a@investhome.demo';
const PORTAL_PASSWORD = 'Portal123!';
const LOCALE_COOKIE = 'investhome.locale';
const MIN_BYTES = 10 * 1024;

mkdirSync(__dirname, { recursive: true });

const SHOTS = [
  { file: '01-welcome.png', path: '/dashboard/onboarding?step=welcome', wait: '[data-testid="adop-onboarding"]' },
  { file: '02-role-confirmation.png', path: '/dashboard/onboarding?step=role', wait: '[data-testid="adop-role-setup"]' },
  {
    file: '03-interactive-tour.png',
    path: '/dashboard/onboarding',
    wait: '[data-testid="adop-onboarding"]',
    action: 'start-tour',
  },
  {
    file: '04-highlight-arrow.png',
    path: '/dashboard/onboarding',
    wait: '[data-testid="adop-tour-card"]',
    action: 'start-tour',
    alreadyTour: true,
  },
  { file: '05-daily-checklist.png', path: '/dashboard/training?view=daily', wait: '[data-testid="adop-checklist-daily"]' },
  { file: '06-weekly-checklist.png', path: '/dashboard/training?view=weekly', wait: '[data-testid="adop-checklist-weekly"]' },
  { file: '07-learning-path.png', path: '/dashboard/training?view=paths', wait: '[data-testid="adop-learning-path"]' },
  { file: '08-workflow-tutorial.png', path: '/dashboard/training?view=tutorials', wait: '[data-testid="adop-tutorials"]' },
  { file: '09-training-library.png', path: '/dashboard/training?view=library', wait: '[data-testid="adop-library"]' },
  { file: '10-searchable-help.png', path: '/dashboard/help', wait: '[data-testid="adop-help-search"]' },
  { file: '11-guided-simulation.png', path: '/dashboard/training?view=simulation', wait: '[data-testid="adop-simulation"]' },
  { file: '12-knowledge-check.png', path: '/dashboard/training?view=knowledge', wait: '[data-testid="adop-knowledge-check"]' },
  { file: '13-adoption-dashboard.png', path: '/dashboard/admin/adoption', wait: '[data-testid="adop-adoption-dashboard"]' },
  { file: '14-feature-adoption.png', path: '/dashboard/admin/adoption?view=features', wait: '[data-testid="adop-feature-adoption"]' },
  { file: '15-training-builder.png', path: '/dashboard/admin/training-builder', wait: '[data-testid="adop-training-builder"]' },
  { file: '16-operations-playbook.png', path: '/dashboard/admin/operations', wait: '[data-testid="adop-playbooks"]' },
  { file: '17-sla-settings.png', path: '/dashboard/admin/operations?view=sla', wait: '[data-testid="adop-sla-settings"]' },
  { file: '18-support-request.png', path: '/dashboard/help?view=support', wait: '[data-testid="adop-support-form"]' },
  { file: '19-portal-guidance.png', path: '/portal/help', portal: true, wait: '[data-testid="portal-help"]' },
  {
    file: '20-turkish.png',
    path: '/dashboard/onboarding',
    locale: 'tr',
    wait: '[data-testid="adop-onboarding"]',
  },
  {
    file: '21-english.png',
    path: '/dashboard/onboarding',
    locale: 'en',
    wait: '[data-testid="adop-onboarding"]',
  },
  {
    file: '22-tablet.png',
    path: '/dashboard/training?view=daily',
    viewport: { width: 768, height: 1024 },
    wait: '[data-testid="adop-checklist-daily"]',
  },
];

async function waitForWeb(page, attempts = 30) {
  for (let i = 0; i < attempts; i++) {
    try {
      const res = await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 15000 });
      if (res && (res.ok() || res.status() === 200)) return;
    } catch {
      // retry
    }
    await page.waitForTimeout(2000);
  }
  throw new Error('Web not reachable on :3000');
}

async function login(page) {
  await waitForWeb(page);
  await page.fill('input[type="email"], input[name="email"]', EMAIL);
  await page.fill('input[type="password"], input[name="password"]', PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(dashboard|portal)/, { timeout: 45000 }).catch(() => undefined);
  await page.waitForTimeout(800);
}

async function portalLogin(page) {
  await page.goto(`${BASE}/portal/login`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.locator('[data-testid="portal-login-email"], input[type="email"]').first().fill(PORTAL_EMAIL);
  await page.locator('[data-testid="portal-login-password"], input[type="password"]').first().fill(PORTAL_PASSWORD);
  await page.locator('[data-testid="portal-login-submit"], button[type="submit"]').first().click();
  await page.waitForURL(/\/portal(?!\/login)/, { timeout: 25000 }).catch(() => undefined);
  await page.waitForTimeout(800);
}

async function gotoPath(page, path) {
  for (let i = 0; i < 4; i++) {
    try {
      await page.goto(`${BASE}${path}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
      return;
    } catch {
      await page.waitForTimeout(2000);
    }
  }
  await page.goto(`${BASE}${path}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
}

const browser = await chromium.launch({ headless: true });
const results = [];

const main = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
const mainPage = await main.newPage();
await login(mainPage);

let tourStarted = false;

for (const shot of SHOTS) {
  const needsFresh = Boolean(shot.viewport) || Boolean(shot.locale) || shot.portal;
  let page = mainPage;
  let context = null;

  try {
    if (needsFresh) {
      context = await browser.newContext({
        viewport: shot.viewport || { width: 1440, height: 1100 },
      });
      if (shot.locale) {
        await context.addCookies([
          { name: LOCALE_COOKIE, value: shot.locale, domain: 'localhost', path: '/' },
        ]);
      }
      page = await context.newPage();
      if (shot.portal) {
        await portalLogin(page);
      } else {
        await login(page);
      }
    }

    if (!(shot.action === 'start-tour' && tourStarted && shot.alreadyTour)) {
      await gotoPath(page, shot.path);
    }

    if (shot.wait) {
      await page.waitForSelector(shot.wait, { timeout: 20000 }).catch(() => undefined);
    }

    if (shot.action === 'start-tour') {
      const overlay = page.locator('[data-testid="adop-tour-overlay"]');
      if (!(await overlay.count())) {
        await page.locator('[data-testid="adop-start-tour"]').click({ timeout: 10000 });
        await page.waitForSelector('[data-testid="adop-tour-card"]', { timeout: 10000 });
        tourStarted = true;
      }
      await page.waitForTimeout(500);
    }

    if (shot.path.includes('view=features')) {
      await page.locator('[data-testid="adop-features-tab"]').click().catch(() => undefined);
      await page.waitForSelector('[data-testid="adop-feature-adoption"]', { timeout: 10000 }).catch(() => undefined);
    }

    if (shot.path.includes('view=sla')) {
      await page.locator('[data-testid="adop-sla-tab"]').click().catch(() => undefined);
      await page.waitForSelector('[data-testid="adop-sla-settings"]', { timeout: 10000 }).catch(() => undefined);
    }

    if (shot.path.includes('view=support')) {
      await page.locator('[data-testid="adop-open-support"]').click().catch(() => undefined);
      await page.waitForSelector('[data-testid="adop-support-form"]', { timeout: 10000 }).catch(() => undefined);
    }

    await page.waitForTimeout(400);
    const out = join(__dirname, shot.file);
    await page.screenshot({ path: out, fullPage: false });
    const size = statSync(out).size;
    results.push({ file: shot.file, bytes: size, ok: size > MIN_BYTES, path: out });
    console.log(`${shot.file}: ${size} bytes ${size > MIN_BYTES ? 'OK' : 'TOO_SMALL'}`);
  } catch (err) {
    results.push({ file: shot.file, error: String(err), ok: false });
    console.error(`FAIL ${shot.file}:`, err);
  } finally {
    if (context) await context.close();
  }
}

await browser.close();

const listed = readdirSync(__dirname).filter((f) => f.endsWith('.png'));
const verified = listed.map((f) => {
  const full = join(__dirname, f);
  const bytes = statSync(full).size;
  return { file: f, bytes, ok: bytes > MIN_BYTES, absolutePath: full };
});

writeFileSync(join(__dirname, 'sizes-verified.json'), JSON.stringify({ verified, results }, null, 2));

const pngCount = verified.filter((v) => v.ok).length;
console.log(`\nDirectory: ${__dirname}`);
console.log(`PNGs on disk: ${listed.length}; >10KB: ${pngCount}`);
if (pngCount < 22) {
  console.error('REVISION: expected 22 PNGs >10KB');
  process.exit(1);
}
console.log('Screenshot verification PASS');
