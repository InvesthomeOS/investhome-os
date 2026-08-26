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
    await expect(projectSelect).toBeVisible({ timeout: 30_000 });
    await expect
      .poll(async () => projectSelect.locator('option').count(), { timeout: 30_000 })
      .toBeGreaterThan(1);
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
    expect(templeValue).toBeTruthy();
    await projectSelect.selectOption(templeValue);
    await expect(projectSelect).toHaveValue(templeValue);

    await page.getByTestId('smb-local-rail-left-ai').click();
    await expect(page.getByTestId('smb-ai-prompt')).toBeVisible({ timeout: 15_000 });
    await page.getByTestId('smb-ai-prompt').fill(BRIEF);
    await expect(page.getByTestId('smb-ai-prompt')).toHaveValue(BRIEF);
    await expect(page.getByTestId('smb-ai-generate')).toBeEnabled();

    const campaignWait = page.waitForResponse(
      (res) =>
        res.url().includes('/ai/creative-studio/campaigns') &&
        !res.url().includes('/generate-ad') &&
        !res.url().includes('/revise') &&
        res.request().method() === 'POST',
      { timeout: 120_000 },
    );
    const generateWait = page.waitForResponse(
      (res) => res.url().includes('/generate-ad') && res.request().method() === 'POST',
      { timeout: 600_000 },
    );
    await page.getByTestId('smb-ai-generate').click();
    const campaignRes = await campaignWait;
    expect(campaignRes.status(), await campaignRes.text()).toBe(200);
    const generateRes = await generateWait;
    expect(generateRes.status()).toBe(200);

    const artboard = page.getByTestId('smb-artboard');
    await expect(artboard).toHaveAttribute('data-finished-ad-canvas', 'true', { timeout: 60_000 });
    await expect(artboard).toHaveAttribute('data-generation-lifecycle', 'ready', { timeout: 60_000 });
    await page.screenshot({
      path: resolve(screenshotDir, 'smb-generation-engine-v1-lock.png'),
      fullPage: true,
    });
    await artboard.screenshot({ path: resolve(screenshotDir, 'artboard-lock.png') });

    const campaign = campaignPayloads[campaignPayloads.length - 1];
    expect(campaign?.status).toBe(200);
    const campaignCtx = (campaign?.body?.campaign_context || {}) as Record<string, unknown>;
    const engine = (campaignCtx.generation_engine || {}) as Record<string, unknown>;
    expect(engine.ad_scope).toBe('brand');
    expect(engine.format_preset).toBe('portrait');
    expect(engine.aspect_ratio).toBe('4:5');
    expect(engine.production_mode).toBe('finished_ad');
    expect(engine.native_renderer_primary).toBe(false);

    const drive = (campaignCtx.drive_research || {}) as Record<string, unknown>;
    const hero = (drive.selected_interior || {}) as Record<string, unknown>;
    const logo = (drive.selected_logo || {}) as Record<string, unknown>;
    const truth = (drive.architecture_truth || {}) as Record<string, unknown>;
    expect(hero.project_relation).toBe('brand_independent');
    expect(logo.project_relation).toBe('brand_independent');
    expect(String(hero.filename || '').toLowerCase()).not.toContain('temple');
    expect(String(hero.filename || '').toLowerCase()).not.toContain('screencapture');
    expect(String(hero.filename || '').toLowerCase()).not.toContain('localhost');
    expect(String(logo.filename || '').toLowerCase()).toContain('investhome');
    const design = (campaignCtx.design_direction || {}) as Record<string, unknown>;
    const designBlob = Object.values(design).join(' ').toLowerCase();
    expect(designBlob).not.toContain('approved interiors only');
    const trace = (hero.selection_trace || truth.asset_trace || {}) as Record<string, unknown>;
    expect(String(trace.asset_id || hero.asset_id || '')).toBeTruthy();
    expect(String(trace.visual_role || hero.role || '')).toBe('city_visual');
    expect(String(trace.approval_status || '')).toMatch(/approved|unapproved/);

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
    const assetLock = (pb.asset_lock || {}) as Record<string, unknown>;
    const archTruth = (pb.architecture_truth || {}) as Record<string, unknown>;
    expect(assetLock.project_relation).toBe('brand_independent');
    expect(archTruth.project_relation).toBe('brand_independent');

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
          project_relation: hero.project_relation,
          design_direction: design,
          visual_asset: {
            asset_id: hero.asset_id,
            filename: hero.filename,
            role: hero.role,
            selection_trace: trace,
          },
          asset_approval_status: trace.approval_status || hero.approved_status,
          logo_asset: {
            asset_id: logo.asset_id,
            filename: logo.filename,
            role: logo.role,
          },
          campaign_status: campaign?.status,
          generate_status: gen?.status,
          production_mode: genBody.production_mode,
          format_preset: genBody.format_preset,
          aspect_ratio: genBody.aspect_ratio,
          interior_asset_id: genBody.interior_asset_id,
          logo_asset_id: genBody.logo_asset_id,
          provider_call_count: genBody.provider_call_count,
          gpt_image_call_count: genBody.gpt_image_call_count,
          screenshot: 'artifacts/creative-generation-engine-v1/smb-generation-engine-v1-lock.png',
        },
        null,
        2,
      ),
    );
  });
});
