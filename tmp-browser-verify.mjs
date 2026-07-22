import { chromium } from 'playwright';
import { writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';

const BASE = 'http://localhost:3000';
const OUT = join(process.cwd(), 'tmp-browser-verify-output');
mkdirSync(OUT, { recursive: true });

const consoleMessages = [];
const networkFailures = [];

async function saveScreenshot(page, name) {
  const path = join(OUT, `${name}.png`);
  await page.screenshot({ path, fullPage: true });
  return path;
}

async function getVisibleText(page) {
  return page.evaluate(() => {
    const texts = [];
    const walk = (el) => {
      if (el.nodeType === Node.TEXT_NODE) {
        const t = el.textContent?.trim();
        if (t) texts.push(t);
      } else if (el.nodeType === Node.ELEMENT_NODE) {
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden') return;
        for (const child of el.childNodes) walk(child);
      }
    };
    walk(document.body);
    return texts;
  });
}

async function setTurkish(page) {
  // Try common language selector patterns
  const selectors = [
    'button[aria-label*="language" i]',
    'button[aria-label*="dil" i]',
    '[data-testid*="language" i]',
    'select[name*="locale" i]',
    'select[name*="language" i]',
  ];

  for (const sel of selectors) {
    const el = page.locator(sel).first();
    if (await el.count() > 0 && await el.isVisible().catch(() => false)) {
      await el.click();
      const trOption = page.getByRole('option', { name: /turkish|türkçe|tr/i }).or(page.getByText(/turkish|türkçe|tr/i));
      if (await trOption.count() > 0) {
        await trOption.first().click();
        await page.waitForTimeout(1000);
        return 'selector-click';
      }
    }
  }

  // Look for language button with EN/TR text
  const langButtons = page.locator('button, a, [role="button"]').filter({ hasText: /^(EN|TR|English|Türkçe|Turkish)$/i });
  if (await langButtons.count() > 0) {
    for (let i = 0; i < await langButtons.count(); i++) {
      const btn = langButtons.nth(i);
      const text = (await btn.textContent())?.trim() || '';
      if (/türkçe|turkish|^tr$/i.test(text)) {
        await btn.click();
        await page.waitForTimeout(1000);
        return 'lang-button-tr';
      }
    }
    // Open dropdown and pick Turkish
    await langButtons.first().click();
    await page.waitForTimeout(500);
    const tr = page.getByText(/türkçe|turkish/i).first();
    if (await tr.count() > 0) {
      await tr.click();
      await page.waitForTimeout(1000);
      return 'dropdown-tr';
    }
  }

  // localStorage / cookie approach
  await page.evaluate(() => {
    localStorage.setItem('locale', 'tr');
    localStorage.setItem('language', 'tr');
    localStorage.setItem('i18nextLng', 'tr');
  });
  await page.reload({ waitUntil: 'networkidle' });
  return 'localStorage-reload';
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  page.on('console', (msg) => {
    if (['error', 'warning'].includes(msg.type())) {
      consoleMessages.push({ type: msg.type(), text: msg.text(), url: page.url() });
    }
  });

  page.on('pageerror', (err) => {
    consoleMessages.push({ type: 'pageerror', text: err.message, url: page.url() });
  });

  page.on('requestfailed', (req) => {
    networkFailures.push({
      url: req.url(),
      method: req.method(),
      failure: req.failure()?.errorText || 'unknown',
      pageUrl: page.url(),
    });
  });

  page.on('response', (resp) => {
    if (resp.status() >= 400) {
      networkFailures.push({
        url: resp.url(),
        method: resp.request().method(),
        status: resp.status(),
        pageUrl: page.url(),
      });
    }
  });

  const report = {
    appRunning: false,
    loginRequired: false,
    loginSuccess: false,
    languageMethod: null,
    marketingDashboard: {},
    executiveDashboard: {},
    consoleMessages: [],
    networkFailures: [],
  };

  try {
    const resp = await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 });
    report.appRunning = resp?.ok() ?? false;
    report.initialUrl = page.url();
    report.initialTitle = await page.title();

    // Login if needed
    const isLoginPage = /login|sign.?in|giriş/i.test(page.url()) ||
      (await page.locator('input[type="email"], input[name="email"], input[type="password"]').count()) >= 2;

    if (isLoginPage) {
      report.loginRequired = true;
      const email = page.locator('input[type="email"], input[name="email"]').first();
      const password = page.locator('input[type="password"], input[name="password"]').first();
      await email.fill('superadmin@investhome.demo');
      await password.fill('Demo123!');
      const submit = page.locator('button[type="submit"], button:has-text("Sign in"), button:has-text("Log in"), button:has-text("Giriş")').first();
      await submit.click();
      await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
      await page.waitForTimeout(2000);
      report.loginSuccess = !/login|sign.?in/i.test(page.url());
      report.postLoginUrl = page.url();
    }

    report.languageMethod = await setTurkish(page);
    await page.waitForTimeout(1500);

    // Marketing dashboard
    await page.goto(`${BASE}/workspaces/marketing/dashboard`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    const dashTexts = await getVisibleText(page);
    const dashScreenshot = await saveScreenshot(page, 'marketing-dashboard');

    report.marketingDashboard = {
      url: page.url(),
      title: await page.title(),
      screenshot: dashScreenshot,
      headerTitle: await page.locator('h1').first().textContent().catch(() => null),
      eyebrow: await page.locator('[class*="eyebrow"], [data-slot="eyebrow"], p.text-muted-foreground, .text-xs.uppercase').first().textContent().catch(() => null),
      quickActions: await page.locator('[class*="quick-action"], [data-testid*="quick"]').allTextContents().catch(() => []),
      sectionTitles: await page.locator('h2, h3, [class*="section-title"]').allTextContents().catch(() => []),
      allVisibleTexts: dashTexts.slice(0, 80),
      englishStrings: dashTexts.filter(t => /^[\x00-\x7F]+$/.test(t) && /[a-zA-Z]{3,}/.test(t) && t.length > 2),
    };

    // Clear console for executive page focus
    const consoleBeforeExec = consoleMessages.length;
    const networkBeforeExec = networkFailures.length;

    // Executive dashboard
    await page.goto(`${BASE}/workspaces/marketing/dashboard/executive`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);
    const execTexts = await getVisibleText(page);
    const execScreenshot = await saveScreenshot(page, 'marketing-executive');

    const overlayError = await page.locator('[role="alert"], [class*="error"], [class*="toast"], [data-nextjs-dialog]').allTextContents().catch(() => []);
    const errorBoundary = await page.locator('text=/something went wrong|error|failed|hata/i').allTextContents().catch(() => []);

    report.executiveDashboard = {
      url: page.url(),
      title: await page.title(),
      screenshot: execScreenshot,
      headerTitle: await page.locator('h1').first().textContent().catch(() => null),
      eyebrow: await page.locator('[class*="eyebrow"], [data-slot="eyebrow"], p.text-muted-foreground, .text-xs.uppercase').first().textContent().catch(() => null),
      overlayErrors: overlayError.filter(Boolean),
      errorBoundaryTexts: errorBoundary.filter(Boolean),
      allVisibleTexts: execTexts.slice(0, 100),
      englishStrings: execTexts.filter(t => /^[\x00-\x7F]+$/.test(t) && /[a-zA-Z]{3,}/.test(t) && t.length > 2),
      untranslatedLikely: execTexts.filter(t => /^(Dashboard|Executive|Summary|Overview|Campaign|Analytics|Loading|Error|Failed|Retry|View|Create|Edit|Delete|Save|Cancel|Back|Next|Previous|Search|Filter|Export|Import|Settings|Marketing|Lead|Audience|Segment|Automation|Attribution|Budget|Channel|Content|Landing|Conversion|Performance|ROI|CTR|CPC|CPM|Spend|Revenue|Growth|Trend|Report|Insights|Recommendations|Quick Actions|View all|See all|No data|Coming soon)$/i.test(t.trim())),
    };

    report.consoleMessages = consoleMessages.slice(consoleBeforeExec);
    report.networkFailures = networkFailures.slice(networkBeforeExec);
    report.allConsoleMessages = consoleMessages;
    report.allNetworkFailures = networkFailures;

  } catch (err) {
    report.error = err.message;
    await saveScreenshot(page, 'error-state').catch(() => {});
  } finally {
    writeFileSync(join(OUT, 'report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
    await browser.close();
  }
})();
