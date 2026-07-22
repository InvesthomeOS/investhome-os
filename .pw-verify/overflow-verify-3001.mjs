import { chromium } from 'playwright';

const BASE = process.env.BASE || 'http://localhost:3001';

function findOverflowElements() {
  const docW = document.documentElement.clientWidth;
  const offenders = [];
  for (const el of document.querySelectorAll('*')) {
    const rect = el.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) continue;
    const style = getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') continue;
    const overflowRight = rect.right - docW;
    const overflowLeft = -rect.left;
    const maxOverflow = Math.max(overflowRight, overflowLeft);
    if (maxOverflow > 1) {
      offenders.push({
        tag: el.tagName.toLowerCase(),
        classes: el.className && typeof el.className === 'string' ? el.className.slice(0, 100) : null,
        overflowPx: Math.round(maxOverflow * 10) / 10,
        rect: { left: Math.round(rect.left), right: Math.round(rect.right), width: Math.round(rect.width) },
      });
    }
  }
  offenders.sort((a, b) => b.overflowPx - a.overflowPx);
  const seen = new Set();
  const unique = [];
  for (const o of offenders) {
    const key = `${o.tag}.${o.classes}`;
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(o);
  }
  const actions = document.querySelector('.dashboard__header-actions');
  const cs = actions ? getComputedStyle(actions) : null;
  return {
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    actionsStyles: cs ? { flexWrap: cs.flexWrap, flexShrink: cs.flexShrink, maxWidth: cs.maxWidth } : null,
    offenders: unique.slice(0, 10),
  };
}

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);
  await page.locator('input[type="email"]').first().fill('superadmin@investhome.demo');
  await page.locator('input[type="password"]').first().fill('Demo123!');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(3000);
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
const page = await context.newPage();
await login(page);

for (const path of ['/dashboard', '/workspaces/crm/contacts']) {
  await page.goto(`${BASE}${path}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  const result = await page.evaluate(findOverflowElements);
  console.log(`\n=== ${path} ===`);
  console.log(JSON.stringify(result, null, 2));
}
await browser.close();
