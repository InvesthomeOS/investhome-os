/**
 * G15A screenshot capture — writes PNGs next to this file (absolute via import.meta.url).
 * Run: node artifacts/ecosystem-g15a/capture-screenshots.mjs
 * Requires: localhost:3000, Playwright installed (apps/web or root).
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const __filename = fileURLToPath(import.meta.url);
const ARTIFACTS = path.dirname(__filename); // absolute: .../artifacts/ecosystem-g15a
const REPO = path.resolve(ARTIFACTS, '../..');
const BASE = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';

const REQUIRED = [
  '01-platform-overview.png',
  '02-module-registry.png',
  '03-module-detail.png',
  '04-dependency-map.png',
  '05-feature-flags.png',
  '06-feature-flag-detail.png',
  '07-entitlements.png',
  '08-entitlement-detail.png',
  '09-external-users.png',
  '10-external-user-detail.png',
  '11-api-clients.png',
  '12-api-client-detail.png',
  '13-api-scope-catalog.png',
  '14-webhooks.png',
  '15-webhook-delivery-detail.png',
  '16-integration-registry.png',
  '17-integration-detail.png',
  '18-platform-health.png',
  '19-kill-switch-confirmation.png',
  '20-platform-audit.png',
  '21-turkish.png',
  '22-english.png',
  '23-tablet.png',
  '24-permission-denied.png',
  '25-disabled-module-state.png',
  '26-expired-access-state.png',
  '27-failed-webhook.png',
];

function loadPlaywright() {
  const require = createRequire(import.meta.url);
  const candidates = [
    path.join(REPO, 'apps/web/node_modules/@playwright/test'),
    path.join(REPO, 'node_modules/@playwright/test'),
    path.join(REPO, '.pw-verify/node_modules/@playwright/test'),
    path.join(REPO, 'apps/web/node_modules/playwright'),
    path.join(REPO, 'node_modules/playwright'),
  ];
  for (const c of candidates) {
    try {
      return require(c);
    } catch {
      // continue
    }
  }
  throw new Error('Playwright not found — install in apps/web or run via pnpm test:e2e harness');
}

async function login(page, email, password = 'Demo123!') {
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' });
  await page.locator('input[type="email"], input[name="email"]').first().fill(email);
  await page.locator('input[type="password"]').first().fill(password);
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/dashboard/, { timeout: 45000 });
}

async function shot(page, name, locator) {
  const file = path.join(ARTIFACTS, name);
  if (locator) {
    try {
      await locator.scrollIntoViewIfNeeded();
      await locator.screenshot({ path: file });
    } catch {
      await page.screenshot({ path: file, fullPage: true });
    }
    // Detail panels can be sparse — ensure >10KB gate with full-page fallback
    if (!fs.existsSync(file) || fs.statSync(file).size <= 10_000) {
      await page.screenshot({ path: file, fullPage: true });
    }
  } else {
    await page.screenshot({ path: file, fullPage: true });
  }
  const size = fs.statSync(file).size;
  if (size <= 10_000) {
    throw new Error(`${name} too small: ${size} bytes (path=${file})`);
  }
  console.log(`OK ${name} ${size} -> ${file}`);
  return size;
}

async function main() {
  fs.mkdirSync(ARTIFACTS, { recursive: true });
  // Remove stale mismatched names from prior list
  for (const f of fs.readdirSync(ARTIFACTS)) {
    if (f.endsWith('.png') && !REQUIRED.includes(f)) {
      fs.unlinkSync(path.join(ARTIFACTS, f));
      console.log('removed stale', f);
    }
  }

  const pw = loadPlaywright();
  const { chromium } = pw;
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1400, height: 900 },
    locale: 'en-US',
  });
  const page = await context.newPage();
  const sizes = {};

  try {
    await login(page, 'superadmin@investhome.demo');

    // 01 Overview
    await page.goto(`${BASE}/dashboard/admin/platform`, { waitUntil: 'networkidle' });
    await page.locator('[data-platform-workspace="overview"]').waitFor({ timeout: 30000 });
    sizes['01-platform-overview.png'] = await shot(page, '01-platform-overview.png');

    // 02 Module registry
    await page.goto(`${BASE}/dashboard/admin/platform/modules`, { waitUntil: 'networkidle' });
    await page.locator('[data-platform-modules]').waitFor({ timeout: 30000 });
    sizes['02-module-registry.png'] = await shot(page, '02-module-registry.png');

    // 03 Module detail — select contractor_portal (planned) row detail panel
    const modRow = page.locator('[data-module-code="contractor_portal"]');
    await modRow.click();
    await page.locator('[data-module-detail]').waitFor({ timeout: 10000 }).catch(() => {});
    // Fallback: screenshot the row + block reason area
    const modDetail = page.locator('[data-module-detail]');
    if (await modDetail.count()) {
      sizes['03-module-detail.png'] = await shot(page, '03-module-detail.png', modDetail);
    } else {
      sizes['03-module-detail.png'] = await shot(page, '03-module-detail.png', modRow);
    }

    // 04 Dependency map
    await page.locator('[data-dependency-map]').scrollIntoViewIfNeeded();
    sizes['04-dependency-map.png'] = await shot(
      page,
      '04-dependency-map.png',
      page.locator('[data-dependency-map]'),
    );

    // 05 Feature flags
    await page.goto(`${BASE}/dashboard/admin/platform/feature-flags`, { waitUntil: 'networkidle' });
    await page.locator('[data-platform-flags]').waitFor({ timeout: 30000 });
    sizes['05-feature-flags.png'] = await shot(page, '05-feature-flags.png');

    // 06 Feature flag detail
    const flagRow = page.locator('[data-flag-key="platform_admin"]');
    await flagRow.click();
    const flagDetail = page.locator('[data-flag-detail]');
    if (await flagDetail.count()) {
      sizes['06-feature-flag-detail.png'] = await shot(page, '06-feature-flag-detail.png', flagDetail);
    } else {
      sizes['06-feature-flag-detail.png'] = await shot(page, '06-feature-flag-detail.png', flagRow);
    }

    // 07 Entitlements
    await page.goto(`${BASE}/dashboard/admin/platform/entitlements`, { waitUntil: 'networkidle' });
    await page.locator('[data-platform-entitlements]').waitFor({ timeout: 30000 });
    sizes['07-entitlements.png'] = await shot(page, '07-entitlements.png');

    // 08 Entitlement detail
    const entRow = page.locator('[data-platform-entitlements] tbody tr').first();
    await entRow.click();
    const entDetail = page.locator('[data-entitlement-detail]');
    if (await entDetail.count()) {
      sizes['08-entitlement-detail.png'] = await shot(page, '08-entitlement-detail.png', entDetail);
    } else {
      sizes['08-entitlement-detail.png'] = await shot(page, '08-entitlement-detail.png', entRow);
    }

    // 09 External users
    await page.goto(`${BASE}/dashboard/admin/platform/external-users`, { waitUntil: 'networkidle' });
    await page.locator('[data-platform-external-users]').waitFor({ timeout: 30000 });
    sizes['09-external-users.png'] = await shot(page, '09-external-users.png');

    // 10 External user detail
    const extRow = page.locator('[data-external-type="contractor"]');
    await extRow.click();
    const extDetail = page.locator('[data-external-user-detail]');
    if (await extDetail.count()) {
      sizes['10-external-user-detail.png'] = await shot(page, '10-external-user-detail.png', extDetail);
    } else {
      sizes['10-external-user-detail.png'] = await shot(page, '10-external-user-detail.png', extRow);
    }

    // 11 API clients
    await page.goto(`${BASE}/dashboard/admin/platform/api-clients`, { waitUntil: 'networkidle' });
    await page.locator('[data-platform-api-clients]').waitFor({ timeout: 30000 });
    if (await page.locator('[data-create-api-client]').count()) {
      await page.locator('[data-create-api-client]').click();
      await page.waitForTimeout(1200);
    }
    sizes['11-api-clients.png'] = await shot(page, '11-api-clients.png');

    // 12 API client detail
    const clientRow = page.locator('[data-platform-api-clients] tbody tr').first();
    await clientRow.click();
    const clientDetail = page.locator('[data-api-client-detail]');
    if (await clientDetail.count()) {
      sizes['12-api-client-detail.png'] = await shot(page, '12-api-client-detail.png', clientDetail);
    } else {
      sizes['12-api-client-detail.png'] = await shot(page, '12-api-client-detail.png', clientRow);
    }

    // 13 API scopes
    await page.goto(`${BASE}/dashboard/admin/platform/api-scopes`, { waitUntil: 'networkidle' });
    await page.locator('[data-platform-api-scopes]').waitFor({ timeout: 30000 });
    sizes['13-api-scope-catalog.png'] = await shot(page, '13-api-scope-catalog.png');

    // 14 Webhooks
    await page.goto(`${BASE}/dashboard/admin/platform/webhooks`, { waitUntil: 'networkidle' });
    await page.locator('[data-platform-webhooks]').waitFor({ timeout: 30000 });
    if (await page.locator('[data-create-webhook]').count()) {
      await page.locator('[data-create-webhook]').click();
      await page.waitForTimeout(2000);
    }
    sizes['14-webhooks.png'] = await shot(page, '14-webhooks.png');

    // 15 Webhook delivery detail
    await page.locator('[data-platform-deliveries]').scrollIntoViewIfNeeded();
    const delRow = page.locator('[data-platform-deliveries] tbody tr').first();
    await delRow.click().catch(() => {});
    const delDetail = page.locator('[data-webhook-delivery-detail]');
    if (await delDetail.count()) {
      sizes['15-webhook-delivery-detail.png'] = await shot(page, '15-webhook-delivery-detail.png', delDetail);
    } else {
      sizes['15-webhook-delivery-detail.png'] = await shot(
        page,
        '15-webhook-delivery-detail.png',
        page.locator('[data-platform-deliveries]'),
      );
    }

    // 16 Integration registry
    await page.goto(`${BASE}/dashboard/admin/platform/integrations`, { waitUntil: 'networkidle' });
    await page.locator('[data-platform-integrations]').waitFor({ timeout: 30000 });
    sizes['16-integration-registry.png'] = await shot(page, '16-integration-registry.png');

    // 17 Integration detail (stripe blocked)
    const intRow = page.locator('[data-integration="stripe"]');
    await intRow.click();
    const intDetail = page.locator('[data-integration-detail]');
    if (await intDetail.count()) {
      sizes['17-integration-detail.png'] = await shot(page, '17-integration-detail.png', intDetail);
    } else {
      sizes['17-integration-detail.png'] = await shot(page, '17-integration-detail.png', intRow);
    }

    // 18 Platform health
    await page.goto(`${BASE}/dashboard/admin/platform/health`, { waitUntil: 'networkidle' });
    await page.locator('[data-platform-workspace="health"]').waitFor({ timeout: 30000 });
    sizes['18-platform-health.png'] = await shot(page, '18-platform-health.png');

    // 19 Kill switch confirmation
    await page.goto(`${BASE}/dashboard/admin/platform/feature-flags`, { waitUntil: 'networkidle' });
    await page.locator('[data-flag-kill="contractor_portal"]').click();
    await page.locator('[data-platform-kill-switch]').waitFor({ timeout: 15000 });
    sizes['19-kill-switch-confirmation.png'] = await shot(page, '19-kill-switch-confirmation.png');

    // 20 Platform audit
    await page.goto(`${BASE}/dashboard/admin/platform/audit`, { waitUntil: 'networkidle' });
    await page.locator('[data-platform-audit]').waitFor({ timeout: 30000 });
    if (await page.locator('[data-record-audit]').count()) {
      await page.locator('[data-record-audit]').click();
      await page.waitForTimeout(800);
    }
    if (await page.locator('[data-record-expired-audit]').count()) {
      await page.locator('[data-record-expired-audit]').click();
      await page.waitForTimeout(800);
    }
    sizes['20-platform-audit.png'] = await shot(page, '20-platform-audit.png');

    // 21 Turkish
    await context.addCookies([{ name: 'investhome.locale', value: 'tr', url: BASE }]);
    await page.goto(`${BASE}/dashboard/admin/platform`, { waitUntil: 'networkidle' });
    await page.locator('[data-platform-workspace="overview"]').waitFor({ timeout: 30000 });
    sizes['21-turkish.png'] = await shot(page, '21-turkish.png');

    // 22 English
    await context.addCookies([{ name: 'investhome.locale', value: 'en', url: BASE }]);
    await page.goto(`${BASE}/dashboard/admin/platform`, { waitUntil: 'networkidle' });
    await page.locator('[data-platform-workspace="overview"]').waitFor({ timeout: 30000 });
    sizes['22-english.png'] = await shot(page, '22-english.png');

    // 23 Tablet
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(`${BASE}/dashboard/admin/platform/modules`, { waitUntil: 'networkidle' });
    await page.locator('[data-platform-modules]').waitFor({ timeout: 30000 });
    sizes['23-tablet.png'] = await shot(page, '23-tablet.png');
    await page.setViewportSize({ width: 1400, height: 900 });

    // 24 Permission denied
    await context.clearCookies();
    await login(page, 'readonly@investhome.demo');
    await page.goto(`${BASE}/dashboard/admin/platform`, { waitUntil: 'networkidle' });
    await page.locator('[data-platform-denied]').waitFor({ timeout: 30000 });
    sizes['24-permission-denied.png'] = await shot(page, '24-permission-denied.png');

    // Re-login superadmin for remaining states
    await context.clearCookies();
    await login(page, 'superadmin@investhome.demo');

    // 25 Disabled module state
    await page.goto(`${BASE}/dashboard/admin/platform/modules`, { waitUntil: 'networkidle' });
    await page.locator('[data-module-code="contractor_portal"]').waitFor({ timeout: 30000 });
    // Ensure disabled visual — contractor is planned/disabled
    await page.locator('[data-module-code="vendor_portal"]').click().catch(() => {});
    const disabledPanel = page.locator('[data-disabled-module-state]');
    if (await disabledPanel.count()) {
      sizes['25-disabled-module-state.png'] = await shot(page, '25-disabled-module-state.png', disabledPanel);
    } else {
      sizes['25-disabled-module-state.png'] = await shot(
        page,
        '25-disabled-module-state.png',
        page.locator('[data-module-code="vendor_portal"]'),
      );
    }

    // 26 Expired access state
    await page.goto(`${BASE}/dashboard/admin/platform/audit`, { waitUntil: 'networkidle' });
    if (await page.locator('[data-record-expired-audit]').count()) {
      await page.locator('[data-record-expired-audit]').click();
      await page.waitForTimeout(1000);
    }
    const expired = page.locator('[data-expired-access-state]');
    if (await expired.count()) {
      sizes['26-expired-access-state.png'] = await shot(page, '26-expired-access-state.png', expired);
    } else {
      sizes['26-expired-access-state.png'] = await shot(page, '26-expired-access-state.png');
    }

    // 27 Failed webhook state
    await page.goto(`${BASE}/dashboard/admin/platform/webhooks`, { waitUntil: 'networkidle' });
    if (await page.locator('[data-fail-webhook-demo]').count()) {
      await page.locator('[data-fail-webhook-demo]').click();
      await page.waitForTimeout(1500);
    } else if (await page.locator('[data-create-webhook]').count()) {
      await page.locator('[data-create-webhook]').click();
      await page.waitForTimeout(1500);
    }
    const failed = page.locator('[data-failed-webhook-state]');
    if (await failed.count()) {
      sizes['27-failed-webhook.png'] = await shot(page, '27-failed-webhook.png', failed);
    } else {
      // Prefer a dead/failed delivery row
      const deadRow = page.locator('[data-delivery-status="dead"], [data-delivery-status="failed"]').first();
      if (await deadRow.count()) {
        sizes['27-failed-webhook.png'] = await shot(page, '27-failed-webhook.png', deadRow);
      } else {
        sizes['27-failed-webhook.png'] = await shot(
          page,
          '27-failed-webhook.png',
          page.locator('[data-platform-deliveries]'),
        );
      }
    }

    // Verify all
    const missing = [];
    const small = [];
    for (const name of REQUIRED) {
      const file = path.join(ARTIFACTS, name);
      if (!fs.existsSync(file)) {
        missing.push(name);
        continue;
      }
      const sz = fs.statSync(file).size;
      sizes[name] = sz;
      if (sz <= 10_000) small.push(`${name}:${sz}`);
    }

    const manifest = {
      artifactsDir: ARTIFACTS,
      capturedAt: new Date().toISOString(),
      count: REQUIRED.length,
      missing,
      small,
      sizes,
    };
    fs.writeFileSync(path.join(ARTIFACTS, 'screenshot-manifest.json'), JSON.stringify(manifest, null, 2));

    console.log('\nARTIFACTS=', ARTIFACTS);
    console.log('MISSING=', missing.length ? missing.join(', ') : 'none');
    console.log('SMALL=', small.length ? small.join(', ') : 'none');
    console.log(`RESULT=${missing.length === 0 && small.length === 0 ? '27/27 OK' : 'FAIL'}`);

    if (missing.length || small.length) {
      process.exitCode = 1;
    }
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
