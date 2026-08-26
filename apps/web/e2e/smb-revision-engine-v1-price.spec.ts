import { expect, test } from '@playwright/test';
import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { DEMO_USERS, loginAs } from './fixtures';

const PRICE_INSTRUCTION = [
  '675.000 USD liste fiyatının üzerini çiz.',
  'Lansman fiyatını 438.750 USD yap.',
  'Altına Kazancınız 236.250 USD yaz.',
  'Tasarımın geri kalan hiçbir şeyini değiştirme.',
].join('\n');

const TEMPLE_ALIRKEN_CAMPAIGN = '1fcf06f9-790c-480a-8c34-f17d001f4ed5';
const TEMPLE_ALIRKEN_COVER = 'f2fc8d2d-2887-4e38-bfa5-c699910992b5';
const screenshotDir = resolve(process.cwd(), '../artifacts/revision-engine-v1-price');

async function hashArtboardImage(
  page: import('@playwright/test').Page,
): Promise<{ src: string; hash: string; coverAssetId: string; bytes: Buffer }> {
  const artboard = page.getByTestId('smb-artboard');
  const coverAssetId = (await artboard.getAttribute('data-cover-asset-id')) || '';
  const img = page.getByTestId('smb-artboard-img');
  await expect(img).toBeVisible({ timeout: 20_000 });
  const src = (await img.getAttribute('src')) || '';
  const bytesArr = await page.evaluate(async () => {
    const el = document.querySelector('[data-testid="smb-artboard-img"]') as HTMLImageElement | null;
    if (!el?.src) return [];
    const res = await fetch(el.src);
    const buf = await res.arrayBuffer();
    return Array.from(new Uint8Array(buf));
  });
  const bytes = Buffer.from(bytesArr);
  const hash = createHash('sha256').update(bytes).digest('hex');
  return { src, hash, coverAssetId, bytes };
}

test.describe('Revision Engine v1 — local price block', () => {
  test('AI ile Düzenle edits only the baked price zone on Alırken Kazan', async ({ page }) => {
    test.setTimeout(240_000);
    mkdirSync(screenshotDir, { recursive: true });

    let reviseStatus = 0;
    let revisePayload: Record<string, unknown> | null = null;
    let generateAdDuringRevise = 0;
    let gptImageDuringRevise = 0;
    let revising = false;

    page.on('request', (request) => {
      if (!revising || request.method() !== 'POST') return;
      const url = request.url();
      if (url.includes('/generate-ad')) generateAdDuringRevise += 1;
      if (url.includes('/gpt-image') || url.includes('images/generations') || url.includes('images/edits')) {
        gptImageDuringRevise += 1;
      }
    });
    page.on('response', async (response) => {
      if (!response.url().includes('/revise') || response.request().method() !== 'POST') return;
      reviseStatus = response.status();
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
    await expect(projectSelect).toBeVisible({ timeout: 30_000 });
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
    expect(templeValue, 'The Temple project must be selectable').toBeTruthy();
    await projectSelect.selectOption(templeValue);

    const finishedCard = page.locator('[data-testid^="smb-post-card-"][data-finished-ad-canvas="true"]');
    await expect(finishedCard.first(), 'Real SMB must already have a finished-ad filmstrip post').toBeVisible({
      timeout: 20_000,
    });

    const count = await finishedCard.count();
    let selected = false;
    for (let i = 0; i < count; i += 1) {
      const card = finishedCard.nth(i);
      const campaignId = (await card.getAttribute('data-campaign-id')) || '';
      await card.locator('button').first().click();
      const artboard = page.getByTestId('smb-artboard');
      await expect(artboard).toHaveAttribute('data-finished-ad-canvas', 'true', { timeout: 20_000 });
      const cover = (await artboard.getAttribute('data-cover-asset-id')) || '';
      if (campaignId === TEMPLE_ALIRKEN_CAMPAIGN || cover === TEMPLE_ALIRKEN_COVER) {
        selected = true;
        break;
      }
    }
    if (!selected) {
      for (let i = 0; i < count; i += 1) {
        await finishedCard.nth(i).locator('button').first().click();
        const artboard = page.getByTestId('smb-artboard');
        const cover = (await artboard.getAttribute('data-cover-asset-id')) || '';
        if (!cover) continue;
        const img = page.getByTestId('smb-artboard-img');
        if ((await img.count()) === 0) continue;
        selected = true;
        break;
      }
    }
    expect(selected, 'Need a real Temple finished_ad with baked 675.000 USD').toBeTruthy();

    const artboard = page.getByTestId('smb-artboard');
    const identityBefore = {
      postId: (await artboard.getAttribute('data-selected-post-id')) || '',
      campaignId: (await artboard.getAttribute('data-campaign-id')) || '',
      coverAssetId: (await artboard.getAttribute('data-cover-asset-id')) || '',
      interiorAssetId: (await artboard.getAttribute('data-interior-asset-id')) || '',
      logoAssetId: (await artboard.getAttribute('data-logo-asset-id')) || '',
    };
    writeFileSync(resolve(screenshotDir, 'identity-before.json'), JSON.stringify(identityBefore, null, 2));

    const before = await hashArtboardImage(page);
    const box = await page.getByTestId('smb-artboard').boundingBox();
    expect(box).toBeTruthy();
    const zoneClip = {
      x: Math.round((box?.width || 800) * 0.28),
      y: Math.round((box?.height || 1000) * 0.70),
      width: Math.round((box?.width || 800) * 0.44),
      height: Math.round((box?.height || 1000) * 0.28),
    };
    await page.getByTestId('smb-artboard').screenshot({
      path: resolve(screenshotDir, 'smb-price-before.png'),
    });
    await page.getByTestId('smb-artboard').screenshot({
      path: resolve(screenshotDir, 'smb-price-zone-before.png'),
      clip: zoneClip,
    });

    const prompt = page.getByTestId('smb-ai-design-input');
    await expect(prompt).toBeVisible();
    await prompt.fill(PRICE_INSTRUCTION);
    await expect(prompt).toHaveValue(PRICE_INSTRUCTION);

    const submit = page.getByTestId('smb-ai-revision-submit');
    await expect(submit).toBeEnabled();
    revising = true;
    await submit.click();

    await expect
      .poll(() => reviseStatus, { timeout: 120_000 })
      .toBeGreaterThan(0);
    revising = false;

    writeFileSync(
      resolve(screenshotDir, 'revise-response.json'),
      JSON.stringify({ status: reviseStatus, body: revisePayload }, null, 2),
    );

    expect(reviseStatus, 'PRICE_BLOCK_ONLY must not persist a failed revision').toBe(200);
    expect(generateAdDuringRevise).toBe(0);
    expect(gptImageDuringRevise).toBe(0);
    expect(revisePayload).toBeTruthy();
    const providerCalls = Number(
      (revisePayload as { gpt_image_call_count?: number; provider_call_count?: number })
        .gpt_image_call_count ??
        (revisePayload as { provider_call_count?: number }).provider_call_count ??
        -1,
    );
    expect(providerCalls).toBe(0);

    await expect
      .poll(async () => (await artboard.getAttribute('data-cover-asset-id')) || '', {
        timeout: 30_000,
      })
      .not.toBe(identityBefore.coverAssetId);

    const after = await hashArtboardImage(page);
    await page.getByTestId('smb-artboard').screenshot({
      path: resolve(screenshotDir, 'smb-price-after.png'),
    });
    await page.getByTestId('smb-artboard').screenshot({
      path: resolve(screenshotDir, 'smb-price-zone-after.png'),
      clip: zoneClip,
    });

    const identityAfter = {
      postId: (await artboard.getAttribute('data-selected-post-id')) || '',
      campaignId: (await artboard.getAttribute('data-campaign-id')) || '',
      coverAssetId: (await artboard.getAttribute('data-cover-asset-id')) || '',
      interiorAssetId: (await artboard.getAttribute('data-interior-asset-id')) || '',
      logoAssetId: (await artboard.getAttribute('data-logo-asset-id')) || '',
      beforeHash: before.hash,
      afterHash: after.hash,
      coverChanged: after.coverAssetId !== identityBefore.coverAssetId,
      providerCalls,
      revisionRoute: (revisePayload as { revision_route?: string }).revision_route ?? null,
    };
    writeFileSync(resolve(screenshotDir, 'identity-after.json'), JSON.stringify(identityAfter, null, 2));
    writeFileSync(resolve(screenshotDir, 'artboard-after.bin.png'), after.bytes);

    expect(after.hash).not.toBe(before.hash);
    expect(identityAfter.postId).toBe(identityBefore.postId);
    expect(identityAfter.campaignId).toBe(identityBefore.campaignId);
    expect(identityAfter.interiorAssetId).toBe(identityBefore.interiorAssetId);
    expect(identityAfter.logoAssetId).toBe(identityBefore.logoAssetId);
  });
});
