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

async function waitStable(page, ms = 1500) {
  await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => {});
  await page.waitForTimeout(ms);
}

async function pageState(page) {
  return page.evaluate(() => ({
    url: location.href,
    pathname: location.pathname,
    text: (document.body?.innerText || '').slice(0, 12000),
    h1: document.querySelector('h1')?.textContent?.trim() || null,
    navLinks: [...document.querySelectorAll('aside a, nav a, [class*="sidebar"] a')]
      .map((a) => (a.textContent || '').trim()).filter(Boolean).slice(0, 40),
    breadcrumbs: [...document.querySelectorAll('[class*="breadcrumb"] *, [aria-label*="breadcrumb" i] *')]
      .map((e) => (e.textContent || '').trim()).filter(Boolean).slice(0, 15),
    hasLoginForm: !!document.querySelector('input[type="email"], input[name="email"]'),
    lang: document.documentElement.lang,
    scrollW: document.documentElement.scrollWidth,
    clientW: document.documentElement.clientWidth,
    horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 5,
  }));
}

async function login(page, creds) {
  await page.context().clearCookies();
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await waitStable(page, 800);
  await page.fill('input[type="email"], input[name="email"]', creds.email);
  await page.fill('input[type="password"]', creds.password);
  await page.click('button[type="submit"]');
  await waitStable(page, 2500);
  const s = await pageState(page);
  return !s.hasLoginForm && !/login|giriş/i.test(s.pathname);
}

async function logout(page) {
  const btn = page.locator('.dashboard__logout, button:has-text("Çıkış"), button:has-text("Logout"), button:has-text("Log out")').first();
  if (await btn.count()) {
    await btn.click();
    await waitStable(page, 2000);
  } else {
    await page.context().clearCookies();
    await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' });
    await waitStable(page, 1000);
  }
}

async function setLocale(page, locale) {
  const toggle = page.locator('button, a').filter({ hasText: locale === 'tr' ? /^(TR|Türkçe)$/i : /^(EN|English)$/i }).first();
  if (await toggle.count()) {
    await toggle.click();
    await waitStable(page, 1000);
    return true;
  }
  const langBtn = page.locator('button, a').filter({ hasText: /^(TR|EN|Dil|Language)$/i }).first();
  if (await langBtn.count()) {
    await langBtn.click();
    await page.waitForTimeout(400);
    const pick = page.locator('button, a, li').filter({ hasText: locale === 'tr' ? /Türkçe|TR/i : /English|EN/i }).first();
    if (await pick.count()) await pick.click();
    await waitStable(page, 1000);
    return true;
  }
  return false;
}

function rawKeys(text) {
  const found = new Set();
  for (const re of [/MISSING_MESSAGE/g, /\bcrm\.[a-zA-Z0-9_.]+\b/g, /\bmarketing\.[a-zA-Z0-9_.]+\b/g]) {
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(text)) !== null) found.add(m[0]);
  }
  return [...found];
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const supplement = { dataPersistence: {}, roleMatrix: {}, i18n: {}, responsive: {} };

  // DATA PERSISTENCE
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    try {
      await login(page, ROLES.superadmin);
      await page.goto(`${BASE}/workspaces/crm/contacts`, { waitUntil: 'domcontentloaded' });
      await waitStable(page, 1500);
      let s = await pageState(page);
      let found = s.text.includes(CONTACT_NAME);

      if (!found) {
        await page.goto(`${BASE}/workspaces/crm/contacts/new`, { waitUntil: 'domcontentloaded' });
        await waitStable(page, 1500);
        const fields = page.locator('input:visible, textarea:visible');
        const n = await fields.count();
        let nameFilled = false;
        for (let i = 0; i < n; i++) {
          const el = fields.nth(i);
          const meta = `${await el.getAttribute('name') || ''}${await el.getAttribute('placeholder') || ''}${await el.getAttribute('aria-label') || ''}`;
          if (/name|ad|isim|full/i.test(meta)) { await el.fill(CONTACT_NAME); nameFilled = true; }
          if (/email|e-posta/i.test(meta)) await el.fill(`qa.final.20260719.${Date.now()}@investhome.demo`);
        }
        const save = page.getByRole('button', { name: /save|kaydet|create|oluştur|submit/i }).first();
        if (await save.count()) await save.click();
        await waitStable(page, 3500);
        supplement.dataPersistence.nameFieldFilled = nameFilled;
      }

      await page.goto(`${BASE}/workspaces/crm/contacts`, { waitUntil: 'domcontentloaded' });
      await waitStable(page, 2000);
      s = await pageState(page);
      const foundList = s.text.includes(CONTACT_NAME);
      await page.reload();
      await waitStable(page, 2000);
      s = await pageState(page);
      const foundRefresh = s.text.includes(CONTACT_NAME);

      supplement.dataPersistence = {
        pass: foundList && foundRefresh,
        contactCreatePersist: foundList && foundRefresh,
        foundAfterCreate: foundList,
        foundAfterRefresh: foundRefresh,
        usedExisting: found,
        contactName: CONTACT_NAME,
      };
    } catch (e) {
      supplement.dataPersistence = { pass: false, error: e.message };
    }
    await ctx.close();
  }

  // ROLE MATRIX
  supplement.roleMatrix = { pass: true, roles: {} };
  for (const [roleName, creds] of Object.entries(ROLES)) {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    supplement.roleMatrix.roles[roleName] = {};
    try {
      await login(page, creds);
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
        let pass = true;
        if (roleName === 'superadmin') pass = loaded && !denied;
        else if (roleName === 'sales') {
          if (key === 'admin' || key === 'marketing') pass = denied || loginRedirect;
          else pass = loaded && !denied;
        } else if (roleName === 'readonly') {
          if (key === 'admin' || key === 'marketing') pass = denied || loginRedirect;
          else if (key === 'crm') pass = loaded || denied;
          else pass = loaded && !denied;
        }
        supplement.roleMatrix.roles[roleName][key] = { pass, denied, loaded, pathname: st.pathname };
        if (!pass) supplement.roleMatrix.pass = false;
      }
    } catch (e) {
      supplement.roleMatrix.roles[roleName].error = e.message;
      supplement.roleMatrix.pass = false;
    }
    await ctx.close();
  }

  // i18n
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    supplement.i18n = { pass: true, tr: {}, en: {}, issues: [] };
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

      supplement.i18n.tr = {
        crmDashboard: { h1: trCrm.h1, rawKeys: rawKeys(trCrm.text), marketingLeak: /\bMarketing\b/.test(trCrm.text) },
        marketingSidebar: { labels: trMkt.navLinks.slice(0, 15), marketingLeak: trMkt.navLinks.some((l) => l === 'Marketing') || /\bMarketing\b/.test(trMkt.text) },
        investorBreadcrumbs: { breadcrumbs: trInv.breadcrumbs, rawKeys: rawKeys(trInv.text) },
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

      supplement.i18n.en = {
        crmDashboard: { h1: enCrm.h1, rawKeys: rawKeys(enCrm.text), turkishLeak: /\bPazarlama\b|\bKişiler\b|\bGiriş\b/.test(enCrm.text) },
        marketingSidebar: { labels: enMkt.navLinks.slice(0, 15), turkishLeak: enMkt.navLinks.some((l) => /Pazarlama|Kampanya|İçerik/i.test(l)) },
        investorBreadcrumbs: { breadcrumbs: enInv.breadcrumbs, rawKeys: rawKeys(enInv.text) },
      };

      if (supplement.i18n.tr.crmDashboard.marketingLeak) supplement.i18n.issues.push('TR: English "Marketing" in CRM area');
      if (supplement.i18n.tr.marketingSidebar.marketingLeak) supplement.i18n.issues.push('TR: English "Marketing" in sidebar');
      for (const loc of ['tr', 'en']) {
        for (const section of Object.values(supplement.i18n[loc])) {
          if (section.rawKeys?.length) supplement.i18n.issues.push(`${loc} raw keys: ${section.rawKeys.join(', ')}`);
        }
      }
      supplement.i18n.pass = supplement.i18n.issues.length === 0;
    } catch (e) {
      supplement.i18n = { pass: false, error: e.message };
    }
    await ctx.close();
  }

  // RESPONSIVE
  supplement.responsive = { pass: true, viewports: {} };
  {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
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
        supplement.responsive.viewports[width] = {
          dashboard: { overflow: dash.horizontalOverflow, scrollW: dash.scrollW, clientW: dash.clientW },
          crm: { overflow: crm.horizontalOverflow, scrollW: crm.scrollW, clientW: crm.clientW },
        };
        if (overflow390) supplement.responsive.pass = false;
      }
    } catch (e) {
      supplement.responsive = { pass: false, error: e.message };
    }
    await ctx.close();
  }

  fs.writeFileSync(path.join(OUT, 'supplement.json'), JSON.stringify(supplement, null, 2));
  console.log(JSON.stringify(supplement, null, 2));
  await browser.close();
})();
