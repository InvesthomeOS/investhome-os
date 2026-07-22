import { chromium } from 'playwright';

const BASE = 'http://localhost:3000';
const EMAIL = 'superadmin@investhome.demo';
const PASSWORD = 'Demo123!';

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
        id: el.id || null,
        classes: el.className && typeof el.className === 'string' ? el.className.slice(0, 120) : null,
        overflowPx: Math.round(maxOverflow * 10) / 10,
        rect: {
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          width: Math.round(rect.width),
        },
        scrollWidth: el.scrollWidth,
        clientWidth: el.clientWidth,
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

  return {
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    bodyScrollWidth: document.body.scrollWidth,
    offenders: unique.slice(0, 25),
  };
}

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);
  const email = page.locator('input[type="email"], input[name="email"]').first();
  const password = page.locator('input[type="password"]').first();
  await email.fill(EMAIL);
  await password.fill(PASSWORD);
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(2000);
}

async function inspect(page, path) {
  await page.goto(`${BASE}${path}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2500);
  return page.evaluate(findOverflowElements);
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
const page = await context.newPage();

try {
  await login(page);
  const dashboard = await inspect(page, '/dashboard');
  console.log('\n=== /dashboard @ 390px ===');
  console.log(JSON.stringify(dashboard, null, 2));

  const contacts = await inspect(page, '/workspaces/crm/contacts');
  console.log('\n=== /workspaces/crm/contacts @ 390px ===');
  console.log(JSON.stringify(contacts, null, 2));
} catch (err) {
  console.error('ERROR:', err.message);
  process.exitCode = 1;
} finally {
  await browser.close();
}
