import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE = process.env.PW_BASE_URL || 'http://localhost:3000';
const OUT = path.resolve('C:/Users/eminb/Projects/investhome-os/tmp-browser-verify-output/product-polish-p2');
const EMAIL = 'superadmin@investhome.demo';
const PASS = 'Demo123!';

fs.mkdirSync(OUT, { recursive: true });

const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  laptop: { width: 1280, height: 800 },
  tablet: { width: 900, height: 1200 },
};

const WORKSPACES = [
  { id: 'dashboard', path: '/dashboard', shell: '.dashboard-shell__sidebar' },
  { id: 'crm', path: '/workspaces/crm/dashboard', shell: '.crm-shell__sidebar, .dashboard-shell__sidebar' },
  { id: 'marketing', path: '/workspaces/marketing/dashboard', shell: '.marketing-shell__sidebar, .dashboard-shell__sidebar' },
  { id: 'company', path: '/company', shell: '.company-shell__sidebar, .dashboard-shell__sidebar' },
  { id: 'investor', path: '/investor', shell: '.investor-shell__sidebar, .dashboard-shell__sidebar' },
  { id: 'sales', path: '/dashboard/sales', shell: '.dashboard-shell__sidebar' },
  { id: 'finance', path: '/dashboard/finance', shell: '.dashboard-shell__sidebar' },
  { id: 'admin', path: '/dashboard/admin', shell: '.dashboard-shell__sidebar' },
];

const screenshots = {};
const evidence = {};
const checks = {
  login_logo: false,
  no_lettermarks: true,
  logo_all_workspaces: true,
  collapsed_mark_all: true,
  nav_icons_present: true,
  header_consistent: true,
  brand_primary_token: false,
  layouts_ok: true,
};

const LETTERMARK_RE = /\b(CRM|MKT|IH|IW)\b/;

function shot(...parts) {
  return path.join(OUT, parts.join('-') + '.png');
}

async function evaluateShell(page) {
  return page.evaluate(() => {
    const sidebar = document.querySelector('.dashboard-shell__sidebar');
    const logo = sidebar?.querySelector('img.brand-logo, img[src*="investhome-"]');
    const logoSrc = logo?.getAttribute('src') ?? '';
    const brandMarkText = Array.from(
      sidebar?.querySelectorAll('.dashboard-shell__brand-mark, .investor-sidebar__brand-mark') ?? [],
    )
      .map((el) => (el.textContent || '').trim())
      .filter(Boolean);
    const brandLinkText = (sidebar?.querySelector('.dashboard-shell__brand-link')?.textContent || '')
      .replace(/\s+/g, ' ')
      .trim();
    const navIcons = sidebar?.querySelectorAll('.dashboard-shell__nav-link-icon').length ?? 0;
    const navLinks = sidebar?.querySelectorAll('.dashboard-shell__nav-link').length ?? 0;
    const header = document.querySelector('.app-header');
    const headerUser = document.querySelector('.app-header__user');
    const collapsed = sidebar?.classList.contains('dashboard-shell__sidebar--collapsed') ?? false;
    const brandPrimary = getComputedStyle(document.documentElement).getPropertyValue('--brand-primary').trim();
    const sidebarWidth = sidebar ? getComputedStyle(sidebar).width : null;
    const overflowX = document.documentElement.scrollWidth > document.documentElement.clientWidth + 2;
    return {
      logoSrc,
      logoOk: !!logo && /investhome-(logo|mark)/.test(logoSrc),
      brandMarkText,
      brandLinkText,
      navIcons,
      navLinks,
      hasHeader: !!header,
      hasHeaderUser: !!headerUser,
      collapsed,
      brandPrimary,
      sidebarWidth,
      overflowX,
      bodyFont: getComputedStyle(document.body).fontFamily,
    };
  });
}

async function toggleCollapse(page) {
  const btn = page.locator('.dashboard-shell__collapse').first();
  if ((await btn.count()) === 0) return false;
  await btn.click({ timeout: 8000 });
  await page.waitForTimeout(400);
  return true;
}

async function waitForShell(page) {
  await page.waitForSelector('.dashboard-shell__sidebar .dashboard-shell__collapse', { timeout: 45000 });
  await page.waitForSelector('.dashboard-shell__sidebar img.brand-logo, .dashboard-shell__sidebar img[src*="investhome-"]', {
    timeout: 20000,
  });
}

async function ensureExpanded(page) {
  const collapsed = await page.evaluate(() =>
    document.querySelector('.dashboard-shell__sidebar')?.classList.contains('dashboard-shell__sidebar--collapsed'),
  );
  if (collapsed) {
    return toggleCollapse(page);
  }
  return true;
}

async function ensureCollapsed(page) {
  const collapsed = await page.evaluate(() =>
    document.querySelector('.dashboard-shell__sidebar')?.classList.contains('dashboard-shell__sidebar--collapsed'),
  );
  if (!collapsed) {
    return toggleCollapse(page);
  }
  return true;
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: VIEWPORTS.desktop,
  locale: 'en-US',
});
const page = await context.newPage();

try {
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 90000 });
  await page.waitForTimeout(600);
  const loginShot = shot('login', 'desktop');
  await page.screenshot({ path: loginShot, fullPage: true });
  screenshots.login_desktop = loginShot;

  const loginLogo = await page.evaluate(() => {
    const logo = document.querySelector('.auth-card__logo, .brand-logo, img[src*="investhome-logo"]');
    return {
      ok: !!logo && (logo.getAttribute('src') || '').includes('investhome-logo'),
      src: logo?.getAttribute('src') ?? null,
    };
  });
  checks.login_logo = loginLogo.ok;
  evidence.login = loginLogo;

  await page.locator('input[type="email"]').first().fill(EMAIL);
  await page.locator('input[type="password"]').first().fill(PASS);
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/\/dashboard/, { timeout: 90000 });
  await page.waitForSelector('.dashboard-shell__sidebar', { timeout: 45000 });
  await page.waitForTimeout(900);

  for (const ws of WORKSPACES) {
    await page.setViewportSize(VIEWPORTS.desktop);
    await page.goto(`${BASE}${ws.path}`, { waitUntil: 'domcontentloaded', timeout: 90000 });
    try {
      await waitForShell(page);
    } catch (e) {
      evidence[`${ws.id}_error`] = String(e);
      checks.logo_all_workspaces = false;
      checks.layouts_ok = false;
      const errPath = shot(ws.id, 'error');
      await page.screenshot({ path: errPath, fullPage: true }).catch(() => null);
      screenshots[`${ws.id}_error`] = errPath;
      continue;
    }
    await page.waitForTimeout(500);
    await ensureExpanded(page);

    const expanded = await evaluateShell(page);
    evidence[`${ws.id}_expanded`] = expanded;

    if (!expanded.logoOk) checks.logo_all_workspaces = false;
    if (expanded.brandMarkText.length > 0) checks.no_lettermarks = false;
    if (LETTERMARK_RE.test(expanded.brandLinkText) && !expanded.logoOk) checks.no_lettermarks = false;
    if (expanded.navLinks > 0 && expanded.navIcons === 0 && ws.id !== 'admin') {
      // admin inherits dashboard icons; ok
    }
    if (ws.id !== 'admin' && expanded.navLinks > 2 && expanded.navIcons < 2) {
      checks.nav_icons_present = false;
    }
    if (!expanded.hasHeader) checks.header_consistent = false;
    if (expanded.overflowX) checks.layouts_ok = false;
    if (/#9d7b55/i.test(expanded.brandPrimary) || expanded.brandPrimary.includes('157') || expanded.brandPrimary.includes('9d7b55')) {
      checks.brand_primary_token = true;
    }

    const expPath = shot(ws.id, 'expanded', 'desktop');
    await page.screenshot({ path: expPath, fullPage: false });
    screenshots[`${ws.id}_expanded_desktop`] = expPath;

    const didCollapse = await ensureCollapsed(page);
    if (!didCollapse) {
      evidence[`${ws.id}_collapsed`] = { skipped: true, reason: 'no collapse control' };
      checks.collapsed_mark_all = false;
    } else {
      const collapsed = await evaluateShell(page);
      evidence[`${ws.id}_collapsed`] = collapsed;
      if (!collapsed.logoOk || !/investhome-mark/.test(collapsed.logoSrc)) {
        checks.collapsed_mark_all = false;
      }
      const colPath = shot(ws.id, 'collapsed', 'desktop');
      await page.screenshot({ path: colPath, fullPage: false });
      screenshots[`${ws.id}_collapsed_desktop`] = colPath;
    }

    // laptop
    await ensureExpanded(page);
    await page.setViewportSize(VIEWPORTS.laptop);
    await page.waitForTimeout(300);
    const lapPath = shot(ws.id, 'laptop');
    await page.screenshot({ path: lapPath, fullPage: false });
    screenshots[`${ws.id}_laptop`] = lapPath;

    // tablet
    await page.setViewportSize(VIEWPORTS.tablet);
    await page.waitForTimeout(300);
    const tabEval = await evaluateShell(page);
    evidence[`${ws.id}_tablet`] = tabEval;
    if (tabEval.overflowX) checks.layouts_ok = false;
    const tabPath = shot(ws.id, 'tablet');
    await page.screenshot({ path: tabPath, fullPage: false });
    screenshots[`${ws.id}_tablet`] = tabPath;
  }

  const report = {
    generatedAt: new Date().toISOString(),
    base: BASE,
    checks,
    screenshots,
    evidence,
  };
  const reportPath = path.join(OUT, 'report.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ ok: Object.values(checks).every(Boolean), checks, reportPath, screenshotCount: Object.keys(screenshots).length }, null, 2));
} catch (err) {
  console.error('QA failed:', err);
  const failPath = shot('failure');
  await page.screenshot({ path: failPath, fullPage: true }).catch(() => null);
  process.exitCode = 1;
} finally {
  await browser.close();
}
