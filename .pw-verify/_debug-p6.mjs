import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const OUT = path.resolve('C:/Users/eminb/Projects/investhome-os/tmp-browser-verify-output/product-polish-p6');
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
const errors = [];
page.on('console', (m) => {
  if (m.type() === 'error') errors.push(m.text());
});
page.on('pageerror', (e) => errors.push(String(e)));

await page.goto('http://localhost:3000/login', { waitUntil: 'domcontentloaded', timeout: 90000 });
await page.locator('input[type=email]').fill('superadmin@investhome.demo');
await page.locator('input[type=password]').fill('Demo123!');
await page.locator('button[type=submit]').click();
await page.waitForURL(/\/dashboard/, { timeout: 90000 });
await page.waitForTimeout(2000);

const nav = await page.evaluate(() =>
  [...document.querySelectorAll('.dashboard-shell__nav-link')].map((a) => ({
    text: (a.textContent || '').trim(),
    href: a.getAttribute('href'),
  })),
);
console.log('NAV', JSON.stringify(nav, null, 2));

await page.goto('http://localhost:3000/dashboard/ai', { waitUntil: 'networkidle', timeout: 90000 }).catch(() => {});
await page.waitForTimeout(2500);
console.log('URL', page.url());
const text = await page.locator('body').innerText();
console.log('BODY', text.slice(0, 1200));
console.log('ERRORS', errors.slice(0, 20));
await page.screenshot({ path: path.join(OUT, 'debug-ai.png'), fullPage: true });
await browser.close();
