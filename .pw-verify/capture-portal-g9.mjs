import { chromium } from 'playwright';
import { mkdir, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.resolve(__dirname, '../artifacts/portal-g9');
await mkdir(outDir, { recursive: true });

const base = process.env.BASE_URL || 'http://localhost:3000';
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

async function login(email = 'investor.a@investhome.demo', password = 'Portal123!') {
  await page.goto(`${base}/portal/login`, { waitUntil: 'domcontentloaded' });
  await page.getByTestId('portal-login-email').fill(email);
  await page.getByTestId('portal-login-password').fill(password);
  await page.getByTestId('portal-login-submit').click();
  await page.waitForSelector('[data-testid="portal-shell"]', { timeout: 45_000 });
  await page.waitForTimeout(800);
}

async function gotoRetry(url, attempts = 4) {
  let lastErr;
  for (let i = 0; i < attempts; i += 1) {
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45_000 });
      return;
    } catch (err) {
      lastErr = err;
      console.warn('goto retry', i + 1, url, String(err?.message || err));
      await page.waitForTimeout(1500);
    }
  }
  throw lastErr;
}

async function shot(name, url, setup) {
  if (url) await gotoRetry(url);
  if (setup) await setup();
  await page.waitForTimeout(1000);
  const filePath = path.join(outDir, name);
  await page.screenshot({ path: filePath, fullPage: false });
  console.log('saved', filePath);
}

await login();

await shot('01-dashboard.png', `${base}/portal`);
await shot('02-portfolio.png', `${base}/portal/portfolio`);
await shot('03-project-detail.png', `${base}/portal/projects/proj-nisantasi`, async () => {
  await page.waitForSelector('[data-testid="portal-project-detail"]', { timeout: 30_000 });
  const photos = page.getByTestId('portal-project-tab-photos');
  if (await photos.isVisible().catch(() => false)) {
    await photos.click();
    await page.waitForTimeout(400);
  }
});
await shot('04-reservations.png', `${base}/portal/reservations`);
await shot('05-contracts.png', `${base}/portal/contracts`);
await shot('06-payments.png', `${base}/portal/payments`);
await shot('07-rental-income.png', `${base}/portal/rental-income`);
await shot('08-documents.png', `${base}/portal/documents`);
await shot('09-reports.png', `${base}/portal/reports`);
await shot('10-messages.png', `${base}/portal/messages`);
await shot('11-notifications.png', `${base}/portal/notifications`);
await shot('12-account-security.png', `${base}/portal/account`);

await page.setViewportSize({ width: 820, height: 1100 });
await shot('13-tablet.png', `${base}/portal/portfolio`);

await page.setViewportSize({ width: 1440, height: 900 });
await page.goto(`${base}/portal`, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('[data-testid="portal-shell"]', { timeout: 30_000 });
const trBtn = page.getByTestId('portal-lang').getByRole('button', { name: 'TR' });
if (await trBtn.isVisible().catch(() => false)) {
  await trBtn.click();
  await page.waitForTimeout(700);
}
await page.screenshot({ path: path.join(outDir, '14-turkish.png'), fullPage: false });
console.log('saved', path.join(outDir, '14-turkish.png'));

const enBtn = page.getByTestId('portal-lang').getByRole('button', { name: 'EN' });
if (await enBtn.isVisible().catch(() => false)) {
  await enBtn.click();
  await page.waitForTimeout(700);
}
await page.screenshot({ path: path.join(outDir, '15-english.png'), fullPage: false });
console.log('saved', path.join(outDir, '15-english.png'));

await browser.close();

const required = [
  '01-dashboard.png',
  '02-portfolio.png',
  '03-project-detail.png',
  '04-reservations.png',
  '05-contracts.png',
  '06-payments.png',
  '07-rental-income.png',
  '08-documents.png',
  '09-reports.png',
  '10-messages.png',
  '11-notifications.png',
  '12-account-security.png',
  '13-tablet.png',
  '14-turkish.png',
  '15-english.png',
];

const sizes = {};
let ok = true;
for (const name of required) {
  const full = path.join(outDir, name);
  const s = await stat(full);
  sizes[name] = s.size;
  if (s.size <= 10_000) {
    ok = false;
    console.error('TOO_SMALL', name, s.size);
  } else {
    console.log('OK', name, s.size);
  }
}

await writeFile(path.join(outDir, 'sizes-verified.json'), JSON.stringify({ ok, sizes, outDir }, null, 2));
console.log('sizes-verified.json written to', outDir);
if (!ok) process.exit(1);
console.log('done');
