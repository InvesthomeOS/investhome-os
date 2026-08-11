import { test, expect, loginAs, DEMO_USERS } from './fixtures';

test.describe('Dashboard user menu logout', () => {
  test('home dashboard account menu logs out via shared auth flow', async ({ page }) => {
    await loginAs(page, DEMO_USERS.sales);
    await page.goto('/dashboard');
    await expect(page.getByTestId('screenshot-dashboard')).toBeVisible({ timeout: 30_000 });

    await page.getByTestId('dashboard-user-menu').click();
    await expect(page.getByTestId('dashboard-user-menu-panel')).toBeVisible();
    await page.getByTestId('dashboard-user-logout').click();

    await expect(page).toHaveURL(/\/login/, { timeout: 30_000 });

    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/);
  });
});
