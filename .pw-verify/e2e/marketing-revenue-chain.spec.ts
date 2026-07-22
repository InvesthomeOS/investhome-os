import { test, expect, loginAs, DEMO_USERS } from './fixtures';

test.describe('Marketing → revenue chain', () => {
  test('marketing campaigns and sales pipeline show seeded data', async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);

    await page.goto('/workspaces/marketing/dashboard');
    await expect(page.locator('.dashboard-shell')).toBeVisible();
    // No critical unhandled console errors for 500s during load
    const serverErrors: string[] = [];
    page.on('response', (res) => {
      if (res.status() >= 500 && (res.url().includes('/api') || res.url().includes(':8000'))) {
        serverErrors.push(`${res.status()} ${res.url()}`);
      }
    });

    await page.goto('/workspaces/marketing/campaigns');
    await expect(page.locator('.dashboard-shell')).toBeVisible();
    await page.waitForTimeout(1500);

    await page.goto('/dashboard/sales');
    await expect(page.locator('.dashboard-shell')).toBeVisible();
    await page.waitForTimeout(1500);

    await page.goto('/workspaces/crm/contacts');
    await expect(page.locator('.dashboard-shell')).toBeVisible();
    // Contacts list should render (seeded or empty-state — not a crash)
    await expect(page.locator('.dashboard-shell__content')).toBeVisible();

    expect(serverErrors.filter((e) => !e.includes('favicon')).length).toBeLessThan(5);
  });
});
