import { chromium } from 'playwright';
import { stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.join(__dirname, '..', 'artifacts', 'finance-g5');
const base = process.env.BASE_URL || 'http://localhost:3000';

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded' });
await page.locator('input[type="email"]').fill('superadmin@investhome.demo');
await page.locator('input[type="password"]').fill('Demo123!');
await page.locator('button[type="submit"]').click();
await page.waitForURL(/dashboard/, { timeout: 45_000 });

async function hydrate() {
  await page.waitForSelector('[data-testid="fin-g5-workspace"]', { timeout: 60_000 });
  await page.waitForFunction(
    () => {
      const ws = document.querySelector('[data-testid="fin-g5-workspace"]');
      if (!ws) return false;
      const t = ws.innerText.toLowerCase();
      if (t.includes('yükleniyor') || t.includes('loading finance')) return false;
      return /\$[\d.,]{3,}|₺[\d.,]{3,}/.test(ws.innerText);
    },
    { timeout: 120_000 },
  );
}

await context.addCookies([
  { name: 'investhome.locale', value: 'tr', url: base },
]);
await page.goto(`${base}/dashboard/finance`, { waitUntil: 'domcontentloaded' });
await hydrate();
await page.waitForFunction(() => /Finans & Hazine|Nakit Pozisyonu/i.test(document.body.innerText), {
  timeout: 60_000,
});
const trPath = path.join(outDir, '17-turkish.png');
await page.screenshot({ path: trPath, fullPage: false });
console.log('saved', trPath, (await stat(trPath)).size);

await context.addCookies([
  { name: 'investhome.locale', value: 'en', url: base },
]);
await page.goto(`${base}/dashboard/finance?view=cash`, { waitUntil: 'domcontentloaded' });
await hydrate();
await page.waitForFunction(() => /Finance & Treasury|Cash Position/i.test(document.body.innerText), {
  timeout: 60_000,
});
const enPath = path.join(outDir, '18-english.png');
await page.screenshot({ path: enPath, fullPage: false });
console.log('saved', enPath, (await stat(enPath)).size);

await browser.close();
