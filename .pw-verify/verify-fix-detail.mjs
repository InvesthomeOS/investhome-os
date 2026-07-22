import { chromium } from 'playwright';

const BASE = 'http://localhost:3001';
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
await page.goto(`${BASE}/login`);
await page.waitForTimeout(1500);
await page.locator('input[type="email"]').first().fill('superadmin@investhome.demo');
await page.locator('input[type="password"]').first().fill('Demo123!');
await page.locator('button[type="submit"]').first().click();
await page.waitForTimeout(3000);
await page.goto(`${BASE}/dashboard`, { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);

const info = await page.evaluate(() => ({
  url: location.pathname,
  hasActions: !!document.querySelector('.dashboard__header-actions'),
  scrollWidth: document.documentElement.scrollWidth,
  clientWidth: document.documentElement.clientWidth,
  actions: (() => {
    const el = document.querySelector('.dashboard__header-actions');
    if (!el) return null;
    const cs = getComputedStyle(el);
    return { flexWrap: cs.flexWrap, flexShrink: cs.flexShrink, maxWidth: cs.maxWidth, width: cs.width };
  })(),
  themeLabel: (() => {
    const el = document.querySelector('.app-header__theme-label');
    return el ? getComputedStyle(el).display : null;
  })(),
}));
console.log(JSON.stringify(info, null, 2));
await browser.close();
