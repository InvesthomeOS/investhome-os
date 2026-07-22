const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:3000';
const OUT = path.join(__dirname, 'tmp-browser-verify-output');
fs.mkdirSync(OUT, { recursive: true });

(async () => {
  const consoleMessages = [];
  const networkFailures = [];

  const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  page.on('console', (msg) => {
    const type = msg.type();
    if (type === 'error' || type === 'warning') {
      consoleMessages.push({ type, text: msg.text(), url: page.url() });
    }
  });
  page.on('pageerror', (err) => {
    consoleMessages.push({ type: 'pageerror', text: err.message, url: page.url() });
  });
  page.on('requestfailed', (req) => {
    networkFailures.push({ url: req.url(), method: req.method(), failure: req.failure()?.errorText, pageUrl: page.url() });
  });
  page.on('response', (resp) => {
    if (resp.status() >= 400) {
      networkFailures.push({ url: resp.url(), method: resp.request().method(), status: resp.status(), pageUrl: page.url() });
    }
  });

  const report = { appRunning: false, loginRequired: false, loginSuccess: false, languageMethod: null, marketingDashboard: {}, executiveDashboard: {}, allConsoleMessages: consoleMessages, allNetworkFailures: networkFailures };

  const getVisibleText = async () => page.evaluate(() => {
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

  const setTurkish = async () => {
    const clicked = await page.evaluate(() => {
      const candidates = [...document.querySelectorAll('button, a, [role="button"], select option, li')];
      const tr = candidates.find(el => /türkçe|turkish|^tr$/i.test((el.textContent || '').trim()));
      if (tr) { tr.click(); return 'clicked-tr'; }
      const langBtn = candidates.find(el => /^(en|english|dil|language)$/i.test((el.textContent || '').trim()));
      if (langBtn) { langBtn.click(); return 'opened-lang'; }
      return null;
    });
    if (clicked === 'opened-lang') {
      await page.waitForTimeout(500);
      await page.evaluate(() => {
        const tr = [...document.querySelectorAll('*')].find(el => /türkçe|turkish/i.test(el.textContent || ''));
        tr?.click();
      });
      await page.waitForTimeout(1000);
      return 'dropdown-tr';
    }
    if (clicked) return clicked;
    await page.evaluate(() => {
      localStorage.setItem('locale', 'tr');
      localStorage.setItem('language', 'tr');
      localStorage.setItem('i18nextLng', 'tr');
    });
    await page.reload({ waitUntil: 'networkidle2' });
    return 'localStorage-reload';
  };

  try {
    const resp = await page.goto(BASE, { waitUntil: 'networkidle2', timeout: 30000 });
    report.appRunning = resp?.ok() ?? false;
    report.initialUrl = page.url();
    report.initialTitle = await page.title();

    const inputCount = await page.$$eval('input[type="email"], input[name="email"], input[type="password"]', els => els.length);
    const isLogin = /login|sign.?in|giriş/i.test(page.url()) || inputCount >= 2;
    if (isLogin) {
      report.loginRequired = true;
      await page.type('input[type="email"], input[name="email"]', 'superadmin@investhome.demo', { delay: 20 });
      await page.type('input[type="password"], input[name="password"]', 'Demo123!', { delay: 20 });
      await page.click('button[type="submit"]');
      await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 30000 }).catch(() => {});
      await page.waitForTimeout(2000);
      report.loginSuccess = !/login|sign.?in/i.test(page.url());
      report.postLoginUrl = page.url();
    }

    report.languageMethod = await setTurkish();
    await page.waitForTimeout(1500);

    await page.goto(`${BASE}/workspaces/marketing/dashboard`, { waitUntil: 'networkidle2', timeout: 30000 });
    await page.waitForTimeout(2000);
    const dashTexts = await getVisibleText();
    await page.screenshot({ path: path.join(OUT, 'marketing-dashboard.png'), fullPage: true });
    const h1 = await page.$eval('h1', el => el.textContent?.trim()).catch(() => null);
    const h2s = await page.$$eval('h2, h3', els => els.map(e => e.textContent?.trim()).filter(Boolean)).catch(() => []);

    report.marketingDashboard = {
      url: page.url(), title: await page.title(), headerTitle: h1, sectionTitles: h2s,
      allVisibleTexts: dashTexts.slice(0, 80),
      englishStrings: dashTexts.filter(t => /^[\x00-\x7F]+$/.test(t) && /[a-zA-Z]{3,}/.test(t) && t.length > 2),
    };

    const consoleBeforeExec = consoleMessages.length;
    const networkBeforeExec = networkFailures.length;

    await page.goto(`${BASE}/workspaces/marketing/dashboard/executive`, { waitUntil: 'networkidle2', timeout: 30000 });
    await page.waitForTimeout(3000);
    const execTexts = await getVisibleText();
    await page.screenshot({ path: path.join(OUT, 'marketing-executive.png'), fullPage: true });
    const overlayErrors = await page.$$eval('[role="alert"], [class*="error"], [data-nextjs-dialog]', els => els.map(e => e.textContent?.trim()).filter(Boolean)).catch(() => []);

    report.executiveDashboard = {
      url: page.url(), title: await page.title(),
      headerTitle: await page.$eval('h1', el => el.textContent?.trim()).catch(() => null),
      overlayErrors,
      allVisibleTexts: execTexts.slice(0, 100),
      englishStrings: execTexts.filter(t => /^[\x00-\x7F]+$/.test(t) && /[a-zA-Z]{3,}/.test(t) && t.length > 2),
    };
    report.consoleMessagesExecutive = consoleMessages.slice(consoleBeforeExec);
    report.networkFailuresExecutive = networkFailures.slice(networkBeforeExec);
  } catch (err) {
    report.error = err.message;
    await page.screenshot({ path: path.join(OUT, 'error-state.png'), fullPage: true }).catch(() => {});
  }

  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})();
