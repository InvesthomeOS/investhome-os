import { test, expect, loginAs, expectOsShell, DEMO_USERS } from './fixtures';

test.describe('Workspace navigation — unified OS shell', () => {
  test('CRM and Marketing keep OS sidebar and session; Ana Menü returns home', async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);
    await expectOsShell(page);

    await page.goto('/workspaces/crm/dashboard');
    await expectOsShell(page);
    await expect(page.locator('.dashboard-shell__sidebar')).toBeVisible();
    await expect(page.locator('.os-workspace-rail, .crm-shell__sidebar')).toBeVisible();
    // Main OS nav still present (not replaced by CRM-only shell)
    await expect(page.getByTestId('os-main-menu').first()).toBeVisible();

    await page.goto('/workspaces/marketing/dashboard');
    await expectOsShell(page);
    await expect(page.locator('.dashboard-shell__sidebar')).toBeVisible();

    // Switch without logout
    await page.getByTestId('os-main-menu').first().click();
    await expect(page).toHaveURL(/\/dashboard\/?$/);
    await expect(page.locator('.dashboard-shell')).toBeVisible();

    // Session still valid — navigate to finance
    await page.goto('/dashboard/finance');
    await expect(page.locator('.dashboard-shell')).toBeVisible();
    await expect(page).not.toHaveURL(/\/login/);
  });
});
