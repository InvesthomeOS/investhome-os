import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
const logs = [];
page.on('console', (m) => logs.push(`[${m.type()}] ${m.text()}`));
page.on('response', (r) => {
  if (r.url().includes('/auth') || r.status() >= 400) {
    logs.push(`RESP ${r.status()} ${r.url()}`);
  }
});

await page.goto('http://localhost:3000/login', { waitUntil: 'networkidle', timeout: 90000 });
await page.locator('input[type=email]').fill('superadmin@investhome.demo');
await page.locator('input[type=password]').fill('Demo123!');
page.on('request', (r) => {
  if (r.url().includes('/auth')) logs.push(`REQ ${r.method()} ${r.url()}`);
});
await page.locator('button[type=submit]').click();
await page.waitForTimeout(8000);
console.log('URL', page.url());
console.log('BODY', (await page.locator('body').innerText()).slice(0, 800));
console.log('LOGS\n', logs.join('\n'));
await browser.close();
