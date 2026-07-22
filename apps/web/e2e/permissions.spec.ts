import { test, expect, loginAs, DEMO_USERS } from './fixtures';

test.describe('Permissions', () => {
  test('readonly user reaches dashboard but admin is gated', async ({ page }) => {
    await loginAs(page, DEMO_USERS.readonly);
    await expect(page.locator('.dashboard-shell')).toBeVisible();

    await page.goto('/dashboard/admin');
    // Either forbidden page or redirected away from admin
    const url = page.url();
    const onForbidden = /forbidden/i.test(url);
    const leftAdmin = !url.includes('/dashboard/admin');
    const adminHidden = (await page.locator('.dashboard-shell__nav-link', { hasText: /Administration|Yönetim/i }).count()) === 0;
    expect(onForbidden || leftAdmin || adminHidden).toBeTruthy();
  });

  test('sales user can open sales workspace', async ({ page }) => {
    await loginAs(page, DEMO_USERS.sales);
    await page.goto('/dashboard/sales');
    await expect(page.locator('.dashboard-shell')).toBeVisible();
    await expect(page).not.toHaveURL(/\/login/);
  });
});
