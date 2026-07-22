import { test as base, expect, type Page } from '@playwright/test';

export const DEMO_PASSWORD = 'Demo123!';

export const DEMO_USERS = {
  superadmin: 'superadmin@investhome.demo',
  executive: 'executive@investhome.demo',
  sales: 'sales@investhome.demo',
  finance: 'finance@investhome.demo',
  readonly: 'readonly@investhome.demo',
  marketing: 'marketing@investhome.demo',
} as const;

export async function loginAs(page: Page, email: string, password = DEMO_PASSWORD) {
  await page.goto('/login');
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');
  await expect(page.locator('.dashboard-shell')).toBeVisible({ timeout: 30_000 });
}

export async function expectOsShell(page: Page) {
  await expect(page.locator('.dashboard-shell__sidebar')).toBeVisible();
  await expect(page.locator('.app-header')).toBeVisible();
  await expect(page.getByTestId('os-main-menu').first()).toBeVisible();
}

export const test = base.extend({});
export { expect };
