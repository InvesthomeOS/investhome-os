import { chromium } from 'playwright';
import { mkdir, stat, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const outDir = path.join(repoRoot, 'artifacts', 'projects-g4');
await mkdir(outDir, { recursive: true });

const REQUIRED = [
  '01-portfolio-desktop.png',
  '02-detail-overview.png',
  '03-construction-board.png',
  '04-task-drawer.png',
  '05-timeline.png',
  '06-milestones.png',
  '07-budget.png',
  '08-contractors.png',
  '09-permits.png',
  '10-inspections.png',
  '11-issues-risks.png',
  '12-analytics.png',
  '13-tablet.png',
  '14-turkish.png',
  '15-english.png',
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

async function shot(name, url, setup) {
  if (url) await page.goto(url, { waitUntil: 'domcontentloaded' });
  if (setup) await setup();
  await page.waitForSelector('[data-testid="proj-g4-workspace"]', { timeout: 45_000 });
  await page
    .waitForFunction(
      () => {
        const text = document.body.innerText.toLowerCase();
        const loading = text.includes('yükleniyor') || text.includes('loading');
        const ready = document.querySelector(
          '[data-testid="proj-g4-portfolio"], [data-testid="proj-g4-board"], .proj-g4__panel, [data-testid="proj-g4-analytics"], [data-testid="proj-g4-tasks"], [data-testid="proj-g4-drawer"], [data-testid="proj-g4-task-drawer"]',
        );
        return !loading && Boolean(ready);
      },
      { timeout: 45_000 },
    )
    .catch(() => {});
  await page.waitForTimeout(1400);
  const file = path.join(outDir, name);
  await page.screenshot({ path: file, fullPage: false });
  const size = (await stat(file)).size;
  console.log('saved', file, size);
  if (size < 10_000) throw new Error(`${name} too small: ${size}`);
}

await login();

await shot('01-portfolio-desktop.png', `${base}/dashboard/projects`);

await shot('02-detail-overview.png', `${base}/dashboard/projects`, async () => {
  const card = page.locator('[data-testid^="proj-g4-card-"]').first();
  await card.waitFor({ timeout: 30_000 });
  await card.click();
  await page.waitForSelector('[data-testid="proj-g4-drawer"]', { timeout: 15_000 });
});

await shot('03-construction-board.png', `${base}/dashboard/projects?view=board`);

await shot('04-task-drawer.png', `${base}/dashboard/projects?view=board`, async () => {
  const card = page.locator('[data-testid^="proj-g4-task-"]').first();
  await card.waitFor({ timeout: 30_000 });
  await card.click();
  await page.waitForSelector('[data-testid="proj-g4-task-drawer"]', { timeout: 15_000 });
});

await shot('05-timeline.png', `${base}/dashboard/projects?view=timeline`);
await shot('06-milestones.png', `${base}/dashboard/projects?view=milestones`);
await shot('07-budget.png', `${base}/dashboard/projects?view=budget`);
await shot('08-contractors.png', `${base}/dashboard/projects?view=contractors`);
await shot('09-permits.png', `${base}/dashboard/projects?view=permits`);
await shot('10-inspections.png', `${base}/dashboard/projects?view=inspections`);
await shot('11-issues-risks.png', `${base}/dashboard/projects?view=issues`);
await shot('12-analytics.png', `${base}/dashboard/projects?view=analytics`);

await page.setViewportSize({ width: 820, height: 1100 });
await shot('13-tablet.png', `${base}/dashboard/projects`);

await page.setViewportSize({ width: 1440, height: 900 });
await shot('14-turkish.png', `${base}/dashboard/projects`);

await page.goto(`${base}/dashboard/projects?view=tasks`, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('[data-testid="proj-g4-workspace"]', { timeout: 45_000 });
const enBtn = page.getByRole('button', { name: /English/i }).first();
if (await enBtn.isVisible().catch(() => false)) {
  await enBtn.click();
  await page.waitForTimeout(1000);
}
await page.waitForTimeout(800);
const enPath = path.join(outDir, '15-english.png');
await page.screenshot({ path: enPath, fullPage: false });
const enSize = (await stat(enPath)).size;
console.log('saved', enPath, enSize);
if (enSize < 10_000) throw new Error(`15-english.png too small: ${enSize}`);

await browser.close();

// Final verification listing
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
console.log(`\nRESULT ${ok}/15`);
console.log('PNG_COUNT_IN_DIR', pngs.length);
console.log('SIZES_JSON', JSON.stringify(sizes));
if (ok !== 15) process.exitCode = 1;
