import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { expect, test } from '@playwright/test';
import { DEMO_USERS, loginAs } from './fixtures';

const POST_ID = '067c22d3-dcc3-4569-8f3c-127a0afbef98';
const MASTER = 'f1310474-d9b9-45f9-8fde-99aaddbc2431';
const RECOMPOSE_PROMPT = [
  "Başlığı 'Zamansız Bir Yaşam' yap.",
  'Soldaki ilk açıklamayı kaldır.',
  "Logoyu %15 küçült.",
  "Arka planı, CTA'yı, diğer metinleri ve renkleri değiştirme.",
].join('\n');
const screenshotDir = resolve(process.cwd(), '../artifacts/smb-master-preserving-recompose');

test.describe('SMB master-preserving CREATIVE_RECOMPOSE', () => {
  test('one Temple recompose from restored master', async ({ page }) => {
    test.setTimeout(600_000);
    mkdirSync(screenshotDir, { recursive: true });

    const revisePayloads: Array<{ status: number; body: Record<string, unknown> | null }> = [];
    let generateAdDuringRevise = 0;
    let revising = false;

    page.on('request', (request) => {
      if (!revising || request.method() !== 'POST') return;
      if (request.url().includes('/generate-ad')) generateAdDuringRevise += 1;
    });
    page.on('response', async (response) => {
      if (!response.url().includes('/revise') || response.request().method() !== 'POST') return;
      let body: Record<string, unknown> | null = null;
      try {
        body = JSON.parse(await response.text()) as Record<string, unknown>;
      } catch {
        body = null;
      }
      revisePayloads.push({ status: response.status(), body });
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

    const card = page.locator(`[data-testid="smb-post-card-${POST_ID}"]`);
    await expect(card.first()).toBeVisible({ timeout: 20_000 });
    await card.first().locator('button').first().click();

    const artboard = page.getByTestId('smb-artboard');
    await expect(artboard).toHaveAttribute('data-finished-ad-canvas', 'true', { timeout: 20_000 });
    await expect(artboard).toHaveAttribute('data-selected-post-id', POST_ID);
    await expect(artboard).toHaveAttribute('data-cover-asset-id', MASTER);
    await expect(artboard).toHaveAttribute('data-master-finished-ad-asset-id', MASTER);
    await expect(page.getByTestId('smb-artboard-img')).toBeVisible({ timeout: 30_000 });

    const coverBefore = (await artboard.getAttribute('data-cover-asset-id')) || '';
    const masterBefore = (await artboard.getAttribute('data-master-finished-ad-asset-id')) || '';
    await page.screenshot({ path: resolve(screenshotDir, 'smb-before.png'), fullPage: false });

    const submit = page.locator(
      '[data-testid="smb-ai-revision-submit"], [data-testid="smb-ai-design-submit"]',
    );
    await page.getByTestId('smb-ai-design-input').fill(RECOMPOSE_PROMPT);
    revising = true;
    generateAdDuringRevise = 0;
    await submit.first().click();
    await expect.poll(() => revisePayloads.length, { timeout: 480_000 }).toBeGreaterThan(0);
    revising = false;

    const recompose = revisePayloads[revisePayloads.length - 1];
    const detail = (recompose?.body?.detail || {}) as Record<string, unknown>;
    const quality =
      (recompose?.body?.quality_guard as Record<string, unknown> | undefined) ||
      (detail.quality_guard as Record<string, unknown> | undefined) ||
      null;
    const revisionBrief =
      (recompose?.body?.revision_brief as Record<string, unknown> | undefined) || null;

    await expect(page.getByTestId('smb-artboard-img')).toBeVisible({ timeout: 30_000 });
    const coverAfter = (await artboard.getAttribute('data-cover-asset-id')) || '';
    const masterAfter = (await artboard.getAttribute('data-master-finished-ad-asset-id')) || '';
    await page.screenshot({ path: resolve(screenshotDir, 'smb-after.png'), fullPage: false });

    expect(generateAdDuringRevise).toBe(0);
    expect(masterAfter).toBe(MASTER);
    if (recompose?.status !== 200) {
      expect(coverAfter).toBe(coverBefore);
    }

    writeFileSync(
      resolve(screenshotDir, 'summary.json'),
      JSON.stringify(
        {
          visual_quality_pass_declared: false,
          provider_input: {
            image_1: 'IMAGE 1 IS THE DESIGN TO EDIT (master finished-ad)',
            image_2: 'IMAGE 2 IS RECONSTRUCTION MATERIAL ONLY (source photo)',
          },
          change_list: revisionBrief?.change_list || detail.change_list || null,
          lock_list: revisionBrief?.lock_list || detail.lock_list || null,
          provider_result: {
            http: recompose?.status ?? null,
            revision_route: recompose?.body?.revision_route ?? null,
            final_asset_id: recompose?.body?.final_asset_id ?? null,
            rejected_asset_id: detail.rejected_asset_id ?? null,
            message: detail.message ?? null,
          },
          fidelity_result: quality,
          cover_before: coverBefore,
          cover_after: coverAfter,
          master_id: masterAfter || masterBefore,
          provider_call_count:
            recompose?.body?.gpt_image_call_count ??
            recompose?.body?.provider_call_count ??
            detail.gpt_image_call_count ??
            null,
          generate_ad_during_revise: generateAdDuringRevise,
        },
        null,
        2,
      ),
      'utf8',
    );
  });
});
