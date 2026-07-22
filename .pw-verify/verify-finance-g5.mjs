import { chromium } from 'playwright';

const base = process.env.BASE_URL || 'http://localhost:3000';
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

const views = [
  'executive',
  'cash',
  'accounts',
  'wires_in',
  'wires_out',
  'investor_payments',
  'vendor_payments',
  'ar',
  'ap',
  'treasury',
  'forecast',
  'budget',
  'approvals',
  'documents',
  'audit',
];

let passed = 0;
const results = [];

async function login() {
  await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded' });
  await page.locator('input[type="email"], input[name="email"]').first().fill('superadmin@investhome.demo');
  await page.locator('input[type="password"], input[name="password"]').first().fill('Demo123!');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/dashboard/, { timeout: 45_000 });
}

await login();

await page.goto(`${base}/dashboard/finance`, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('[data-testid="fin-g5-workspace"]', { timeout: 45_000 });
await page.waitForFunction(
  () => /\$[\d.,]{3,}/.test(document.querySelector('[data-testid="fin-g5-workspace"]')?.innerText || ''),
  { timeout: 90_000 },
);

for (const view of views) {
  try {
    const nav = page.locator(`[data-testid="fin-g5-nav-${view}"]`);
    await nav.scrollIntoViewIfNeeded();
    await nav.click();
    await page.waitForFunction(
      (id) => document.querySelector(`[data-testid="fin-g5-nav-${id}"]`)?.classList.contains('is-active'),
      view,
      { timeout: 20_000 },
    );
    await page.waitForTimeout(400);
    passed += 1;
    results.push({ view, ok: true });
    console.log('PASS', view);
  } catch (err) {
    results.push({ view, ok: false, error: String(err) });
    console.log('FAIL', view, err?.message || err);
  }
}

// TR/EN smoke
try {
  const langSelect = page.locator('select.dashboard__language-select').first();
  await langSelect.selectOption('tr');
  await page.waitForTimeout(1000);
  await page.goto(`${base}/dashboard/finance`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid="fin-g5-workspace"]', { timeout: 45_000 });
  await page.waitForFunction(
    () => /Finans & Hazine|Nakit Pozisyonu/i.test(document.querySelector('[data-testid="fin-g5-workspace"]')?.innerText || ''),
    { timeout: 60_000 },
  );
  const hasTr = true;
  await langSelect.selectOption('en');
  await page.waitForTimeout(1000);
  await page.goto(`${base}/dashboard/finance`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid="fin-g5-workspace"]', { timeout: 45_000 });
  await page.waitForFunction(
    () => /Finance & Treasury|Cash Position/i.test(document.querySelector('[data-testid="fin-g5-workspace"]')?.innerText || ''),
    { timeout: 60_000 },
  );
  const hasEn = true;
  console.log('I18N', { hasTr, hasEn });
  passed += 1;
  results.push({ view: 'i18n', ok: true });
} catch (err) {
  results.push({ view: 'i18n', ok: false, error: String(err) });
  console.log('FAIL i18n', err?.message || err);
}

await browser.close();
console.log(`RESULT ${passed}/16`);
console.log(JSON.stringify(results, null, 2));
if (passed < 16) process.exitCode = 1;
