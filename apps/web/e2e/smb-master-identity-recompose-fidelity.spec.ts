import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { expect, test } from '@playwright/test';
import { DEMO_USERS, loginAs } from './fixtures';

const RECOMPOSE_PROMPT = [
  "Başlığı 'Zamansız Bir Yaşam' yap.",
  'Soldaki ilk açıklamayı kaldır.',
  "Logoyu %15 küçült.",
  "Arka planı, CTA'yı, diğer metinleri ve renkleri değiştirme.",
].join('\n');

const screenshotDir = resolve(process.cwd(), '../artifacts/smb-master-identity-recompose-fidelity');

test.describe('SMB master identity + CREATIVE_RECOMPOSE fidelity', () => {
  test('revise currently selected Temple finished-ad then restore the same selection on refresh', async ({
    page,
  }) => {
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
        body = (await response.json()) as Record<string, unknown>;
      } catch {
        /* ignore */
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
      masterFinishedAdAssetId: (await artboard.getAttribute('data-master-finished-ad-asset-id')) || '',
    };
    await page.screenshot({
      path: resolve(screenshotDir, 'smb-before.png'),
      fullPage: false,
    });

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
    const identityAfter = {
      postId: (await artboard.getAttribute('data-selected-post-id')) || '',
      campaignId: (await artboard.getAttribute('data-campaign-id')) || '',
      coverAssetId: (await artboard.getAttribute('data-cover-asset-id')) || '',
      masterFinishedAdAssetId: (await artboard.getAttribute('data-master-finished-ad-asset-id')) || '',
    };

    await page.screenshot({
      path: resolve(screenshotDir, 'smb-after-recompose.png'),
      fullPage: false,
    });

    expect(generateAdDuringRevise, 'must not create a new campaign via generate-ad').toBe(0);
    expect(identityAfter.postId).toBe(identityBefore.postId);
    expect(identityAfter.campaignId).toBe(identityBefore.campaignId);
    if (identityBefore.masterFinishedAdAssetId) {
      expect(identityAfter.masterFinishedAdAssetId).toBe(identityBefore.masterFinishedAdAssetId);
    }

    if (recompose?.status === 200) {
      expect(recompose.body?.revision_route).toBe('CREATIVE_RECOMPOSE');
      const quality = (recompose.body?.quality_guard || {}) as Record<string, unknown>;
      expect(quality.composition_fidelity === 'fail' ? 'fail' : 'ok').not.toBe('fail');
    }

    await page.reload();
    await expect(page.getByTestId('smb-ai-design-input')).toBeVisible({ timeout: 30_000 });
    const artboardAfterRefresh = page.getByTestId('smb-artboard');
    await expect(artboardAfterRefresh).toHaveAttribute('data-finished-ad-canvas', 'true', {
      timeout: 30_000,
    });
    const identityRefresh = {
      postId: (await artboardAfterRefresh.getAttribute('data-selected-post-id')) || '',
      campaignId: (await artboardAfterRefresh.getAttribute('data-campaign-id')) || '',
      coverAssetId: (await artboardAfterRefresh.getAttribute('data-cover-asset-id')) || '',
      masterFinishedAdAssetId:
        (await artboardAfterRefresh.getAttribute('data-master-finished-ad-asset-id')) || '',
    };
    expect(identityRefresh.postId).toBe(identityAfter.postId);
    expect(identityRefresh.campaignId).toBe(identityAfter.campaignId);
    expect(identityRefresh.coverAssetId).toBe(identityAfter.coverAssetId);
    if (identityAfter.masterFinishedAdAssetId) {
      expect(identityRefresh.masterFinishedAdAssetId).toBe(identityAfter.masterFinishedAdAssetId);
    }

    await page.screenshot({
      path: resolve(screenshotDir, 'smb-after-refresh.png'),
      fullPage: false,
    });

    writeFileSync(
      resolve(screenshotDir, 'summary.json'),
      JSON.stringify(
        {
          visual_quality_pass_declared: false,
          identity_before: identityBefore,
          identity_after_recompose: identityAfter,
          identity_after_refresh: identityRefresh,
          recompose_http: recompose?.status ?? null,
          revision_route: recompose?.body?.revision_route ?? null,
          quality_guard:
            recompose?.body?.quality_guard ??
            (recompose?.body?.detail as { quality_guard?: unknown } | undefined)?.quality_guard ??
            null,
          fidelity_message:
            (recompose?.body?.detail as { message?: unknown } | undefined)?.message ?? null,
          rejected_asset_id:
            (recompose?.body?.detail as { rejected_asset_id?: unknown } | undefined)
              ?.rejected_asset_id ?? null,
          final_asset_id: recompose?.body?.final_asset_id ?? null,
          generate_ad_during_revise: generateAdDuringRevise,
          cover_unchanged_on_fail:
            recompose?.status !== 200 && identityAfter.coverAssetId === identityBefore.coverAssetId,
        },
        null,
        2,
      ),
      'utf8',
    );
  });
});
