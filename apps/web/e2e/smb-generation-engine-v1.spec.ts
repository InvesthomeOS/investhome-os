import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { expect, test } from '@playwright/test';
import { DEMO_USERS, loginAs } from './fixtures';

const BRIEF =
  "Washington DC'deki gayrimenkul yatırım fırsatlarını Türkiye'deki yatırımcılara anlatan çarpıcı bir Instagram postu hazırla. Amerikan renklerini kullan.";

const TEMPLE_INTERIOR = 'c3d11c35-d8b7-485c-b216-0a4da68b751a';
const TEMPLE_LOGO = '7b58877e-efca-4e9a-9027-6fd18fb1b345';
const screenshotDir = resolve(process.cwd(), '../artifacts/creative-generation-engine-v1');

test.describe('Creative Generation Engine v1', () => {
  test('short DC prompt → brand finished-ad 4:5 — no extra production instructions', async ({
    page,
  }) => {
    test.setTimeout(720_000);
    mkdirSync(screenshotDir, { recursive: true });

    const campaignPayloads: Array<{ status: number; body: Record<string, unknown> | null }> = [];
    const generatePayloads: Array<{ status: number; body: Record<string, unknown> | null }> = [];

    page.on('response', async (response) => {
      const url = response.url();
      const method = response.request().method();
      if (method !== 'POST') return;
      let body: Record<string, unknown> | null = null;
      try {
        body = (await response.json()) as Record<string, unknown>;
      } catch {
        /* ignore */
      }
      if (
        url.includes('/ai/creative-studio/campaigns') &&
        !url.includes('/generate-ad') &&
        !url.includes('/revise')
      ) {
        campaignPayloads.push({ status: response.status(), body });
      }
      if (url.includes('/generate-ad')) {
        generatePayloads.push({ status: response.status(), body });
      }
    });

    await loginAs(page, DEMO_USERS.marketing);
    await page.goto('/workspaces/creative-studio/social-media-builder');
    await expect(page.getByTestId('smb-ai-design-input')).toBeVisible({ timeout: 30_000 });

    const projectSelect = page.locator('#smb-project');
    if (await projectSelect.count()) {
      const options = projectSelect.locator('option');
      const n = await options.count();
      for (let i = 0; i < n; i += 1) {
        const label = ((await options.nth(i).textContent()) || '').toLowerCase();
        const value = await options.nth(i).getAttribute('value');
        if (value && (label.includes('temple') || label.includes('tapınak') || label.includes('tapinak'))) {
          await projectSelect.selectOption(value);
          break;
        }
      }
    }

    await page.getByTestId('smb-local-rail-left-ai').click();
    await expect(page.getByTestId('smb-ai-prompt')).toBeVisible({ timeout: 15_000 });
    await page.getByTestId('smb-ai-prompt').fill(BRIEF);

    const generateWait = page.waitForResponse(
      (res) => res.url().includes('/generate-ad') && res.request().method() === 'POST',
      { timeout: 600_000 },
    );
    await page.getByTestId('smb-ai-generate').click();
    const generateRes = await generateWait;
    expect(generateRes.status()).toBe(200);

    const artboard = page.getByTestId('smb-artboard');
    await expect(artboard).toHaveAttribute('data-finished-ad-canvas', 'true', { timeout: 60_000 });
    await expect(artboard).toHaveAttribute('data-generation-lifecycle', 'ready', { timeout: 60_000 });
    await page.screenshot({
      path: resolve(screenshotDir, 'smb-generation-engine-v1.png'),
      fullPage: true,
    });
    await artboard.screenshot({ path: resolve(screenshotDir, 'artboard.png') });

    const campaign = campaignPayloads[campaignPayloads.length - 1];
    expect(campaign?.status).toBe(200);
    const campaignCtx = (campaign?.body?.campaign_context || {}) as Record<string, unknown>;
    const engine = (campaignCtx.generation_engine || {}) as Record<string, unknown>;
    expect(engine.ad_scope).toBe('brand');
    expect(engine.format_preset).toBe('portrait');
    expect(engine.aspect_ratio).toBe('4:5');
    expect(engine.production_mode).toBe('finished_ad');
    expect(engine.native_renderer_primary).toBe(false);

    const gen = generatePayloads[generatePayloads.length - 1];
    expect(gen?.status).toBe(200);
    const genBody = gen?.body || {};
    expect(genBody.production_mode).toBe('finished_ad');
    expect(genBody.format_preset).toBe('portrait');
    expect(genBody.aspect_ratio).toBe('4:5');
    expect(String(genBody.interior_asset_id || '')).not.toBe(TEMPLE_INTERIOR);
    expect(String(genBody.logo_asset_id || '')).not.toBe(TEMPLE_LOGO);

    const pb = (genBody.production_brief || {}) as Record<string, unknown>;
    const pbEngine = (pb.generation_engine || engine) as Record<string, unknown>;
    expect(pbEngine.ad_scope).toBe('brand');

    const gpt = (genBody.gpt_image || {}) as Record<string, unknown>;
    const extras = Array.isArray(gpt.extra_images) ? (gpt.extra_images as Array<Record<string, unknown>>) : [];
    expect(extras.some((row) => row.role === 'investhome_logo')).toBe(true);
    expect(extras.some((row) => row.role === 'project_logo')).toBe(false);

    writeFileSync(
      resolve(screenshotDir, 'summary.json'),
      JSON.stringify(
        {
          user_brief: BRIEF,
          classification: engine,
          campaign_status: campaign?.status,
          generate_status: gen?.status,
          production_mode: genBody.production_mode,
          format_preset: genBody.format_preset,
          aspect_ratio: genBody.aspect_ratio,
          interior_asset_id: genBody.interior_asset_id,
          logo_asset_id: genBody.logo_asset_id,
          provider_call_count: genBody.provider_call_count,
          gpt_image_call_count: genBody.gpt_image_call_count,
          screenshot: 'artifacts/creative-generation-engine-v1/smb-generation-engine-v1.png',
        },
        null,
        2,
      ),
    );
  });
});
