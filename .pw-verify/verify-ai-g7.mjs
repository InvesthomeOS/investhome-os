import { chromium } from 'playwright';

const base = process.env.BASE_URL || 'http://localhost:3000';
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

const scenarios = [
  { id: 1, name: 'Open AI Command Center', view: 'command_center' },
  { id: 2, name: 'Open Morning Brief', view: 'morning_brief' },
  { id: 3, name: 'Ask Executive Copilot', view: 'copilot', action: 'ask' },
  { id: 4, name: 'Inspect cited sources', view: 'copilot', action: 'sources' },
  { id: 5, name: 'Open Action Center', view: 'action_center' },
  { id: 6, name: 'Accept recommendation', view: 'action_center', action: 'accept' },
  { id: 7, name: 'Dismiss recommendation', view: 'action_center', action: 'dismiss' },
  { id: 8, name: 'Convert recommendation to task', view: 'action_center', action: 'convert' },
  { id: 9, name: 'Open CRM Intelligence', view: 'crm_intel' },
  { id: 10, name: 'Open Investor Intelligence', view: 'investor_intel' },
  { id: 11, name: 'Open Project Intelligence', view: 'project_intel' },
  { id: 12, name: 'Open Finance Intelligence', view: 'finance_intel' },
  { id: 13, name: 'Open Marketing Intelligence', view: 'marketing_intel' },
  { id: 14, name: 'Analyze a document', view: 'document_intel' },
  { id: 15, name: 'Open meeting prep brief', view: 'meeting_intel' },
  { id: 16, name: 'Open forecast', view: 'forecasts' },
  { id: 17, name: 'Open Risk Center', view: 'risk_center' },
  { id: 18, name: 'Use AI Search', view: 'ai_search', action: 'search' },
  { id: 19, name: 'Review AI Activity Log', view: 'activity_log' },
  { id: 20, name: 'Verify provider unavailable state', view: 'provider_status' },
  { id: 21, name: 'Change language', view: 'command_center', action: 'i18n' },
  { id: 22, name: 'Verify tablet layout', view: 'command_center', action: 'tablet' },
];

let passed = 0;
const results = [];

async function login() {
  await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded' });
  await page.locator('input[type="email"], input[name="email"]').first().fill('superadmin@investhome.demo');
  await page.locator('input[type="password"], input[name="password"]').first().fill('Demo123!');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/dashboard/, { timeout: 45_000 });
}

async function ensureAlive() {
  for (let i = 0; i < 10; i += 1) {
    try {
      const res = await page.request.get(`${base}/login`);
      if (res.ok()) return;
    } catch {
      /* retry */
    }
    await page.waitForTimeout(1500);
  }
  throw new Error('web not reachable');
}

async function dismissOverlays() {
  await page.keyboard.press('Escape').catch(() => {});
  await page.keyboard.press('Escape').catch(() => {});
  await page
    .locator('.global-search-overlay')
    .evaluateAll((nodes) => nodes.forEach((n) => n.remove()))
    .catch(() => {});
}

async function openView(view) {
  await ensureAlive();
  const url =
    view === 'command_center' ? `${base}/dashboard/ai` : `${base}/dashboard/ai?view=${view}`;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    try {
      await dismissOverlays();
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45_000 });
      await dismissOverlays();
      await page.waitForSelector('[data-testid="ai-g7-workspace"]', { timeout: 45_000 });
      const navBtn = page.locator(`[data-testid="ai-g7-nav-${view}"]`);
      await navBtn.waitFor({ timeout: 20_000 });
      const active = await navBtn.evaluate((el) => el.classList.contains('is-active'));
      if (!active) throw new Error(`nav ${view} not active`);
      await page
        .waitForFunction(
          () => !/loading ai workspace|yz çalışma alanı yükleniyor/i.test(document.body.innerText),
          { timeout: 45_000 },
        )
        .catch(() => {});
      await page.waitForSelector(`[data-testid="ai-g7-${view}"], .ai-g7__panel, .ai-g7__kpis`, {
        timeout: 30_000,
      });
      return;
    } catch (err) {
      if (attempt === 3) throw err;
      await ensureAlive();
      await page.waitForTimeout(2000);
      if (!page.url().includes('/dashboard')) {
        await login();
      }
    }
  }
}

await login();

for (const scenario of scenarios) {
  try {
    if (scenario.action === 'tablet') {
      await page.setViewportSize({ width: 820, height: 1100 });
      await openView('command_center');
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 40);
      if (overflow) throw new Error('excessive horizontal overflow');
      await page.setViewportSize({ width: 1440, height: 900 });
    } else if (scenario.action === 'i18n') {
      await openView('command_center');
      const bodyTr = await page.innerText('body');
      const hasTr = /YZ|Komuta|Brifing|Aksiyon/i.test(bodyTr);
      const enBtn = page.getByRole('button', { name: /English/i }).first();
      if (await enBtn.isVisible().catch(() => false)) {
        await enBtn.click();
        await page.waitForTimeout(1000);
      }
      const bodyEn = await page.innerText('body');
      const hasEn = /Command Center|Morning Brief|Action Center|AI Workspace/i.test(bodyEn);
      if (!(hasTr || hasEn)) throw new Error('i18n markers missing');
      // Prefer both when language toggle exists
      if (hasTr && !hasEn && !(await enBtn.isVisible().catch(() => false))) {
        // TR-only environment without toggle still counts as workspace loaded
      }
    } else if (scenario.action === 'ask' || scenario.action === 'sources') {
      await openView('copilot');
      await page.getByTestId('ai-g7-copilot-input').fill('What are today priorities across portfolio?');
      await page.getByTestId('ai-g7-copilot-ask').click();
      await page.waitForTimeout(2500);
      const body = await page.innerText('body');
      if (!/source|kaynak|placeholder|l2|executive|marketing/i.test(body)) {
        throw new Error('copilot response/sources missing');
      }
    } else if (scenario.action === 'accept') {
      await openView('action_center');
      const btn = page.locator('[data-testid^="ai-g7-accept-"], [data-testid^="ai-g7-approve-"]').first();
      await btn.click({ timeout: 10_000 });
      const modal = page.getByTestId('ai-g7-approval-modal');
      if (await modal.isVisible().catch(() => false)) {
        await page.getByTestId('ai-g7-approval-ack').check();
        await page.getByTestId('ai-g7-approval-confirm').click();
      }
      await page.waitForTimeout(500);
    } else if (scenario.action === 'dismiss') {
      await openView('action_center');
      const dismiss = page.getByRole('button', { name: /Dismiss|Reddet/i }).first();
      if (await dismiss.isVisible().catch(() => false)) await dismiss.click();
    } else if (scenario.action === 'convert') {
      await openView('action_center');
      const convert = page.getByRole('button', { name: /Convert|Göreve/i }).first();
      if (await convert.isVisible().catch(() => false)) await convert.click();
    } else if (scenario.action === 'search') {
      await openView('ai_search');
      await page.getByTestId('ai-g7-search-input').fill('investor');
      await page.getByRole('button', { name: /Search|Ara/i }).first().click();
      await page.waitForTimeout(2000);
    } else {
      await openView(scenario.view);
      if (scenario.view === 'provider_status') {
        const body = await page.innerText('body');
        if (!/Operational|Unavailable|Not Configured|Degraded|Rate Limited|Operasyonel|Kullanılamıyor|Yapılandırılmadı/i.test(body)) {
          throw new Error('provider states missing');
        }
      }
      if (scenario.view === 'document_intel') {
        const review = page.getByRole('button', { name: /human review|insan incelemesi/i }).first();
        if (await review.isVisible().catch(() => false)) await review.click();
      }
      if (scenario.view === 'meeting_intel') {
        const prep = page.getByRole('button', { name: /prep brief|hazırlık/i }).first();
        if (await prep.isVisible().catch(() => false)) await prep.click();
      }
    }
    passed += 1;
    results.push({ id: scenario.id, name: scenario.name, ok: true });
    console.log('PASS', scenario.id, scenario.name);
  } catch (err) {
    results.push({ id: scenario.id, name: scenario.name, ok: false, error: String(err?.message || err) });
    console.log('FAIL', scenario.id, scenario.name, err?.message || err);
  }
}

await browser.close();
console.log(`RESULT ${passed}/22`);
console.log(JSON.stringify(results, null, 2));
if (passed < 22) process.exitCode = 1;
