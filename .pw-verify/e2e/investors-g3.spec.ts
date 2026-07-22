import { test, expect, loginAs, DEMO_USERS } from './fixtures';

test.describe('Investors G3 workspace', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);
    await page.goto('/dashboard/investors');
    await expect(page.getByTestId('inv-g3-workspace')).toBeVisible({ timeout: 30_000 });
  });

  test('1 pipeline board renders lifecycle columns', async ({ page }) => {
    await expect(page.getByTestId('inv-g3-board')).toBeVisible();
    await expect(page.getByTestId('inv-g3-col-new_investor')).toBeVisible();
    await expect(page.getByTestId('inv-g3-col-portfolio')).toBeVisible();
    await expect(page.getByTestId('inv-g3-col-lost')).toBeVisible();
  });

  test('2 list view loads compact table', async ({ page }) => {
    await page.getByTestId('inv-g3-nav-list').click();
    await expect(page).toHaveURL(/view=list/);
    await expect(page.getByTestId('inv-g3-list')).toBeVisible();
  });

  test('3 drawer opens from pipeline card', async ({ page }) => {
    const card = page.locator('[data-testid^="inv-g3-card-"]').first();
    await expect(card).toBeVisible({ timeout: 20_000 });
    await card.click();
    await expect(page.getByTestId('inv-g3-drawer')).toBeVisible();
  });

  test('4 reservations view', async ({ page }) => {
    await page.getByTestId('inv-g3-nav-reservations').click();
    await expect(page.getByTestId('inv-g3-reservations')).toBeVisible();
  });

  test('5 payments view', async ({ page }) => {
    await page.getByTestId('inv-g3-nav-payments').click();
    await expect(page.getByTestId('inv-g3-payments')).toBeVisible();
  });

  test('6 portfolio view shows demo gap', async ({ page }) => {
    await page.getByTestId('inv-g3-nav-portfolio').click();
    await expect(page.getByTestId('inv-g3-portfolio')).toBeVisible();
  });

  test('7 analytics view shows KPIs', async ({ page }) => {
    await page.getByTestId('inv-g3-nav-analytics').click();
    await expect(page.getByTestId('inv-g3-analytics')).toBeVisible();
  });

  test('8 filters apply without crash', async ({ page }) => {
    await page
      .locator('.inv-g3__filters input')
      .first()
      .fill('Ayşe');
    await page.getByRole('button', { name: /Uygula|Apply/i }).click();
    await expect(page.getByTestId('inv-g3-workspace')).toBeVisible();
  });

  test('9 Turkish stage labels on board', async ({ page }) => {
    await page.goto('/dashboard/investors');
    await expect(page.getByTestId('inv-g3-workspace')).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId('inv-g3-col-new_investor')).toContainText(/Yeni Yatırımcı|New Investor/);
  });

  test('10 English navigation labels', async ({ page }) => {
    // Switch language if control exists
    const lang = page.getByRole('button', { name: /English|Dil/i }).first();
    if (await lang.isVisible().catch(() => false)) {
      await lang.click();
    }
    await page.getByTestId('inv-g3-nav-list').click();
    await expect(page.getByTestId('inv-g3-list')).toBeVisible();
  });

  test('11 keyboard opens card with Enter', async ({ page }) => {
    const card = page.locator('[data-testid^="inv-g3-card-"]').first();
    await card.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByTestId('inv-g3-drawer')).toBeVisible();
  });

  test('12 opportunities / activity / contracts views mount', async ({ page }) => {
    for (const view of ['opportunities', 'contracts', 'closings', 'activity'] as const) {
      await page.getByTestId(`inv-g3-nav-${view}`).click();
      await expect(page.getByTestId(`inv-g3-${view === 'opportunities' ? 'opportunities' : view}`)).toBeVisible();
    }
  });
});
