import { chromium } from 'playwright';
import { mkdir, stat, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const outDir = path.join(repoRoot, 'artifacts', 'finance-g5');
await mkdir(outDir, { recursive: true });

const REQUIRED = [
  '01-executive-dashboard.png',
  '02-cash-position.png',
  '03-bank-accounts.png',
  '04-incoming-wires.png',
  '05-outgoing-wires.png',
  '06-investor-payments.png',
  '07-vendor-payments.png',
  '08-ar.png',
  '09-ap.png',
  '10-treasury.png',
  '11-forecast.png',
  '12-budget.png',
  '13-approvals.png',
  '14-documents.png',
  '15-audit.png',
  '16-tablet.png',
  '17-turkish.png',
  '18-english.png',
];

console.log('outDir=', outDir);

const base = process.env.BASE_URL || 'http://localhost:3000';
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

async function login() {
  await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1000);
  await page.locator('input[type="email"], input[name="email"]').first().fill('superadmin@investhome.demo');
  await page.locator('input[type="password"], input[name="password"]').first().fill('Demo123!');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/dashboard/, { timeout: 45_000 });
  await page.waitForTimeout(1200);
}

async function waitWorkspaceHydrated() {
  await page.waitForSelector('[data-testid="fin-g5-workspace"]', { timeout: 60_000 });
  await page.waitForFunction(
    () => {
      const ws = document.querySelector('[data-testid="fin-g5-workspace"]');
      if (!ws) return false;
      const text = ws.innerText.toLowerCase();
      if (
        text.includes('finans verileri yükleniyor') ||
        text.includes('loading finance data') ||
        text.includes('permission to view') ||
        text.includes('izniniz yok')
      ) {
        return false;
      }
      return /\$[\d.,]{3,}|₺[\d.,]{3,}/.test(ws.innerText);
    },
    { timeout: 120_000 },
  );
}

async function openView(viewId) {
  const nav = page.locator(`[data-testid="fin-g5-nav-${viewId}"]`);
  await nav.click();
  await page.waitForFunction(
    (id) => {
      const btn = document.querySelector(`[data-testid="fin-g5-nav-${id}"]`);
      return Boolean(btn && btn.classList.contains('is-active'));
    },
    viewId,
    { timeout: 30_000 },
  );
  const panelMap = {
    executive: 'fin-g5-executive',
    cash: 'fin-g5-cash',
    accounts: 'fin-g5-accounts',
    wires_in: 'fin-g5-wires-in',
    wires_out: 'fin-g5-wires-out',
    investor_payments: 'fin-g5-investor-payments',
    vendor_payments: 'fin-g5-vendor-payments',
    ar: 'fin-g5-ar',
    ap: 'fin-g5-ap',
    treasury: 'fin-g5-treasury',
    forecast: 'fin-g5-forecast',
    budget: 'fin-g5-budget',
    approvals: 'fin-g5-approvals',
    documents: 'fin-g5-documents',
    audit: 'fin-g5-audit',
  };
  await page.waitForSelector(`[data-testid="${panelMap[viewId]}"]`, { timeout: 45_000 });
  await page.waitForTimeout(700);
}

async function shot(name) {
  const file = path.join(outDir, name);
  await page.screenshot({ path: file, fullPage: false });
  const size = (await stat(file)).size;
  console.log('saved', file, size);
  if (size < 10_000) throw new Error(`${name} too small: ${size}`);
}

await login();
await page.goto(`${base}/dashboard/finance`, { waitUntil: 'domcontentloaded' });
await waitWorkspaceHydrated();
await page.waitForSelector('[data-testid="fin-g5-executive"]', { timeout: 45_000 });
await page.waitForTimeout(800);

const sequence = [
  ['01-executive-dashboard.png', 'executive'],
  ['02-cash-position.png', 'cash'],
  ['03-bank-accounts.png', 'accounts'],
  ['04-incoming-wires.png', 'wires_in'],
  ['05-outgoing-wires.png', 'wires_out'],
  ['06-investor-payments.png', 'investor_payments'],
  ['07-vendor-payments.png', 'vendor_payments'],
  ['08-ar.png', 'ar'],
  ['09-ap.png', 'ap'],
  ['10-treasury.png', 'treasury'],
  ['11-forecast.png', 'forecast'],
  ['12-budget.png', 'budget'],
  ['13-approvals.png', 'approvals'],
  ['14-documents.png', 'documents'],
  ['15-audit.png', 'audit'],
];

for (const [name, viewId] of sequence) {
  await openView(viewId);
  await shot(name);
}

await openView('executive');
await page.setViewportSize({ width: 820, height: 1100 });
await page.waitForTimeout(600);
await shot('16-tablet.png');

await page.setViewportSize({ width: 1440, height: 900 });
const langSelect = page.locator('select.dashboard__language-select').first();
await langSelect.waitFor({ timeout: 15_000 });
await langSelect.selectOption('tr');
await page.waitForTimeout(1200);
await page.goto(`${base}/dashboard/finance`, { waitUntil: 'domcontentloaded' });
await waitWorkspaceHydrated();
await page.waitForSelector('[data-testid="fin-g5-executive"]', { timeout: 45_000 });
await page.waitForFunction(
  () => /Finans & Hazine|Nakit Pozisyonu/i.test(document.body.innerText),
  { timeout: 30_000 },
);
await shot('17-turkish.png');

await langSelect.selectOption('en');
await page.waitForTimeout(1500);
await page.goto(`${base}/dashboard/finance?view=cash`, { waitUntil: 'domcontentloaded' });
await waitWorkspaceHydrated();
await page.waitForSelector('[data-testid="fin-g5-cash"]', { timeout: 45_000 });
await page.waitForFunction(
  () => /Finance & Treasury|Cash Position/i.test(document.body.innerText),
  { timeout: 30_000 },
);
await shot('18-english.png');

await browser.close();

const entries = await readdir(outDir);
const pngs = entries.filter((e) => e.endsWith('.png')).sort();
console.log('\n=== VERIFY LISTING ===');
console.log('dir=', outDir);
let ok = 0;
const sizes = {};
for (const name of REQUIRED) {
  const full = path.join(outDir, name);
  try {
    const s = (await stat(full)).size;
    sizes[name] = s;
    const pass = s > 10_000;
    console.log(`${pass ? 'OK' : 'FAIL'}\t${name}\t${s}`);
    if (pass) ok += 1;
  } catch {
    console.log(`MISSING\t${name}`);
    sizes[name] = 0;
  }
}
await writeFile(path.join(outDir, 'sizes-verified.json'), JSON.stringify(sizes, null, 2));
console.log(`\nRESULT ${ok}/${REQUIRED.length}`);
console.log('PNG_COUNT_IN_DIR', pngs.length);
console.log('SIZES_JSON', JSON.stringify(sizes));
if (ok !== REQUIRED.length) process.exitCode = 1;
