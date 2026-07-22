/**
 * G10 Global QA — sample crawl of primary OS + portal routes.
 * Evidence written under artifacts/g10-readiness/
 */
import { chromium } from '../../.pw-verify/node_modules/playwright/index.mjs';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BASE = process.env.G10_BASE || 'http://localhost:3000';
const OUT = __dirname;
const SHOTS = path.join(OUT, 'screenshots');
const LOGS = path.join(OUT, 'logs');
fs.mkdirSync(SHOTS, { recursive: true });
fs.mkdirSync(LOGS, { recursive: true });

const STAFF = { email: 'superadmin@investhome.demo', password: 'Demo123!' };
const PORTAL = { email: 'investor.a@investhome.demo', password: 'Portal123!' };

const PRIMARY_ROUTES = [
  '/dashboard',
  '/dashboard/executive',
  '/dashboard/sales',
  '/dashboard/investors',
  '/dashboard/projects',
  '/dashboard/inventory',
  '/dashboard/finance',
  '/dashboard/marketing',
  '/workspaces/crm/dashboard',
  '/workspaces/crm/leads',
  '/workspaces/crm/pipeline',
  '/company',
  '/dashboard/analytics',
  '/dashboard/analytics/reports',
  '/dashboard/ai',
  '/dashboard/knowledge',
  '/dashboard/activity',
  '/dashboard/automation',
  '/dashboard/settings',
  '/dashboard/admin',
  '/dashboard/admin/users',
  '/dashboard/admin/security',
  '/dashboard/profile',
];

const PORTAL_ROUTES = [
  '/portal',
  '/portal/portfolio',
  '/portal/projects',
  '/portal/documents',
  '/portal/reports',
  '/portal/notifications',
  '/portal/account',
];

const ALIAS_ROUTES = [
  '/dashboard/crm',
  '/dashboard/crm/leads',
  '/dashboard/leads',
];

const report = {
  timestamp: new Date().toISOString(),
  base: BASE,
  staffLogin: { ok: false, error: null },
  portalLogin: { ok: false, error: null },
  routes: [],
  aliases: [],
  portalRoutes: [],
  consoleErrors: [],
  pageErrors: [],
  summary: {},
};

function slug(p) {
  return p.replace(/^\//, '').replace(/[/?=&]/g, '_') || 'root';
}

async function loginStaff(page) {
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.fill('input[type="email"], input[name="email"]', STAFF.email);
  await page.fill('input[type="password"]', STAFF.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/dashboard/, { timeout: 30000 });
  await page.waitForSelector('.dashboard-shell, [data-testid="dashboard-shell"], main', {
    timeout: 20000,
  }).catch(() => {});
}

async function loginPortal(page) {
  await page.goto(`${BASE}/portal/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.fill('[data-testid="portal-login-email"], input[type="email"]', PORTAL.email);
  await page.fill('[data-testid="portal-login-password"], input[type="password"]', PORTAL.password);
  await page.click('[data-testid="portal-login-submit"], button[type="submit"]');
  await page.waitForURL(/\/portal(?!\/login)/, { timeout: 30000 });
}

async function probe(page, route, bucket) {
  const entry = {
    route,
    ok: false,
    status: null,
    finalUrl: null,
    title: null,
    h1: null,
    redirectedToLogin: false,
    errorBoundary: false,
    consoleErrors: [],
    screenshot: null,
    ms: 0,
  };
  const errors = [];
  const onConsole = (msg) => {
    if (msg.type() === 'error') errors.push(msg.text());
  };
  const onPageError = (err) => {
    errors.push(String(err));
    report.pageErrors.push({ route, error: String(err) });
  };
  page.on('console', onConsole);
  page.on('pageerror', onPageError);
  const t0 = Date.now();
  try {
    const res = await page.goto(`${BASE}${route}`, {
      waitUntil: 'domcontentloaded',
      timeout: 45000,
    });
    entry.status = res?.status() ?? null;
    await page.waitForTimeout(1200);
    entry.finalUrl = page.url();
    entry.redirectedToLogin =
      /\/login/.test(entry.finalUrl) && !entry.finalUrl.includes('/portal/login');
    const state = await page.evaluate(() => ({
      title: document.title,
      h1: document.querySelector('h1')?.textContent?.trim() || null,
      bodySnippet: (document.body?.innerText || '').slice(0, 400),
      hasErrorText: /something went wrong|application error|internal server error/i.test(
        document.body?.innerText || '',
      ),
    }));
    entry.title = state.title;
    entry.h1 = state.h1;
    entry.errorBoundary = state.hasErrorText;
    entry.ok =
      entry.status !== null &&
      entry.status < 400 &&
      !entry.redirectedToLogin &&
      !entry.errorBoundary;
    const shotPath = path.join(SHOTS, `${slug(route)}.png`);
    await page.screenshot({ path: shotPath, fullPage: false });
    entry.screenshot = path.relative(OUT, shotPath).replace(/\\/g, '/');
  } catch (e) {
    entry.error = String(e);
    entry.ok = false;
  } finally {
    entry.ms = Date.now() - t0;
    entry.consoleErrors = errors.slice(0, 10);
    for (const e of errors) {
      report.consoleErrors.push({ route, message: e });
    }
    page.off('console', onConsole);
    page.off('pageerror', onPageError);
    bucket.push(entry);
  }
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true,
  });
  const page = await context.newPage();

  try {
    await loginStaff(page);
    report.staffLogin.ok = true;
    await page.screenshot({ path: path.join(SHOTS, 'staff-dashboard.png') });
  } catch (e) {
    report.staffLogin.error = String(e);
  }

  if (report.staffLogin.ok) {
    for (const route of PRIMARY_ROUTES) {
      await probe(page, route, report.routes);
    }
    for (const route of ALIAS_ROUTES) {
      await probe(page, route, report.aliases);
    }
  }

  // Fresh context for portal
  await context.clearCookies();
  try {
    await loginPortal(page);
    report.portalLogin.ok = true;
    await page.screenshot({ path: path.join(SHOTS, 'portal-home.png') });
  } catch (e) {
    report.portalLogin.error = String(e);
  }
  if (report.portalLogin.ok) {
    for (const route of PORTAL_ROUTES) {
      await probe(page, route, report.portalRoutes);
    }
  }

  const all = [...report.routes, ...report.aliases, ...report.portalRoutes];
  report.summary = {
    totalProbed: all.length,
    ok: all.filter((r) => r.ok).length,
    failed: all.filter((r) => !r.ok).length,
    failedRoutes: all.filter((r) => !r.ok).map((r) => r.route),
    avgMs: all.length ? Math.round(all.reduce((s, r) => s + r.ms, 0) / all.length) : 0,
    consoleErrorCount: report.consoleErrors.length,
    pageErrorCount: report.pageErrors.length,
  };

  fs.writeFileSync(path.join(LOGS, 'route-crawl.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report.summary, null, 2));
  await browser.close();
  process.exit(report.summary.failed > 0 || !report.staffLogin.ok ? 1 : 0);
}

main().catch((e) => {
  console.error(e);
  process.exit(2);
});
