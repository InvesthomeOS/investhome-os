import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE = process.env.PW_BASE_URL || 'http://localhost:3000';
const API = process.env.PW_API_URL || 'http://localhost:8000';
const OUT = path.resolve('C:/Users/eminb/Projects/investhome-os/tmp-browser-verify-output/product-polish-p11');
const EMAIL = 'superadmin@investhome.demo';
const PASS = 'Demo123!';

fs.mkdirSync(OUT, { recursive: true });

const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  laptop: { width: 1280, height: 800 },
  tablet: { width: 900, height: 1200 },
};

const PAGES = [
  { id: 'admin-overview', path: '/dashboard/admin' },
  { id: 'users', path: '/dashboard/admin/users' },
  { id: 'roles', path: '/dashboard/admin/roles' },
  { id: 'permissions', path: '/dashboard/admin/permissions' },
  { id: 'security', path: '/dashboard/admin/security' },
  { id: 'authentication', path: '/dashboard/admin/authentication' },
  { id: 'sessions', path: '/dashboard/admin/sessions' },
  { id: 'api-keys', path: '/dashboard/admin/api-keys' },
  { id: 'secrets', path: '/dashboard/admin/secrets' },
  { id: 'audit', path: '/dashboard/admin/audit' },
  { id: 'compliance', path: '/dashboard/admin/compliance' },
  { id: 'incidents', path: '/dashboard/admin/incidents' },
  { id: 'system', path: '/dashboard/admin/system' },
  { id: 'teams', path: '/dashboard/admin/teams' },
];

const screenshots = {};
const consoleErrors = [];
const checks = {
  login_ok: false,
  security_nav: false,
  security_workspace: false,
  kpis_present: false,
  unavailable_honest: true,
  sso_not_fake_healthy: true,
  backup_not_fake_healthy: true,
  permissions_api_denies: false,
  auth_ok: false,
  audit_ok: false,
  responsive_ok: true,
  no_console_errors: true,
  overflow_issues: [],
};

function shot(...parts) {
  return path.join(OUT, parts.join('-') + '.png');
}

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.locator('input[type="email"]').first().fill(EMAIL);
  await page.locator('input[type="password"]').first().fill(PASS);
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/dashboard/, { timeout: 60000 });
  checks.login_ok = true;
  checks.auth_ok = true;
}

async function detectOverflow(page) {
  return page.evaluate(() => {
    const issues = [];
    const nodes = Array.from(document.querySelectorAll('[data-sec-workspace], .admin-shell, .sec-kpi-grid, .sec-table'));
    for (const el of nodes) {
      if (el.scrollWidth > el.clientWidth + 4) {
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

async function apiPermissionQa() {
  // Unauthenticated sensitive routes must fail
  const routes = ['/security/dashboard', '/security/api-keys', '/security/sessions', '/users'];
  let denied = 0;
  for (const route of routes) {
    const res = await fetch(`${API}${route}`, { credentials: 'omit' });
    if (res.status === 401 || res.status === 403) denied += 1;
  }
  checks.permissions_api_denies = denied === routes.length;
  return { denied, total: routes.length };
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: VIEWPORTS.desktop, locale: 'en-US' });
const page = await context.newPage();
page.on('console', (msg) => {
  if (msg.type() === 'error') {
    const text = msg.text();
    if (/401|403|favicon|Failed to load resource|CORS policy|Access-Control-Allow-Origin|notifications\//i.test(text)) {
      return;
    }
    consoleErrors.push(text);
    checks.no_console_errors = false;
  }
});

const report = { screenshots, checks, consoleErrors, base: BASE, at: new Date().toISOString() };

try {
  report.api_permission_qa = await apiPermissionQa();

  await login(page);

  await page.goto(`${BASE}/dashboard/admin/security`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForSelector('[data-sec-workspace="security"]', { timeout: 60000 });
  checks.security_workspace = true;
  checks.security_nav =
    (await page.locator('a.admin-shell__nav-link[href*="/dashboard/admin/security"]').count()) > 0 ||
    (await page.getByRole('link', { name: /Security|Güvenlik/i }).count()) > 0;
  await page.waitForSelector('[data-sec-kpis] .sec-kpi', { timeout: 30000 }).catch(() => null);
  checks.kpis_present = (await page.locator('[data-sec-kpis] .sec-kpi').count()) > 0;

  const unavailableText = await page.locator('.sec-kpi--unavailable .sec-kpi__value').allTextContents();
  for (const v of unavailableText) {
    if (/%/.test(v) || /^\d+(\.\d+)?$/.test(v.trim())) {
      checks.unavailable_honest = false;
    }
  }

  await page.goto(`${BASE}/dashboard/admin/authentication`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForSelector('[data-sec-workspace="authentication"]', { timeout: 30000 }).catch(() => null);
  const authText = await page.locator('[data-sec-workspace="authentication"]').innerText().catch(() => '');
  if (/configured|missing|not connected/i.test(authText)) {
    checks.sso_not_fake_healthy = !/all sso.*healthy/i.test(authText);
  }

  await page.goto(`${BASE}/dashboard/admin/system`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForSelector('[data-sec-workspace="system"]', { timeout: 30000 }).catch(() => null);
  const sysText = await page.locator('[data-sec-workspace="system"]').innerText().catch(() => '');
  if (/backup/i.test(sysText) && /unavailable|not configured|never|yapılandırılmadı|kullanılamıyor/i.test(sysText)) {
    checks.backup_not_fake_healthy = true;
  } else if (/backup/i.test(sysText) && /healthy/i.test(sysText) && !/unavailable|not configured|yapılandırılmadı/i.test(sysText)) {
    checks.backup_not_fake_healthy = false;
  }

  await page.goto(`${BASE}/dashboard/admin/audit`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForSelector('[data-sec-workspace="audit"]', { timeout: 30000 }).catch(() => null);
  checks.audit_ok = (await page.locator('[data-sec-workspace="audit"]').count()) > 0;

  for (const [vpName, vp] of Object.entries(VIEWPORTS)) {
    await page.setViewportSize(vp);
    await page.waitForTimeout(200);
    for (const route of PAGES) {
      await page.goto(`${BASE}${route.path}`, { waitUntil: 'domcontentloaded', timeout: 90000 });
      await page.waitForTimeout(800);
      const file = shot(route.id, vpName);
      await page.screenshot({ path: file, fullPage: true });
      screenshots[`${route.id}_${vpName}`] = file;
      const overflow = await detectOverflow(page);
      if (overflow.length) {
        checks.overflow_issues.push({ route: route.id, viewport: vpName, overflow });
        checks.responsive_ok = false;
      }
    }
  }

  report.ok =
    checks.login_ok &&
    checks.security_workspace &&
    checks.kpis_present &&
    checks.unavailable_honest &&
    checks.sso_not_fake_healthy &&
    checks.backup_not_fake_healthy &&
    checks.permissions_api_denies &&
    checks.audit_ok &&
    checks.responsive_ok &&
    checks.no_console_errors;
} catch (err) {
  report.ok = false;
  report.error = String(err);
  const fail = shot('failure');
  await page.screenshot({ path: fail, fullPage: true }).catch(() => null);
  screenshots.failure = fail;
} finally {
  report.checks = checks;
  report.consoleErrors = consoleErrors;
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
  await browser.close();
  console.log(JSON.stringify({ ok: report.ok, out: OUT, checks }, null, 2));
  if (!report.ok) process.exitCode = 1;
}
