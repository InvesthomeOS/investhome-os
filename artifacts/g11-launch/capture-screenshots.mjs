/**
 * G11 launch screenshots against localhost (NOT production).
 * Requires: local web+api up; demo user credentials via env DEMO_EMAIL / DEMO_PASSWORD.
 * Masks nothing in files — avoid capturing PII-heavy pages; use demo data only.
 *
 * Usage: node artifacts/g11-launch/capture-screenshots.mjs
 */
import { mkdir, writeFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(__dirname);
const BASE = process.env.G11_BASE_URL || 'http://localhost:3000';
const API = process.env.G11_API_URL || 'http://localhost:8000';
const EMAIL = process.env.DEMO_EMAIL || 'superadmin@investhome.demo';
const PASSWORD = process.env.DEMO_PASSWORD || 'Demo123!';

async function ensurePlaywright() {
  try {
    return await import('playwright');
  } catch {
    console.error('playwright not installed in this context; trying puppeteer-core/chrome CDP skip');
    return null;
  }
}

async function loginAndCapture(chromium) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    locale: 'tr-TR',
  });
  const page = await context.newPage();

  const shots = [];

  async function shot(name, url, opts = {}) {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    if (opts.waitMs) await page.waitForTimeout(opts.waitMs);
    const file = path.join(OUT, name);
    await page.screenshot({ path: file, fullPage: !!opts.fullPage });
    const s = await stat(file);
    shots.push({ name, bytes: s.size, url });
    console.log(`OK ${name} ${s.size} bytes`);
  }

  // 01 login
  await shot('01-login.png', `${BASE}/login`);

  // authenticate via API cookie if UI login is heavy
  const loginRes = await page.request.post(`${API}/auth/login`, {
    data: { email: EMAIL, password: PASSWORD },
  });
  if (!loginRes.ok()) {
    console.error('Login failed', loginRes.status(), await loginRes.text());
    await browser.close();
    process.exit(2);
  }

  await shot('02-home-dashboard.png', `${BASE}/dashboard`);
  await page.goto(`${BASE}/dashboard/admin/launch-health`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('[data-probe="env"]', { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2000);
  {
    const file = path.join(OUT, '03-admin-launch-health.png');
    await page.screenshot({ path: file, fullPage: false });
    const s = await stat(file);
    shots.push({ name: '03-admin-launch-health.png', bytes: s.size, url: `${BASE}/dashboard/admin/launch-health` });
    console.log(`OK 03-admin-launch-health.png ${s.size} bytes`);
  }
  await shot('04-admin-system.png', `${BASE}/dashboard/admin/system`, { waitMs: 1000 });
  await shot('05-executive.png', `${BASE}/dashboard/executive`, { waitMs: 1500 });
  await shot('06-crm.png', `${BASE}/workspaces/crm`, { waitMs: 1000 });
  await shot('07-projects.png', `${BASE}/dashboard/projects`, { waitMs: 1000 });
  await shot('08-investors.png', `${BASE}/dashboard/investors`, { waitMs: 1000 });
  await shot('09-finance.png', `${BASE}/dashboard/finance`, { waitMs: 1000 });
  await shot('10-documents.png', `${BASE}/dashboard/documents`, { waitMs: 1000 });
  await shot('11-marketing.png', `${BASE}/workspaces/marketing`, { waitMs: 1000 });
  await shot('12-automation.png', `${BASE}/dashboard/automation`, { waitMs: 1000 });
  await shot('13-security.png', `${BASE}/dashboard/admin/security`, { waitMs: 1000 });
  await shot('14-settings.png', `${BASE}/dashboard/settings`, { waitMs: 1000 });

  // mobile / tablet viewports
  await page.setViewportSize({ width: 390, height: 844 });
  await shot('15-mobile-home.png', `${BASE}/dashboard`);
  await page.setViewportSize({ width: 768, height: 1024 });
  await shot('16-tablet-launch-health.png', `${BASE}/dashboard/admin/launch-health`, { waitMs: 1000 });

  await writeFile(
    path.join(OUT, 'screenshot-manifest.json'),
    JSON.stringify(
      {
        env: 'localhost-docker-compose',
        notProduction: true,
        base: BASE,
        capturedAt: new Date().toISOString(),
        shots,
      },
      null,
      2,
    ),
  );

  await browser.close();
}

await mkdir(OUT, { recursive: true });
const pw = await ensurePlaywright();
if (!pw) {
  await writeFile(
    path.join(OUT, 'screenshot-manifest.json'),
    JSON.stringify({
      env: 'localhost-docker-compose',
      notProduction: true,
      error: 'playwright unavailable',
      capturedAt: new Date().toISOString(),
    }),
    'utf8',
  );
  process.exit(1);
}
await loginAndCapture(pw.chromium);
