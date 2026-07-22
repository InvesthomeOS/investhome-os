import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE = process.env.PW_BASE_URL || 'http://localhost:3000';
const OUT = path.resolve('C:/Users/eminb/Projects/investhome-os/tmp-browser-verify-output/product-polish-p9');
const EMAIL = 'superadmin@investhome.demo';
const PASS = 'Demo123!';

fs.mkdirSync(OUT, { recursive: true });

const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  laptop: { width: 1280, height: 800 },
  tablet: { width: 900, height: 1200 },
};

const PAGES = [
  { id: 'executive', path: '/dashboard/analytics?preset=30d' },
  { id: 'sales', path: '/dashboard/analytics/sales?preset=30d' },
  { id: 'marketing', path: '/dashboard/analytics/marketing?preset=30d' },
  { id: 'investor', path: '/dashboard/analytics/investor?preset=30d' },
  { id: 'finance', path: '/dashboard/analytics/finance?preset=30d' },
  { id: 'project', path: '/dashboard/analytics/project?preset=30d' },
  { id: 'website', path: '/dashboard/analytics/website?preset=30d' },
  { id: 'operational', path: '/dashboard/analytics/operational?preset=30d' },
  { id: 'reports', path: '/dashboard/analytics/reports' },
  { id: 'builder', path: '/dashboard/analytics/reports/builder' },
  { id: 'data-quality', path: '/dashboard/analytics/data-quality' },
];

const screenshots = {};
const checks = {
  bi_nav_visible: false,
  bi_workspace_present: false,
  filter_bar_present: false,
  metric_cards_present: false,
  unavailable_not_fake_pct: true,
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
    const nodes = Array.from(document.querySelectorAll('.bi-workspace, .bi-section__charts, .bi-chart__labels, .inv-portfolio-donut__legend'));
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

async function assertNoFakePercents(page) {
  const text = await page.locator('[data-bi-workspace]').innerText().catch(() => '');
  // Fake decorative percentages often look like "—" replaced with invented numbers; flag bare % without Unavailable context on unavailable cards
  const unavailableCards = await page.locator('.bi-metric--unavailable .bi-metric__value').allTextContents();
  for (const v of unavailableCards) {
    if (/%/.test(v) && !/Unavailable|Kullanılamıyor|—/.test(v)) {
      return false;
    }
  }
  return !/%\s*change\s*N\/A/i.test(text);
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: VIEWPORTS.desktop, locale: 'en-US' });
const page = await context.newPage();
const report = { screenshots, checks, base: BASE, at: new Date().toISOString() };

try {
  await login(page);

  await page.goto(`${BASE}/dashboard/analytics?preset=30d`, { waitUntil: 'networkidle', timeout: 90000 });
  await page.waitForSelector('[data-bi-workspace]', { timeout: 45000 });

  checks.bi_workspace_present = (await page.locator('[data-bi-workspace]').count()) > 0;
  checks.filter_bar_present = (await page.locator('.bi-filters').count()) > 0;
  checks.metric_cards_present = (await page.locator('.bi-metric').count()) > 0;
  checks.bi_nav_visible =
    (await page.getByRole('link', { name: /Business Intelligence|İş Zekâsı/i }).count()) > 0;

  for (const [vpName, vp] of Object.entries(VIEWPORTS)) {
    await page.setViewportSize(vp);
    await page.waitForTimeout(250);
    for (const route of PAGES) {
      await page.goto(`${BASE}${route.path}`, { waitUntil: 'networkidle', timeout: 90000 });
      await page.waitForSelector('[data-bi-workspace]', { timeout: 45000 }).catch(() => null);
      await page.waitForTimeout(400);
      const file = shot(route.id, vpName);
      await page.screenshot({ path: file, fullPage: true });
      screenshots[`${route.id}_${vpName}`] = file;

      const overflow = await detectOverflow(page);
      if (overflow.length) {
        checks.overflow_issues.push({ route: route.id, viewport: vpName, overflow });
        checks.layouts_ok = false;
      }
      const okPct = await assertNoFakePercents(page);
      if (!okPct) checks.unavailable_not_fake_pct = false;
    }
  }

  report.ok = checks.bi_workspace_present && checks.filter_bar_present && checks.layouts_ok && checks.unavailable_not_fake_pct;
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
