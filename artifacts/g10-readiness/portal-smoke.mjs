import { chromium } from '../../.pw-verify/node_modules/playwright/index.mjs';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const out = [];
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
page.on('console', (m) => {
  if (m.type() === 'error') out.push('console:' + m.text());
});
page.on('pageerror', (e) => out.push('pageerror:' + String(e)));

try {
  await page.goto('http://localhost:3000/portal/login', {
    waitUntil: 'domcontentloaded',
    timeout: 60000,
  });
  await page.fill('[data-testid=portal-login-email]', 'investor.a@investhome.demo');
  await page.fill('[data-testid=portal-login-password]', 'Portal123!');
  await page.click('[data-testid=portal-login-submit]');
  await page.waitForURL(/\/portal(?!\/login)/, { timeout: 30000 });
  await page.waitForTimeout(2000);
  out.push('url=' + page.url());
  const body = await page.locator('body').innerText();
  out.push('body=' + body.slice(0, 400).replace(/\n/g, ' | '));
  await page.screenshot({
    path: path.join(__dirname, 'screenshots', 'portal-after-login-debug.png'),
  });

  for (const r of ['/portal', '/portal/portfolio', '/portal/documents', '/portal/account', '/portal/notifications']) {
    try {
      const res = await page.goto('http://localhost:3000' + r, {
        waitUntil: 'domcontentloaded',
        timeout: 30000,
      });
      out.push(r + ' => ' + res?.status() + ' ' + page.url());
      await page.screenshot({
        path: path.join(__dirname, 'screenshots', 'portal' + r.replace(/\//g, '_') + '.png'),
      });
    } catch (e) {
      out.push(r + ' ERROR ' + String(e).slice(0, 240));
    }
  }
} catch (e) {
  out.push('FATAL ' + String(e));
}

fs.writeFileSync(path.join(__dirname, 'logs', 'portal-smoke.txt'), out.join('\n'));
console.log(out.join('\n'));
await browser.close();
process.exit(out.some((l) => l.includes('ERROR') || l.includes('FATAL') || /=> 404/.test(l)) ? 1 : 0);
