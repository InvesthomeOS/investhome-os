import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE = process.env.PW_BASE_URL || 'http://localhost:3000';
const OUT = path.resolve('C:/Users/eminb/Projects/investhome-os/tmp-browser-verify-output/product-polish-p10');
const EMAIL = 'superadmin@investhome.demo';
const PASS = 'Demo123!';

fs.mkdirSync(OUT, { recursive: true });

const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  laptop: { width: 1280, height: 800 },
  tablet: { width: 900, height: 1200 },
};

const PAGES = [
  { id: 'overview', path: '/dashboard/knowledge' },
  { id: 'documents', path: '/dashboard/knowledge/documents' },
  { id: 'collections', path: '/dashboard/knowledge/collections' },
  { id: 'search', path: '/dashboard/knowledge/search' },
  { id: 'review', path: '/dashboard/knowledge/review' },
  { id: 'retention', path: '/dashboard/knowledge/retention' },
  { id: 'audit', path: '/dashboard/knowledge/audit' },
  { id: 'settings', path: '/dashboard/knowledge/settings' },
];

const screenshots = {};
const checks = {
  knowledge_nav_visible: false,
  knowledge_hub_present: false,
  overview_widgets: false,
  tabs_present: false,
  unavailable_providers_honest: true,
  overflow_issues: [],
  layouts_ok: true,
};

function shot(...parts) {
  return path.join(OUT, parts.join('-') + '.png');
}

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 90000 });
  await page.locator('input[type="email"]').first().fill(EMAIL);
  await page.locator('input[type="password"]').first().fill(PASS);
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/dashboard/, { timeout: 60000 });
}

async function detectOverflow(page) {
  return page.evaluate(() => {
    const issues = [];
    const nodes = Array.from(document.querySelectorAll('[data-knowledge-hub], .knowledge-hub__tabs, .knowledge-hub__list'));
    for (const el of nodes) {
      if (el.scrollWidth > el.clientWidth + 2) {
        issues.push({
          className: el.className,
          scrollWidth: el.scrollWidth,
          clientWidth: el.clientWidth,
        });
      }
    }
    return issues;
  });
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: VIEWPORTS.desktop, locale: 'en-US' });
const page = await context.newPage();
const report = { screenshots, checks, base: BASE, at: new Date().toISOString() };

try {
  await login(page);

  await page.goto(`${BASE}/dashboard/knowledge`, { waitUntil: 'networkidle', timeout: 90000 });
  await page.waitForSelector('[data-knowledge-hub]', { timeout: 45000 });

  checks.knowledge_hub_present = (await page.locator('[data-knowledge-hub]').count()) > 0;
  checks.knowledge_nav_visible =
    (await page.getByRole('link', { name: /Knowledge Hub|Bilgi Merkezi/i }).count()) > 0;
  checks.tabs_present = (await page.locator('.knowledge-hub__tabs').count()) > 0;
  checks.overview_widgets = (await page.locator('.documents-overview__card').count()) >= 3;

  const unavailable = await page.locator('.knowledge-hub__provider--unavailable').allTextContents();
  for (const text of unavailable) {
    if (/%\d/.test(text) && !/Unavailable|Kullanılamıyor|not configured|missing/i.test(text)) {
      checks.unavailable_providers_honest = false;
    }
  }

  for (const [vpName, vp] of Object.entries(VIEWPORTS)) {
    await page.setViewportSize(vp);
    await page.waitForTimeout(250);
    for (const route of PAGES) {
      await page.goto(`${BASE}${route.path}`, { waitUntil: 'networkidle', timeout: 90000 });
      await page.waitForSelector('[data-knowledge-hub]', { timeout: 45000 }).catch(() => null);
      await page.waitForTimeout(400);
      const file = shot(route.id, vpName);
      await page.screenshot({ path: file, fullPage: true });
      screenshots[`${route.id}_${vpName}`] = file;

      const overflow = await detectOverflow(page);
      if (overflow.length) {
        checks.overflow_issues.push({ route: route.id, viewport: vpName, overflow });
        checks.layouts_ok = false;
      }
    }
  }

  // TR smoke
  await page.goto(`${BASE}/dashboard/knowledge`, { waitUntil: 'networkidle', timeout: 90000 });
  const localeToggle = page.getByRole('button', { name: /TR|Türkçe|EN|English/i }).first();
  if ((await localeToggle.count()) > 0) {
    await localeToggle.click().catch(() => null);
    await page.waitForTimeout(500);
  }
  const trShot = shot('overview', 'tr');
  await page.screenshot({ path: trShot, fullPage: true });
  screenshots.overview_tr = trShot;

  report.ok =
    checks.knowledge_hub_present &&
    checks.tabs_present &&
    checks.overview_widgets &&
    checks.layouts_ok &&
    checks.unavailable_providers_honest;
} catch (err) {
  report.ok = false;
  report.error = String(err);
  const fail = shot('failure');
  await page.screenshot({ path: fail, fullPage: true }).catch(() => null);
  screenshots.failure = fail;
} finally {
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
  await browser.close();
  console.log(JSON.stringify({ ok: report.ok, out: OUT, checks }, null, 2));
  if (!report.ok) process.exitCode = 1;
}
