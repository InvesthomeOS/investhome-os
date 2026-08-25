import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { DEMO_USERS, expect, loginAs, test } from './fixtures';

const RECOMPOSE_PROMPT = [
  "Başlığı 'Zamansız Bir Yaşam' yap.",
  'Soldaki ilk açıklamayı kaldır.',
  "Logoyu %15 küçült.",
  'Arka planı, CTA\'yı, diğer metinleri ve renkleri değiştirme.',
].join('\n');

const MICRO_PROMPT = 'Logoyu %10 küçült. Başka hiçbir şeyi değiştirme.';

const screenshotDir = resolve(process.cwd(), '../artifacts/golden-creative-revision-preservation');

test.describe('Golden Creative Revision Preservation v1', () => {
  test('CREATIVE_RECOMPOSE then MICRO_EDIT then undo on a real Temple finished-ad', async ({
    page,
  }) => {
    test.setTimeout(600_000);
    mkdirSync(screenshotDir, { recursive: true });

    const revisePayloads: Array<{ status: number; body: Record<string, unknown> | null; url: string }> =
      [];
    let revising = false;
    let generateAdDuringRevise = 0;

    page.on('request', (request) => {
      if (!revising || request.method() !== 'POST') return;
      if (request.url().includes('/generate-ad')) generateAdDuringRevise += 1;
    });
    page.on('response', async (response) => {
      if (!response.url().includes('/revise') || response.request().method() !== 'POST') return;
      let body: Record<string, unknown> | null = null;
      try {
        body = (await response.json()) as Record<string, unknown>;
      } catch {
        /* ignore */
      }
      revisePayloads.push({ status: response.status(), body, url: response.url() });
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

    const finishedCard = page.locator(
      '[data-testid^="smb-post-card-"][data-finished-ad-canvas="true"]',
    );
    await expect(finishedCard.first()).toBeVisible({ timeout: 20_000 });
    const realFailing = page.locator(
      '[data-testid^="smb-post-card-"][data-finished-ad-canvas="true"][data-campaign-id="a45f7a43-cade-447e-8aa5-b6d126688ff7"]',
    );
    const cardToOpen = (await realFailing.count()) > 0 ? realFailing.first() : finishedCard.first();
    await cardToOpen.locator('button').first().click();

    const artboard = page.getByTestId('smb-artboard');
    await expect(artboard).toHaveAttribute('data-finished-ad-canvas', 'true', { timeout: 20_000 });

    const identityBefore = {
      postId: (await artboard.getAttribute('data-selected-post-id')) || '',
      campaignId: (await artboard.getAttribute('data-campaign-id')) || '',
      coverAssetId: (await artboard.getAttribute('data-cover-asset-id')) || '',
      interiorAssetId: (await artboard.getAttribute('data-interior-asset-id')) || '',
      logoAssetId: (await artboard.getAttribute('data-logo-asset-id')) || '',
    };
    await page.screenshot({ path: resolve(screenshotDir, 'smb-before.png'), fullPage: false });

    const submit = page.locator(
      '[data-testid="smb-ai-revision-submit"], [data-testid="smb-ai-design-submit"]',
    );
    await page.getByTestId('smb-ai-design-input').fill(RECOMPOSE_PROMPT);
    revising = true;
    generateAdDuringRevise = 0;
    await submit.first().click();
    await expect
      .poll(async () => (await artboard.getAttribute('data-cover-asset-id')) || '', {
        timeout: 480_000,
      })
      .not.toBe(identityBefore.coverAssetId);
    revising = false;

    await page.screenshot({ path: resolve(screenshotDir, 'smb-after-recompose.png'), fullPage: false });

    const recompose = revisePayloads[revisePayloads.length - 1];
    expect(recompose?.status, `recompose HTTP ${recompose?.status}`).toBe(200);
    expect(recompose?.body?.revision_route).toBe('CREATIVE_RECOMPOSE');
    expect(Number(recompose?.body?.gpt_image_call_count ?? 0)).toBeGreaterThan(0);
    expect(generateAdDuringRevise, 'must not create a new campaign via generate-ad').toBe(0);

    const identityAfterRecompose = {
      postId: (await artboard.getAttribute('data-selected-post-id')) || '',
      campaignId: (await artboard.getAttribute('data-campaign-id')) || '',
      coverAssetId: (await artboard.getAttribute('data-cover-asset-id')) || '',
      interiorAssetId: (await artboard.getAttribute('data-interior-asset-id')) || '',
      logoAssetId: (await artboard.getAttribute('data-logo-asset-id')) || '',
    };
    expect(identityAfterRecompose.postId).toBe(identityBefore.postId);
    expect(identityAfterRecompose.campaignId).toBe(identityBefore.campaignId);
    expect(identityAfterRecompose.interiorAssetId).toBe(identityBefore.interiorAssetId);
    expect(identityAfterRecompose.logoAssetId).toBe(identityBefore.logoAssetId);
    expect(identityAfterRecompose.coverAssetId).not.toBe(identityBefore.coverAssetId);

    const hidePlates = page.locator('[data-testid^="smb-el-hide-plate"]');
    await expect(hidePlates).toHaveCount(0);

    await page.getByTestId('smb-ai-design-input').fill(MICRO_PROMPT);
    const beforeMicroCount = revisePayloads.length;
    revising = true;
    generateAdDuringRevise = 0;
    await submit.first().click();
    await expect
      .poll(() => revisePayloads.length, { timeout: 60_000 })
      .toBeGreaterThan(beforeMicroCount);
    revising = false;

    const micro = revisePayloads[revisePayloads.length - 1];
    expect(micro?.status).toBe(200);
    expect(micro?.body?.revision_route).toBe('MICRO_EDIT');
    expect(Number(micro?.body?.gpt_image_call_count ?? 0)).toBe(0);
    expect(generateAdDuringRevise).toBe(0);

    const identityAfterMicro = {
      coverAssetId: (await artboard.getAttribute('data-cover-asset-id')) || '',
      interiorAssetId: (await artboard.getAttribute('data-interior-asset-id')) || '',
      logoAssetId: (await artboard.getAttribute('data-logo-asset-id')) || '',
    };
    expect(identityAfterMicro.coverAssetId).toBe(identityAfterRecompose.coverAssetId);
    expect(identityAfterMicro.interiorAssetId).toBe(identityBefore.interiorAssetId);
    expect(identityAfterMicro.logoAssetId).toBe(identityBefore.logoAssetId);
    await expect(hidePlates).toHaveCount(0);

    await page.screenshot({ path: resolve(screenshotDir, 'smb-after-micro.png'), fullPage: false });

    const undoBtn = page.getByTestId('smb-undo');
    if (await undoBtn.count()) {
      revising = true;
      await undoBtn.click();
      await page.waitForTimeout(1500);
      revising = false;
    }

    writeFileSync(
      resolve(screenshotDir, 'summary.json'),
      JSON.stringify(
        {
          identity_before: identityBefore,
          identity_after_recompose: identityAfterRecompose,
          identity_after_micro: identityAfterMicro,
          revise_payloads: revisePayloads.map((row) => ({
            status: row.status,
            revision_route: row.body?.revision_route ?? null,
            gpt_image_call_count: row.body?.gpt_image_call_count ?? null,
            quality_guard: row.body?.quality_guard ?? null,
            final_asset_id: row.body?.final_asset_id ?? null,
            revision_source_asset_id: row.body?.revision_source_asset_id ?? null,
            interior_asset_id: row.body?.interior_asset_id ?? null,
            logo_asset_id: row.body?.logo_asset_id ?? null,
          })),
        },
        null,
        2,
      ),
      'utf8',
    );
  });
});
