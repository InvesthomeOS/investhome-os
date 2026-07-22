import { chromium } from 'playwright';

const base = process.env.BASE_URL || 'http://localhost:3000';
const results = [];

function pass(name) {
  results.push({ name, ok: true });
  console.log('PASS', name);
}

function fail(name, err) {
  results.push({ name, ok: false, err: String(err) });
  console.error('FAIL', name, err);
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

  await page.goto(`${base}/dashboard/projects`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid="proj-g4-workspace"]', { timeout: 45_000 });

  // 1 portfolio
  try {
    await page.waitForSelector('[data-testid="proj-g4-portfolio"]', { timeout: 20_000 });
    pass('1 portfolio');
  } catch (e) {
    fail('1 portfolio', e);
  }

  // 2 board
  try {
    await page.getByTestId('proj-g4-nav-board').click();
    await page.waitForSelector('[data-testid="proj-g4-board"]', { timeout: 15_000 });
    await page.waitForSelector('[data-testid="proj-g4-col-planned"]');
    await page.waitForSelector('[data-testid="proj-g4-col-completed"]');
    pass('2 construction board');
  } catch (e) {
    fail('2 construction board', e);
  }

  // 3 task drawer
  try {
    const card = page.locator('[data-testid^="proj-g4-task-"]').first();
    await card.waitFor({ timeout: 20_000 });
    await card.click();
    await page.waitForSelector('[data-testid="proj-g4-task-drawer"]', { timeout: 10_000 });
    await page.keyboard.press('Escape').catch(() => {});
    // close via button if still open
    const close = page.locator('[data-testid="proj-g4-task-drawer"] .proj-g4__btn').first();
    if (await close.isVisible().catch(() => false)) await close.click();
    pass('3 task drawer');
  } catch (e) {
    fail('3 task drawer', e);
  }

  const views = [
    ['4 timeline', 'timeline', 'proj-g4-timeline'],
    ['5 milestones', 'milestones', 'proj-g4-milestones'],
    ['6 budget', 'budget', 'proj-g4-budget'],
    ['7 contractors', 'contractors', 'proj-g4-contractors'],
    ['8 permits', 'permits', 'proj-g4-permits'],
    ['9 inspections', 'inspections', 'proj-g4-inspections'],
    ['10 issues', 'issues', 'proj-g4-issues'],
    ['11 analytics', 'analytics', 'proj-g4-analytics'],
  ];

  for (const [name, view, testId] of views) {
    try {
      await page.getByTestId(`proj-g4-nav-${view}`).click();
      await page.waitForSelector(`[data-testid="${testId}"]`, { timeout: 20_000 });
      pass(name);
    } catch (e) {
      fail(name, e);
    }
  }

  // 12 filters
  try {
    await page.getByTestId('proj-g4-nav-portfolio').click();
    await page.waitForSelector('[data-testid="proj-g4-portfolio"]', { timeout: 15_000 });
    await page.locator('.proj-g4__filters input').first().fill('Demo');
    await page.getByRole('button', { name: /Uygula|Apply/i }).click();
    await page.waitForSelector('[data-testid="proj-g4-workspace"]');
    pass('12 filters');
  } catch (e) {
    fail('12 filters', e);
  }

  // 13 Turkish
  try {
    await page.goto(`${base}/dashboard/projects`);
    await page.waitForSelector('[data-testid="proj-g4-workspace"]', { timeout: 30_000 });
    const text = await page.getByTestId('proj-g4-nav-portfolio').innerText();
    if (!/Portföy|Portfolio/.test(text)) throw new Error(`unexpected nav text: ${text}`);
    pass('13 turkish labels');
  } catch (e) {
    fail('13 turkish labels', e);
  }

  // 14 english / tasks
  try {
    const lang = page.getByRole('button', { name: /English|Dil/i }).first();
    if (await lang.isVisible().catch(() => false)) await lang.click();
    await page.getByTestId('proj-g4-nav-tasks').click();
    await page.waitForSelector('[data-testid="proj-g4-tasks"]', { timeout: 15_000 });
    pass('14 tasks / english');
  } catch (e) {
    fail('14 tasks / english', e);
  }

  // 15 keyboard
  try {
    await page.getByTestId('proj-g4-nav-portfolio').click();
    await page.waitForSelector('[data-testid="proj-g4-portfolio"]', { timeout: 15_000 });
    const card = page.locator('[data-testid^="proj-g4-card-"]').first();
    const row = page.locator('[data-testid^="proj-g4-row-"]').first();
    if (await card.isVisible().catch(() => false)) {
      await card.focus();
      await page.keyboard.press('Enter');
    } else {
      await row.focus();
      await page.keyboard.press('Enter');
    }
    await page.waitForSelector('[data-testid="proj-g4-drawer"]', { timeout: 10_000 });
    pass('15 keyboard drawer');
  } catch (e) {
    fail('15 keyboard drawer', e);
  }
} finally {
  await browser.close();
}

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} passed`);
if (failed.length) {
  process.exitCode = 1;
}
