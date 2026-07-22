import { chromium } from 'playwright';

const base = process.env.BASE_URL || 'http://localhost:3000';
const results = [];

function pass(name) {
  results.push({ name, ok: true });
  console.log('PASS', name);
}

function fail(name, err) {
  results.push({ name, ok: false, err: String(err?.message || err) });
  console.error('FAIL', name, err?.message || err);
}

async function waitReady(page, testId, timeout = 45_000) {
  await page.waitForSelector('[data-testid="mkt-g6-workspace"]', { timeout });
  await page.waitForFunction(
    () => !document.querySelector('[data-testid="mkt-g6-loading"]'),
    null,
    { timeout },
  );
  if (testId) {
    await page.waitForSelector(`[data-testid="${testId}"]`, { timeout });
  }
}

async function clickNav(page, viewId) {
  await page.getByTestId(`mkt-g6-nav-${viewId}`).click();
  await page.waitForTimeout(600);
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

try {
  await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(800);
  await page.locator('input[type="email"], input[name="email"]').first().fill('superadmin@investhome.demo');
  await page.locator('input[type="password"], input[name="password"]').first().fill('Demo123!');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/dashboard/, { timeout: 45_000 });

  // 1 overview
  try {
    await page.goto(`${base}/dashboard/marketing`, { waitUntil: 'domcontentloaded' });
    await waitReady(page, 'mkt-g6-overview');
    pass('1-overview');
  } catch (e) {
    fail('1-overview', e);
  }

  // 2 campaigns
  try {
    await clickNav(page, 'campaigns');
    await waitReady(page, 'mkt-g6-campaigns');
    pass('2-campaigns');
  } catch (e) {
    fail('2-campaigns', e);
  }

  // 3 campaign drawer
  try {
    await clickNav(page, 'campaigns');
    await waitReady(page, 'mkt-g6-campaigns');
    const row = page.locator('[data-testid^="mkt-g6-campaign-row-"], [data-testid^="mkt-g6-campaign-card-"]').first();
    await row.waitFor({ timeout: 30_000 });
    await row.click();
    await page.waitForSelector('[data-testid="mkt-g6-drawer"]', { timeout: 15_000 });
    pass('3-campaign-drawer');
    await page.getByTestId('mkt-g6-drawer-close').click();
  } catch (e) {
    fail('3-campaign-drawer', e);
  }

  // 4 filter
  try {
    await waitReady(page, 'mkt-g6-campaigns');
    await page.getByTestId('mkt-g6-campaign-status').selectOption({ index: 1 });
    await page.waitForTimeout(400);
    pass('4-campaign-filter');
  } catch (e) {
    fail('4-campaign-filter', e);
  }

  // 5 save view
  try {
    await page.getByTestId('mkt-g6-saved-view-name').fill('G6 QA View');
    await page.getByTestId('mkt-g6-save-view').click();
    await page.waitForTimeout(400);
    pass('5-save-view');
  } catch (e) {
    fail('5-save-view', e);
  }

  const views = [
    ['6-attribution', 'attribution', 'mkt-g6-attribution'],
    ['7-funnel', 'funnel', 'mkt-g6-funnel'],
    ['8-lead-sources', 'lead_sources', 'mkt-g6-lead-sources'],
    ['9-website-analytics', 'website_analytics', 'mkt-g6-website-analytics'],
    ['10-seo', 'seo', 'mkt-g6-seo'],
    ['11-content-studio', 'content_studio', 'mkt-g6-content-studio'],
    ['12-blog', 'blog', 'mkt-g6-blog'],
    ['13-social', 'social', 'mkt-g6-social'],
    ['14-email', 'email', 'mkt-g6-email'],
    ['15-paid-ads', 'paid_ads', 'mkt-g6-paid-ads'],
    ['16-landing-pages', 'landing_pages', 'mkt-g6-landing-pages'],
    ['17-calculators', 'calculators', 'mkt-g6-calculators'],
    ['18-calendar', 'calendar', 'mkt-g6-calendar'],
  ];

  for (const [name, viewId, testId] of views) {
    try {
      await clickNav(page, viewId);
      await waitReady(page, testId);
      if (viewId === 'seo') {
        const blocked = await page.locator('.mkt-g6__data-tag--blocked').first().isVisible();
        if (!blocked) throw new Error('SEO should disclose blocked/integration-required');
      }
      pass(name);
    } catch (e) {
      fail(name, e);
    }
  }

  // 19 language
  try {
    await clickNav(page, 'overview');
    await waitReady(page, 'mkt-g6-overview');
    await page.getByTestId('mkt-g6-lang-en').click();
    await page.waitForTimeout(2500);
    await waitReady(page, null);
    pass('19-language');
  } catch (e) {
    fail('19-language', e);
  }

  // 20 tablet
  try {
    await page.setViewportSize({ width: 820, height: 1100 });
    await page.goto(`${base}/dashboard/marketing`, { waitUntil: 'domcontentloaded' });
    await waitReady(page, 'mkt-g6-overview');
    pass('20-tablet');
  } catch (e) {
    fail('20-tablet', e);
  }
} finally {
  await browser.close();
}

const ok = results.filter((r) => r.ok).length;
console.log(`\nRESULT ${ok}/${results.length}`);
if (ok !== results.length) process.exitCode = 1;
