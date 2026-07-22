import { chromium } from 'playwright';

const base = 'http://localhost:3000';
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext();
const page = await context.newPage();

const marketingRes = [];
page.on('response', async (res) => {
  const url = res.url();
  if (url.includes('/marketing/')) {
    marketingRes.push({ url: url.slice(0, 120), status: res.status() });
  }
});

await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded' });
await page.locator('input[type="email"]').first().fill('superadmin@investhome.demo');
await page.locator('input[type="password"]').first().fill('Demo123!');
await page.locator('button[type="submit"]').first().click();
await page.waitForURL(/dashboard/, { timeout: 45_000 });

await page.goto(`${base}/dashboard/marketing?view=campaigns`, { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => !document.querySelector('[data-testid="mkt-g6-loading"]'), null, {
  timeout: 60_000,
});
await page.waitForTimeout(2000);

const ui = await page.evaluate(() => ({
  campaigns: Boolean(document.querySelector('[data-testid="mkt-g6-campaigns"]')),
  rows: document.querySelectorAll('[data-testid^="mkt-g6-campaign-row-"]').length,
  denied: document.body.innerText.includes('permission') || document.body.innerText.includes('izin'),
  subtitle: document.querySelector('.mkt-g6__subtitle')?.textContent ?? null,
  tableText: document.querySelector('[data-testid="mkt-g6-campaign-table"]')?.innerText?.slice(0, 400) ?? null,
}));

console.log('UI', JSON.stringify(ui, null, 2));
console.log('MARKETING_RES', JSON.stringify(marketingRes.slice(0, 30), null, 2));

// Compare with legacy workspace campaigns page
await page.goto(`${base}/workspaces/marketing/campaigns`, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(5000);
const legacy = await page.evaluate(() => document.body.innerText.slice(0, 500));
console.log('LEGACY', legacy);

await browser.close();
