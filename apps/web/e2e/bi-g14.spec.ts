import { test, expect } from '@playwright/test';

/**
 * G14 critical paths — run against local stack with demo superadmin.
 * Requires apps up + migration 0060 applied + optional ingestion.
 */
test.describe('G14 BI warehouse foundation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').first().fill('superadmin@investhome.demo');
    await page.locator('input[type="password"]').first().fill('Demo123!');
    await page.locator('button[type="submit"]').first().click();
    await page.waitForURL(/dashboard/, { timeout: 30000 });
  });

  test('analytics overview loads', async ({ page }) => {
    await page.goto('/dashboard/analytics');
    await expect(page.locator('[data-bi-workspace]')).toBeVisible({ timeout: 20000 });
  });

  test('explorer is governed', async ({ page }) => {
    await page.goto('/dashboard/analytics/explorer');
    await expect(page.getByTestId('analytics-explorer')).toBeVisible({ timeout: 20000 });
  });

  test('data platform admin', async ({ page }) => {
    await page.goto('/dashboard/admin/data-platform');
    await expect(page.getByTestId('data-platform')).toBeVisible({ timeout: 20000 });
  });

  test('metric catalog', async ({ page }) => {
    await page.goto('/dashboard/admin/metric-catalog');
    await expect(page.getByTestId('metric-catalog')).toBeVisible({ timeout: 20000 });
  });

  test('portfolio mart page', async ({ page }) => {
    await page.goto('/dashboard/analytics/portfolio');
    await expect(page.getByTestId('analytics-portfolio')).toBeVisible({ timeout: 20000 });
  });
});
