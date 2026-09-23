import { expect, test, DEMO_USERS, loginAs } from './fixtures';

test.describe('CRM people workspace', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('tabs, search, filters, and person card', async ({ page }) => {
    await loginAs(page, DEMO_USERS.superadmin);
    await page.goto('/workspaces/crm/contacts');
    await expect(page.getByTestId('crm-people-workspace')).toBeVisible({ timeout: 30_000 });

    const total = page.getByTestId('crm-people-count-all');
    const active = page.getByTestId('crm-people-count-active');
    const junk = page.getByTestId('crm-people-count-junk');
    const review = page.getByTestId('crm-people-count-review');
    const missing = page.getByTestId('crm-people-count-missing');
    await expect(total).not.toHaveText('—');
    await expect(active).not.toHaveText('—');
    await expect(junk).not.toHaveText('—');

    const parseCount = async (locator: ReturnType<typeof page.getByTestId>) =>
      Number((await locator.innerText()).replace(/[^\d]/g, ''));
    const totalN = await parseCount(total);
    const activeN = await parseCount(active);
    const junkN = await parseCount(junk);
    const reviewN = await parseCount(review);
    const missingN = await parseCount(missing);
    expect(totalN).toBeGreaterThan(8000);
    expect(activeN).toBeGreaterThan(100);
    expect(junkN).toBeGreaterThan(8000);
    expect(totalN).toBe(activeN + junkN);
    expect(missingN).toBeGreaterThan(0);
    expect(reviewN).toBeGreaterThan(0);

    await page.getByTestId('crm-people-tab-all').click();
    await expect(page.getByTestId('crm-people-filtered-count')).toContainText(String(totalN.toLocaleString('tr-TR')));

    await page.getByTestId('crm-people-chip-active').click();
    await expect(page.getByTestId('crm-people-tab-active')).toHaveClass(/is-active/);
    await expect(page.locator('.ctc-ds__table tbody tr').first()).toBeVisible();

    await page.getByTestId('crm-people-tab-junk').click();
    await expect(page.getByTestId('crm-people-filter-junk-reason')).toBeVisible();
    await expect(page.locator('.ctc-ds__table tbody tr').first()).toBeVisible();

    await page.getByTestId('crm-people-tab-review').click();
    await expect(page.getByTestId('crm-people-filter-junk-reason')).toHaveCount(0);
    await expect(page.locator('.ctc-ds__table tbody tr').first()).toBeVisible();

    await page.getByTestId('crm-people-tab-missing').click();
    await expect(page.locator('.ctc-ds__table tbody tr').first()).toBeVisible();

    await page.getByTestId('crm-people-tab-all').click();
    const search = page.getByTestId('crm-people-search');
    await search.fill('Lale');
    await expect(page.locator('.ctc-ds__table tbody tr').first()).toBeVisible({ timeout: 15_000 });

    await page.getByTestId('crm-people-filter-category').selectOption('agent');
    await page.getByTestId('crm-people-filter-source').selectOption('bitrix');
    await expect(page.getByTestId('crm-people-workspace')).toBeVisible();

    await page.getByTestId('crm-people-filter-category').selectOption('');
    await page.getByTestId('crm-people-filter-source').selectOption('');
    await search.fill('');
    await expect(page.locator('.ctc-ds__table tbody tr').first()).toBeVisible({ timeout: 15_000 });
    await page.locator('.ctc-ds__table tbody tr').first().click();
    await expect(page.getByTestId('unified-contact-card')).toBeVisible({ timeout: 20_000 });
  });
});
