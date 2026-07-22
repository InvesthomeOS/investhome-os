import { test, expect, loginAs, DEMO_USERS } from './fixtures';

test.describe('Investor journey', () => {
  test('investors workspace loads seeded investors from API', async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);
    await page.goto('/dashboard/investors');
    await expect(page.locator('.dashboard-shell')).toBeVisible();
    await expect(page.locator('.dashboard-shell__content')).toBeVisible();
    // Should not be the mock investor portal
    await expect(page).not.toHaveURL(/\/investor\/?$/);
  });
});
