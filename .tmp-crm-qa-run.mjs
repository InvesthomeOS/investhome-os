import { chromium } from 'playwright';

const BASE = 'http://localhost:3000';
const ROUTES = [
  '/workspaces/crm/dashboard',
  '/workspaces/crm/contacts',
  '/workspaces/crm/contacts/new',
  '/workspaces/crm/contacts/import',
  '/workspaces/crm/companies',
  '/workspaces/crm/companies/new',
  '/workspaces/crm/companies/import',
  '/workspaces/crm/relationships',
  '/workspaces/crm/relationships/new',
  '/workspaces/crm/relationships/network',
  '/workspaces/crm/relationships/intelligence',
  '/workspaces/crm/timeline',
  '/workspaces/crm/activities',
  '/workspaces/crm/tasks',
  '/workspaces/crm/calendar',
  '/workspaces/crm/notes',
  '/workspaces/crm/files',
  '/workspaces/crm/tags',
  '/workspaces/crm/communication',
  '/workspaces/crm/communication/calls',
  '/workspaces/crm/communication/meetings',
  '/workspaces/crm/communication/templates',
  '/workspaces/crm/communication/sequences',
  '/workspaces/crm/communication/signatures',
  '/workspaces/crm/communication/analytics',
  '/workspaces/crm/communication/preferences',
  '/workspaces/crm/documents',
  '/workspaces/crm/search',
  '/workspaces/crm/search/advanced',
  '/workspaces/crm/search/saved',
  '/workspaces/crm/reports',
  '/workspaces/crm/settings',
  '/dashboard/leads',
  '/dashboard/sales',
];

const RAW_KEY_RE = /\b(crm|activity|common)\.[a-zA-Z0-9_.]+/g;
const APPROVED = new Set([
  'CRM', 'CSV', 'SMS', 'WhatsApp', 'API', 'UUID', 'AND', 'OR',
  'Investhome', 'Zoom', 'Microsoft Teams', 'Ctrl+K', 'Super Admin', 'Demo', 'English',
]);
const TURKISH_CHARS = /[çğıöşüÇĞİÖŞÜ]/;

const ENGLISH_PHRASES = [
  'Access denied', 'Loading', 'Error', 'Save', 'Cancel', 'Delete', 'Edit', 'Create',
  'Search', 'Filter', 'Export', 'Import', 'Settings', 'Dashboard', 'Contacts',
  'Companies', 'Relationships', 'Activities', 'Tasks', 'Calendar', 'Notes',
  'Documents', 'Reports', 'New contact', 'New company', 'New relationship',
  'No results', 'Something went wrong', 'Try again', 'Back', 'Next', 'Previous',
  'Submit', 'Add', 'Remove', 'View', 'Details', 'Overview', 'Timeline',
  'Communication', 'Templates', 'Preferences', 'Analytics', 'Sign in', 'Log in',
  'Welcome', 'Manage', 'Select', 'Choose', 'Upload', 'Download', 'Refresh',
  'Show more', 'Show less', 'Required', 'Optional', 'Status', 'Type', 'Name',
  'Email', 'Phone', 'Address', 'Description', 'Title', 'Date', 'Time',
  'Network', 'Intelligence', 'Advanced', 'Saved searches', 'Tags', 'Files',
  'Calls', 'Meetings', 'Sequences', 'Signatures', 'Leads', 'Sales',
  'Step', 'Wizard', 'Continue', 'Finish', 'Skip',
];

function extractEnglishLeakage(text) {
  const found = new Set();
  for (const phrase of ENGLISH_PHRASES) {
    const re = new RegExp(`\\b${phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
    if (re.test(text)) {
      if (!APPROVED.has(phrase) && !APPROVED.has(phrase.replace(/\b\w/g, c => c.toUpperCase()))) {
        const match = text.match(re);
        if (match && !APPROVED.has(match[0])) found.add(match[0]);
      }
    }
  }
  // Standalone ASCII words 4+ chars not approved
  const words = text.match(/\b[A-Za-z]{4,}\b/g) || [];
  for (const w of words) {
    if (APPROVED.has(w) || APPROVED.has(w.charAt(0).toUpperCase() + w.slice(1))) continue;
    if (/^(http|https|true|false|null|undefined|Investhome)$/i.test(w)) continue;
    found.add(w);
  }
  return [...found];
}

function extractTurkishLeakage(text) {
  const found = new Set();
  const turkishWords = [
    'Giriş', 'Şifre', 'E-posta', 'Kaydet', 'İptal', 'Sil', 'Düzenle', 'Oluştur',
    'Ara', 'Filtre', 'Ayarlar', 'Kişiler', 'Şirketler', 'İlişkiler', 'Görevler',
    'Takvim', 'Notlar', 'Belgeler', 'Raporlar', 'Yeni', 'Erişim', 'Reddedildi',
    'Yükleniyor', 'Hata', 'Geri', 'İleri', 'Devam', 'Tamamla',
  ];
  for (const w of turkishWords) {
    if (text.includes(w)) found.add(w);
  }
  if (TURKISH_CHARS.test(text)) {
    const trMatches = text.match(/[A-Za-zçğıöşüÇĞİÖŞÜ]{3,}/g) || [];
    for (const m of trMatches) {
      if (TURKISH_CHARS.test(m) && m.length >= 4) found.add(m);
    }
  }
  return [...found];
}

async function analyzePage(page, route) {
  await page.waitForTimeout(2000);
  return page.evaluate(({ route, rawKeyPattern }) => {
    const bodyText = document.body?.innerText || '';
    const h1 = document.querySelector('h1')?.innerText?.trim() || null;
    const title = document.title || '';
    const rawKeys = [...new Set((bodyText.match(new RegExp(rawKeyPattern, 'g')) || []))];
    const objectObject = bodyText.includes('[object Object]');
    const accessDenied = /erişim reddedildi|access denied/i.test(bodyText);
    const accessDeniedVisible = !!document.querySelector('[class*="access"], [class*="denied"], [data-testid*="access-denied"]');
    const overlay = !!document.querySelector('[role="dialog"], [class*="overlay"], [class*="modal"][class*="open"], .modal:not([hidden])');
    const blank = bodyText.replace(/\s+/g, ' ').trim().length < 80;
    const main = document.querySelector('main') || document.body;
    const buttons = [...document.querySelectorAll('button, a.btn, [role="button"]')].map(el => el.innerText?.trim()).filter(Boolean);
    const headings = [...document.querySelectorAll('h1,h2,h3,h4,[class*="step"],[class*="wizard"]')].map(el => el.innerText?.trim()).filter(Boolean);
    const combobox = [...document.querySelectorAll('select, [role="combobox"]')].map(el => ({
      label: el.getAttribute('aria-label') || el.closest('label')?.innerText || '',
      value: el.value || el.innerText?.trim(),
    }));
    return {
      url: location.href,
      route,
      h1,
      title,
      bodySample: bodyText.slice(0, 1500),
      blank,
      overlay,
      accessDeniedStuck: accessDenied && !/giriş yap|sign in|login/i.test(bodyText),
      rawKeys,
      objectObject,
      buttons: buttons.slice(0, 30),
      headings: headings.slice(0, 20),
      combobox,
    };
  }, { route, rawKeyPattern: String.raw`\b(crm|activity|common)\.[a-zA-Z0-9_.]+` });
}

async function setLanguage(page, lang) {
  const label = lang === 'en' ? 'English' : 'Türkçe';
  const selectors = [
    'select:has(option)',
    '[role="combobox"]',
    'button:has-text("Dil")',
    'button:has-text("Language")',
  ];
  for (const sel of selectors) {
    const el = page.locator(sel).first();
    if (await el.count()) {
      try {
        if (await el.evaluate(e => e.tagName === 'SELECT')) {
          await el.selectOption({ label });
          await page.waitForTimeout(1500);
          return `select:${label}`;
        }
        await el.click();
        await page.waitForTimeout(500);
        await page.getByRole('option', { name: new RegExp(label, 'i') }).click({ timeout: 3000 });
        await page.waitForTimeout(1500);
        return `combobox:${label}`;
      } catch { /* try next */ }
    }
  }
  await page.evaluate((l) => {
    localStorage.setItem('locale', l);
    localStorage.setItem('language', l);
    localStorage.setItem('i18nextLng', l);
  }, lang === 'en' ? 'en' : 'tr');
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  return `localStorage:${lang}`;
}

async function login(page) {
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  if (!/login|giriş/i.test(page.url()) && !await page.locator('input[type="password"]').count()) {
    return { alreadyLoggedIn: true };
  }
  await page.fill('input[type="email"], input[name="email"]', 'superadmin@investhome.demo');
  await page.fill('input[type="password"], input[name="password"]', 'Demo123!');
  await page.click('button[type="submit"]');
  await page.waitForURL(u => !/login/i.test(u.pathname), { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2000);
  return { alreadyLoggedIn: false, url: page.url() };
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ locale: 'tr-TR' });
const page = await context.newPage();
const consoleErrors = [];
page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push({ text: msg.text(), url: page.url() }); });
page.on('pageerror', err => consoleErrors.push({ text: err.message, url: page.url(), type: 'pageerror' }));

const report = {
  routesTested: 0,
  perRoute: {},
  rawKeys: new Set(),
  englishLeakage: new Set(),
  accessDeniedFlash: [],
  brokenRoutes: [],
  relationshipCreateButtonLabel: null,
  wizardLabelsTR: {},
  objectObjectRoutes: [],
  englishPass: {},
  languageSwitchMethod: null,
  consoleErrors: [],
  summaryVerdict: '',
  mcpNote: 'cursor-ide-browser MCP tabs did not persist; Playwright fallback with login used',
};

try {
  await login(page);
  report.languageSwitchMethod = await setLanguage(page, 'tr');

  for (const route of ROUTES) {
    const consoleBefore = consoleErrors.length;
    try {
      await page.goto(`${BASE}${route}`, { waitUntil: 'networkidle', timeout: 45000 });
      const data = await analyzePage(page, route);
      const engLeak = extractEnglishLeakage(data.bodySample + ' ' + data.headings.join(' ') + ' ' + data.buttons.join(' '));
      data.rawKeys.forEach(k => report.rawKeys.add(k));
      engLeak.forEach(e => report.englishLeakage.add(e));
      if (data.objectObject) report.objectObjectRoutes.push(route);
      if (data.accessDeniedStuck) report.accessDeniedFlash.push(route);

      let status = 'OK';
      const notes = [];
      if (data.blank) { status = 'FAIL'; notes.push('blank page'); report.brokenRoutes.push(route); }
      if (data.rawKeys.length) { status = status === 'OK' ? 'WARN' : status; notes.push(`rawKeys: ${data.rawKeys.join(', ')}`); }
      if (engLeak.length) { status = status === 'OK' ? 'WARN' : status; notes.push(`english: ${engLeak.slice(0, 5).join(', ')}`); }
      if (data.objectObject) { status = 'FAIL'; notes.push('[object Object]'); }
      if (data.accessDeniedStuck) { status = 'FAIL'; notes.push('accessDenied stuck'); report.brokenRoutes.push(route); }
      if (/404|not found|sayfa bulunamadı/i.test(data.bodySample)) { status = 'FAIL'; notes.push('404/not found'); report.brokenRoutes.push(route); }

      const routeConsole = consoleErrors.slice(consoleBefore);
      if (routeConsole.length) notes.push(`consoleErrors: ${routeConsole.length}`);

      report.perRoute[route] = {
        status,
        url: data.url,
        h1: data.h1,
        title: data.title,
        blank: data.blank,
        overlay: data.overlay,
        accessDeniedStuck: data.accessDeniedStuck,
        rawKeys: data.rawKeys,
        englishLeakage: engLeak,
        consoleErrors: routeConsole,
        notes: notes.join('; ') || 'ok',
        bodySample: data.bodySample.slice(0, 400),
      };

      if (route === '/workspaces/crm/relationships') {
        const btn = data.buttons.find(b => /yeni|new|ilişki|relationship/i.test(b));
        report.relationshipCreateButtonLabel = btn || data.buttons.find(b => /\+|add|create/i.test(b)) || null;
      }
      if (route === '/workspaces/crm/relationships/new') {
        report.wizardLabelsTR = { headings: data.headings, buttons: data.buttons.slice(0, 15) };
      }
      if (route === '/dashboard/sales') {
        report.perRoute[route].isCRM = /crm|kişi|ilişki|müşteri/i.test(data.bodySample);
        report.perRoute[route].notes += `; Sales module (not CRM workspace): ${!report.perRoute[route].isCRM}`;
      }
    } catch (err) {
      report.perRoute[route] = { status: 'FAIL', notes: err.message };
      report.brokenRoutes.push(route);
    }
    report.routesTested++;
  }

  // English pass
  await setLanguage(page, 'en');
  for (const route of ['/workspaces/crm/dashboard', '/workspaces/crm/contacts', '/workspaces/crm/relationships/new']) {
    await page.goto(`${BASE}${route}`, { waitUntil: 'networkidle', timeout: 45000 });
    const data = await analyzePage(page, route);
    const trLeak = extractTurkishLeakage(data.bodySample + ' ' + data.headings.join(' '));
    report.englishPass[route] = {
      h1: data.h1,
      title: data.title,
      turkishLeakage: trLeak.slice(0, 20),
      rawKeys: data.rawKeys,
      status: trLeak.length === 0 && data.rawKeys.length === 0 ? 'OK' : 'WARN',
    };
  }
  await setLanguage(page, 'tr');

  report.consoleErrors = consoleErrors.slice(0, 50);
  report.brokenRoutes = [...new Set(report.brokenRoutes)];

  const failCount = Object.values(report.perRoute).filter(r => r.status === 'FAIL').length;
  const warnCount = Object.values(report.perRoute).filter(r => r.status === 'WARN').length;
  const rawKeyCount = report.rawKeys.size;
  const engCount = report.englishLeakage.size;

  if (failCount === 0 && rawKeyCount === 0 && engCount < 5) {
    report.summaryVerdict = 'PASS — Turkish CRM routes render with minimal i18n issues';
  } else if (failCount === 0) {
    report.summaryVerdict = `WARN — ${warnCount} routes with warnings; ${rawKeyCount} raw keys; ${engCount} English leakage tokens`;
  } else {
    report.summaryVerdict = `FAIL — ${failCount} broken routes; ${rawKeyCount} raw keys; review required`;
  }
} catch (err) {
  report.fatalError = err.message;
  report.summaryVerdict = `FAIL — crawl error: ${err.message}`;
}

await browser.close();

const out = {
  ...report,
  rawKeys: [...report.rawKeys].sort(),
  englishLeakage: [...report.englishLeakage].sort(),
};
console.log(JSON.stringify(out, null, 2));
