import { test, expect, loginAs, DEMO_USERS } from './fixtures';

async function mockJson(route, status: number, body: unknown) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  });
}

test.describe('MFA admin reset UI', () => {
  test('unauthorized users cannot see Reset MFA', async ({ page }) => {
    await loginAs(page, DEMO_USERS.executive);
    await page.goto('/dashboard/admin/users');
    await expect(page.getByRole('heading', { name: /users|kullanıcılar/i }).first()).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId('mfa-reset-button')).toHaveCount(0);
    await expect(page.getByTestId('mfa-reset-confirm-dialog')).toHaveCount(0);
  });

  test('security:manage sees Reset MFA, confirmation is required, POST hits existing endpoint', async ({
    page,
  }) => {
    const posted: string[] = [];
    await page.route('**/users/**/mfa/reset', async (route) => {
      posted.push(route.request().url());
      expect(route.request().method()).toBe('POST');
      await mockJson(route, 200, {
        message: 'MFA reset. User must sign in again with password.',
        sessions_revoked: 2,
      });
    });

    await loginAs(page, DEMO_USERS.superadmin);
    await page.goto('/dashboard/admin/users');
    await expect(page.getByTestId('mfa-reset-button').first()).toBeVisible({ timeout: 30_000 });

    await page.getByTestId('mfa-reset-button').first().click();
    await expect(page.getByTestId('mfa-reset-confirm-dialog')).toBeVisible();
    await expect(page.getByTestId('mfa-reset-confirm-dialog')).toContainText(
      /All active sessions for this user will be revoked|tüm aktif oturumları iptal/i,
    );

    await page.getByTestId('mfa-reset-cancel').click();
    await expect(page.getByTestId('mfa-reset-confirm-dialog')).toHaveCount(0);
    expect(posted).toEqual([]);

    const targetButton = page.getByTestId('mfa-reset-button').nth(1);
    const targetId = await targetButton.getAttribute('data-user-id');
    expect(targetId).toBeTruthy();
    await targetButton.click();
    await page.getByTestId('mfa-reset-confirm').click();
    await expect.poll(() => posted.length).toBe(1);
    expect(posted[0]).toContain(`/users/${targetId}/mfa/reset`);
    await expect(page.getByText(/MFA reset\. All sessions for this user were revoked\.|MFA sıfırlandı\. Bu kullanıcının tüm oturumları iptal edildi\./)).toBeVisible();
    await expect(page).toHaveURL(/\/dashboard\/admin\/users/);
  });

  test('self-reset redirects to login', async ({ page }) => {
    await page.route('**/users/**/mfa/reset', async (route) => {
      expect(route.request().method()).toBe('POST');
      await mockJson(route, 200, {
        message: 'MFA reset. User must sign in again with password.',
        sessions_revoked: 1,
      });
    });

    await loginAs(page, DEMO_USERS.superadmin);
    await page.goto('/dashboard/admin/users');
    const selfRow = page.locator('tr', { hasText: DEMO_USERS.superadmin });
    await expect(selfRow.getByTestId('mfa-reset-button')).toBeVisible({ timeout: 30_000 });
    await selfRow.getByTestId('mfa-reset-button').click();
    await expect(page.getByTestId('mfa-reset-confirm-dialog')).toBeVisible();
    await page.getByTestId('mfa-reset-confirm').click();
    await expect(page).toHaveURL(/\/login/, { timeout: 30_000 });
  });
});
