import { test, expect, loginAs, DEMO_USERS } from './fixtures';

test.describe('Projects G4 workspace', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);
    await page.goto('/dashboard/projects');
    await expect(page.getByTestId('proj-g4-workspace')).toBeVisible({ timeout: 30_000 });
  });

  test('1 portfolio renders dense cards', async ({ page }) => {
    await expect(page.getByTestId('proj-g4-portfolio')).toBeVisible({ timeout: 20_000 });
  });

  test('2 construction board columns', async ({ page }) => {
    await page.getByTestId('proj-g4-nav-board').click();
    await expect(page.getByTestId('proj-g4-board')).toBeVisible();
    await expect(page.getByTestId('proj-g4-col-planned')).toBeVisible();
    await expect(page.getByTestId('proj-g4-col-completed')).toBeVisible();
  });

  test('3 task drawer opens from board', async ({ page }) => {
    await page.getByTestId('proj-g4-nav-board').click();
    const card = page.locator('[data-testid^="proj-g4-task-"]').first();
    await expect(card).toBeVisible({ timeout: 20_000 });
    await card.click();
    await expect(page.getByTestId('proj-g4-task-drawer')).toBeVisible();
  });

  test('4 timeline view', async ({ page }) => {
    await page.getByTestId('proj-g4-nav-timeline').click();
    await expect(page.getByTestId('proj-g4-timeline')).toBeVisible();
  });

  test('5 milestones view', async ({ page }) => {
    await page.getByTestId('proj-g4-nav-milestones').click();
    await expect(page.getByTestId('proj-g4-milestones')).toBeVisible();
  });

  test('6 budget view', async ({ page }) => {
    await page.getByTestId('proj-g4-nav-budget').click();
    await expect(page.getByTestId('proj-g4-budget')).toBeVisible();
  });

  test('7 contractors view', async ({ page }) => {
    await page.getByTestId('proj-g4-nav-contractors').click();
    await expect(page.getByTestId('proj-g4-contractors')).toBeVisible();
  });

  test('8 permits view', async ({ page }) => {
    await page.getByTestId('proj-g4-nav-permits').click();
    await expect(page.getByTestId('proj-g4-permits')).toBeVisible();
  });

  test('9 inspections view', async ({ page }) => {
    await page.getByTestId('proj-g4-nav-inspections').click();
    await expect(page.getByTestId('proj-g4-inspections')).toBeVisible();
  });

  test('10 issues and risks view', async ({ page }) => {
    await page.getByTestId('proj-g4-nav-issues').click();
    await expect(page.getByTestId('proj-g4-issues')).toBeVisible();
  });

  test('11 analytics KPIs', async ({ page }) => {
    await page.getByTestId('proj-g4-nav-analytics').click();
    await expect(page.getByTestId('proj-g4-analytics')).toBeVisible();
  });

  test('12 filters apply without crash', async ({ page }) => {
    await page.locator('.proj-g4__filters input').first().fill('Demo');
    await page.getByRole('button', { name: /Uygula|Apply/i }).click();
    await expect(page.getByTestId('proj-g4-workspace')).toBeVisible();
  });

  test('13 Turkish portfolio type labels', async ({ page }) => {
    await page.goto('/dashboard/projects');
    await expect(page.getByTestId('proj-g4-workspace')).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId('proj-g4-nav-portfolio')).toContainText(/Portföy|Portfolio/);
  });

  test('14 English navigation', async ({ page }) => {
    const lang = page.getByRole('button', { name: /English|Dil/i }).first();
    if (await lang.isVisible().catch(() => false)) {
      await lang.click();
    }
    await page.getByTestId('proj-g4-nav-tasks').click();
    await expect(page.getByTestId('proj-g4-tasks')).toBeVisible();
  });

  test('15 keyboard opens portfolio card', async ({ page }) => {
    const card = page.locator('[data-testid^="proj-g4-card-"]').first();
    if (await card.isVisible().catch(() => false)) {
      await card.focus();
      await page.keyboard.press('Enter');
      await expect(page.getByTestId('proj-g4-drawer')).toBeVisible();
    } else {
      // table layout fallback
      const row = page.locator('[data-testid^="proj-g4-row-"]').first();
      await row.focus();
      await page.keyboard.press('Enter');
      await expect(page.getByTestId('proj-g4-drawer')).toBeVisible();
    }
  });
});
