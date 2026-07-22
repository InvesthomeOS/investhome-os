import { test, expect, loginAs, DEMO_USERS } from './fixtures';

test.describe('Finance G5 workspace', () => {
  test('executive dashboard loads with KPIs', async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);
    await page.goto('/dashboard/finance');
    await expect(page.getByTestId('fin-g5-workspace')).toBeVisible({ timeout: 45_000 });
    await expect(page.getByTestId('fin-g5-executive')).toBeVisible({ timeout: 45_000 });
    await expect(page.getByTestId('fin-g5-kpi-cash')).toBeVisible();
  });

  test('navigates cash and accounts views', async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);
    await page.goto('/dashboard/finance?view=cash');
    await expect(page.getByTestId('fin-g5-cash')).toBeVisible({ timeout: 45_000 });
    await page.getByTestId('fin-g5-nav-accounts').click();
    await expect(page.getByTestId('fin-g5-accounts')).toBeVisible({ timeout: 30_000 });
  });

  test('budget and forecast views render', async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);
    await page.goto('/dashboard/finance?view=budget');
    await expect(page.getByTestId('fin-g5-budget')).toBeVisible({ timeout: 45_000 });
    await page.goto('/dashboard/finance?view=forecast');
    await expect(page.getByTestId('fin-g5-forecast')).toBeVisible({ timeout: 45_000 });
  });
});
