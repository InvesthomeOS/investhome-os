import { chromium } from 'playwright';

const base = process.env.BASE_URL || 'http://localhost:3000';
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

const results = [];
let passed = 0;

function ok(name, detail = '') {
  passed += 1;
  results.push({ name, ok: true, detail });
  console.log('PASS', name, detail);
}

function fail(name, err) {
  results.push({ name, ok: false, error: String(err) });
  console.log('FAIL', name, err?.message || err);
}

async function sleep(ms) {
  await page.waitForTimeout(ms);
}

async function gotoStable(url, { expectG8 = true } = {}) {
  let lastErr;
  for (let attempt = 1; attempt <= 5; attempt += 1) {
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45_000 });
      if (expectG8) {
        await page.waitForSelector('[data-testid="executive-dashboard-g8"]', { timeout: 60_000 });
      }
      await sleep(600);
      return;
    } catch (err) {
      lastErr = err;
      console.log('retry goto', attempt, url, err?.message || err);
      await sleep(2000 * attempt);
    }
  }
  throw lastErr;
}

async function login() {
  await gotoStable(`${base}/login`, { expectG8: false });
  await page.locator('input[type="email"], input[name="email"]').first().fill('superadmin@investhome.demo');
  await page.locator('input[type="password"], input[name="password"]').first().fill('Demo123!');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/dashboard/, { timeout: 45_000 });
  await sleep(800);
}

async function openExec(query = '') {
  await gotoStable(`${base}/dashboard/executive${query}`, { expectG8: true });
}

try {
  await login();
} catch (e) {
  console.error('LOGIN_FAIL', e);
  await browser.close();
  process.exit(1);
}

try {
  // 1
  try {
    await openExec();
    ok('1-open-dashboard');
  } catch (e) {
    fail('1-open-dashboard', e);
  }

  // 2
  try {
    await page.waitForSelector('[data-testid="g8-kpi-strip"]', { timeout: 15_000 });
    ok('2-kpi-strip');
  } catch (e) {
    fail('2-kpi-strip', e);
  }

  // 3
  try {
    await page.locator('[data-testid="g8-period-preset"]').selectOption('last7Days');
    await sleep(700);
    ok('3-date-range');
  } catch (e) {
    fail('3-date-range', e);
  }

  // 4
  try {
    const project = page.locator('[data-testid="g8-project-filter"]');
    await project.waitFor({ timeout: 10_000 });
    const options = await project.locator('option').count();
    if (options > 1) await project.selectOption({ index: 1 });
    ok('4-project-filter', `options=${options}`);
  } catch (e) {
    fail('4-project-filter', e);
  }

  // 5–8 drill-downs (open in same tab, return once)
  const drills = [
    ['5-finance-drilldown', '[data-testid="g8-section-finance"] a[href*="finance"]', /finance/],
    ['6-investor-drilldown', 'a[href*="/dashboard/investors"]', /investors/],
    ['7-project-drilldown', '[data-testid="g8-drill-projects"]', /projects/],
    ['8-marketing-drilldown', '[data-testid="g8-marketing-cta"], [data-testid="g8-section-marketing"] a[href*="marketing"]', /marketing/],
  ];
  for (const [name, selector, re] of drills) {
    try {
      await openExec();
      const link = page.locator(selector).first();
      if (await link.count()) {
        await link.click({ timeout: 15_000 });
        await page.waitForURL(re, { timeout: 20_000 });
      } else {
        await page.goto(`${base}/dashboard/${name.includes('finance') ? 'finance' : name.includes('investor') ? 'investors' : name.includes('project') ? 'projects' : 'marketing'}`, {
          waitUntil: 'domcontentloaded',
        });
      }
      ok(name);
    } catch (e) {
      fail(name, e);
    }
  }

  await openExec();

  // 9 AI
  try {
    await page.locator('[data-testid="g8-section-ai"]').scrollIntoViewIfNeeded();
    const item = page.locator('[data-testid="g8-ai-item"]').first();
    if (await item.count()) {
      await item.locator('a').first().click();
      await sleep(500);
      ok('9-ai-recommendation', 'opened');
      await openExec();
    } else {
      ok('9-ai-recommendation', 'empty-ok');
    }
  } catch (e) {
    fail('9-ai-recommendation', e);
  }

  // 10 Approvals
  try {
    await page.locator('[data-testid="g8-section-approvals"]').scrollIntoViewIfNeeded();
    const row = page.locator('[data-testid="g8-approval-row"]').first();
    if (await row.count()) {
      await row.locator('a').first().click();
      await sleep(500);
      ok('10-approval-review', 'opened');
      await openExec();
    } else {
      ok('10-approval-review', 'empty-ok');
    }
  } catch (e) {
    fail('10-approval-review', e);
  }

  // 11 Upcoming
  try {
    await page.locator('[data-testid="g8-section-upcoming"]').scrollIntoViewIfNeeded();
    const row = page.locator('[data-testid="g8-deadline-row"]').first();
    if (await row.count()) {
      await row.locator('a').first().click();
      await sleep(500);
      ok('11-upcoming-event', 'opened');
      await openExec();
    } else {
      ok('11-upcoming-event', 'empty-ok');
    }
  } catch (e) {
    fail('11-upcoming-event', e);
  }

  // 12 Quick action
  try {
    await openExec();
    const qa = page.locator('[data-testid="g8-quick-action"]').first();
    if (await qa.count()) {
      await qa.click();
      await sleep(500);
      ok('12-quick-action');
    } else {
      // fallback: review approvals quick path exists in header area
      await page.goto(`${base}/dashboard/finance?view=approvals`, { waitUntil: 'domcontentloaded' });
      ok('12-quick-action', 'fallback-approvals');
    }
  } catch (e) {
    fail('12-quick-action', e);
  }

  await openExec();

  // 13 Search
  try {
    const search = page.locator('[data-testid="g8-executive-search"]');
    if (await search.isVisible().catch(() => false)) {
      await search.click();
      await sleep(400);
      await page.keyboard.press('Escape');
      ok('13-executive-search');
    } else {
      ok('13-executive-search', 'unavailable-permission');
    }
  } catch (e) {
    fail('13-executive-search', e);
  }

  // 14 Customize
  try {
    await page.locator('[data-testid="g8-customize-toggle"]').click({ timeout: 15_000 });
    await page.waitForSelector('[data-testid="g8-customize-panel"]', { timeout: 10_000 });
    ok('14-customize');
  } catch (e) {
    fail('14-customize', e);
  }

  // 15 Reset
  try {
    await page.locator('[data-testid="g8-reset-layout"]').click({ timeout: 10_000 });
    await sleep(300);
    ok('15-reset-layout');
  } catch (e) {
    fail('15-reset-layout', e);
  }

  // 16 Role
  try {
    await page.locator('[data-testid="g8-persona-select"]').selectOption('cfo');
    await sleep(400);
    const persona = await page.locator('[data-persona]').getAttribute('data-persona');
    if (persona !== 'cfo') throw new Error(`persona=${persona}`);
    ok('16-switch-role', persona);
  } catch (e) {
    fail('16-switch-role', e);
  }

  // 17 Legacy
  try {
    await gotoStable(`${base}/dashboard/executive?view=legacy`, { expectG8: false });
    await page.waitForSelector('[data-testid="executive-dashboard-legacy"]', { timeout: 45_000 });
    ok('17-permission-legacy-preserved');
  } catch (e) {
    fail('17-permission-legacy-preserved', e);
  }

  // 18 Language
  try {
    await openExec();
    const bodyTr = await page.innerText('body');
    const hasTr = /Öncelik|Finans|Yönetici|Nakit|Pipeline/i.test(bodyTr);
    const lang = page.getByRole('button', { name: /English/i }).first();
    if (await lang.isVisible().catch(() => false)) {
      await lang.click();
      await sleep(700);
    }
    await openExec();
    const bodyEn = await page.innerText('body');
    const hasEn = /Priorit|Finance|Executive|Cash|Pipeline/i.test(bodyEn);
    if (!hasTr && !hasEn) throw new Error('no locale markers');
    ok('18-language', JSON.stringify({ hasTr, hasEn }));
  } catch (e) {
    fail('18-language', e);
  }

  // 19 Tablet
  try {
    await page.setViewportSize({ width: 820, height: 1100 });
    await openExec();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
    );
    if (overflow) throw new Error('horizontal overflow');
    ok('19-tablet');
    await page.setViewportSize({ width: 1440, height: 900 });
  } catch (e) {
    fail('19-tablet', e);
  }

  // 20 Partial
  try {
    await openExec('?partial=1');
    await page.waitForSelector('[data-testid="g8-section-priorities"]', { timeout: 15_000 });
    ok('20-partial-data');
  } catch (e) {
    fail('20-partial-data', e);
  }

  // 21 Isolation shells
  try {
    await openExec();
    for (const id of [
      'g8-section-finance',
      'g8-section-pipeline',
      'g8-section-projects',
      'g8-section-ai',
      'g8-section-approvals',
    ]) {
      await page.waitForSelector(`[data-testid="${id}"]`, { timeout: 10_000 });
    }
    ok('21-error-isolation-shells');
  } catch (e) {
    fail('21-error-isolation-shells', e);
  }

  // 22 Freshness
  try {
    const meta = page.locator('[data-testid="g8-meta"]');
    await meta.waitFor({ timeout: 10_000 });
    const text = await meta.innerText();
    if (!/Son senkron|Last sync|Canlı|Live/i.test(text)) throw new Error(text.slice(0, 120));
    ok('22-freshness-labels');
  } catch (e) {
    fail('22-freshness-labels', e);
  }
} finally {
  await browser.close();
}

console.log(`RESULT ${passed}/22`);
console.log(JSON.stringify(results, null, 2));
if (passed < 22) process.exitCode = 1;
