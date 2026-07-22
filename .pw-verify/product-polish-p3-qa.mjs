import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE = process.env.PW_BASE_URL || 'http://localhost:3000';
const OUT = path.resolve(
  'C:/Users/eminb/Projects/investhome-os/tmp-browser-verify-output/product-polish-p3',
);
const EMAIL = 'superadmin@investhome.demo';
const PASS = 'Demo123!';
const PHASE = process.env.PW_PHASE || 'after';

fs.mkdirSync(OUT, { recursive: true });

const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  laptop: { width: 1280, height: 800 },
  tablet: { width: 900, height: 1200 },
  wide: { width: 1920, height: 1080 },
};

const ROUTES = [
  { id: 'home', path: '/dashboard', wait: '.ex-home' },
  { id: 'executive', path: '/dashboard/executive', wait: '.executive, .ex-home, main' },
  { id: 'sales', path: '/dashboard/sales', wait: 'main' },
  { id: 'finance', path: '/dashboard/finance', wait: 'main' },
  { id: 'admin', path: '/dashboard/admin', wait: 'main' },
];

function shot(...parts) {
  return path.join(OUT, [PHASE, ...parts].join('-') + '.png');
}

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  const email = page.locator('input[type="email"]').first();
  await email.waitFor({ state: 'visible', timeout: 45000 });
  await email.fill(EMAIL);
  await page.locator('input[type="password"]').first().fill(PASS);
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/\/dashboard/, { timeout: 90000 });
  await page.waitForSelector('.dashboard-shell__sidebar', { timeout: 45000 });
  await page.waitForTimeout(600);
}

async function measureHome(page) {
  return page.evaluate(() => {
    const root = document.querySelector('.ex-home');
    const kpis = [...document.querySelectorAll('.ex-home__kpi-grid .ih-kpi-card')];
    const panels = [...document.querySelectorAll('.ex-home .ih-panel')];
    const charts = [...document.querySelectorAll('.ih-chart')];
    const skeletons = document.querySelectorAll('.ih-skeleton, .ih-kpi-card--loading').length;
    const loadingText = [...document.querySelectorAll('p, span, div')]
      .map((el) => (el.textContent || '').trim())
      .filter((t) => /Yükleniyor|Loading…|Loading\.\.\./i.test(t))
      .slice(0, 8);
    const brandPrimary = getComputedStyle(document.documentElement)
      .getPropertyValue('--brand-primary')
      .trim();
    const focusSample = document.querySelector('.ih-btn, .ex-home__hero-btn, .dashboard-shell__nav-link');
    let focusOutline = null;
    if (focusSample) {
      focusSample.focus();
      const cs = getComputedStyle(focusSample);
      focusOutline = { outline: cs.outline, boxShadow: cs.boxShadow, outlineColor: cs.outlineColor };
    }
    const overflowX = document.documentElement.scrollWidth > document.documentElement.clientWidth + 2;
    const kpiStyles = kpis.slice(0, 4).map((el, i) => {
      const cs = getComputedStyle(el);
      const value = el.querySelector('.ih-kpi-card__value');
      const valueCs = value ? getComputedStyle(value) : null;
      return {
        index: i,
        padding: cs.padding,
        radius: cs.borderRadius,
        shadow: cs.boxShadow,
        minHeight: cs.minHeight,
        valueSize: valueCs?.fontSize ?? null,
        classes: el.className,
      };
    });
    const panelPad = panels.slice(0, 3).map((p) => {
      const body = p.querySelector('.ih-panel__body');
      const header = p.querySelector('.ih-panel__header');
      return {
        bodyPad: body ? getComputedStyle(body).padding : null,
        headerPad: header ? getComputedStyle(header).padding : null,
      };
    });
    const btn = document.querySelector('.ih-btn--primary');
    const btnCs = btn ? getComputedStyle(btn) : null;
    return {
      hasHome: !!root,
      kpiCount: kpis.length,
      panelCount: panels.length,
      chartCount: charts.length,
      skeletons,
      loadingText,
      brandPrimary,
      focusOutline,
      overflowX,
      kpiStyles,
      panelPad,
      button: btnCs
        ? {
            height: btnCs.height,
            radius: btnCs.borderRadius,
            fontSize: btnCs.fontSize,
            color: btnCs.color,
            bg: btnCs.backgroundColor,
            gap: btnCs.gap,
          }
        : null,
      legendPresent: !!document.querySelector('.ih-chart__legend'),
    };
  });
}

async function measureTable(page) {
  return page.evaluate(() => {
    const table = document.querySelector('.ih-table, .admin-table, .leads__table');
    if (!table) return { present: false };
    const th = table.querySelector('th');
    const tr = table.querySelector('tbody tr') || table.querySelector('tr');
    const thCs = th ? getComputedStyle(th) : null;
    const trCs = tr ? getComputedStyle(tr) : null;
    return {
      present: true,
      thPad: thCs?.padding ?? null,
      rowHeight: tr ? tr.getBoundingClientRect().height : null,
      hasSort: !!table.querySelector('[aria-sort], .ih-table__sort, th[data-sortable]'),
      hoverRule: !!document.styleSheets,
    };
  });
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ locale: 'tr-TR' });
  const page = await context.newPage();
  const report = {
    phase: PHASE,
    base: BASE,
    startedAt: new Date().toISOString(),
    checks: {},
    evidence: {},
    screenshots: {},
    failures: [],
  };

  try {
    await page.setViewportSize(VIEWPORTS.desktop);

    // Login / brand (before auth)
    await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.locator('input[type="email"]').first().waitFor({ state: 'visible', timeout: 45000 });
    await page.waitForTimeout(400);
    const loginLogo = await page.locator('img[src*="investhome"]').first().count();
    report.checks.login_logo = loginLogo > 0;
    const loginShot = shot('login', 'desktop');
    await page.screenshot({ path: loginShot, fullPage: false });
    report.screenshots.login_desktop = loginShot;

    await login(page);

    for (const route of ROUTES) {
      for (const [vpName, vp] of Object.entries(VIEWPORTS)) {
        if (route.id !== 'home' && vpName === 'wide') continue;
        if (route.id !== 'home' && route.id !== 'executive' && vpName === 'tablet') continue;
        await page.setViewportSize(vp);
        await page.goto(`${BASE}${route.path}`, { waitUntil: 'domcontentloaded', timeout: 90000 });
        try {
          await page.waitForSelector(route.wait, { timeout: 30000 });
        } catch {
          /* continue with evidence */
        }
        await page.waitForTimeout(700);
        const file = shot(route.id, vpName);
        await page.screenshot({ path: file, fullPage: true });
        report.screenshots[`${route.id}_${vpName}`] = file;

        if (route.id === 'home' && vpName === 'desktop') {
          report.evidence.home = await measureHome(page);
          // focus ring on refresh / nav
          const refresh = page.locator('.ex-home__hero-btn').first();
          if (await refresh.count()) {
            await refresh.focus();
            const focusShot = shot('home', 'focus-hero');
            await page.screenshot({ path: focusShot, fullPage: false });
            report.screenshots.home_focus = focusShot;
          }
        }
        if (route.id === 'executive' && vpName === 'desktop') {
          report.evidence.executive = await measureHome(page).catch(() => null);
          report.evidence.executiveTable = await measureTable(page);
        }
        if (route.id === 'sales' && vpName === 'desktop') {
          report.evidence.salesTable = await measureTable(page);
        }
        if (route.id === 'admin' && vpName === 'desktop') {
          report.evidence.adminTable = await measureTable(page);
        }

        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
        );
        if (overflow) {
          report.failures.push(`overflow:${route.id}:${vpName}`);
        }
      }
    }

    // Collapsed sidebar brand check
    await page.setViewportSize(VIEWPORTS.desktop);
    await page.goto(`${BASE}/dashboard`, { waitUntil: 'networkidle' });
    const collapseBtn = page.locator(
      'button.dashboard-shell__collapse, [aria-label*="collapse" i], [aria-label*="Daralt" i], .dashboard-shell__collapse-btn',
    );
    if (await collapseBtn.count()) {
      await collapseBtn.first().click();
      await page.waitForTimeout(400);
      const collapsed = shot('home', 'sidebar-collapsed');
      await page.screenshot({ path: collapsed, fullPage: false });
      report.screenshots.sidebar_collapsed = collapsed;
    }

    const home = report.evidence.home || {};
    const brand = (home.brandPrimary || '').toLowerCase();
    report.checks.brand_primary = brand === '#9d7b55';
    report.checks.home_surface = !!home.hasHome && (home.panelCount || 0) >= 4;
    report.checks.home_kpis_or_error =
      (home.kpiCount || 0) >= 1 ||
      home.skeletons >= 1 ||
      !!(await page.locator('.ih-error, .ex-home__kpi-grid, .ih-kpi-card').count());
    report.checks.no_abrupt_loading_text = (home.loadingText || []).length === 0;
    report.checks.no_overflow = report.failures.filter((f) => f.startsWith('overflow')).length === 0;
    report.checks.chart_legend =
      PHASE === 'before' ? true : !!home.legendPresent || (home.chartCount || 0) === 0;
    const hasBtn = await page.locator('.ih-btn, .ex-home__hero-btn, .auth-form__submit').count();
    report.checks.button_system = hasBtn > 0;
    report.checks.focus_visible = !!(
      home.focusOutline &&
      ((home.focusOutline.outline && home.focusOutline.outline !== 'none') ||
        (home.focusOutline.boxShadow && home.focusOutline.boxShadow !== 'none'))
    );
    report.checks.primary_secondary_hierarchy =
      PHASE === 'before'
        ? true
        : (home.kpiStyles || []).some((k) => String(k.classes || '').includes('ih-kpi-card--primary')) ||
          (home.kpiCount || 0) === 0;

    report.ok = Object.values(report.checks).every(Boolean) && report.failures.length === 0;
  } catch (err) {
    report.ok = false;
    report.error = String(err?.stack || err);
    try {
      await page.screenshot({ path: shot('failure'), fullPage: true });
    } catch {
      /* ignore */
    }
  } finally {
    report.finishedAt = new Date().toISOString();
    fs.writeFileSync(path.join(OUT, `report-${PHASE}.json`), JSON.stringify(report, null, 2));
    await browser.close();
  }

  console.log(JSON.stringify({ ok: report.ok, phase: PHASE, checks: report.checks, failures: report.failures, error: report.error }, null, 2));
  process.exit(report.ok ? 0 : 1);
}

run();
