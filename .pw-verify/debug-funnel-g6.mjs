import { chromium } from 'playwright';

const base = 'http://localhost:3000';
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('pageerror', (e) => console.log('PAGEERROR', e.message));
page.on('console', (m) => {
  if (m.type() === 'error') console.log('CONSOLE', m.text());
});

await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded' });
await page.locator('input[type="email"], input[name="email"]').first().fill('superadmin@investhome.demo');
await page.locator('input[type="password"], input[name="password"]').first().fill('Demo123!');
await page.locator('button[type="submit"]').first().click();
await page.waitForURL(/dashboard/, { timeout: 45_000 });
await page.goto(`${base}/dashboard/marketing?view=funnel`, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(6000);
const html = await page.evaluate(() => ({
  hasWorkspace: Boolean(document.querySelector('[data-testid="mkt-g6-workspace"]')),
  hasFunnel: Boolean(document.querySelector('[data-testid="mkt-g6-funnel"]')),
  hasLoading: Boolean(document.querySelector('[data-testid="mkt-g6-loading"]')),
  bodySnippet: document.querySelector('.mkt-g6__body')?.innerText?.slice(0, 800) ?? null,
  activeNav: document.querySelector('.mkt-g6__nav-btn.is-active')?.getAttribute('data-testid'),
  url: location.href,
}));
console.log(JSON.stringify(html, null, 2));
await browser.close();
