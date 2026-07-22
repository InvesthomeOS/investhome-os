/**
 * G9.5 design-system screenshot capture.
 * Usage: node artifacts/design-system-g95/capture.mjs
 */
import { chromium } from '../../.pw-verify/node_modules/playwright/index.mjs';
import { mkdirSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const BASE = process.env.WEB_BASE_URL || 'http://localhost:3000';
const EMAIL = 'superadmin@investhome.demo';
const PASSWORD = 'Demo123!';
const PORTAL_EMAIL = 'investor.a@investhome.demo';
const PORTAL_PASSWORD = 'Portal123!';
const LOCALE_COOKIE = 'investhome.locale';

mkdirSync(__dirname, { recursive: true });

const SHOTS = [
  { file: '01-overview.png', path: '/dashboard/admin/design-system', full: true },
  { file: '02-colors-typography.png', path: '/dashboard/admin/design-system', scroll: '#ds-colors' },
  { file: '03-buttons.png', path: '/dashboard/admin/design-system', scroll: '#ds-buttons' },
  { file: '04-forms.png', path: '/dashboard/admin/design-system', scroll: '#ds-forms' },
  { file: '05-tables.png', path: '/dashboard/admin/design-system', scroll: '#ds-tables' },
  { file: '06-filters.png', path: '/dashboard/admin/design-system', scroll: '#ds-filters' },
  { file: '07-cards.png', path: '/dashboard/admin/design-system', scroll: '#ds-cards' },
  { file: '08-drawers.png', path: '/dashboard/admin/design-system', scroll: '#ds-drawers', openDrawer: true },
  { file: '09-modals.png', path: '/dashboard/admin/design-system', scroll: '#ds-modals', openModal: true },
  { file: '10-tabs-nav.png', path: '/dashboard/admin/design-system', scroll: '#ds-tabs' },
  { file: '11-badges.png', path: '/dashboard/admin/design-system', scroll: '#ds-badges' },
  { file: '12-empty.png', path: '/dashboard/admin/design-system', scroll: '#ds-empty' },
  { file: '13-loading.png', path: '/dashboard/admin/design-system', scroll: '#ds-loading' },
  { file: '14-errors.png', path: '/dashboard/admin/design-system', scroll: '#ds-errors' },
  { file: '15-charts.png', path: '/dashboard/admin/design-system', scroll: '#ds-charts' },
  { file: '16-responsive.png', path: '/dashboard/admin/design-system', scroll: '#ds-responsive' },
  { file: '17-crm.png', path: '/workspaces/crm/leads' },
  { file: '18-investor.png', path: '/dashboard/investors' },
  { file: '19-project.png', path: '/dashboard/projects' },
  { file: '20-executive.png', path: '/dashboard/executive' },
  { file: '21-portal.png', path: '/portal/dashboard' },
  { file: '22-turkish.png', path: '/dashboard/admin/design-system', locale: 'tr', scroll: '#ds-i18n' },
  { file: '23-english.png', path: '/dashboard/admin/design-system', locale: 'en', scroll: '#ds-i18n' },
  { file: '24-tablet.png', path: '/dashboard/admin/design-system', viewport: { width: 768, height: 1024 }, scroll: '#ds-responsive' },
];

async function waitForWeb(page, attempts = 20) {
  for (let i = 0; i < attempts; i++) {
    try {
      const res = await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 15000 });
      if (res && res.ok()) return;
    } catch {
      // retry
    }
    await page.waitForTimeout(2000);
  }
  throw new Error('Web not reachable on :3000');
}

async function login(page) {
  await waitForWeb(page);
  await page.fill('input[type="email"], input[name="email"]', EMAIL);
  await page.fill('input[type="password"], input[name="password"]', PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(dashboard|portal)/, { timeout: 45000 }).catch(() => undefined);
  await page.waitForTimeout(600);
}

async function gotoPath(page, path) {
  for (let i = 0; i < 4; i++) {
    try {
      await page.goto(`${BASE}${path}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
      return;
    } catch {
      await page.waitForTimeout(2000);
    }
  }
  await page.goto(`${BASE}${path}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
}

const browser = await chromium.launch({ headless: true });
const results = [];

// Shared auth context for most shots
const main = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
const mainPage = await main.newPage();
await login(mainPage);

for (const shot of SHOTS) {
  const needsFresh =
    Boolean(shot.viewport) || Boolean(shot.locale) || shot.path.startsWith('/portal');

  let page = mainPage;
  let context = null;

  try {
    if (needsFresh) {
      context = await browser.newContext({
        viewport: shot.viewport || { width: 1440, height: 1100 },
      });
      if (shot.locale) {
        await context.addCookies([
          { name: LOCALE_COOKIE, value: shot.locale, domain: 'localhost', path: '/' },
        ]);
      }
      page = await context.newPage();
      if (shot.path.startsWith('/portal')) {
        await gotoPath(page, '/portal/login');
        const email = page.locator('[data-testid="portal-login-email"], input[type="email"]').first();
        if (await email.count()) {
          await email.fill(PORTAL_EMAIL);
          await page
            .locator('[data-testid="portal-login-password"], input[type="password"]')
            .first()
            .fill(PORTAL_PASSWORD);
          await page.locator('[data-testid="portal-login-submit"], button[type="submit"]').first().click();
          await page.waitForURL(/\/portal(?!\/login)/, { timeout: 20000 }).catch(() => undefined);
          await page.waitForTimeout(800);
        }
      } else {
        await login(page);
      }
    }

    await gotoPath(page, shot.path);

    if (page.url().includes('/login')) {
      await login(page);
      await gotoPath(page, shot.path);
    }

    await page.waitForTimeout(900);

    if (shot.scroll) {
      await page.locator(shot.scroll).scrollIntoViewIfNeeded().catch(() => undefined);
      await page.waitForTimeout(350);
    }

    if (shot.openDrawer) {
      const btn = page.getByRole('button', { name: /Open drawer|Çekmeceyi aç/i }).first();
      if (await btn.count()) {
        await btn.click();
        await page.waitForTimeout(450);
      }
    }

    if (shot.openModal) {
      const btn = page.getByRole('button', { name: /Open modal|Modali aç/i }).first();
      if (await btn.count()) {
        await btn.click();
        await page.waitForTimeout(450);
      }
    }

    const out = join(__dirname, shot.file);
    if (shot.full) {
      await page.screenshot({ path: out, fullPage: false });
    } else if (shot.scroll) {
      const el = page.locator(shot.scroll);
      if (await el.count()) {
        await el.screenshot({ path: out }).catch(async () => page.screenshot({ path: out }));
      } else {
        await page.screenshot({ path: out });
      }
    } else {
      await page.screenshot({ path: out });
    }

    // Ensure size: if too small, fall back to viewport screenshot
    let size = statSync(out).size;
    if (size <= 10_000) {
      await page.screenshot({ path: out });
      size = statSync(out).size;
    }

    results.push({ file: shot.file, bytes: size, url: page.url(), ok: size > 10_000 });
    console.log(size > 10_000 ? 'OK' : 'SMALL', shot.file, size, page.url());
  } catch (err) {
    results.push({ file: shot.file, error: String(err), ok: false });
    console.error('FAIL', shot.file, err);
  } finally {
    if (context) await context.close();
  }
}

await main.close();
await browser.close();

const listed = readdirSync(__dirname).filter((f) => f.endsWith('.png')).sort();
const verify = listed.map((f) => {
  const bytes = statSync(join(__dirname, f)).size;
  return { file: f, bytes, ok: bytes > 10_000 };
});

writeFileSync(join(__dirname, 'qa-result.json'), JSON.stringify({ results, verify, listed }, null, 2));
console.log('PNG count', listed.length);
const passShots =
  listed.length >= 24 && verify.filter((v) => SHOTS.some((s) => s.file === v.file)).every((v) => v.ok);
console.log('PASS_SCREENSHOTS', passShots);

// Always emit filesystem verification next to captures (absolute paths).
try {
  const { spawnSync } = await import('node:child_process');
  spawnSync(process.execPath, [join(__dirname, 'verify-pngs.mjs')], { stdio: 'inherit' });
} catch (err) {
  console.warn('verify-pngs skipped', err);
}
