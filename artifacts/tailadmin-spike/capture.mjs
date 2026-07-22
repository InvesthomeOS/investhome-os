/**
 * TailAdmin spike screenshot helper — demo login + 1440px capture.
 * Usage: node artifacts/tailadmin-spike/capture.mjs
 */
import { chromium } from '../../.pw-verify/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, 'tailadmin-preview-1440.png');
const BASE = process.env.WEB_BASE_URL || 'http://localhost:3000';
const EMAIL = 'superadmin@investhome.demo';
const PASSWORD = 'Demo123!';

mkdirSync(__dirname, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });

await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
await page.fill('input[type="email"], input[name="email"]', EMAIL);
await page.fill('input[type="password"], input[name="password"]', PASSWORD);
await page.click('button[type="submit"]');
await page.waitForURL(/\/dashboard/, { timeout: 30000 });

await page.goto(`${BASE}/dashboard/admin/tailadmin-preview`, { waitUntil: 'networkidle' });
await page.waitForSelector('[data-testid="tailadmin-spike-preview"]', { timeout: 30000 });
// Let Outfit font + layout settle
await page.waitForTimeout(800);

await page.screenshot({ path: OUT, fullPage: true });
console.log('WROTE', OUT);
console.log('TITLE', await page.title());
console.log('URL', page.url());

const preview = page.locator('[data-testid="tailadmin-spike-preview"]');
const box = await preview.boundingBox();
console.log('PREVIEW_BOX', JSON.stringify(box));

await browser.close();
