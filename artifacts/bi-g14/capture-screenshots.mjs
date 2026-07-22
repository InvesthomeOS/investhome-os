/**
 * G14 screenshot capture — writes PNGs under artifacts/bi-g14/ via import.meta.url.
 * Demo: superadmin@investhome.demo / Demo123!
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = __dirname;
const BASE = process.env.BI_G14_BASE_URL || 'http://localhost:3000';
const API = process.env.BI_G14_API_URL || 'http://localhost:8000';
const EMAIL = process.env.BI_G14_EMAIL || 'superadmin@investhome.demo';
const PASSWORD = process.env.BI_G14_PASSWORD || 'Demo123!';

const SHOTS = [
  ['01-analytics-overview.png', '/dashboard/analytics'],
  ['02-analytics-executive.png', '/dashboard/analytics/executive'],
  ['03-analytics-sales.png', '/dashboard/analytics/sales'],
  ['04-analytics-investors.png', '/dashboard/analytics/investors'],
  ['05-analytics-projects.png', '/dashboard/analytics/projects'],
  ['06-analytics-finance.png', '/dashboard/analytics/finance'],
  ['07-analytics-marketing.png', '/dashboard/analytics/marketing'],
  ['08-analytics-portfolio.png', '/dashboard/analytics/portfolio'],
  ['09-analytics-reports.png', '/dashboard/analytics/reports'],
  ['10-analytics-explorer.png', '/dashboard/analytics/explorer'],
  ['11-admin-data-platform.png', '/dashboard/admin/data-platform'],
  ['12-admin-data-quality.png', '/dashboard/admin/data-quality'],
  ['13-admin-metric-catalog.png', '/dashboard/admin/metric-catalog'],
  ['14-admin-data-lineage.png', '/dashboard/admin/data-lineage'],
  ['15-report-builder.png', '/dashboard/analytics/reports/builder'],
  ['16-analytics-tr.png', '/dashboard/analytics?locale=tr'],
  ['17-analytics-en.png', '/dashboard/analytics?locale=en'],
  ['18-analytics-tablet.png', '/dashboard/analytics', { width: 834, height: 1112 }],
  ['19-metric-catalog-certified.png', '/dashboard/admin/metric-catalog'],
  ['20-ingestion-runs.png', '/dashboard/admin/data-platform'],
  ['21-reconciliation.png', '/dashboard/admin/data-platform'],
  ['22-lineage-detail.png', '/dashboard/admin/data-lineage'],
  ['23-failed-ingestion-state.png', '/dashboard/admin/data-platform'],
];

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  const email = page.locator('input[type="email"], input[name="email"]').first();
  const password = page.locator('input[type="password"]').first();
  if (await email.count()) {
    await email.fill(EMAIL);
    await password.fill(PASSWORD);
    await page.locator('button[type="submit"]').first().click();
    await page.waitForURL(/dashboard/, { timeout: 30000 }).catch(() => {});
  }
}

async function triggerIngestion(page) {
  try {
    const cookies = await page.context().cookies();
    const cookieHeader = cookies.map((c) => `${c.name}=${c.value}`).join('; ');
    await page.request.post(`${API}/analytics/warehouse/ingestion-runs`, {
      data: { mode: 'full_refresh' },
      headers: { Cookie: cookieHeader, 'Content-Type': 'application/json' },
    });
  } catch (e) {
    console.warn('ingestion trigger skipped', e.message);
  }
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await login(page);
  await triggerIngestion(page);

  const sizes = {};
  for (const [file, route, vp] of SHOTS) {
    if (vp) await page.setViewportSize(vp);
    else await page.setViewportSize({ width: 1440, height: 900 });
    const url = route.startsWith('http') ? route : `${BASE}${route}`;
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
    await page.waitForTimeout(1200);
    const dest = path.join(OUT, file);
    await page.screenshot({ path: dest, fullPage: true });
    const st = fs.statSync(dest);
    sizes[file] = st.size;
    console.log(file, st.size);
    if (st.size < 10_000) console.warn('WARN small screenshot', file, st.size);
  }

  fs.writeFileSync(path.join(OUT, 'screenshot-sizes.json'), JSON.stringify(sizes, null, 2));
  const listing = fs
    .readdirSync(OUT)
    .filter((f) => f.endsWith('.png'))
    .map((f) => {
      const st = fs.statSync(path.join(OUT, f));
      return `${f}\t${st.size}`;
    })
    .join('\n');
  fs.writeFileSync(path.join(OUT, 'screenshot-dir-listing.txt'), listing + '\n');
  await browser.close();
  console.log('done', OUT);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
