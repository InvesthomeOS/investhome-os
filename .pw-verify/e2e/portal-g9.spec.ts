import { expect, test, type Page } from '@playwright/test';

const INVESTOR_A = {
  email: 'investor.a@investhome.demo',
  password: 'Portal123!',
};
const INVESTOR_B = {
  email: 'investor.b@investhome.demo',
  password: 'Portal123!',
};

async function waitForPortal(page: Page) {
  for (let i = 0; i < 20; i += 1) {
    try {
      const res = await page.request.get('/portal/login');
      if (res.ok()) return;
    } catch {
      /* retry */
    }
    await page.waitForTimeout(1500);
  }
  throw new Error('Portal web not reachable on :3000');
}

async function portalLogin(page: Page, email: string, password: string) {
  await waitForPortal(page);
  await page.goto('/portal/login', { waitUntil: 'domcontentloaded' });
  await page.getByTestId('portal-login-email').fill(email);
  await page.getByTestId('portal-login-password').fill(password);
  await page.getByTestId('portal-login-submit').click();
  await expect(page.getByTestId('portal-shell')).toBeVisible({ timeout: 45_000 });
}

test.describe('G9 Investor Portal', () => {
  test('investor login and dashboard', async ({ page }) => {
    await portalLogin(page, INVESTOR_A.email, INVESTOR_A.password);
    await expect(page.getByTestId('portal-dashboard')).toBeVisible();
    await expect(page.getByTestId('portal-sidebar')).toBeVisible();
  });

  test('portfolio payments documents reports notifications messaging', async ({ page }) => {
    await portalLogin(page, INVESTOR_A.email, INVESTOR_A.password);

    await page.goto('/portal/portfolio');
    await expect(page.getByTestId('portal-portfolio')).toBeVisible();

    await page.goto('/portal/payments');
    await expect(page.getByTestId('portal-payments')).toBeVisible();

    await page.goto('/portal/documents');
    await expect(page.getByTestId('portal-documents')).toBeVisible();
    await page.getByTestId('portal-doc-dl-doc-a1').click();

    await page.goto('/portal/reports');
    await expect(page.getByTestId('portal-reports')).toBeVisible();

    await page.goto('/portal/notifications');
    await expect(page.getByTestId('portal-notifications')).toBeVisible();

    await page.goto('/portal/messages');
    await expect(page.getByTestId('portal-messages')).toBeVisible();
    await expect(page.getByTestId('portal-msg-msg-a1')).toBeVisible();
  });

  test('localization TR/EN', async ({ page }) => {
    await portalLogin(page, INVESTOR_A.email, INVESTOR_A.password);
    await page.goto('/portal');
    await page.getByTestId('portal-lang').getByRole('button', { name: 'TR' }).click();
    await page.waitForTimeout(500);
    await expect(page.getByTestId('portal-dashboard')).toBeVisible();
    await page.getByTestId('portal-lang').getByRole('button', { name: 'EN' }).click();
    await page.waitForTimeout(500);
    await expect(page.getByTestId('portal-dashboard')).toBeVisible();
  });

  test('responsive tablet viewport', async ({ page }) => {
    await portalLogin(page, INVESTOR_A.email, INVESTOR_A.password);
    await page.setViewportSize({ width: 820, height: 1100 });
    await page.goto('/portal/portfolio');
    await expect(page.getByTestId('portal-portfolio')).toBeVisible();
  });

  test('permission isolation — A cannot see B holdings or download B docs', async ({ page }) => {
    await portalLogin(page, INVESTOR_A.email, INVESTOR_A.password);
    await page.goto('/portal/portfolio');
    await expect(page.getByText('Bosphorus Tower (CONFIDENTIAL B)')).toHaveCount(0);
    await expect(page.getByTestId('portal-holding-hold-a1')).toBeVisible();

    const forbidden = await page.request.get('/api/portal/documents/doc-b1/download');
    expect(forbidden.status()).toBe(403);

    const allowed = await page.request.get('/api/portal/documents/doc-a1/download');
    expect(allowed.status()).toBe(200);

    await page.goto('/portal/projects/proj-bosphorus');
    await expect(page.getByTestId('portal-project-detail-missing')).toBeVisible();
  });

  test('investor B session is isolated from A documents', async ({ page }) => {
    await portalLogin(page, INVESTOR_B.email, INVESTOR_B.password);
    await page.goto('/portal/portfolio');
    await expect(page.getByText('Bosphorus Tower (CONFIDENTIAL B)')).toBeVisible();
    await expect(page.getByText('Nişantaşı Residence')).toHaveCount(0);

    const forbiddenA = await page.request.get('/api/portal/documents/doc-a1/download');
    expect(forbiddenA.status()).toBe(403);

    const allowedB = await page.request.get('/api/portal/documents/doc-b1/download');
    expect(allowedB.status()).toBe(200);
  });
});
