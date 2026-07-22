import { test, expect, loginAs, DEMO_USERS } from './fixtures';

test.describe('Project finance', () => {
  test('projects and finance dashboards load backend-backed views', async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);

    await page.goto('/dashboard/projects');
    await expect(page.locator('.dashboard-shell')).toBeVisible();
    await expect(page.locator('.dashboard-shell__content')).toBeVisible();

    await page.goto('/dashboard/finance');
    await expect(page.locator('.dashboard-shell')).toBeVisible();
    await expect(page.locator('.dashboard-shell__content')).toBeVisible();
  });
});
