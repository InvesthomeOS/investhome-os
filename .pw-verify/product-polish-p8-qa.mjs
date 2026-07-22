import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE = process.env.PW_BASE_URL || 'http://localhost:3000';
const OUT = path.resolve('C:/Users/eminb/Projects/investhome-os/tmp-browser-verify-output/product-polish-p8');
const EMAIL = 'superadmin@investhome.demo';
const PASS = 'Demo123!';

fs.mkdirSync(OUT, { recursive: true });

const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  laptop: { width: 1280, height: 800 },
  tablet: { width: 900, height: 1200 },
};

const PAGES = [
  { id: 'dashboard', path: '/dashboard/automation' },
  { id: 'workflows', path: '/dashboard/automation/workflows' },
  { id: 'executions', path: '/dashboard/automation/executions' },
  { id: 'errors', path: '/dashboard/automation/errors' },
  { id: 'schedules', path: '/dashboard/automation/schedules' },
  { id: 'integrations', path: '/dashboard/automation/integrations' },
  { id: 'audit', path: '/dashboard/automation/audit' },
];

const screenshots = {};
const checks = {
  login_ok: false,
  nav_visible: false,
  overview_sections: false,
  workflow_list: false,
  workflow_detail: false,
  execution_history: false,
  responsive_ok: true,
  no_console_errors: true,
};
const consoleErrors = [];
const evidence = { consoleErrors: [], pages: {} };

function shot(...parts) {
  return path.join(OUT, parts.join('-') + '.png');
}

async function waitForShell(page) {
  await page.waitForSelector('.dashboard-shell__sidebar .dashboard-shell__collapse', { timeout: 45000 });
}

async function gotoPage(page, path) {
  await page.goto(`${BASE}${path}`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForLoadState('load').catch(() => null);
  await page.waitForTimeout(800);
}

async function login(page) {
  await gotoPage(page, '/login');
  await page.locator('input[type="email"]').first().fill(EMAIL);
  await page.locator('input[type="password"]').first().fill(PASS);
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/dashboard|workspaces/, { timeout: 60000 });
  await waitForShell(page);
  checks.login_ok = true;
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: VIEWPORTS.desktop,
  locale: 'en-US',
});
const page = await context.newPage();

page.on('console', (msg) => {
  if (msg.type() === 'error') {
    const text = msg.text();
    consoleErrors.push(text);
    evidence.consoleErrors.push(text);
    // Ignore known ambient noise (notifications CORS races, favicon, React DevTools).
    const ignore =
      /Download the React DevTools/i.test(text) ||
      /favicon/i.test(text) ||
      /\/notifications/i.test(text) ||
      /CORS policy/i.test(text) ||
      /status of 401/i.test(text) ||
      /net::ERR_FAILED/i.test(text);
    // Fail only on automation-center console failures.
    if (!ignore && /\/automation/i.test(text)) {
      checks.no_console_errors = false;
    }
  }
});

try {
  await login(page);

  // Nav entry
  const nav = page.locator('a.dashboard-shell__nav-link[href="/dashboard/automation"]');
  await nav.first().waitFor({ timeout: 15000 });
  checks.nav_visible = (await nav.count()) > 0;
  await page.screenshot({ path: shot('nav', 'desktop'), fullPage: true });
  screenshots.nav_desktop = shot('nav', 'desktop');

  for (const entry of PAGES) {
    await gotoPage(page, entry.path);
    await waitForShell(page);
    await page.waitForSelector('[data-automation-center]', { timeout: 30000 });
    const file = shot(entry.id, 'desktop');
    await page.screenshot({ path: file, fullPage: true });
    screenshots[`${entry.id}_desktop`] = file;
    evidence.pages[entry.id] = {
      path: entry.path,
      title: await page.locator('.automation-center__title').first().innerText().catch(() => null),
      hasShell: (await page.locator('[data-automation-center]').count()) > 0,
    };
  }

  // Overview sections
  await gotoPage(page, '/dashboard/automation');
  await page.waitForSelector('[data-automation-center]', { timeout: 30000 });
  const sectionTitles = await page.locator('.automation-center__panel-title').allInnerTexts();
  evidence.overview_sections = sectionTitles;
  checks.overview_sections =
    sectionTitles.length >= 4 &&
    /workflow|queue|execution|failure|schedule|integration|ai|akış|kuyruk|çalıştır|hata|zaman|entegrasyon|yz/i.test(
      sectionTitles.join(' '),
    );

  // Workflow list + detail
  await gotoPage(page, '/dashboard/automation/workflows');
  await page.waitForSelector('[data-automation-center]', { timeout: 30000 });
  const rows = page.locator('.automation-center__table tbody tr');
  await rows.first().waitFor({ timeout: 20000 }).catch(() => null);
  checks.workflow_list = (await rows.count()) > 0;
  if (checks.workflow_list) {
    const href = await rows.first().locator('a').first().getAttribute('href');
    if (href) {
      await gotoPage(page, href);
      await page.waitForSelector('[data-automation-center]', { timeout: 30000 });
      checks.workflow_detail =
        (await page.locator('.automation-center__panel-title').count()) >= 2 ||
        (await page.locator('.automation-center__banner').count()) > 0;
      const detailShot = shot('workflow-detail', 'desktop');
      await page.screenshot({ path: detailShot, fullPage: true });
      screenshots.workflow_detail_desktop = detailShot;
    }
  }

  // Execution history
  await gotoPage(page, '/dashboard/automation/executions');
  await page.waitForSelector('[data-automation-center]', { timeout: 30000 });
  checks.execution_history =
    (await page.locator('.automation-center__kpis').count()) > 0 &&
    ((await page.locator('.automation-center__table').count()) > 0 ||
      (await page.locator('.automation-center__empty, .ih-empty, [class*="EmptyState"]').count()) > 0);
  screenshots.executions_desktop = shot('executions', 'history');
  await page.screenshot({ path: screenshots.executions_desktop, fullPage: true });

  // Responsive matrix on overview
  for (const [name, viewport] of Object.entries(VIEWPORTS)) {
    await page.setViewportSize(viewport);
    await gotoPage(page, '/dashboard/automation');
    await page.waitForSelector('[data-automation-center]', { timeout: 30000 });
    const file = shot('overview', name);
    await page.screenshot({ path: file, fullPage: true });
    screenshots[`overview_${name}`] = file;
    const overflow = await page.evaluate(() => {
      const el = document.querySelector('[data-automation-center]');
      if (!el) return true;
      return el.scrollWidth > el.clientWidth + 40;
    });
    if (overflow) checks.responsive_ok = false;
  }

  const report = {
    ok:
      checks.login_ok &&
      checks.nav_visible &&
      checks.overview_sections &&
      checks.workflow_list &&
      checks.workflow_detail &&
      checks.execution_history &&
      checks.responsive_ok &&
      checks.no_console_errors,
    checks,
    screenshots,
    evidence,
    base: BASE,
    generatedAt: new Date().toISOString(),
  };

  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  if (!report.ok) process.exitCode = 1;
} catch (error) {
  const failure = {
    ok: false,
    error: String(error),
    checks,
    screenshots,
    evidence,
  };
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(failure, null, 2));
  await page.screenshot({ path: shot('failure'), fullPage: true }).catch(() => null);
  console.error(error);
  process.exitCode = 1;
} finally {
  await browser.close();
}
