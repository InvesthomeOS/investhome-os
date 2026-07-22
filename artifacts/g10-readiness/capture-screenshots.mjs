/**
 * G10 evidence screenshot capture — writes PNGs under screenshots/ using absolute paths.
 */
import { chromium } from '../../.pw-verify/node_modules/playwright/index.mjs';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const OUT_DIR = path.join(__dirname, 'screenshots');
const BASE = process.env.G10_BASE || 'http://localhost:3000';

fs.mkdirSync(OUT_DIR, { recursive: true });

const STAFF_ROUTES = [
  ['login', '/login', { authed: false }],
  ['staff-dashboard', '/dashboard', { authed: true }],
  ['dashboard', '/dashboard', { authed: true }],
  ['dashboard_executive', '/dashboard/executive', { authed: true }],
  ['dashboard_sales', '/dashboard/sales', { authed: true }],
  ['dashboard_investors', '/dashboard/investors', { authed: true }],
  ['dashboard_projects', '/dashboard/projects', { authed: true }],
  ['dashboard_inventory', '/dashboard/inventory', { authed: true }],
  ['dashboard_finance', '/dashboard/finance', { authed: true }],
  ['dashboard_marketing', '/dashboard/marketing', { authed: true }],
  ['workspaces_crm_dashboard', '/workspaces/crm/dashboard', { authed: true }],
  ['workspaces_crm_leads', '/workspaces/crm/leads', { authed: true }],
  ['workspaces_crm_pipeline', '/workspaces/crm/pipeline', { authed: true }],
  ['company', '/company', { authed: true }],
  ['dashboard_analytics', '/dashboard/analytics', { authed: true }],
  ['dashboard_analytics_reports', '/dashboard/analytics/reports', { authed: true }],
  ['dashboard_ai', '/dashboard/ai', { authed: true }],
  ['dashboard_knowledge', '/dashboard/knowledge', { authed: true }],
  ['dashboard_activity', '/dashboard/activity', { authed: true }],
  ['dashboard_automation', '/dashboard/automation', { authed: true }],
  ['dashboard_settings', '/dashboard/settings', { authed: true }],
  ['dashboard_admin', '/dashboard/admin', { authed: true }],
  ['dashboard_admin_users', '/dashboard/admin/users', { authed: true }],
  ['dashboard_admin_security', '/dashboard/admin/security', { authed: true }],
  ['dashboard_profile', '/dashboard/profile', { authed: true }],
];

const PORTAL_ROUTES = [
  ['portal-login', '/portal/login'],
  ['portal-home', '/portal'],
  ['portal', '/portal'],
  ['portal_portfolio', '/portal/portfolio'],
  ['portal_projects', '/portal/projects'],
  ['portal_documents', '/portal/documents'],
  ['portal_reports', '/portal/reports'],
  ['portal_notifications', '/portal/notifications'],
  ['portal_account', '/portal/account'],
];

async function shot(page, name) {
  const filePath = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: false, type: 'png' });
  const st = fs.statSync(filePath);
  if (st.size < 10_240) {
    throw new Error(`Screenshot too small: ${filePath} (${st.size} bytes)`);
  }
  return { name: `${name}.png`, path: filePath, bytes: st.size };
}

async function loginStaff(page) {
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.fill('input[type="email"], input[name="email"]', 'superadmin@investhome.demo');
  await page.fill('input[type="password"]', 'Demo123!');
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/dashboard/, { timeout: 30000 });
  await page.waitForTimeout(1200);
}

async function loginPortal(page) {
  await page.goto(`${BASE}/portal/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.fill('[data-testid="portal-login-email"], input[type="email"]', 'investor.a@investhome.demo');
  await page.fill(
    '[data-testid="portal-login-password"], input[type="password"]',
    'Portal123!',
  );
  await page.click('[data-testid="portal-login-submit"], button[type="submit"]');
  await page.waitForURL(/\/portal(?!\/login)/, { timeout: 30000 });
  await page.waitForTimeout(1200);
}

async function captureRoute(page, name, route) {
  await page.goto(`${BASE}${route}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(1400);
  return shot(page, name);
}

async function main() {
  const manifest = {
    timestamp: new Date().toISOString(),
    base: BASE,
    outDir: OUT_DIR,
    files: [],
    errors: [],
  };

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();

  try {
    // Login page (pre-auth)
    manifest.files.push(await captureRoute(page, 'login', '/login'));

    await loginStaff(page);
    for (const [name, route, meta] of STAFF_ROUTES) {
      if (!meta.authed) continue;
      try {
        manifest.files.push(await captureRoute(page, name, route));
      } catch (e) {
        manifest.errors.push({ name, route, error: String(e) });
      }
    }

    await context.clearCookies();
    try {
      manifest.files.push(await captureRoute(page, 'portal-login', '/portal/login'));
      await loginPortal(page);
      for (const [name, route] of PORTAL_ROUTES) {
        if (name === 'portal-login') continue;
        try {
          manifest.files.push(await captureRoute(page, name, route));
        } catch (e) {
          manifest.errors.push({ name, route, error: String(e) });
        }
      }
    } catch (e) {
      manifest.errors.push({ name: 'portal', error: String(e) });
    }
  } finally {
    await browser.close();
  }

  // Deduplicate by name (keep last)
  const byName = new Map();
  for (const f of manifest.files) byName.set(f.name, f);
  manifest.files = [...byName.values()].sort((a, b) => a.name.localeCompare(b.name));
  manifest.count = manifest.files.length;
  manifest.totalBytes = manifest.files.reduce((s, f) => s + f.bytes, 0);
  manifest.minBytes = Math.min(...manifest.files.map((f) => f.bytes));
  manifest.allAbove10kb = manifest.files.every((f) => f.bytes > 10240);

  const manifestPath = path.join(__dirname, 'logs', 'screenshot-manifest.json');
  fs.mkdirSync(path.dirname(manifestPath), { recursive: true });
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));

  console.log(
    JSON.stringify(
      {
        outDir: OUT_DIR,
        count: manifest.count,
        allAbove10kb: manifest.allAbove10kb,
        minBytes: manifest.minBytes,
        errors: manifest.errors.length,
        files: manifest.files.map((f) => `${f.name} ${f.bytes}`),
      },
      null,
      2,
    ),
  );

  if (manifest.count < 15 || !manifest.allAbove10kb || manifest.errors.length) {
    process.exit(1);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(2);
});
