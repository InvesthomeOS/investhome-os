import { test, expect, loginAs, DEMO_USERS } from './fixtures';

const CHALLENGE = 'mfa-challenge-token-aaaa';
const USER = {
  id: '00000000-0000-0000-0000-000000000099',
  full_name: 'MFA User',
  email: 'mfa-user@investhome.demo',
  phone: null,
  job_title: null,
  department: null,
  status: 'active',
  preferred_language: 'en',
  timezone: 'UTC',
  avatar_url: null,
  is_demo: true,
  last_login_at: null,
  mfa_enabled: true,
  mfa_method: 'totp',
  roles: [],
  permissions: [],
};

async function mockJson(route, status: number, body: unknown) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  });
}

test.describe('MFA frontend login', () => {
  test('non-MFA login still reaches the dashboard', async ({ page }) => {
    await loginAs(page, DEMO_USERS.sales);
    await expect(page.locator('.dashboard-shell')).toBeVisible();
    await expect(page.getByTestId('mfa-verify-screen')).toHaveCount(0);
  });

  test('MFA users see a second-step screen and stay unauthenticated until verify', async ({ page }) => {
    await page.route('**/auth/me', async (route) => {
      await mockJson(route, 401, { detail: 'Not authenticated' });
    });
    await page.route('**/auth/login', async (route) => {
      await mockJson(route, 200, {
        mfa_required: true,
        mfa_challenge_token: CHALLENGE,
        mfa_method: 'totp',
        expires_in: 300,
      });
    });

    await page.goto('/login');
    await page.fill('input[type="email"]', 'mfa-user@investhome.demo');
    await page.fill('input[type="password"]', 'Investhome2026!');
    await page.click('button[type="submit"]');

    await expect(page.getByTestId('mfa-verify-screen')).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
    await expect(page.locator('.dashboard-shell')).toHaveCount(0);

    const storage = await page.evaluate(() => ({
      local: { ...localStorage },
      session: { ...sessionStorage },
    }));
    const blob = JSON.stringify(storage);
    expect(blob).not.toContain(CHALLENGE);
    expect(blob).not.toContain('otpauth://');
    expect(blob.toLowerCase()).not.toContain('recovery');
  });

  test('invalid TOTP, 429, expired challenge, then recovery code verify', async ({ page }) => {
    let verifyCalls = 0;
    await page.route('**/auth/me', async (route) => {
      await mockJson(route, 401, { detail: 'Not authenticated' });
    });
    await page.route('**/auth/login', async (route) => {
      await mockJson(route, 200, {
        mfa_required: true,
        mfa_challenge_token: CHALLENGE,
        mfa_method: 'totp',
        expires_in: 300,
      });
    });
    await page.route('**/auth/mfa/verify', async (route) => {
      verifyCalls += 1;
      const posted = route.request().postDataJSON() as { challenge_token?: string; code?: string };
      expect(posted.challenge_token).toBe(CHALLENGE);
      if (verifyCalls === 1) {
        await mockJson(route, 401, { detail: 'Invalid or expired verification code' });
        return;
      }
      if (verifyCalls === 2) {
        await mockJson(route, 429, { detail: 'Too many attempts' });
        return;
      }
      if (verifyCalls === 3) {
        await mockJson(route, 401, { detail: 'Invalid or expired verification code' });
        return;
      }
      expect(posted.code).toBe('AAAAA-11111');
      await mockJson(route, 200, USER);
    });

    await page.goto('/login');
    await page.fill('input[type="email"]', 'mfa-user@investhome.demo');
    await page.fill('input[type="password"]', 'Investhome2026!');
    await page.click('button[type="submit"]');
    await expect(page.getByTestId('mfa-verify-screen')).toBeVisible();

    await page.getByTestId('mfa-verify-code').fill('000000');
    await page.getByTestId('mfa-verify-submit').click();
    await expect(page.getByTestId('mfa-verify-error')).toBeVisible();
    await expect(page).toHaveURL(/\/login/);

    await page.getByTestId('mfa-verify-code').fill('111111');
    await page.getByTestId('mfa-verify-submit').click();
    await expect(page.getByTestId('mfa-verify-error')).toBeVisible();

    await page.getByTestId('mfa-verify-code').fill('222222');
    await page.getByTestId('mfa-verify-submit').click();
    await expect(page.getByTestId('mfa-verify-error')).toBeVisible();

    await page.getByTestId('mfa-verify-code').fill('AAAAA-11111');
    await page.getByTestId('mfa-verify-submit').click();
    await expect.poll(() => verifyCalls).toBe(4);
  });
});

test.describe('MFA frontend enrollment', () => {
  test('profile enrollment start/confirm shows recovery codes once', async ({ page }) => {
    await loginAs(page, DEMO_USERS.sales);

    await page.route('**/auth/mfa/enroll/confirm', async (route) => {
      await mockJson(route, 200, {
        mfa_enabled: true,
        mfa_method: 'totp',
        recovery_codes: ['SAVE0-ONCE1', 'SAVE0-ONCE2'],
      });
    });
    await page.route('**/auth/mfa/enroll', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.continue();
        return;
      }
      await mockJson(route, 200, {
        otpauth_uri:
          'otpauth://totp/InvestHomeOS:sales@investhome.demo?secret=JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP&issuer=InvestHomeOS',
        issuer: 'InvestHomeOS',
        account_label: 'sales@investhome.demo',
        pending: true,
      });
    });

    await page.goto('/dashboard/profile');
    await expect(page.getByTestId('mfa-enroll-enable')).toBeVisible();
    await page.getByTestId('mfa-enroll-enable').click();
    await expect(page.getByTestId('mfa-enroll-qr')).toBeVisible();
    await expect(page.getByTestId('mfa-enroll-manual-key')).toContainText('JBSW');

    await page.getByTestId('mfa-enroll-code').fill('123456');
    await page.getByTestId('mfa-enroll-confirm').click();
    await expect(page.getByTestId('mfa-enroll-recovery')).toContainText('SAVE0-ONCE1');
    await expect(page.getByTestId('mfa-enroll-enabled')).toBeVisible();

    await page.getByTestId('mfa-enroll-recovery-ack').click();
    await expect(page.getByTestId('mfa-enroll-recovery')).toHaveCount(0);
    await expect(page.getByTestId('mfa-enroll-enabled')).toBeVisible();

    const storage = await page.evaluate(() => ({
      local: { ...localStorage },
      session: { ...sessionStorage },
    }));
    const blob = JSON.stringify(storage);
    expect(blob).not.toContain('SAVE0-ONCE1');
    expect(blob).not.toContain('otpauth://');
    expect(blob).not.toContain('JBSWY3DPEHPK3PXP');
  });
});
