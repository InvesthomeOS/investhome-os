import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { DEMO_USERS, expect, loginAs, test } from './fixtures';

const REVISION_PROMPT = [
  'Üstteki küçük açıklama metnini tamamen kaldır.',
  'Ana başlığı %10 büyüt.',
  'Soldaki iki açıklama metnini %15 büyüt.',
  'Logo, arka plan görseli, CTA butonu, renkler ve tasarımın geri kalanını kesinlikle değiştirme.',
].join('\n');

const screenshotDir = resolve(process.cwd(), '../artifacts/smb-revision-execution-lock');

async function hashArtboardImage(
  page: import('@playwright/test').Page,
): Promise<{ src: string; hash: string; coverAssetId: string }> {
  const artboard = page.getByTestId('smb-artboard');
  const coverAssetId = (await artboard.getAttribute('data-cover-asset-id')) || '';
  const img = page.getByTestId('smb-artboard-img');
  await expect(img).toBeVisible({ timeout: 20_000 });
  const src = (await img.getAttribute('src')) || '';
  const bytes = await page.evaluate(async () => {
    const el = document.querySelector('[data-testid="smb-artboard-img"]') as HTMLImageElement | null;
    if (!el?.src) return [];
    const res = await fetch(el.src);
    const buf = await res.arrayBuffer();
    return Array.from(new Uint8Array(buf));
  });
  const hash = createHash('sha256').update(Buffer.from(bytes)).digest('hex');
  return { src, hash, coverAssetId };
}

test.describe('SMB Revision Intelligence v3.1 — selected design preservation', () => {
  test('LAYER_ONLY revises the selected filmstrip post without generating a new creative', async ({
    page,
  }) => {
    test.setTimeout(240_000);
    mkdirSync(screenshotDir, { recursive: true });

    let revisePayload: Record<string, unknown> | null = null;
    let generateAdDuringRevise = 0;
    let gptImageDuringRevise = 0;
    let ideogramDuringRevise = 0;
    let revising = false;

    page.on('request', (request) => {
      if (!revising || request.method() !== 'POST') return;
      const url = request.url();
      if (url.includes('/generate-ad')) generateAdDuringRevise += 1;
      if (url.includes('/gpt-image') || url.includes('images/generations') || url.includes('images/edits')) {
        gptImageDuringRevise += 1;
      }
      if (url.toLowerCase().includes('ideogram')) ideogramDuringRevise += 1;
    });
    page.on('response', async (response) => {
      if (!response.url().includes('/revise') || response.request().method() !== 'POST') return;
      try {
        revisePayload = (await response.json()) as Record<string, unknown>;
      } catch {
        /* ignore */
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

    const finishedCard = page.locator('[data-testid^="smb-post-card-"][data-finished-ad-canvas="true"]');
    await expect(finishedCard.first(), 'Real SMB must already have a selected finished-ad filmstrip post').toBeVisible({
      timeout: 20_000,
    });
    await finishedCard.first().locator('button').first().click();

    const artboard = page.getByTestId('smb-artboard');
    await expect(artboard).toHaveAttribute('data-finished-ad-canvas', 'true', { timeout: 20_000 });

    const identityBefore = {
      postId: (await artboard.getAttribute('data-selected-post-id')) || '',
      campaignId: (await artboard.getAttribute('data-campaign-id')) || '',
      coverAssetId: (await artboard.getAttribute('data-cover-asset-id')) || '',
      interiorAssetId: (await artboard.getAttribute('data-interior-asset-id')) || '',
      logoAssetId: (await artboard.getAttribute('data-logo-asset-id')) || '',
      rasterAssetId: (await artboard.getAttribute('data-raster-asset-id')) || '',
      width: (await artboard.getAttribute('data-width')) || '',
      height: (await artboard.getAttribute('data-height')) || '',
    };
    const beforeImage = await hashArtboardImage(page);

    const fontOf = async (selector: string) => {
      const locator = page.locator(selector);
      if ((await locator.count()) === 0) return 0;
      return Number(
        await locator.first().evaluate((el) => {
          const attr = el.getAttribute('data-font-size');
          if (attr) return parseFloat(attr);
          return parseFloat(getComputedStyle(el).fontSize);
        }),
      );
    };
    const kickerSel =
      '[data-testid="smb-el-unit-label"], [data-testid="smb-el-subheadline"], [data-testid="smb-el-eyebrow"], [data-testid="smb-el-top-description"]';
    const headlineSel = '[data-testid="smb-el-headline"]';
    const f1Sel = '[data-testid="smb-el-support-message-1"], [data-testid="smb-el-feature-1"]';
    const f2Sel = '[data-testid="smb-el-support-message-2"], [data-testid="smb-el-feature-2"]';
    const headlineBefore = await fontOf(headlineSel);
    const f1Before = await fontOf(f1Sel);
    const f2Before = await fontOf(f2Sel);

    await page.screenshot({ path: resolve(screenshotDir, 'e2e-before.png'), fullPage: false });

    await page.getByTestId('smb-ai-design-input').fill(REVISION_PROMPT);
    const submit = page.locator(
      '[data-testid="smb-ai-revision-submit"], [data-testid="smb-ai-design-submit"]',
    );
    revising = true;
    await submit.first().click();
    await expect(artboard).toHaveAttribute('data-editable-finished-ad', 'true', { timeout: 120_000 });
    revising = false;

    await page.screenshot({ path: resolve(screenshotDir, 'e2e-after.png'), fullPage: false });

    const identityAfter = {
      postId: (await artboard.getAttribute('data-selected-post-id')) || '',
      campaignId: (await artboard.getAttribute('data-campaign-id')) || '',
      coverAssetId: (await artboard.getAttribute('data-cover-asset-id')) || '',
      interiorAssetId: (await artboard.getAttribute('data-interior-asset-id')) || '',
      logoAssetId: (await artboard.getAttribute('data-logo-asset-id')) || '',
      rasterAssetId: (await artboard.getAttribute('data-raster-asset-id')) || '',
      width: (await artboard.getAttribute('data-width')) || '',
      height: (await artboard.getAttribute('data-height')) || '',
    };
    const afterImage = await hashArtboardImage(page);

    expect(identityAfter.postId, 'post identity must stay on the selected filmstrip post').toBe(
      identityBefore.postId,
    );
    expect(identityAfter.campaignId).toBe(identityBefore.campaignId);
    expect(identityAfter.coverAssetId).toBe(identityBefore.coverAssetId);
    expect(afterImage.hash, 'background / raster bytes must be identical').toBe(beforeImage.hash);
    expect(identityAfter.width).toBe(identityBefore.width);
    expect(identityAfter.height).toBe(identityBefore.height);
    if (identityBefore.logoAssetId) {
      expect(identityAfter.logoAssetId).toBe(identityBefore.logoAssetId);
    }
    if (identityBefore.interiorAssetId) {
      expect(identityAfter.interiorAssetId).toBe(identityBefore.interiorAssetId);
    }

    await expect(page.locator(kickerSel)).toHaveCount(0);
    await expect(page.locator(headlineSel)).toHaveCount(1);
    const overlayTexts = await page.locator('[data-testid^="smb-el-"]').allTextContents();
    const normalized = overlayTexts.map((t) => t.replace(/\s+/g, ' ').trim().toLowerCase()).filter(Boolean);
    expect(new Set(normalized).size, 'duplicate semantic overlay text').toBe(normalized.length);

    const headlineAfter = await fontOf(headlineSel);
    const f1After = await fontOf(f1Sel);
    const f2After = await fontOf(f2Sel);
    await expect(page.locator(f1Sel).first()).toBeVisible();
    await expect(page.locator(f2Sel).first()).toBeVisible();
    if (headlineBefore > 0) expect(headlineAfter).toBeCloseTo(headlineBefore * 1.1, 0);
    else expect(headlineAfter).toBeGreaterThan(0);
    if (f1Before > 0) expect(f1After).toBeCloseTo(f1Before * 1.15, 0);
    if (f2Before > 0) expect(f2After).toBeCloseTo(f2Before * 1.15, 0);

    expect(revisePayload).not.toBeNull();
    expect(revisePayload?.revision_route).toBe('LAYER_ONLY');
    expect(revisePayload?.gpt_image_call_count ?? revisePayload?.provider_call_count ?? 0).toBe(0);
    expect(generateAdDuringRevise, 'LAYER_ONLY must never call generate-ad').toBe(0);
    expect(gptImageDuringRevise).toBe(0);
    expect(ideogramDuringRevise).toBe(0);

    writeFileSync(
      resolve(screenshotDir, 'e2e-identity.json'),
      JSON.stringify(
        {
          identity_before: identityBefore,
          identity_after: identityAfter,
          background_hash_before: beforeImage.hash,
          background_hash_after: afterImage.hash,
          provider_calls: {
            generate_ad: generateAdDuringRevise,
            gpt_image: gptImageDuringRevise,
            ideogram: ideogramDuringRevise,
            response_gpt_image_call_count: revisePayload?.gpt_image_call_count ?? null,
          },
          fonts: {
            headline_before: headlineBefore,
            headline_after: headlineAfter,
            feature1_before: f1Before,
            feature1_after: f1After,
            feature2_before: f2Before,
            feature2_after: f2After,
          },
          overlay_texts: overlayTexts,
        },
        null,
        2,
      ),
      'utf8',
    );
  });
});
