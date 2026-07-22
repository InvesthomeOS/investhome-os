import { chromium } from 'playwright';
import { mkdir, stat, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const outDir = path.join(repoRoot, 'artifacts', 'ai-g7');
await mkdir(outDir, { recursive: true });

const REQUIRED = [
  '01-command-center.png',
  '02-morning-brief.png',
  '03-executive-copilot.png',
  '04-action-center.png',
  '05-crm-intelligence.png',
  '06-investor-intelligence.png',
  '07-project-intelligence.png',
  '08-finance-intelligence.png',
  '09-marketing-intelligence.png',
  '10-document-intelligence.png',
  '11-meeting-intelligence.png',
  '12-forecasts.png',
  '13-risk-center.png',
  '14-ai-search.png',
  '15-prompt-library.png',
  '16-activity-log.png',
  '17-provider-status.png',
  '18-tablet.png',
  '19-turkish.png',
  '20-english.png',
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

async function waitReady() {
  await page.waitForSelector('[data-testid="ai-g7-workspace"]', { timeout: 45_000 });
  await page.waitForSelector('[data-testid^="ai-g7-nav-"]', { timeout: 30_000 });
  await page
    .waitForFunction(
      () => {
        const text = document.body.innerText.toLowerCase();
        const loading = text.includes('yz çalışma alanı yükleniyor') || text.includes('loading ai workspace');
        const ready = document.querySelector(
          '[data-testid^="ai-g7-command"], [data-testid^="ai-g7-morning"], [data-testid^="ai-g7-copilot"], [data-testid^="ai-g7-action"], [data-testid^="ai-g7-crm"], [data-testid^="ai-g7-investor"], [data-testid^="ai-g7-project"], [data-testid^="ai-g7-finance"], [data-testid^="ai-g7-marketing"], [data-testid^="ai-g7-document"], [data-testid^="ai-g7-meeting"], [data-testid^="ai-g7-forecasts"], [data-testid^="ai-g7-risk"], [data-testid^="ai-g7-ai_search"], [data-testid^="ai-g7-prompt"], [data-testid^="ai-g7-activity"], [data-testid^="ai-g7-settings"], [data-testid^="ai-g7-provider"], .ai-g7__kpis, .ai-g7__panel',
        );
        return Boolean(ready) && !loading;
      },
      { timeout: 60_000 },
    )
    .catch(() => {});
  await page.waitForTimeout(800);
}

async function shot(name, url) {
  if (url) await page.goto(url, { waitUntil: 'domcontentloaded' });
  await waitReady();
  const file = path.join(outDir, name);
  await page.screenshot({ path: file, fullPage: false });
  const size = (await stat(file)).size;
  console.log('saved', file, size);
  if (size < 10_000) throw new Error(`${name} too small: ${size}`);
}

await login();

const views = [
  ['01-command-center.png', `${base}/dashboard/ai`],
  ['02-morning-brief.png', `${base}/dashboard/ai?view=morning_brief`],
  ['03-executive-copilot.png', `${base}/dashboard/ai?view=copilot`],
  ['04-action-center.png', `${base}/dashboard/ai?view=action_center`],
  ['05-crm-intelligence.png', `${base}/dashboard/ai?view=crm_intel`],
  ['06-investor-intelligence.png', `${base}/dashboard/ai?view=investor_intel`],
  ['07-project-intelligence.png', `${base}/dashboard/ai?view=project_intel`],
  ['08-finance-intelligence.png', `${base}/dashboard/ai?view=finance_intel`],
  ['09-marketing-intelligence.png', `${base}/dashboard/ai?view=marketing_intel`],
  ['10-document-intelligence.png', `${base}/dashboard/ai?view=document_intel`],
  ['11-meeting-intelligence.png', `${base}/dashboard/ai?view=meeting_intel`],
  ['12-forecasts.png', `${base}/dashboard/ai?view=forecasts`],
  ['13-risk-center.png', `${base}/dashboard/ai?view=risk_center`],
  ['14-ai-search.png', `${base}/dashboard/ai?view=ai_search`],
  ['15-prompt-library.png', `${base}/dashboard/ai?view=prompt_library`],
  ['16-activity-log.png', `${base}/dashboard/ai?view=activity_log`],
  ['17-provider-status.png', `${base}/dashboard/ai?view=provider_status`],
];

for (const [name, url] of views) {
  await shot(name, url);
}

// Copilot with a question for richer screenshot
await page.goto(`${base}/dashboard/ai?view=copilot`, { waitUntil: 'domcontentloaded' });
await waitReady();
const input = page.getByTestId('ai-g7-copilot-input');
if (await input.isVisible().catch(() => false)) {
  await input.fill('What should leadership prioritize today?');
  await page.getByTestId('ai-g7-copilot-ask').click();
  await page.waitForTimeout(2500);
  await shot('03-executive-copilot.png');
}

await page.setViewportSize({ width: 820, height: 1100 });
await shot('18-tablet.png', `${base}/dashboard/ai`);

await page.setViewportSize({ width: 1440, height: 900 });
await shot('19-turkish.png', `${base}/dashboard/ai`);

await page.goto(`${base}/dashboard/ai?view=morning_brief`, { waitUntil: 'domcontentloaded' });
await waitReady();
const enBtn = page.getByRole('button', { name: /English/i }).first();
if (await enBtn.isVisible().catch(() => false)) {
  await enBtn.click();
  await page.waitForTimeout(1200);
}
await waitReady();
const enPath = path.join(outDir, '20-english.png');
await page.screenshot({ path: enPath, fullPage: false });
const enSize = (await stat(enPath)).size;
console.log('saved', enPath, enSize);
if (enSize < 10_000) throw new Error(`20-english.png too small: ${enSize}`);

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
if (ok !== REQUIRED.length) process.exitCode = 1;
