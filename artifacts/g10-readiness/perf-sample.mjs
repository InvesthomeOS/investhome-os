import { chromium } from '../../.pw-verify/node_modules/playwright/index.mjs';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BASE = 'http://localhost:3000';
const routes = [
  '/dashboard',
  '/dashboard/finance',
  '/dashboard/investors',
  '/dashboard/marketing',
  '/workspaces/crm/dashboard',
];
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded' });
await page.fill('input[type="email"], input[name="email"]', 'superadmin@investhome.demo');
await page.fill('input[type="password"]', 'Demo123!');
await page.click('button[type="submit"]');
await page.waitForURL(/\/dashboard/, { timeout: 30000 });
const results = [];
for (const route of routes) {
  const t0 = Date.now();
  await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(1500);
  const metrics = await page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation')[0];
    const paints = performance.getEntriesByType('paint');
    const issues = [];
    if (!document.querySelector('main, [role="main"]')) issues.push('missing_main');
    if (!document.querySelector('h1, [role="heading"][aria-level="1"]')) issues.push('missing_h1');
    const images = [...document.querySelectorAll('img')];
    if (images.some((img) => !img.hasAttribute('alt'))) issues.push('img_missing_alt');
    return {
      ttfb: nav ? Math.round(nav.responseStart - nav.requestStart) : null,
      domContentLoaded: nav ? Math.round(nav.domContentLoadedEventEnd - nav.startTime) : null,
      load: nav ? Math.round(nav.loadEventEnd - nav.startTime) : null,
      fcp:
        Math.round(paints.find((p) => p.name === 'first-contentful-paint')?.startTime || 0) ||
        null,
      a11yQuick: issues,
      lang: document.documentElement.lang || null,
    };
  });
  results.push({ route, wallMs: Date.now() - t0, ...metrics });
}
fs.writeFileSync(
  path.join(__dirname, 'logs', 'perf-navigation.json'),
  JSON.stringify({ timestamp: new Date().toISOString(), results }, null, 2),
);
console.log(JSON.stringify(results, null, 2));
await browser.close();
