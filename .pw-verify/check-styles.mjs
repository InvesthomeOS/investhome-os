import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
await page.goto('http://localhost:3000/login');
await page.waitForTimeout(1500);
await page.locator('input[type="email"]').first().fill('superadmin@investhome.demo');
await page.locator('input[type="password"]').first().fill('Demo123!');
await page.locator('button[type="submit"]').first().click();
await page.waitForTimeout(3000);
await page.goto('http://localhost:3000/dashboard', { waitUntil: 'networkidle' });
await page.waitForTimeout(2000);

const styles = await page.evaluate(() => {
  const el = document.querySelector('.dashboard__header-actions');
  if (!el) return { error: 'no element' };
  const cs = getComputedStyle(el);
  const themeLabel = document.querySelector('.app-header__theme-label');
  return {
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    actions: {
      flexWrap: cs.flexWrap,
      flexShrink: cs.flexShrink,
      maxWidth: cs.maxWidth,
      width: cs.width,
      minWidth: cs.minWidth,
    },
    themeLabelDisplay: themeLabel ? getComputedStyle(themeLabel).display : null,
    appHeader: (() => {
      const h = document.querySelector('.app-header');
      const cs2 = h ? getComputedStyle(h) : null;
      return cs2 ? { flexDirection: cs2.flexDirection, overflowX: cs2.overflowX } : null;
    })(),
  };
});
console.log(JSON.stringify(styles, null, 2));
await browser.close();
