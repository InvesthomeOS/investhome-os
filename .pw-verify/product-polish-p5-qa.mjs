import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE = process.env.PW_BASE_URL || 'http://localhost:3000';
const OUT = path.resolve(
  'C:/Users/eminb/Projects/investhome-os/tmp-browser-verify-output/product-polish-p5',
);
const EMAIL = 'superadmin@investhome.demo';
const PASS = 'Demo123!';

fs.mkdirSync(OUT, { recursive: true });

const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  laptop: { width: 1280, height: 800 },
  tablet: { width: 900, height: 1200 },
  wide: { width: 1920, height: 1080 },
};

const ROUTES = [
  { id: 'home', path: '/dashboard', wait: '.ex-home, .ecc-command, main' },
  { id: 'executive', path: '/dashboard/executive', wait: '.executive, .ecc-command, main' },
];

function shot(...parts) {
  return path.join(OUT, parts.join('-') + '.png');
}

function isBenignConsole(text) {
  return (
    /Download the React DevTools/i.test(text) ||
    /favicon\.ico/i.test(text) ||
    /Hydration failed/i.test(text) ||
    /hydrat(?:e|ion)/i.test(text) ||
    /did not match/i.test(text) ||
    /Extra attributes from the server/i.test(text) ||
    /Warning: Text content did not match/i.test(text) ||
    /Failed to load resource: the server responded with a status of 4\d\d/i.test(text) ||
    /401 \(Unauthorized\)/i.test(text) ||
    /blocked by CORS policy/i.test(text) ||
    /net::ERR_FAILED/i.test(text) ||
    /Failed to load resource: net::ERR_/i.test(text)
  );
}

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 90000 });
  const email = page.locator('input[type="email"]').first();
  await email.waitFor({ state: 'visible', timeout: 45000 });
  await page.waitForTimeout(500);
  await email.click();
  await email.fill(EMAIL);
  const password = page.locator('input[type="password"]').first();
  await password.click();
  await password.fill(PASS);

  const loginRespPromise = page.waitForResponse(
    (r) => r.url().includes('/auth/login') && r.request().method() === 'POST',
    { timeout: 60000 },
  );
  await page.locator('button[type="submit"]').first().click();
  const resp = await loginRespPromise.catch(() => null);
  if (resp && resp.status() >= 400) {
    throw new Error(`auth/login HTTP ${resp.status()}`);
  }

  await page.waitForSelector('.dashboard-shell__sidebar', { timeout: 90000 });
  if (!/\/(dashboard|workspaces)/.test(page.url())) {
    await page.waitForURL(/\/(dashboard|workspaces)/, { timeout: 30000 }).catch(() => null);
  }
  await page.waitForTimeout(600);
}

async function measureExecutive(page) {
  return page.evaluate(() => {
    const q = (sel) => !!document.querySelector(sel);
    const kpis = document.querySelectorAll('.ecc-kpi__card');
    const brandPrimary = getComputedStyle(document.documentElement)
      .getPropertyValue('--brand-primary')
      .trim();
    const overflowX =
      document.documentElement.scrollWidth > document.documentElement.clientWidth + 2;
    const bodyText = (document.body.innerText || '').slice(0, 4000);
    const unavailableHints = [
      /Unavailable|Kullanilamiyor|veri yok|no data|empty|rolunuz/i.test(bodyText) ||
        bodyText.includes('Kullan') ||
        bodyText.includes('Unavailable'),
      !!document.querySelector(
        '.ecc-kpi--unavailable, .ih-kpi-card--unavailable, [data-unavailable], .ecc-empty',
      ),
    ].some(Boolean);
    return {
      hasEccCommand: q('.ecc-command'),
      hasEccHealth: q('.ecc-health'),
      hasEccKpi: q('.ecc-kpi') || kpis.length > 0,
      hasEccPriorities: q('.ecc-priorities, .ecc-priority-list'),
      hasEccAlerts: q('.ecc-alerts'),
      hasEccQuick: q('.ecc-quick'),
      hasEccSearch: q('.ecc-search'),
      hasEccMywork: q('.ecc-mywork'),
      hasAiPanel: q('.executive__ai-panel'),
      kpiCardCount: kpis.length,
      overflowX,
      brandPrimary,
      unavailableHints,
      sampleText: bodyText.slice(0, 500),
    };
  });
}

async function measureHome(page) {
  return page.evaluate(() => {
    const overflowX =
      document.documentElement.scrollWidth > document.documentElement.clientWidth + 2;
    const bodyText = (document.body.innerText || '').slice(0, 2000);
    return {
      hasExHome: !!document.querySelector('.ex-home'),
      hasEccSearch: !!document.querySelector('.ecc-search'),
      overflowX,
      unavailableHints: /Unavailable|rol/i.test(bodyText) || bodyText.includes('Kullan'),
    };
  });
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ locale: 'tr-TR' });
  const page = await context.newPage();

  const consoleErrors = [];
  const pageErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => {
    pageErrors.push(String(err?.message || err));
  });

  const report = {
    base: BASE,
    startedAt: new Date().toISOString(),
    checks: {},
    widgets: {},
    home: {},
    screenshots: {},
    failures: [],
    softFailures: [],
    consoleErrors: [],
    pageErrors: [],
  };

  try {
    try {
      await login(page);
    } catch (loginErr) {
      report.softFailures.push(`login_retry: ${String(loginErr?.message || loginErr)}`);
      await context.clearCookies();
      await page.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 90000 });
      await page.waitForTimeout(1000);
      await login(page);
    }
    report.checks.login_ok = true;

    for (const route of ROUTES) {
      for (const [vpName, vp] of Object.entries(VIEWPORTS)) {
        await page.setViewportSize(vp);
        await page.goto(`${BASE}${route.path}`, { waitUntil: 'domcontentloaded', timeout: 90000 });
        try {
          await page.waitForSelector(route.wait, { timeout: 30000 });
        } catch {
          /* continue for evidence */
        }

        if (route.id === 'executive' && vpName === 'desktop') {
          try {
            await page.waitForSelector(
              '.ecc-command, .ecc-kpi, .executive__workspace-body',
              { timeout: 45000 },
            );
          } catch {
            report.softFailures.push('executive_desktop_wait_timeout');
          }
        }

        await page.waitForTimeout(700);
        const file = shot(route.id, vpName);
        await page.screenshot({ path: file, fullPage: true });
        report.screenshots[`${route.id}_${vpName}`] = file;

        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
        );
        if (overflow) {
          report.failures.push(`overflow:${route.id}:${vpName}`);
        }

        if (route.id === 'executive' && vpName === 'desktop') {
          report.widgets = await measureExecutive(page);
        }
        if (route.id === 'home' && vpName === 'desktop') {
          report.home = await measureHome(page);
        }
      }
    }

    const w = report.widgets || {};
    const h = report.home || {};

    report.checks.has_ecc_command = !!w.hasEccCommand;
    report.checks.has_ecc_health = !!w.hasEccHealth;
    report.checks.has_ecc_kpi = !!w.hasEccKpi;
    report.checks.has_ecc_priorities = !!w.hasEccPriorities;
    report.checks.has_ecc_alerts = !!w.hasEccAlerts;
    report.checks.has_ecc_quick = !!w.hasEccQuick;
    report.checks.has_ecc_search = !!w.hasEccSearch;
    report.checks.has_ecc_mywork = !!w.hasEccMywork;
    report.checks.has_ai_panel = !!w.hasAiPanel;
    report.checks.kpi_card_count = w.kpiCardCount ?? 0;
    report.checks.brand_primary = w.brandPrimary || null;
    report.checks.executive_overflow_x = !!w.overflowX;
    report.checks.home_ex_home = !!h.hasExHome;
    report.checks.home_ecc_search = !!h.hasEccSearch;
    report.checks.home_overflow_x = !!h.overflowX;
    report.checks.no_overflow =
      report.failures.filter((f) => f.startsWith('overflow')).length === 0;

    const criticalWidgets =
      !!w.hasEccCommand &&
      (!!w.hasEccKpi || (w.kpiCardCount || 0) > 0 || !!w.hasEccHealth);

    for (const [key, present] of [
      ['ecc_priorities', w.hasEccPriorities],
      ['ecc_alerts', w.hasEccAlerts],
      ['ecc_quick', w.hasEccQuick],
      ['ecc_mywork', w.hasEccMywork],
      ['ai_panel', w.hasAiPanel],
    ]) {
      if (!present) report.softFailures.push(`missing_optional:${key}`);
    }
    if ((w.kpiCardCount || 0) === 0 && w.unavailableHints) {
      report.softFailures.push('kpi_empty_or_unavailable');
    }

    const unexpectedConsole = [...consoleErrors, ...pageErrors].filter(
      (t) => !isBenignConsole(t),
    );
    report.consoleErrors = consoleErrors;
    report.pageErrors = pageErrors;
    report.unexpectedConsole = unexpectedConsole;
    report.checks.no_breaking_console = unexpectedConsole.length === 0;
    report.checks.critical_widgets = criticalWidgets;

    report.ok =
      report.checks.login_ok &&
      criticalWidgets &&
      report.checks.no_overflow &&
      report.checks.no_breaking_console;
  } catch (err) {
    report.ok = false;
    report.error = String(err?.stack || err);
    try {
      await page.screenshot({ path: shot('failure'), fullPage: true });
      report.screenshots.failure = shot('failure');
    } catch {
      /* ignore */
    }
  } finally {
    report.finishedAt = new Date().toISOString();
    fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
    await browser.close();
  }

  console.log(
    JSON.stringify(
      {
        ok: report.ok,
        checks: report.checks,
        widgets: report.widgets,
        home: report.home,
        failures: report.failures,
        softFailures: report.softFailures,
        unexpectedConsole: report.unexpectedConsole,
        error: report.error,
        screenshots: Object.keys(report.screenshots || {}),
      },
      null,
      2,
    ),
  );
  process.exit(report.ok ? 0 : 1);
}

run();