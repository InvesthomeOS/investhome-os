import { expect, test } from '@playwright/test';

/**
 * G8 Executive command center — critical scenarios (host Playwright optional;
 * primary verification runs via `.pw-verify/verify-executive-g8.mjs`).
 */
const base = process.env.BASE_URL || 'http://localhost:3000';

async function login(page: import('@playwright/test').Page) {
  await page.goto(`${base}/login`);
  await page.locator('input[type="email"], input[name="email"]').first().fill('superadmin@investhome.demo');
  await page.locator('input[type="password"], input[name="password"]').first().fill('Demo123!');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/dashboard/);
}

test.describe('Executive G8', () => {
  test('default route is G8 command center; legacy preserved', async ({ page }) => {
    await login(page);
    await page.goto(`${base}/dashboard/executive`);
    await expect(page.getByTestId('executive-dashboard-g8')).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId('g8-kpi-strip')).toBeVisible();
    await expect(page.getByTestId('g8-last-updated').or(page.getByTestId('g8-meta'))).toBeVisible();

    await page.goto(`${base}/dashboard/executive?view=legacy`);
    await expect(page.getByTestId('executive-dashboard-legacy')).toBeVisible({ timeout: 45_000 });
  });

  test('tablet has no horizontal overflow', async ({ page }) => {
    await login(page);
    await page.setViewportSize({ width: 820, height: 1100 });
    await page.goto(`${base}/dashboard/executive`);
    await expect(page.getByTestId('executive-dashboard-g8')).toBeVisible({ timeout: 60_000 });
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
    );
    expect(overflow).toBeFalsy();
  });
});
