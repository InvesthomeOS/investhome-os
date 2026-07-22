/**
 * Product Polish P7 — Public Website Premium Experience QA
 * Evidence: tmp-browser-verify-output/product-polish-p7/
 */
import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE = process.env.PW_BASE_URL || 'http://localhost:3000';
const OUT = path.resolve(
  'C:/Users/eminb/Projects/investhome-os/tmp-browser-verify-output/product-polish-p7',
);

fs.mkdirSync(OUT, { recursive: true });

const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  tablet: { width: 768, height: 1024 },
  mobile: { width: 390, height: 844 },
};

const ROUTES = [
  { id: 'home', path: '/', wait: '.site-hero' },
  { id: 'projects', path: '/projects', wait: '.site-page' },
  { id: 'project-detail', path: '/projects/marina-residences', wait: '.site-project-hero' },
  { id: 'calculators', path: '/calculators', wait: '.site-page' },
  { id: 'calc-roi', path: '/calculators/roi', wait: '.site-calc' },
  { id: 'insights', path: '/insights', wait: '.site-page' },
  { id: 'article', path: '/insights/first-time-investor-checklist', wait: '.site-article' },
  { id: 'contact', path: '/contact', wait: '.site-form' },
  { id: 'lead-consultation', path: '/lead/consultation', wait: '.site-form' },
  { id: 'workflow', path: '/workflow', wait: '.site-workflow' },
  { id: 'sitemap', path: '/sitemap.xml', wait: null },
  { id: 'robots', path: '/robots.txt', wait: null },
];

function shot(...parts) {
  return path.join(OUT, parts.join('-') + '.png');
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const report = {
    base: BASE,
    at: new Date().toISOString(),
    routes: [],
    consoleErrors: [],
    brand: null,
    formSubmit: null,
    dashboardIntact: null,
    summary: { pass: 0, fail: 0 },
  };

  const context = await browser.newContext({
    viewport: VIEWPORTS.desktop,
    locale: 'en-US',
  });
  const page = await context.newPage();

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      report.consoleErrors.push({ text: msg.text(), url: page.url() });
    }
  });
  page.on('pageerror', (err) => {
    report.consoleErrors.push({ text: String(err), url: page.url(), pageerror: true });
  });

  for (const route of ROUTES) {
    const entry = { id: route.id, path: route.path, ok: false, status: null, error: null };
    try {
      const res = await page.goto(`${BASE}${route.path}`, {
        waitUntil: 'domcontentloaded',
        timeout: 60000,
      });
      entry.status = res?.status() ?? null;
      if (route.wait) {
        await page.waitForSelector(route.wait, { timeout: 30000 });
      } else {
        await page.waitForTimeout(400);
      }
      await page.screenshot({ path: shot('desktop', route.id), fullPage: true });
      entry.ok = entry.status !== null && entry.status < 400;
    } catch (err) {
      entry.error = String(err);
      entry.ok = false;
      try {
        await page.screenshot({ path: shot('desktop', route.id, 'error'), fullPage: true });
      } catch {
        /* ignore */
      }
    }
    report.routes.push(entry);
    if (entry.ok) report.summary.pass += 1;
    else report.summary.fail += 1;
  }

  // Brand tokens on homepage
  await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('.site-hero', { timeout: 30000 });
  report.brand = await page.evaluate(() => {
    const cs = getComputedStyle(document.documentElement);
    return {
      brandPrimary: cs.getPropertyValue('--brand-primary').trim(),
      brandSecondary: cs.getPropertyValue('--brand-secondary').trim(),
      brandAccent: cs.getPropertyValue('--brand-accent').trim(),
      fontSans: cs.getPropertyValue('--font-sans').trim(),
      hasHero: !!document.querySelector('.site-hero'),
      hasHeaderLogo: !!document.querySelector('.site-header__logo'),
      hasFooter: !!document.querySelector('.site-footer'),
      overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
    };
  });

  // Responsive shots
  for (const [name, vp] of Object.entries(VIEWPORTS)) {
    await page.setViewportSize(vp);
    await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('.site-hero', { timeout: 30000 });
    await page.screenshot({ path: shot('home', name), fullPage: false });
    await page.goto(`${BASE}/calculators/roi`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('.site-calc', { timeout: 30000 });
    await page.screenshot({ path: shot('calc-roi', name), fullPage: false });
  }

  // Lead form submit (offline-tolerant) — use React-friendly value setters
  await page.setViewportSize(VIEWPORTS.desktop);
  try {
    await page.goto(`${BASE}/lead/consultation`, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForSelector('.site-form', { timeout: 30000 });
    await page.waitForTimeout(400);
    await page.evaluate(() => {
      const form = document.querySelector('form.site-form');
      if (!form) throw new Error('form missing');
      const setVal = (selector, value) => {
        const el = form.querySelector(selector);
        if (!el) return;
        const proto =
          el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
        const desc = Object.getOwnPropertyDescriptor(proto, 'value');
        desc?.set?.call(el, value);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
      };
      setVal('input[name="full_name"]', 'P7 QA Visitor');
      setVal('input[name="email"]', 'p7-qa@example.com');
      setVal('textarea[name="message"]', 'Playwright P7 lead form verification');
    });
    await page.locator('form.site-form button[type="submit"]').click();
    await page.waitForSelector('.site-form__success, .site-form__error', { timeout: 15000 });
    report.formSubmit = await page.evaluate(() => ({
      success: !!document.querySelector('.site-form__success'),
      error: document.querySelector('.site-form__error')?.textContent || null,
      text: document.querySelector('.site-form__success, .site-form__error')?.textContent || null,
    }));
    await page.screenshot({ path: shot('lead-form-result'), fullPage: true });
  } catch (err) {
    report.formSubmit = { success: false, error: String(err), text: null };
    report.summary.fail += 1;
    try {
      await page.screenshot({ path: shot('lead-form-error'), fullPage: true });
    } catch {
      /* ignore */
    }
  }
  // Dashboard still reachable (login page exists; don't break admin boundary)
  const dashProbe = await page.goto(`${BASE}/dashboard`, {
    waitUntil: 'domcontentloaded',
    timeout: 60000,
  });
  report.dashboardIntact = {
    status: dashProbe?.status() ?? null,
    url: page.url(),
    redirectedToLogin: /\/login/.test(page.url()),
  };

  // Filter noisy console noise from extensions / HMR / Playwright caret injection
  report.consoleErrors = report.consoleErrors.filter(
    (e) =>
      !/favicon|Download the React DevTools|Fast Refresh|caret-color/i.test(e.text || ''),
  );

  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ summary: report.summary, brand: report.brand, formSubmit: report.formSubmit, dashboardIntact: report.dashboardIntact, consoleErrors: report.consoleErrors.length }, null, 2));

  await browser.close();
  const formOk = report.formSubmit && report.formSubmit.success;
  process.exit(report.summary.fail > 0 || !formOk ? 1 : 0);
}

main().catch(async (err) => {
  console.error(err);
  try {
    fs.writeFileSync(
      path.join(OUT, 'report.json'),
      JSON.stringify({ fatal: String(err), at: new Date().toISOString() }, null, 2),
    );
  } catch {
    /* ignore */
  }
  process.exit(1);
});
