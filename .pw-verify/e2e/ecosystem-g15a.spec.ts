import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { test, expect } from '@playwright/test';

const ARTIFACTS = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../artifacts/ecosystem-g15a',
);

const REQUIRED_SHOTS = [
  '01-platform-overview.png',
  '02-architecture-audit.png',
  '03-module-registry.png',
  '04-dependency-map.png',
  '05-circular-deps-reject.png',
  '06-feature-flags.png',
  '07-flag-enable-hide.png',
  '08-kill-switch.png',
  '09-entitlements.png',
  '10-entitlement-deny.png',
  '11-external-users.png',
  '12-api-clients.png',
  '13-api-scope-catalog.png',
  '14-api-scope-reject.png',
  '15-webhooks.png',
  '16-webhook-signature.png',
  '17-integrations.png',
  '18-integration-blocked.png',
  '19-module-health.png',
  '20-platform-health.png',
  '21-kill-switches-panel.png',
  '22-environment-controls.png',
  '23-external-access-audit.png',
  '24-permission-denied.png',
  '25-turkish.png',
  '26-english.png',
  '27-tablet.png',
] as const;

async function login(page: import('@playwright/test').Page, email: string, password = 'Demo123!') {
  await page.context().clearCookies();
  await page.goto('/login');
  await page.locator('input[type="email"], input[name="email"]').first().fill(email, { timeout: 30000 });
  await page.locator('input[type="password"]').first().fill(password);
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/dashboard/, { timeout: 30000 });
}

async function shot(page: import('@playwright/test').Page, name: (typeof REQUIRED_SHOTS)[number]) {
  fs.mkdirSync(ARTIFACTS, { recursive: true });
  const file = path.join(ARTIFACTS, name);
  await page.screenshot({ path: file, fullPage: true });
  const stat = fs.statSync(file);
  expect(stat.size, `${name} must be >10KB`).toBeGreaterThan(10_000);
}

test.describe('G15A Platform Core only', () => {
  test('platform foundation critical paths + 27 screenshots', async ({ page }) => {
    test.setTimeout(360_000);
    fs.mkdirSync(ARTIFACTS, { recursive: true });
    await login(page, 'superadmin@investhome.demo');

    await page.goto('/dashboard/admin/platform');
    await expect(page.locator('[data-platform-workspace="overview"]')).toBeVisible({ timeout: 20000 });
    await shot(page, '01-platform-overview.png');
    await expect(page.locator('[data-architecture-audit]')).toBeVisible();
    await shot(page, '02-architecture-audit.png');

    await page.goto('/dashboard/admin/platform/modules');
    await expect(page.locator('[data-platform-modules]')).toBeVisible({ timeout: 20000 });
    await expect(page.locator('[data-module-code="mga_insurance"] [data-block-reason]')).toBeVisible();
    await expect(page.locator('[data-module-code="contractor_portal"]')).toHaveAttribute(
      'data-lifecycle',
      'planned',
    );
    await shot(page, '03-module-registry.png');
    await expect(page.locator('[data-dependency-map]')).toBeVisible();
    await shot(page, '04-dependency-map.png');
    await page.locator('[data-circular-deps-test]').click();
    await expect(page.locator('[data-circular-result]')).toContainText(/reject|redded|Circular|Döngü/i, {
      timeout: 10000,
    });
    await shot(page, '05-circular-deps-reject.png');

    await page.goto('/dashboard/admin/platform/feature-flags');
    await expect(page.locator('[data-platform-flags]')).toBeVisible({ timeout: 20000 });
    await shot(page, '06-feature-flags.png');
    const toggle = page.locator('[data-flag-toggle="contractor_portal"]');
    if (await toggle.count()) {
      await toggle.click();
      await page.waitForTimeout(500);
    }
    await shot(page, '07-flag-enable-hide.png');
    await page.locator('[data-flag-kill="contractor_portal"]').click();
    await expect(page.locator('[data-platform-kill-switch]')).toBeVisible({ timeout: 10000 });
    await shot(page, '08-kill-switch.png');

    await page.goto('/dashboard/admin/platform/entitlements');
    await expect(page.locator('[data-platform-entitlements]')).toBeVisible({ timeout: 20000 });
    await expect(page.locator('[data-billing-note]')).toBeVisible();
    await shot(page, '09-entitlements.png');
    await page.locator('[data-entitlement-check]').click();
    await expect(page.locator('[data-entitlement-result]')).toContainText(/denied|redd/i, { timeout: 10000 });
    await shot(page, '10-entitlement-deny.png');

    await page.goto('/dashboard/admin/platform/external-users');
    await expect(page.locator('[data-platform-external-users]')).toBeVisible({ timeout: 20000 });
    await shot(page, '11-external-users.png');

    await page.goto('/dashboard/admin/platform/api-clients');
    await expect(page.locator('[data-platform-api-clients]')).toBeVisible({ timeout: 20000 });
    await shot(page, '12-api-clients.png');

    await page.goto('/dashboard/admin/platform/api-scopes');
    await expect(page.locator('[data-platform-api-scopes]')).toBeVisible({ timeout: 20000 });
    await expect(page.locator('[data-no-wildcards]')).toBeVisible();
    await shot(page, '13-api-scope-catalog.png');

    await page.goto('/dashboard/admin/platform/api-clients');
    await page.locator('[data-scope-check]').click();
    await expect(page.locator('[data-scope-result]')).toContainText(/reject|redded|invalid/i, {
      timeout: 10000,
    });
    await shot(page, '14-api-scope-reject.png');

    await page.goto('/dashboard/admin/platform/webhooks');
    await expect(page.locator('[data-platform-webhooks]')).toBeVisible({ timeout: 20000 });
    await page.locator('[data-create-webhook]').click();
    await expect(page.locator('[data-signature-result]')).toContainText(/VALID|GEÇERLİ|valid/i, {
      timeout: 15000,
    });
    await shot(page, '15-webhooks.png');
    await shot(page, '16-webhook-signature.png');

    await page.goto('/dashboard/admin/platform/integrations');
    await expect(page.locator('[data-platform-integrations]')).toBeVisible({ timeout: 20000 });
    await shot(page, '17-integrations.png');
    await expect(page.locator('[data-integration="stripe"]')).toHaveAttribute('data-status', 'blocked');
    await shot(page, '18-integration-blocked.png');

    await page.goto('/dashboard/admin/platform/health');
    await expect(page.locator('[data-module-health]')).toBeVisible({ timeout: 20000 });
    await shot(page, '19-module-health.png');
    await shot(page, '20-platform-health.png');
    await expect(page.locator('[data-kill-switches]')).toBeVisible();
    await shot(page, '21-kill-switches-panel.png');
    await expect(page.locator('[data-environment-controls]')).toBeVisible();
    await shot(page, '22-environment-controls.png');

    await page.goto('/dashboard/admin/platform/audit');
    await expect(page.locator('[data-platform-audit]')).toBeVisible({ timeout: 20000 });
    if (await page.locator('[data-record-audit]').count()) {
      await page.locator('[data-record-audit]').click();
      await page.waitForTimeout(500);
    }
    await shot(page, '23-external-access-audit.png');

    // Permission denied
    await page.goto('/login');
    await login(page, 'readonly@investhome.demo');
    await page.goto('/dashboard/admin/platform');
    await expect(page.locator('[data-platform-denied]')).toBeVisible({ timeout: 20000 });
    await shot(page, '24-permission-denied.png');

    await login(page, 'superadmin@investhome.demo');
    await page.context().addCookies([
      { name: 'investhome.locale', value: 'tr', url: 'http://localhost:3000' },
    ]);
    await page.goto('/dashboard/admin/platform');
    await expect(page.locator('[data-platform-workspace="overview"]')).toBeVisible({ timeout: 20000 });
    await shot(page, '25-turkish.png');

    await page.context().addCookies([
      { name: 'investhome.locale', value: 'en', url: 'http://localhost:3000' },
    ]);
    await page.goto('/dashboard/admin/platform');
    await expect(page.locator('[data-platform-workspace="overview"]')).toBeVisible({ timeout: 20000 });
    await shot(page, '26-english.png');

    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/dashboard/admin/platform/modules');
    await expect(page.locator('[data-platform-modules]')).toBeVisible({ timeout: 20000 });
    await shot(page, '27-tablet.png');

    // Verify all 27 on disk
    for (const name of REQUIRED_SHOTS) {
      const file = path.join(ARTIFACTS, name);
      expect(fs.existsSync(file), `${file} missing`).toBeTruthy();
      expect(fs.statSync(file).size, `${name} >10KB`).toBeGreaterThan(10_000);
    }
  });
});
