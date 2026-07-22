import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE = 'http://localhost:3000';
const OUT = path.join(import.meta.dirname, 'final-platform-qa-output');
fs.mkdirSync(OUT, { recursive: true });

const ROLES = {
  superadmin: { email: 'superadmin@investhome.demo', password: 'Demo123!' },
  sales: { email: 'sales@investhome.demo', password: 'Demo123!' },
  readonly: { email: 'readonly@investhome.demo', password: 'Demo123!' },
};

const CONTACT_NAME = 'QA Final Platform Contact 20260719';
const VIEWPORTS = [1440, 1024, 768, 390];

const RAW_KEY_PATTERNS = [
  /MISSING_MESSAGE/g,
  /\bcrm\.[a-zA-Z0-9_.]+\b/g,
  /\bmarketing\.[a-zA-Z0-9_.]+\b/g,
  /\bcommon\.[a-zA-Z0-9_.]+\b/g,
  /\badmin\.[a-zA-Z0-9_.]+\b/g,
];

const consoleEntries = [];
const networkEntries = [];

const report = {
  timestamp: new Date().toISOString(),
  auth: { pass: false, blockers: [], loginPageLocaleToggle: null, notes: [] },
  crossNav: { pass: false, blockers: [], forecastingRedirect: null, localePersists: null, steps: [] },
  dataPersistence: { pass: false, contactCreatePersist: false, contactName: CONTACT_NAME, blockers: [], cleanedUp: false },
  roleMatrix: { pass: false, blockers: [], roles: {} },
  i18n: { pass: false, blockers: [], tr: {}, en: {} },
  responsive: { pass: false, blockers: [], viewports: {} },
  consoleNetwork: { pass: false, criticalConsole: [], criticalNetwork: [], noise: [] },
  filesChanged: [],
  blockers: [],
};

function addBlocker(area, msg) {
  report.blockers.push({ area, msg });
  if (report[area]) report[area].blockers.push(msg);
}

async function waitStable(page, ms = 1500) {
  await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => {});
  await page.waitForTimeout(ms);
}

async function pageState(page) {
  return page.evaluate(() => {
    const text = document.body?.innerText || '';
    const navLinks = [...document.querySelectorAll('nav a, aside a, [class*="sidebar"] a')]
      .map((a) => ({ text: (a.textContent || '').trim(), href: a.getAttribute('href') }))
      .filter((x) => x.text || x.href);
    const breadcrumbs = [...document.querySelectorAll('[aria-label*="breadcrumb" i] *, nav[aria-label*="breadcrumb" i] *, .breadcrumb *, [class*="breadcrumb"] *')]
      .map((e) => (e.textContent || '').trim())
      .filter(Boolean);
    return {
      url: location.href,
      pathname: location.pathname,
      title: document.title,
      text: text.slice(0, 12000),
      h1: document.querySelector('h1')?.textContent?.trim() || null,
      alerts: [...document.querySelectorAll('[role="alert"]')].map((e) => e.textContent?.trim()).filter(Boolean),
      navLinks: navLinks.slice(0, 50),
      breadcrumbs: breadcrumbs.slice(0, 20),
      hasLoginForm: !!document.querySelector('input[type="email"], input[name="email"]'),
      hasPassword: !!document.querySelector('input[type="password"]'),
      lang: document.documentElement.lang,
      scrollW: document.documentElement.scrollWidth,
      clientW: document.documentElement.clientWidth,
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 5,
    };
  });
}

function rawKeys(text) {
  const found = new Set();
  for (const re of RAW_KEY_PATTERNS) {
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(text)) !== null) found.add(m[0]);
  }
  return [...found];
}

function i18nLeaks(text, locale) {
  const leaks = [];
  if (locale === 'tr') {
    if (/\bMarketing\b/.test(text) && !/Pazarlama/.test(text)) leaks.push('English "Marketing" in TR');
    if (/\bDashboard\b/.test(text)) leaks.push('English "Dashboard" in TR');
    if (/\bContacts\b/.test(text)) leaks.push('English "Contacts" in TR');
  }
  if (locale === 'en') {
    if (/\bPazarlama\b/.test(text)) leaks.push('Turkish "Pazarlama" in EN');
    if (/\bGiriş\b/.test(text)) leaks.push('Turkish "Giriş" in EN');
    if (/\bKişiler\b/.test(text)) leaks.push('Turkish "Kişiler" in EN');
  }
  return leaks;
}

async function detectLocaleToggle(page) {
  return page.evaluate(() => {
    const els = [...document.querySelectorAll('button, a, [role="button"], select, option, span')];
    const tr = els.some((el) => /türkçe|turkish|^tr$/i.test((el.textContent || '').trim()));
    const en = els.some((el) => /english|^en$/i.test((el.textContent || '').trim()));
    const lang = els.some((el) => /^(dil|language|locale)$/i.test((el.textContent || '').trim()));
    return { hasTr: tr, hasEn: en, hasLangControl: tr || en || lang };
  });
}

async function setLocale(page, locale) {
  const before = await pageState(page);
  const clicked = await page.evaluate((loc) => {
    const els = [...document.querySelectorAll('button, a, [role="button"], select, option, li, span')];
    const isTr = loc === 'tr';
    const direct = els.find((el) => {
      const t = (el.textContent || '').trim();
      return isTr ? /türkçe|turkish|^tr$/i.test(t) : /^english$|^en$/i.test(t);
    });
    if (direct) {
      direct.click();
      return 'direct';
    }
    const toggle = els.find((el) => /^(en|tr|dil|language|locale)$/i.test((el.textContent || '').trim()));
    if (toggle) {
      toggle.click();
      return 'toggle';
    }
    return null;
  }, locale);

  if (clicked === 'toggle') {
    await page.waitForTimeout(500);
    await page.evaluate((loc) => {
      const isTr = loc === 'tr';
      const pick = [...document.querySelectorAll('button, a, li, option, span')].find((el) =>
        isTr ? /türkçe|turkish|^tr$/i.test(el.textContent || '') : /english|^en$/i.test(el.textContent || '')
      );
      pick?.click();
    }, locale);
  }

  await waitStable(page, 1000);
  const after = await pageState(page);
  return { method: clicked || 'none', beforeLang: before.lang, afterLang: after.lang, textSample: after.text.slice(0, 300) };
}

async function login(page, creds, { expectSuccess = true } = {}) {
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() =>
    page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 30000 })
  );
  await waitStable(page, 800);
  const emailSel = 'input[type="email"], input[name="email"], input[autocomplete="email"]';
  await page.waitForSelector(emailSel, { timeout: 10000 });
  await page.fill(emailSel, creds.email);
  await page.fill('input[type="password"], input[name="password"]', creds.password);
  await page.click('button[type="submit"]');
  await waitStable(page, 2500);
  const state = await pageState(page);
  const onLogin = /login|sign.?in|giriş/i.test(state.pathname) || (state.hasLoginForm && state.hasPassword);
  const ok = expectSuccess ? !onLogin : onLogin;
  return { ok, state };
}

async function logout(page) {
  await page.evaluate(() => {
    const els = [...document.querySelectorAll('button, a, [role="menuitem"]')];
    const logoutBtn = els.find((el) => /logout|log out|çıkış|sign out/i.test(el.textContent || ''));
    if (logoutBtn) return logoutBtn.click();
    const menu = els.find((el) =>
      /profile|account|hesap|avatar|user menu|superadmin|sales|readonly/i.test(el.textContent || el.getAttribute('aria-label') || '')
    );
    menu?.click();
  });
  await page.waitForTimeout(700);
  await page.evaluate(() => {
    const logoutBtn = [...document.querySelectorAll('button, a, [role="menuitem"]')].find((el) =>
      /logout|log out|çıkış|sign out/i.test(el.textContent || '')
    );
    logoutBtn?.click();
  });
  await waitStable(page, 2000);
  return pageState(page);
}

async function checkAuthLoop(page, timeoutMs = 8000) {
  const start = Date.now();
  let lastPath = '';
  let changes = 0;
  while (Date.now() - start < timeoutMs) {
    const s = await pageState(page);
    if (s.pathname !== lastPath) {
      changes += 1;
      lastPath = s.pathname;
    }
    if (/login|dashboard|crm/i.test(s.pathname) && s.text.length > 50 && !s.text.includes('Loading')) break;
    await page.waitForTimeout(400);
  }
  const final = await pageState(page);
  const loop = changes > 6;
  return { loop, changes, finalPath: final.pathname, hasLogin: final.hasLoginForm };
}

function classifyNetwork(entry) {
  const url = entry.url || '';
  if (/favicon|_next\/static|hot-update|sockjs|webpack|analytics|google|fonts\.google|\.woff/i.test(url)) return 'noise';
  if (/cors|blocked by CORS/i.test(entry.failure || '')) return 'noise';
  if (entry.status === 401 || entry.status === 403) return 'critical';
  if (entry.status >= 500) return 'critical';
  if (entry.status === 404 && /\/api\//.test(url)) return 'critical';
  if (entry.status === 404) return 'noise';
  if (entry.failure) return 'critical';
  return entry.status >= 400 ? 'critical' : 'noise';
}

function classifyConsole(entry) {
  const text = entry.text || '';
  if (/favicon|hydration|devtools|source map|ResizeObserver|chunk|React DevTools/i.test(text)) return 'noise';
  return 'critical';
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  page.on('console', (msg) => {
    const type = msg.type();
    if (['error', 'warning', 'pageerror'].includes(type)) {
      consoleEntries.push({ type, text: msg.text(), url: page.url() });
    }
  });
  page.on('pageerror', (err) => consoleEntries.push({ type: 'pageerror', text: err.message, url: page.url() }));
  page.on('requestfailed', (req) => {
    networkEntries.push({ url: req.url(), method: req.method(), failure: req.failure()?.errorText, pageUrl: page.url() });
  });
  page.on('response', (resp) => {
    if (resp.status() >= 400) {
      networkEntries.push({ url: resp.url(), method: resp.request().method(), status: resp.status(), pageUrl: page.url() });
    }
  });

  const authChecks = {};

  try {
    await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitStable(page, 1000);
    report.auth.loginPageLocaleToggle = await detectLocaleToggle(page);
    await setLocale(page, 'tr');

    // Invalid login
    await page.fill('input[type="email"], input[name="email"]', 'bad@investhome.demo');
    await page.fill('input[type="password"]', 'WrongPass1!');
    await page.click('button[type="submit"]');
    await waitStable(page, 2000);
    let s = await pageState(page);
    authChecks.invalidLogin = {
      pass: (s.hasLoginForm || /login|giriş/i.test(s.pathname)) &&
        (/invalid|incorrect|wrong|hatalı|geçersiz|yanlış|başarısız|failed|credentials/i.test(s.text) || s.alerts.length > 0),
      url: s.url,
    };

    // Valid login
    const valid = await login(page, ROLES.superadmin);
    authChecks.validLogin = { pass: valid.ok, url: valid.state.url };

    // Refresh persistence
    await page.reload({ waitUntil: 'domcontentloaded' });
    await waitStable(page, 2000);
    s = await pageState(page);
    authChecks.refreshPersist = { pass: !s.hasLoginForm && !/login|giriş/i.test(s.pathname), url: s.url };

    // Deep link authed
    await page.goto(`${BASE}/workspaces/crm/contacts`, { waitUntil: 'domcontentloaded' });
    await waitStable(page, 2000);
    s = await pageState(page);
    authChecks.deepLinkAuthed = { pass: /crm\/contacts/i.test(s.pathname) && !s.hasLoginForm, url: s.url };

    // Logout
    s = await logout(page);
    authChecks.logout = { pass: s.hasLoginForm || /login|giriş/i.test(s.pathname), url: s.url };

    // Unauth deep link
    await page.goto(`${BASE}/workspaces/crm/contacts`, { waitUntil: 'domcontentloaded' });
    await waitStable(page, 2000);
    const loopCheck = await checkAuthLoop(page);
    s = await pageState(page);
    authChecks.deepLinkUnauthed = {
      pass: (s.hasLoginForm || /login|giriş/i.test(s.pathname)) && !loopCheck.loop,
      url: s.url,
      authLoop: loopCheck.loop,
    };
    authChecks.noAuthLoop = { pass: !loopCheck.loop, changes: loopCheck.changes };

    report.auth.pass = Object.values(authChecks).every((c) => c.pass !== false);
    report.auth.checks = authChecks;
    if (!authChecks.invalidLogin.pass) addBlocker('auth', 'Invalid login did not show error or stay on login');
    if (!authChecks.validLogin.pass) addBlocker('auth', 'Valid superadmin login failed');
    if (loopCheck.loop) addBlocker('auth', 'Auth redirect loop detected on unauthenticated deep link');
  } catch (e) {
    addBlocker('auth', e.message);
    report.auth.error = e.message;
  }

  // --- CROSS-NAV ---
  try {
    await login(page, ROLES.superadmin);
    await setLocale(page, 'tr');
    const trBefore = (await pageState(page)).text.slice(0, 200);

    const steps = [];
    const nav = async (label, urlOrFn) => {
      if (typeof urlOrFn === 'string') {
        await page.goto(`${BASE}${urlOrFn}`, { waitUntil: 'domcontentloaded' });
      } else {
        await urlOrFn();
      }
      await waitStable(page, 1800);
      const st = await pageState(page);
      steps.push({ label, url: st.url, pathname: st.pathname, ok: !st.hasLoginForm && st.text.length > 80 });
      return st;
    };

    await nav('dashboard', '/dashboard');
    await nav('crm', '/workspaces/crm/contacts');

    // Open contact detail
    let contactDetail = null;
    const contactLink = page.locator('a[href*="/workspaces/crm/contacts/"]').first();
    if (await contactLink.count()) {
      await contactLink.click();
      await waitStable(page, 2000);
      contactDetail = await pageState(page);
      steps.push({ label: 'contactDetail', url: contactDetail.url, pathname: contactDetail.pathname, ok: /contacts\/.+/.test(contactDetail.pathname) });
    } else {
      steps.push({ label: 'contactDetail', ok: false, note: 'no contact link in list' });
    }

    await nav('investors', '/dashboard/investors');
    const investorLink = page.locator('a[href*="/dashboard/investors/"]').first();
    if (await investorLink.count()) {
      await investorLink.click();
      await waitStable(page, 2000);
      const inv = await pageState(page);
      steps.push({ label: 'investorDetail', url: inv.url, ok: /investors\/.+/.test(inv.pathname) });
    } else {
      steps.push({ label: 'investorDetail', ok: false, note: 'no investor detail link' });
    }

    await nav('admin', '/dashboard/admin/users');
    await nav('marketing', '/workspaces/marketing/dashboard');

    // Forecasting redirect
    await page.goto(`${BASE}/workspaces/marketing/forecasting`, { waitUntil: 'domcontentloaded' });
    await waitStable(page, 2000);
    const forecast = await pageState(page);
    const forecastingOk = /\/workspaces\/marketing\/ai\/predictions/.test(forecast.pathname);
    report.crossNav.forecastingRedirect = {
      requested: '/workspaces/marketing/forecasting',
      landed: forecast.pathname,
      pass: forecastingOk,
    };
    steps.push({ label: 'forecasting', url: forecast.url, ok: forecastingOk });

    await page.goBack();
    await waitStable(page, 1500);
    const afterBack = await pageState(page);
    steps.push({ label: 'browserBack', url: afterBack.url, ok: !afterBack.hasLoginForm });

    await page.reload({ waitUntil: 'domcontentloaded' });
    await waitStable(page, 2000);
    const afterRefresh = await pageState(page);
    steps.push({ label: 'refresh', url: afterRefresh.url, ok: !afterRefresh.hasLoginForm });

    const enSwitch = await setLocale(page, 'en');
    const enAfter = await pageState(page);
    report.crossNav.localePersists = { trSample: trBefore, enSwitch, enSample: enAfter.text.slice(0, 200) };

    report.crossNav.steps = steps;
    report.crossNav.pass =
      steps.filter((x) => x.label !== 'contactDetail' && x.label !== 'investorDetail').every((x) => x.ok) &&
      forecastingOk &&
      !afterRefresh.hasLoginForm;
    if (!forecastingOk) addBlocker('crossNav', `Forecasting did not redirect to predictions (landed ${forecast.pathname})`);
  } catch (e) {
    addBlocker('crossNav', e.message);
    report.crossNav.error = e.message;
  }

  // --- DATA PERSISTENCE ---
  try {
    await login(page, ROLES.superadmin);
    await page.goto(`${BASE}/workspaces/crm/contacts`, { waitUntil: 'domcontentloaded' });
    await waitStable(page, 1500);
    let s = await pageState(page);
    let foundExisting = s.text.includes(CONTACT_NAME);

    if (!foundExisting) {
      await page.goto(`${BASE}/workspaces/crm/contacts/new`, { waitUntil: 'domcontentloaded' });
      await waitStable(page, 1500);

      const inputs = page.locator('input:visible, textarea:visible');
      const count = await inputs.count();
      let nameFilled = false;
      for (let i = 0; i < count; i++) {
        const el = inputs.nth(i);
        const ph = ((await el.getAttribute('placeholder')) || '') + ((await el.getAttribute('name')) || '') + ((await el.getAttribute('aria-label')) || '');
        if (/name|ad|isim|full/i.test(ph)) {
          await el.fill(CONTACT_NAME);
          nameFilled = true;
        }
        if (/email|e-posta/i.test(ph)) {
          await el.fill(`qa.final.20260719.${Date.now()}@investhome.demo`);
        }
      }

      const submit = page.locator('button[type="submit"]').or(page.getByRole('button', { name: /save|kaydet|create|oluştur/i }));
      if (await submit.count()) await submit.first().click();
      await waitStable(page, 3500);

      report.dataPersistence.nameFieldFilled = nameFilled;
    }

    await page.goto(`${BASE}/workspaces/crm/contacts`, { waitUntil: 'domcontentloaded' });
    await waitStable(page, 2000);
    s = await pageState(page);
    let foundList = s.text.includes(CONTACT_NAME);

    if (!foundList) {
      const search = page.locator('input[type="search"], input[placeholder*="ara" i], input[placeholder*="search" i]').first();
      if (await search.count()) {
        await search.fill(CONTACT_NAME);
        await page.waitForTimeout(1500);
        s = await pageState(page);
        foundList = s.text.includes(CONTACT_NAME);
      }
    }

    await page.reload({ waitUntil: 'domcontentloaded' });
    await waitStable(page, 2000);
    s = await pageState(page);
    const foundRefresh = s.text.includes(CONTACT_NAME);

    report.dataPersistence.contactCreatePersist = foundList && foundRefresh;
    report.dataPersistence.pass = report.dataPersistence.contactCreatePersist;
    report.dataPersistence.foundAfterCreate = foundList;
    report.dataPersistence.foundAfterRefresh = foundRefresh;
    report.dataPersistence.usedExisting = foundExisting;

    if (!report.dataPersistence.pass) addBlocker('dataPersistence', 'Contact not found in list after create/refresh');
  } catch (e) {
    addBlocker('dataPersistence', e.message);
    report.dataPersistence.error = e.message;
  }

  // --- ROLE MATRIX ---
  const roleExpectations = {
    superadmin: { admin: 'allow', crm: 'allow', marketing: 'allow', dashboard: 'allow', investors: 'allow' },
    sales: { admin: 'deny', crm: 'allow', marketing: 'deny', dashboard: 'allow', investors: 'allow' },
    readonly: { admin: 'deny', crm: 'check', marketing: 'deny', dashboard: 'allow', investors: 'allow' },
  };

  for (const [roleName, creds] of Object.entries(ROLES)) {
    report.roleMatrix.roles[roleName] = {};
    try {
      await login(page, creds);
      await waitStable(page, 1500);
      const routes = {
        dashboard: '/dashboard',
        crm: '/workspaces/crm/contacts',
        investors: '/dashboard/investors',
        admin: '/dashboard/admin/users',
        marketing: '/workspaces/marketing/dashboard',
      };
      for (const [key, route] of Object.entries(routes)) {
        await page.goto(`${BASE}${route}`, { waitUntil: 'domcontentloaded' });
        await waitStable(page, 1800);
        const st = await pageState(page);
        const denied = /access denied|forbidden|yetkisiz|erişim reddedildi|403|permission|not authorized/i.test(st.text);
        const loginRedirect = st.hasLoginForm || /login|giriş/i.test(st.pathname);
        const loaded = !loginRedirect && st.text.length > 100;
        const exp = roleExpectations[roleName][key];
        let pass = true;
        if (exp === 'deny') pass = denied || loginRedirect || /403|forbidden/i.test(st.text);
        else if (exp === 'allow') pass = loaded && !denied;
        else pass = loaded || denied; // readonly crm: shell or 403 both ok
        report.roleMatrix.roles[roleName][key] = { pass, expected: exp, denied, loaded, url: st.url, pathname: st.pathname };
      }
      await logout(page);
    } catch (e) {
      report.roleMatrix.roles[roleName].error = e.message;
    }
  }

  const roleFails = [];
  for (const [role, checks] of Object.entries(report.roleMatrix.roles)) {
    for (const [route, r] of Object.entries(checks)) {
      if (route === 'error') continue;
      if (!r.pass) roleFails.push(`${role}:${route}`);
    }
  }
  report.roleMatrix.pass = roleFails.length === 0;
  if (roleFails.length) addBlocker('roleMatrix', `Failed checks: ${roleFails.join(', ')}`);

  // --- i18n ---
  try {
    await login(page, ROLES.superadmin);
    await setLocale(page, 'tr');
    await page.goto(`${BASE}/workspaces/crm/contacts`, { waitUntil: 'domcontentloaded' });
    await waitStable(page, 1500);
    let trCrm = await pageState(page);
    await page.goto(`${BASE}/workspaces/marketing/dashboard`, { waitUntil: 'domcontentloaded' });
    await waitStable(page, 1500);
    let trMkt = await pageState(page);
    await page.goto(`${BASE}/dashboard/investors`, { waitUntil: 'domcontentloaded' });
    await waitStable(page, 1500);
    let trInv = await pageState(page);

    report.i18n.tr = {
      crmDashboard: { rawKeys: rawKeys(trCrm.text), leaks: i18nLeaks(trCrm.text, 'tr'), h1: trCrm.h1 },
      marketingSidebar: {
        labels: trMkt.navLinks.filter((l) => /pazar|market|kampanya|içerik|analit/i.test(l.text || '')),
        rawKeys: rawKeys(trMkt.text),
        leaks: i18nLeaks(trMkt.text, 'tr'),
      },
      investorBreadcrumbs: { breadcrumbs: trInv.breadcrumbs, rawKeys: rawKeys(trInv.text), leaks: i18nLeaks(trInv.text, 'tr') },
    };

    await setLocale(page, 'en');
    await page.goto(`${BASE}/workspaces/crm/contacts`, { waitUntil: 'domcontentloaded' });
    await waitStable(page, 1500);
    let enCrm = await pageState(page);
    await page.goto(`${BASE}/workspaces/marketing/dashboard`, { waitUntil: 'domcontentloaded' });
    await waitStable(page, 1500);
    let enMkt = await pageState(page);
    await page.goto(`${BASE}/dashboard/investors`, { waitUntil: 'domcontentloaded' });
    await waitStable(page, 1500);
    let enInv = await pageState(page);

    report.i18n.en = {
      crmDashboard: { rawKeys: rawKeys(enCrm.text), leaks: i18nLeaks(enCrm.text, 'en'), h1: enCrm.h1 },
      marketingSidebar: {
        labels: enMkt.navLinks.filter((l) => /market|campaign|content|analytic/i.test(l.text || '')),
        rawKeys: rawKeys(enMkt.text),
        leaks: i18nLeaks(enMkt.text, 'en'),
      },
      investorBreadcrumbs: { breadcrumbs: enInv.breadcrumbs, rawKeys: rawKeys(enInv.text), leaks: i18nLeaks(enInv.text, 'en') },
    };

    const i18nIssues = [];
    for (const loc of ['tr', 'en']) {
      const block = report.i18n[loc];
      for (const section of Object.values(block)) {
        if (section.rawKeys?.length) i18nIssues.push(`${loc} raw keys: ${section.rawKeys.join(', ')}`);
        if (section.leaks?.length) i18nIssues.push(`${loc} leaks: ${section.leaks.join(', ')}`);
      }
    }
    report.i18n.pass = i18nIssues.length === 0;
    report.i18n.issues = i18nIssues;
    if (i18nIssues.length) addBlocker('i18n', i18nIssues.join('; '));
  } catch (e) {
    addBlocker('i18n', e.message);
    report.i18n.error = e.message;
  }

  // --- RESPONSIVE ---
  try {
    await login(page, ROLES.superadmin);
    for (const width of VIEWPORTS) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(`${BASE}/dashboard`, { waitUntil: 'domcontentloaded' });
      await waitStable(page, 1200);
      const dash = await pageState(page);
      await page.goto(`${BASE}/workspaces/crm/contacts`, { waitUntil: 'domcontentloaded' });
      await waitStable(page, 1200);
      const crm = await pageState(page);
      const overflow390 = width === 390 && (dash.horizontalOverflow || crm.horizontalOverflow);
      report.responsive.viewports[width] = {
        dashboard: { overflow: dash.horizontalOverflow, scrollW: dash.scrollW, clientW: dash.clientW },
        crm: { overflow: crm.horizontalOverflow, scrollW: crm.scrollW, clientW: crm.clientW },
        pass: !overflow390,
      };
      if (overflow390) addBlocker('responsive', `Horizontal overflow at 390px (dash=${dash.horizontalOverflow}, crm=${crm.horizontalOverflow})`);
    }
    report.responsive.pass = !report.blockers.some((b) => b.area === 'responsive');
  } catch (e) {
    addBlocker('responsive', e.message);
    report.responsive.error = e.message;
  }

  // --- CONSOLE / NETWORK ---
  for (const entry of consoleEntries) {
    const bucket = classifyConsole(entry);
    report.consoleNetwork[bucket === 'noise' ? 'noise' : 'criticalConsole'].push(entry);
  }
  for (const entry of networkEntries) {
    const bucket = classifyNetwork(entry);
    if (bucket === 'noise') report.consoleNetwork.noise.push(entry);
    else report.consoleNetwork.criticalNetwork.push(entry);
  }
  report.consoleNetwork.pass = report.consoleNetwork.criticalConsole.length === 0 && report.consoleNetwork.criticalNetwork.length === 0;

  // Dedupe network by url+status
  const seen = new Set();
  report.consoleNetwork.criticalNetwork = report.consoleNetwork.criticalNetwork.filter((e) => {
    const k = `${e.url}|${e.status}|${e.failure}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });

  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})();
