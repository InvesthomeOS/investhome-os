import { expect, test } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { DEMO_USERS, loginAs } from './fixtures';

const TEMPLE_PROJECT_ID = 'd50708cb-60b3-465a-8b16-6d30f802af8d';
const TEMPLE_LOGO_ID = '7b58877e-efca-4e9a-9027-6fd18fb1b345';

const BRIEF = [
  'The Temple için premium bir lansman reklamı hazırla.',
  'Instagram 4:5 portrait formatında.',
  'Ana mesaj:',
  'ALIRKEN KAZAN',
  '2+1 daire liste fiyatı:',
  '675.000 USD',
  'Lansman avantajı:',
  '%35',
  "The Temple'da yerinizi lansman döneminde alın.",
  'CTA:',
  'PROJEYİ KEŞFET',
].join('\n');

const screenshotDir = resolve(process.cwd(), '../artifacts/ai-first-master-v1');

test.describe('AI-first Master Creative v1 — initial only', () => {
  test('one 4:5 Temple master — no revision', async ({ page }) => {
    test.setTimeout(720_000);
    mkdirSync(screenshotDir, { recursive: true });

    const generatePayloads: Array<{ status: number; body: Record<string, unknown> | null }> = [];
    const campaignPayloads: Array<{ status: number; body: Record<string, unknown> | null }> = [];
    let reviseCount = 0;

    page.on('response', async (response) => {
      const url = response.url();
      if (response.request().method() !== 'POST') return;
      let body: Record<string, unknown> | null = null;
      try {
        body = (await response.json()) as Record<string, unknown>;
      } catch {
        /* ignore */
      }
      if (url.includes('/revise')) reviseCount += 1;
      if (url.includes('/generate-ad')) generatePayloads.push({ status: response.status(), body });
      if (/\/ai\/creative-studio\/campaigns\/?$/.test(url.split('?')[0] || '')) {
        campaignPayloads.push({ status: response.status(), body });
      }
    });

    await page.addInitScript(() => {
      try {
        window.localStorage.removeItem('ih-smb-draft-emergency');
        for (let i = window.sessionStorage.length - 1; i >= 0; i -= 1) {
          const key = window.sessionStorage.key(i);
          if (key && key.startsWith('ih.cs.smb.selectedIdentity')) {
            window.sessionStorage.removeItem(key);
          }
        }
      } catch {
        /* ignore */
      }
    });

    await loginAs(page, DEMO_USERS.marketing);
    await page.setViewportSize({ width: 1600, height: 1000 });
    await page.goto('/workspaces/creative-studio/social-media-builder');
    await expect(page.getByTestId('smb-ai-design-input')).toBeVisible({ timeout: 30_000 });

    const projectSelect = page.locator('#smb-project');
    await expect.poll(async () => projectSelect.locator('option').count(), { timeout: 30_000 }).toBeGreaterThan(1);
    const options = projectSelect.locator('option');
    const n = await options.count();
    let templeValue = '';
    for (let i = 0; i < n; i += 1) {
      const label = ((await options.nth(i).textContent()) || '').toLowerCase();
      const value = await options.nth(i).getAttribute('value');
      if (value && (label.includes('temple') || label.includes('tapınak') || label.includes('tapinak'))) {
        templeValue = value;
        break;
      }
    }
    expect(templeValue).toBe(TEMPLE_PROJECT_ID);
    await projectSelect.selectOption(templeValue);

    const workspace = page.getByTestId('smb-workspace');
    await expect(workspace).toHaveAttribute('data-construction-project-id', TEMPLE_PROJECT_ID, {
      timeout: 45_000,
    });
    await expect(workspace).toHaveAttribute('data-load-status', 'ready', { timeout: 45_000 });
    await expect(projectSelect).toHaveValue(TEMPLE_PROJECT_ID);

    await expect(page.locator('[data-testid^="smb-post-card-"][data-finished-ad-canvas="true"]')).toHaveCount(0, {
      timeout: 20_000,
    });

    await page.getByTestId('smb-local-rail-left-ai').click();
    await expect(page.getByTestId('smb-ai-prompt')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId('smb-ai-generate')).toBeEnabled();
    await page.getByTestId('smb-ai-prompt').fill(BRIEF);
    await expect(page.getByTestId('smb-ai-generate')).toBeEnabled();

    const generateWait = page.waitForResponse(
      (res) => res.url().includes('/generate-ad') && res.request().method() === 'POST',
      { timeout: 600_000 },
    );
    await page.getByTestId('smb-ai-generate').click();
    const generateRes = await generateWait;
    expect(generateRes.status(), await generateRes.text()).toBe(200);
    expect(reviseCount).toBe(0);

    const campaignBody = (campaignPayloads[campaignPayloads.length - 1]?.body || {}) as Record<
      string,
      unknown
    >;
    expect(String(campaignBody.project_id || '')).toBe(TEMPLE_PROJECT_ID);

    const artboard = page.getByTestId('smb-artboard');
    await expect(artboard).toHaveAttribute('data-finished-ad-canvas', 'true', { timeout: 60_000 });
    await expect(artboard).toHaveAttribute('data-generation-lifecycle', 'ready', { timeout: 60_000 });
    await expect(artboard).toHaveAttribute('data-image-state', 'ready', { timeout: 60_000 });
    await expect.poll(async () => (await artboard.boundingBox())?.width ?? 0, { timeout: 30_000 }).toBeGreaterThan(240);

    const genBody = (generatePayloads[generatePayloads.length - 1]?.body || {}) as Record<string, unknown>;
    expect(genBody.production_mode).toBe('finished_ad');
    expect(String(genBody.project_id || '')).toBe(TEMPLE_PROJECT_ID);
    expect(genBody.format_preset).toBe('portrait');
    expect(genBody.aspect_ratio).toBe('4:5');
    expect(Array.isArray(genBody.editable_layers) ? genBody.editable_layers : []).toHaveLength(0);

    const texts = (genBody.final_turkish_texts || {}) as Record<string, string>;
    expect(texts.headline).toMatch(/ALIRKEN KAZAN/i);
    expect(texts.unit).toContain('2+1');
    expect(String(texts.list_price || '')).toMatch(/675/);
    expect(String(texts.value_badge || '')).toMatch(/35/);
    expect(texts.cta).toMatch(/PROJEYİ KEŞFET|PROJEYI KEŞFET/i);

    const master = (genBody.master_creative || {}) as Record<string, unknown>;
    expect(master.workflow).toBe('ai_first_master_v1');
    expect(master.format).toBe('4:5');
    expect(master.ad_scope).toBe('project');
    expect(String(master.project_id || '')).toBe(TEMPLE_PROJECT_ID);
    expect(String(master.source_visual_asset_id || '')).toBe(String(genBody.interior_asset_id || ''));
    expect(String(master.logo_asset_id || '')).toBe(String(genBody.logo_asset_id || ''));
    expect(String(master.logo_asset_id || '')).toBe(TEMPLE_LOGO_ID);

    const sourceName = String(master.source_visual_filename || '').toLowerCase();
    expect(sourceName).not.toContain('screencapture');
    expect(sourceName).not.toContain('localhost');
    expect(sourceName).toMatch(/ih_dc_tmp|render|temple/);
    const folder = String(master.source_visual_folder || '');
    expect(folder.length === 0 || /RENDER|02_/i.test(folder)).toBeTruthy();

    await expect.poll(async () => {
      return page.getByTestId('smb-artboard-img').evaluate((img) => {
        const el = img as HTMLImageElement;
        return el.complete && el.naturalWidth > 80;
      });
    }, { timeout: 60_000 }).toBe(true);

    await expect(page.locator('[data-testid^="smb-post-card-"]')).toHaveCount(1);

    await page.screenshot({ path: resolve(screenshotDir, 'smb-ai-first-master-fullpage.png'), fullPage: true });
    await artboard.screenshot({ path: resolve(screenshotDir, 'smb-ai-first-master-initial.png') });

    writeFileSync(resolve(screenshotDir, 'generate-response.json'), JSON.stringify(genBody, null, 2));
    writeFileSync(
      resolve(screenshotDir, 'summary.json'),
      JSON.stringify(
        {
          campaignId: genBody.campaign_id,
          linkedProjectId: master.project_id,
          postId: await artboard.getAttribute('data-selected-post-id'),
          productionMode: genBody.production_mode,
          format: genBody.aspect_ratio,
          formatPreset: genBody.format_preset,
          interiorAssetId: genBody.interior_asset_id,
          logoAssetId: genBody.logo_asset_id,
          masterCreative: master,
          providerCallCount: genBody.gpt_image_call_count ?? genBody.provider_call_count,
          reviseCount,
          qualityGuard: genBody.quality_guard,
        },
        null,
        2,
      ),
    );
  });
});
