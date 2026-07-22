import { chromium } from 'playwright';

const base = process.env.BASE_URL || 'http://localhost:3000';
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

const results = [];
let passed = 0;

function ok(name, detail = '') {
  passed += 1;
  results.push({ name, ok: true, detail });
  console.log('PASS', name, detail);
}

function fail(name, err) {
  results.push({ name, ok: false, error: String(err?.message || err) });
  console.log('FAIL', name, err?.message || err);
}

async function login(email, password) {
  await context.clearCookies();
  await page.goto(`${base}/portal/login`, { waitUntil: 'domcontentloaded' });
  await page.getByTestId('portal-login-email').fill(email);
  await page.getByTestId('portal-login-password').fill(password);
  await page.getByTestId('portal-login-submit').click();
  await page.waitForSelector('[data-testid="portal-shell"]', { timeout: 45_000 });
}

try {
  try {
    await login('investor.a@investhome.demo', 'Portal123!');
    await page.waitForSelector('[data-testid="portal-dashboard"]', { timeout: 20_000 });
    ok('1-login-dashboard');
  } catch (e) {
    fail('1-login-dashboard', e);
  }

  for (const [name, url, testid] of [
    ['2-portfolio', '/portal/portfolio', 'portal-portfolio'],
    ['3-payments', '/portal/payments', 'portal-payments'],
    ['4-documents', '/portal/documents', 'portal-documents'],
    ['5-reports', '/portal/reports', 'portal-reports'],
    ['6-notifications', '/portal/notifications', 'portal-notifications'],
    ['7-messages', '/portal/messages', 'portal-messages'],
  ]) {
    try {
      await page.goto(`${base}${url}`, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector(`[data-testid="${testid}"]`, { timeout: 20_000 });
      ok(name);
    } catch (e) {
      fail(name, e);
    }
  }

  try {
    await page.goto(`${base}/portal`, { waitUntil: 'domcontentloaded' });
    await page.getByTestId('portal-lang').getByRole('button', { name: 'EN' }).click();
    await page.waitForTimeout(600);
    await page.getByTestId('portal-lang').getByRole('button', { name: 'TR' }).click();
    await page.waitForTimeout(600);
    ok('8-localization');
  } catch (e) {
    fail('8-localization', e);
  }

  try {
    await page.setViewportSize({ width: 820, height: 1100 });
    await page.goto(`${base}/portal/portfolio`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('[data-testid="portal-portfolio"]', { timeout: 20_000 });
    ok('9-responsive-tablet');
  } catch (e) {
    fail('9-responsive-tablet', e);
  }

  try {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`${base}/portal/portfolio`, { waitUntil: 'domcontentloaded' });
    const leak = await page.getByText('Bosphorus Tower (CONFIDENTIAL B)').count();
    if (leak !== 0) throw new Error('Investor A saw Investor B holding');
    const own = await page.getByTestId('portal-holding-hold-a1').count();
    if (own < 1) throw new Error('Investor A missing own holding');
    const forbidden = await page.request.get(`${base}/api/portal/documents/doc-b1/download`);
    if (forbidden.status() !== 403) throw new Error(`Expected 403 for B doc, got ${forbidden.status()}`);
    const allowed = await page.request.get(`${base}/api/portal/documents/doc-a1/download`);
    if (allowed.status() !== 200) throw new Error(`Expected 200 for A doc, got ${allowed.status()}`);
    ok('10-permission-isolation-A');
  } catch (e) {
    fail('10-permission-isolation-A', e);
  }

  try {
    await login('investor.b@investhome.demo', 'Portal123!');
    await page.goto(`${base}/portal/portfolio`, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('[data-testid="portal-portfolio"]', { timeout: 20_000 });
    const hasB = await page.getByText('Bosphorus Tower (CONFIDENTIAL B)').count();
    if (hasB < 1) throw new Error('Investor B missing own holding');
    const hasA = await page.getByText('Nişantaşı Residence').count();
    if (hasA !== 0) throw new Error('Investor B saw Investor A holding');
    const forbiddenA = await page.request.get(`${base}/api/portal/documents/doc-a1/download`);
    if (forbiddenA.status() !== 403) throw new Error(`Expected 403 for A doc as B, got ${forbiddenA.status()}`);
    ok('11-permission-isolation-B');
  } catch (e) {
    fail('11-permission-isolation-B', e);
  }
} finally {
  await browser.close();
}

console.log(`\nResult: ${passed}/${results.length} passed`);
if (passed !== results.length) process.exit(1);
