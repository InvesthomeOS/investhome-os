import { chromium } from 'playwright';

const BASE = 'http://localhost:3000';
const result = {
  dashboard390: { scrollW: null, clientW: null, pass: false },
  crm390: { scrollW: null, clientW: null, pass: false },
  dashboard768: { scrollW: null, clientW: null, pass: false },
  dashboard1440: { scrollW: null, clientW: null, pass: false },
  marketingLabel: null,
  missingMessageGone: false,
};

const criticalConsole = [];
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext();
const page = await ctx.newPage();

page.on('console', (msg) => {
  const text = msg.text();
  if (['error', 'warning'].includes(msg.type()) && /MISSING_MESSAGE/i.test(text)) {
    criticalConsole.push(text);
  }
});

async function measure(width, height, path) {
  await page.setViewportSize({ width, height });
  await page.goto(`${BASE}${path}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  return page.evaluate(() => ({
    scrollW: document.documentElement.scrollWidth,
    clientW: document.documentElement.clientWidth,
  }));
}

await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' });
await page.fill('input[type="email"]', 'superadmin@investhome.demo');
await page.fill('input[type="password"]', 'Demo123!');
await page.click('button[type="submit"]');
await page.waitForTimeout(3000);

const langSelect = page.locator('.dashboard__language-select');
if (await langSelect.count()) {
  await langSelect.selectOption('tr');
  await page.waitForTimeout(1500);
}

const nav = await page.evaluate(() => {
  const links = [...document.querySelectorAll('aside a, nav a, [class*="sidebar"] a')];
  const m = links.find((a) => /marketing|pazarlama/i.test(a.textContent || '') || /marketing/i.test(a.getAttribute('href') || ''));
  return m?.textContent?.trim() || null;
});
result.marketingLabel = nav;

const before = criticalConsole.length;
await page.goto(`${BASE}/dashboard/investors`, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(2500);
result.missingMessageGone =
  !criticalConsole.slice(before).some((t) => /MISSING_MESSAGE.*navigation\.investors/i.test(t)) &&
  !criticalConsole.some((t) => /MISSING_MESSAGE.*navigation\.investors/i.test(t));

for (const [key, w, h, path] of [
  ['dashboard390', 390, 844, '/dashboard'],
  ['crm390', 390, 844, '/workspaces/crm/contacts'],
  ['dashboard768', 768, 900, '/dashboard'],
  ['dashboard1440', 1440, 900, '/dashboard'],
]) {
  const m = await measure(w, h, path);
  result[key] = { scrollW: m.scrollW, clientW: m.clientW, pass: m.scrollW <= m.clientW + 1 };
}

console.log(JSON.stringify(result, null, 2));
await browser.close();
