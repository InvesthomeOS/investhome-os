import { chromium } from 'playwright';

const BASE = 'http://localhost:3000';
const result = {
  marketingLabel: null,
  missingMessageGone: false,
  breadcrumbLabel: null,
  localeSwitchOk: false,
  overflow390: { scrollW: null, clientW: null, pass: false },
  forecastingOk: false,
  remainingCriticalConsoleErrors: [],
};

const criticalConsole = [];
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();

page.on('console', (msg) => {
  const text = msg.text();
  if (['error', 'warning'].includes(msg.type())) {
    if (!/favicon|hydration|devtools|source map|ResizeObserver|chunk|React DevTools/i.test(text)) {
      criticalConsole.push(text);
    }
  }
});
page.on('pageerror', (err) => criticalConsole.push(err.message));

await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' });
await page.fill('input[type="email"]', 'superadmin@investhome.demo');
await page.fill('input[type="password"]', 'Demo123!');
await page.click('button[type="submit"]');
await page.waitForTimeout(3000);

const langSelect = page.locator('.dashboard__language-select');
if (await langSelect.count()) {
  await langSelect.selectOption('tr');
  await page.waitForTimeout(2000);
}

const navText = await page.evaluate(() => {
  const links = [...document.querySelectorAll('aside a, nav a, [class*="sidebar"] a')];
  const marketing = links.find(
    (a) => /marketing|pazarlama/i.test(a.textContent || '') || /marketing/i.test(a.getAttribute('href') || ''),
  );
  return { marketingText: marketing?.textContent?.trim() || null };
});
result.marketingLabel = navText.marketingText;

const beforeInvestors = criticalConsole.length;
await page.goto(`${BASE}/dashboard/investors`, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(2500);
const investorState = await page.evaluate(() => {
  const breadcrumbs = [...document.querySelectorAll('[class*="breadcrumb"] *, [aria-label*="breadcrumb" i] *')]
    .map((e) => (e.textContent || '').trim())
    .filter(Boolean);
  return { breadcrumbs };
});
const investorsConsole = criticalConsole.slice(beforeInvestors);
result.missingMessageGone =
  !investorsConsole.some((t) => /MISSING_MESSAGE.*navigation\.investors/i.test(t)) &&
  !criticalConsole.some((t) => /MISSING_MESSAGE.*navigation\.investors/i.test(t));
result.breadcrumbLabel =
  investorState.breadcrumbs.find((b) => /yatırımcılar/i.test(b)) ||
  investorState.breadcrumbs.find((b) => /yatırımcı|investor/i.test(b)) ||
  investorState.breadcrumbs.join(' > ') ||
  null;

await page.selectOption('.dashboard__language-select', 'en');
await page.waitForTimeout(2000);
await page.goto(`${BASE}/workspaces/crm/contacts`, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(2000);
const enH1 = (await page.locator('h1').first().textContent()) || '';
await page.selectOption('.dashboard__language-select', 'tr');
await page.waitForTimeout(2000);
await page.goto(`${BASE}/workspaces/crm/contacts`, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(1500);
const trH1 = (await page.locator('h1').first().textContent()) || '';
result.localeSwitchOk = /contacts/i.test(enH1) && /kişiler/i.test(trH1);

await page.setViewportSize({ width: 390, height: 844 });
await page.goto(`${BASE}/dashboard`, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(2000);
const overflow = await page.evaluate(() => ({
  scrollW: document.documentElement.scrollWidth,
  clientW: document.documentElement.clientWidth,
}));
result.overflow390 = {
  scrollW: overflow.scrollW,
  clientW: overflow.clientW,
  pass: overflow.scrollW <= overflow.clientW + 5,
};

await page.setViewportSize({ width: 1440, height: 900 });
await page.goto(`${BASE}/workspaces/marketing/forecasting`, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(2000);
result.forecastingOk = /\/workspaces\/marketing\/ai\/predictions/.test(page.url());

result.remainingCriticalConsoleErrors = [
  ...new Set(criticalConsole.filter((t) => !/401|Unauthorized|Failed to load resource/i.test(t))),
];

console.log(JSON.stringify(result, null, 2));
await browser.close();
