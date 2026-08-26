import { expect, test } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { DEMO_USERS, loginAs } from './fixtures';

const BRIEF = [
  'The Temple için premium bir lansman reklamı hazırla.',
  '2+1 dairenin liste fiyatı 675.000 USD.',
  'Lansmana özel %35 avantajı ve alırken kazanma fırsatını vurgula.',
].join('\n');

const PRICE_INSTRUCTION = [
  '675.000 USD liste fiyatının üzerini çiz.',
  'Lansman fiyatını 438.750 USD yap.',
  'Altına Kazancınız 236.250 USD yaz.',
  'Tasarımın geri kalan hiçbir şeyini değiştirme.',
].join('\n');

const screenshotDir = resolve(process.cwd(), '../artifacts/revision-engine-v2-price');

test.describe('Revision Engine v2 — editable commercial layers', () => {
  test('Temple generate + price layer revision + refresh', async ({ page }) => {
    test.setTimeout(720_000);
    mkdirSync(screenshotDir, { recursive: true });

    const generatePayloads: Array<{ status: number; body: Record<string, unknown> | null }> = [];
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
      const url = response.url();
      const method = response.request().method();
      if (method !== 'POST') return;
      let body: Record<string, unknown> | null = null;
      try {
        body = (await response.json()) as Record<string, unknown>;
      } catch {
        /* ignore */
      }
      if (url.includes('/generate-ad')) {
        generatePayloads.push({ status: response.status(), body });
      }
      if (url.includes('/revise')) {
        reviseStatus = response.status();
        revisePayload = body;
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

    const reuseCampaignId = (process.env.REVISION_ENGINE_V2_CAMPAIGN_ID || '').trim();
    if (reuseCampaignId) {
      const finishedCard = page.locator('[data-testid^="smb-post-card-"][data-finished-ad-canvas="true"]');
      await expect(finishedCard.first()).toBeVisible({ timeout: 20_000 });
      const count = await finishedCard.count();
      let selected = false;
      for (let i = 0; i < count; i += 1) {
        const card = finishedCard.nth(i);
        const campaignId = (await card.getAttribute('data-campaign-id')) || '';
        if (campaignId === reuseCampaignId) {
          await card.locator('button').first().click();
          selected = true;
          break;
        }
      }
      expect(selected, `Need generated campaign ${reuseCampaignId}`).toBeTruthy();
    } else {
    await page.getByTestId('smb-local-rail-left-ai').click();
    await expect(page.getByTestId('smb-ai-prompt')).toBeVisible({ timeout: 15_000 });
    await page.getByTestId('smb-ai-prompt').fill(BRIEF);
    await expect(page.getByTestId('smb-ai-prompt')).toHaveValue(BRIEF);
    await expect(page.getByTestId('smb-ai-generate')).toBeEnabled();

    const generateWait = page.waitForResponse(
      (res) => res.url().includes('/generate-ad') && res.request().method() === 'POST',
      { timeout: 600_000 },
    );
    await page.getByTestId('smb-ai-generate').click();
    const generateRes = await generateWait;
    expect(generateRes.status(), await generateRes.text()).toBe(200);
    }

    const artboard = page.getByTestId('smb-artboard');
    await expect(artboard).toHaveAttribute('data-finished-ad-canvas', 'true', { timeout: 60_000 });
    await expect(artboard).toHaveAttribute('data-generation-lifecycle', 'ready', { timeout: 60_000 });

    const gen = generatePayloads[generatePayloads.length - 1];
    const genBody = (
      gen?.body ||
      (reuseCampaignId
        ? (JSON.parse(readFileSync(resolve(screenshotDir, 'generate-response.json'), 'utf8')) as Record<
            string,
            unknown
          >)
        : {})
    ) as Record<string, unknown>;
    if (!reuseCampaignId) {
      writeFileSync(resolve(screenshotDir, 'generate-response.json'), JSON.stringify(genBody, null, 2));
    }

    expect(genBody.production_mode).toBe('editable_finished_ad');
    const layers = Array.isArray(genBody.editable_layers)
      ? (genBody.editable_layers as Array<Record<string, unknown>>)
      : [];
    const layerIds = layers.map((el) => String(el.id || ''));
    expect(layerIds).toContain('old-price');
    expect(layerIds).toContain('discount-badge');
    expect(layerIds).toContain('logo');
    expect(layerIds).toContain('cta');
    const oldPrice = layers.find((el) => el.id === 'old-price');
    expect(String(oldPrice?.content || '')).toMatch(/675/);

    await expect(page.getByTestId('smb-el-old-price')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('smb-el-old-price')).toContainText('675');
    await expect(page.getByTestId('smb-el-discount-badge')).toBeVisible();
    await expect(page.getByTestId('smb-el-logo')).toBeVisible();
    await expect(page.getByTestId('smb-el-cta')).toBeVisible();

    const identityInitial = {
      postId: (await artboard.getAttribute('data-selected-post-id')) || '',
      campaignId: (await artboard.getAttribute('data-campaign-id')) || '',
      coverAssetId: (await artboard.getAttribute('data-cover-asset-id')) || '',
      productionMode: genBody.production_mode,
      providerCalls: genBody.gpt_image_call_count ?? genBody.provider_call_count,
      layerIds,
    };
    writeFileSync(resolve(screenshotDir, 'identity-initial.json'), JSON.stringify(identityInitial, null, 2));
    await artboard.screenshot({ path: resolve(screenshotDir, 'smb-v2-initial.png') });

    const prompt = page.getByTestId('smb-ai-design-input');
    await expect(prompt).toBeVisible();
    await prompt.fill(PRICE_INSTRUCTION);
    await expect(prompt).toHaveValue(PRICE_INSTRUCTION);
    const submit = page.getByTestId('smb-ai-revision-submit');
    await expect(submit).toBeEnabled();
    revising = true;
    await submit.click();

    await expect.poll(() => reviseStatus, { timeout: 120_000 }).toBeGreaterThan(0);
    revising = false;
    writeFileSync(
      resolve(screenshotDir, 'revise-response.json'),
      JSON.stringify({ status: reviseStatus, body: revisePayload }, null, 2),
    );
    expect(reviseStatus, 'v2 price revision must succeed without GPT/inpaint').toBe(200);
    expect(generateAdDuringRevise).toBe(0);
    expect(gptImageDuringRevise).toBe(0);
    const providerCalls = Number(
      (revisePayload as { gpt_image_call_count?: number; provider_call_count?: number })
        .gpt_image_call_count ??
        (revisePayload as { provider_call_count?: number }).provider_call_count ??
        -1,
    );
    expect(providerCalls).toBe(0);
    expect((revisePayload as { revision_route?: string }).revision_route).toBe('MICRO_EDIT');

    await expect(page.getByTestId('smb-el-old-price')).toContainText('675');
    await expect(page.getByTestId('smb-el-new-price')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('smb-el-new-price')).toContainText('438.750');
    await expect(page.getByTestId('smb-el-savings-price')).toBeVisible();
    await expect(page.getByTestId('smb-el-savings-price')).toContainText('236.250');
    await expect(page.getByTestId('smb-el-old-price-strikethrough')).toBeVisible();

    const identityAfter = {
      postId: (await artboard.getAttribute('data-selected-post-id')) || '',
      campaignId: (await artboard.getAttribute('data-campaign-id')) || '',
      coverAssetId: (await artboard.getAttribute('data-cover-asset-id')) || '',
      providerCalls,
      revisionRoute: (revisePayload as { revision_route?: string }).revision_route ?? null,
    };
    expect(identityAfter.postId).toBe(identityInitial.postId);
    expect(identityAfter.campaignId).toBe(identityInitial.campaignId);
    expect(identityAfter.coverAssetId).toBe(identityInitial.coverAssetId);
    writeFileSync(resolve(screenshotDir, 'identity-after.json'), JSON.stringify(identityAfter, null, 2));
    await artboard.screenshot({ path: resolve(screenshotDir, 'smb-v2-after-revision.png') });

    await page.reload();
    await expect(page.getByTestId('smb-ai-design-input')).toBeVisible({ timeout: 30_000 });
    const artboardAfter = page.getByTestId('smb-artboard');
    await expect(artboardAfter).toHaveAttribute('data-finished-ad-canvas', 'true', { timeout: 30_000 });
    await expect
      .poll(async () => (await artboardAfter.getAttribute('data-selected-post-id')) || '', { timeout: 30_000 })
      .toBe(identityInitial.postId);
    await expect(artboardAfter).toHaveAttribute('data-cover-asset-id', identityInitial.coverAssetId);
    await expect(page.getByTestId('smb-el-old-price')).toContainText('675');
    await expect(page.getByTestId('smb-el-new-price')).toContainText('438.750');
    await expect(page.getByTestId('smb-el-savings-price')).toContainText('236.250');
    await artboardAfter.screenshot({ path: resolve(screenshotDir, 'smb-v2-after-refresh.png') });

    writeFileSync(
      resolve(screenshotDir, 'summary.json'),
      JSON.stringify(
        {
          brief: BRIEF,
          generate_status: gen?.status,
          production_mode: genBody.production_mode,
          initial_provider_calls: genBody.gpt_image_call_count ?? genBody.provider_call_count,
          revision_status: reviseStatus,
          revision_route: identityAfter.revisionRoute,
          revision_provider_calls: providerCalls,
          cover_unchanged: identityAfter.coverAssetId === identityInitial.coverAssetId,
          screenshots: {
            initial: 'artifacts/revision-engine-v2-price/smb-v2-initial.png',
            after_revision: 'artifacts/revision-engine-v2-price/smb-v2-after-revision.png',
            after_refresh: 'artifacts/revision-engine-v2-price/smb-v2-after-refresh.png',
          },
        },
        null,
        2,
      ),
    );
  });
});
