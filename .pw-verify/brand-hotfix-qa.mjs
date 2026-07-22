import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE = 'http://localhost:3000';
const OUT = path.resolve('C:/Users/eminb/Projects/investhome-os/tmp-browser-verify-output/brand-hotfix');
const EMAIL = 'superadmin@investhome.demo';
const PASS = 'Demo123!';

fs.mkdirSync(OUT, { recursive: true });

const screenshots = {};
const evidence = {};
const checks = {
  logo_visible_login: false,
  logo_visible_sidebar: false,
  favicon_present: false,
  font_helvetica: false,
  brand_primary_token: false,
  light_theme_ok: false,
  dark_theme_ok: false,
  collapsed_sidebar_ok: false,
  collapsed_mark_src_ok: false,
};

function shot(name) {
  return path.join(OUT, name);
}

function hexToRgb(hex) {
  const h = hex.replace('#', '');
  return {
    r: parseInt(h.slice(0, 2), 16),
    g: parseInt(h.slice(2, 4), 16),
    b: parseInt(h.slice(4, 6), 16),
  };
}

function parseRgbString(s) {
  const m = s.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (!m) return null;
  return { r: +m[1], g: +m[2], b: +m[3] };
}

function rgbClose(a, b, tol = 8) {
  if (!a || !b) return false;
  return Math.abs(a.r - b.r) <= tol && Math.abs(a.g - b.g) <= tol && Math.abs(a.b - b.b) <= tol;
}

async function evaluateLoginBrand(page) {
  return page.evaluate(() => {
    const logo = document.querySelector('.auth-card__logo, .brand-logo, img[src*="investhome-logo"]');
    const logoSrc = logo?.getAttribute('src') ?? '';
    const logoVisible =
      !!logo &&
      logoSrc.includes('investhome-logo') &&
      (logo instanceof HTMLElement ? logo.offsetWidth > 0 && logo.offsetHeight > 0 : true);
    const favicon =
      document.querySelector('link[rel="icon"]') ||
      document.querySelector('link[rel="shortcut icon"]') ||
      document.querySelector('link[href*="favicon"]');
    const bodyFont = getComputedStyle(document.body).fontFamily;
    const root = document.documentElement;
    const brandPrimary = getComputedStyle(root).getPropertyValue('--brand-primary').trim();
    const dataTheme = root.getAttribute('data-theme');
    return {
      logoVisible,
      logoSrc,
      faviconPresent: !!favicon,
      faviconHref: favicon?.getAttribute('href') ?? null,
      bodyFont,
      brandPrimary,
      dataTheme,
    };
  });
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  locale: 'en-US',
});
const page = await context.newPage();

try {
  // Light login
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(800);
  const loginLightPath = shot('login-light.png');
  await page.screenshot({ path: loginLightPath, fullPage: true });
  screenshots.login_light = loginLightPath;

  let loginEval = await evaluateLoginBrand(page);
  evidence.login_light = loginEval;
  checks.logo_visible_login = loginEval.logoVisible;
  checks.favicon_present = loginEval.faviconPresent;
  checks.font_helvetica = /helvetica/i.test(loginEval.bodyFont);
  const targetRgb = hexToRgb('#9d7b55');
  let brandRgb = parseRgbString(loginEval.brandPrimary);
  if (!brandRgb && loginEval.brandPrimary.startsWith('#')) {
    brandRgb = hexToRgb(loginEval.brandPrimary);
  }
  checks.brand_primary_token = rgbClose(brandRgb, targetRgb);
  evidence.brand_primary = { raw: loginEval.brandPrimary, parsed: brandRgb, target: targetRgb };
  checks.light_theme_ok =
    loginEval.dataTheme === 'light' || loginEval.dataTheme === null || loginEval.dataTheme === '';

  // Login
  await page.locator('input[type="email"]').first().fill(EMAIL);
  await page.locator('input[type="password"]').first().fill(PASS);
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/\/dashboard/, { timeout: 60000 });
  await page.waitForSelector('.dashboard-shell__sidebar', { timeout: 30000 });
  await page.waitForSelector('.app-header', { timeout: 30000 });
  await page.waitForTimeout(1200);

  const dashLightPath = shot('dashboard-light.png');
  await page.screenshot({ path: dashLightPath, fullPage: false });
  screenshots.dashboard_light = dashLightPath;

  const sidebarEval = await page.evaluate(() => {
    const img = document.querySelector('.dashboard-shell__brand img, .dashboard-shell__brand-logo');
    const src = img?.getAttribute('src') ?? '';
    const visible =
      !!img &&
      src.includes('investhome-logo') &&
      (img instanceof HTMLElement ? img.offsetWidth > 0 : true);
    return { visible, src, dataTheme: document.documentElement.getAttribute('data-theme') };
  });
  checks.logo_visible_sidebar = sidebarEval.visible;
  evidence.sidebar_logo = sidebarEval;
  if (sidebarEval.dataTheme === 'light' || !sidebarEval.dataTheme) {
    checks.light_theme_ok = checks.light_theme_ok || sidebarEval.dataTheme === 'light';
  }

  const sidebarTop = page.locator('.dashboard-shell__sidebar-top');
  if (await sidebarTop.count()) {
    const sidebarExpandedPath = shot('sidebar-expanded.png');
    await sidebarTop.first().screenshot({ path: sidebarExpandedPath });
    screenshots.sidebar_expanded = sidebarExpandedPath;
  }

  const collapseBtn = page.locator('.dashboard-shell__collapse');
  await collapseBtn.first().click();
  await page.waitForTimeout(500);
  const collapsed = await page.evaluate(() =>
    document.querySelector('.dashboard-shell__sidebar--collapsed') !== null
  );
  checks.collapsed_sidebar_ok = collapsed;
  const collapsedMark = await page.evaluate(() => {
    const img = document.querySelector('.dashboard-shell__brand img, .dashboard-shell__brand-logo');
    const src = img?.getAttribute('src') ?? '';
    return { src, isMark: src.includes('investhome-mark') };
  });
  checks.collapsed_mark_src_ok = collapsedMark.isMark;
  evidence.collapsed_mark = collapsedMark;
  const sidebarCollapsedPath = shot('sidebar-collapsed.png');
  const sidebarEl = page.locator('.dashboard-shell__sidebar');
  await sidebarEl.first().screenshot({ path: sidebarCollapsedPath });
  screenshots.sidebar_collapsed = sidebarCollapsedPath;

  const header = page.locator('.app-header');
  const headerLightPath = shot('header-light.png');
  await header.first().screenshot({ path: headerLightPath });
  screenshots.header_light = headerLightPath;

  // Dark theme on dashboard
  const themeSelect = page.locator('.app-header__theme-select');
  await themeSelect.selectOption('dark');
  await page.waitForFunction(() => document.documentElement.getAttribute('data-theme') === 'dark', {
    timeout: 10000,
  });
  await page.waitForTimeout(600);
  checks.dark_theme_ok = true;
  const dashDarkPath = shot('dashboard-dark.png');
  await page.screenshot({ path: dashDarkPath, fullPage: false });
  screenshots.dashboard_dark = dashDarkPath;

  // Dark login via localStorage
  await context.clearCookies();
  await page.evaluate(() => {
    localStorage.setItem('investhome-theme', 'dark');
  });
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForFunction(() => document.documentElement.getAttribute('data-theme') === 'dark', {
    timeout: 10000,
  });
  await page.waitForTimeout(600);
  const loginDarkPath = shot('login-dark.png');
  await page.screenshot({ path: loginDarkPath, fullPage: true });
  screenshots.login_dark = loginDarkPath;
  const loginDarkEval = await evaluateLoginBrand(page);
  evidence.login_dark = loginDarkEval;
  if (loginDarkEval.dataTheme !== 'dark') {
    checks.dark_theme_ok = false;
  }
} catch (err) {
  evidence.error = String(err?.stack || err);
  const failPath = shot('error-state.png');
  try {
    await page.screenshot({ path: failPath, fullPage: true });
    screenshots.error_state = failPath;
  } catch {
    /* ignore */
  }
} finally {
  await browser.close();
}

const report = {
  generatedAt: new Date().toISOString(),
  baseUrl: BASE,
  outputDir: OUT,
  checks,
  allPassed: Object.values(checks).every(Boolean),
  screenshots,
  evidence,
};

const reportPath = path.join(OUT, 'brand-qa-report.json');
fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
