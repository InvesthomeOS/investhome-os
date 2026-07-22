/**
 * Mosaic Lite isolated UI evaluation — full-page desktop screenshots.
 * Run: node artifacts/mosaic-eval/capture-screenshots.mjs
 */
import { createRequire } from 'node:module';
import { mkdir, readdir, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, '../..');
const OUT = __dirname;

function loadPlaywright() {
  const require = createRequire(import.meta.url);
  const candidates = [
    path.join(REPO, '.pw-verify/node_modules/playwright'),
    path.join(REPO, 'apps/web/node_modules/playwright'),
    path.join(REPO, 'node_modules/playwright'),
    path.join(REPO, 'artifacts/bi-g14/node_modules/playwright'),
  ];
  for (const c of candidates) {
    try {
      return require(c);
    } catch {
      /* continue */
    }
  }
  throw new Error('playwright not found');
}

const { chromium } = loadPlaywright();
await mkdir(OUT, { recursive: true });

const base = process.env.BASE_URL || 'http://localhost:3000';
const shots = [
  { name: 'mosaic-dashboard.png', path: '/ui-preview/mosaic/dashboard', testid: 'mosaic-dashboard' },
  { name: 'mosaic-leads.png', path: '/ui-preview/mosaic/leads', testid: 'mosaic-leads' },
  { name: 'mosaic-customer.png', path: '/ui-preview/mosaic/customer', testid: 'mosaic-customer' },
];

console.log('outDir=', OUT);
console.log('base=', base);

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

const results = [];

try {
  for (const shot of shots) {
    const url = `${base}${shot.path}`;
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60_000 });
    await page.waitForSelector(`[data-testid="${shot.testid}"]`, { timeout: 30_000 });
    await page.waitForTimeout(500);
    const file = path.join(OUT, shot.name);
    await page.screenshot({ path: file, fullPage: true, type: 'png' });
    const size = (await stat(file)).size;
    console.log('saved', shot.name, size);
    if (size < 10_000) throw new Error(`${shot.name} too small: ${size}`);
    results.push({ name: shot.name, path: shot.path, size, ok: true });
  }
} finally {
  await browser.close();
}

const listing = await Promise.all(
  (await readdir(OUT))
    .filter((n) => n.endsWith('.png'))
    .map(async (name) => {
      const size = (await stat(path.join(OUT, name))).size;
      return { name, size };
    }),
);

await writeFile(path.join(OUT, 'capture-results.json'), JSON.stringify({ base, results, listing }, null, 2));
await writeFile(
  path.join(OUT, 'screenshot-dir-listing.txt'),
  listing.map((r) => `${r.name}\t${r.size}`).join('\n') + '\n',
);

console.log('done', results.length, 'screenshots');
