import { expect, test } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { DEMO_USERS, loginAs } from './fixtures';

const BRIEF = [
  'THE TEMPLE — LAUNCH OFFER',
  'The Temple için premium bir lansman reklamı hazırla.',
  'Ana fikir:',
  'ALIRKEN KAZAN',
  '2+1 daire liste fiyatı:',
  '675.000 USD',
  'Lansman avantajı:',
  '%35',
  'Mesaj:',
  "The Temple'da yerinizi lansman döneminde alın.",
  'CTA:',
  'PROJEYİ KEŞFET',
  'Use the real approved The Temple visual and real The Temple logo.',
].join('\n');

const screenshotDir = resolve(process.cwd(), '../artifacts/golden-master-proof');

test.describe('Golden Master proof — one Temple launch ad', () => {
  test('generate one layered advertisement and stop', async ({ page }) => {
    test.setTimeout(720_000);
    mkdirSync(screenshotDir, { recursive: true });

    const campaignPayloads: Array<{ status: number; body: Record<string, unknown> | null }> = [];
    const generatePayloads: Array<{ status: number; body: Record<string, unknown> | null }> = [];
    let reviseCount = 0;

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
      if (url.includes('/revise')) reviseCount += 1;
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
    expect(templeValue, 'The Temple project must be selectable').toBeTruthy();
    await projectSelect.selectOption(templeValue);
    await expect(projectSelect).toHaveValue(templeValue);

    await expect(page.locator('[data-testid^="smb-post-card-"][data-finished-ad-canvas="true"]')).toHaveCount(0, {
      timeout: 20_000,
    });

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
    expect(generateRes.status(), await generateRes.text()).toBe(200);
    expect(reviseCount, 'must not run a price revision').toBe(0);

    const artboard = page.getByTestId('smb-artboard');
    await expect(artboard).toHaveAttribute('data-finished-ad-canvas', 'true', { timeout: 60_000 });
    await expect(artboard).toHaveAttribute('data-generation-lifecycle', 'ready', { timeout: 60_000 });
    await expect.poll(async () => (await artboard.boundingBox())?.width ?? 0, { timeout: 30_000 }).toBeGreaterThan(240);

    const gen = generatePayloads[generatePayloads.length - 1];
    const genBody = (gen?.body || {}) as Record<string, unknown>;
    expect(genBody.production_mode).toBe('editable_finished_ad');
    expect(String(genBody.logo_asset_id || '')).toBeTruthy();
    expect(String(genBody.interior_asset_id || '')).toBeTruthy();

    const texts = (genBody.final_turkish_texts || {}) as Record<string, string>;
    expect(texts.headline).toMatch(/ALIRKEN KAZAN/i);
    expect(texts.unit).toContain('2+1');
    expect(String(texts.list_price || '')).toMatch(/675/);
    expect(String(texts.value_badge || '')).toMatch(/35/);
    expect(texts.cta).toMatch(/PROJEYİ KEŞFET|PROJEYI KEŞFET|PROJEYI KESFET/i);

    const layers = Array.isArray(genBody.editable_layers)
      ? (genBody.editable_layers as Array<Record<string, unknown>>)
      : [];
    const layerIds = layers.map((el) => String(el.id || ''));
    expect(layerIds).toContain('headline');
    expect(layerIds).toContain('old-price');
    expect(layerIds).toContain('discount-badge');
    expect(layerIds).toContain('logo');
    expect(layerIds).toContain('cta');

    const spec = (genBody.design_spec || {}) as Record<string, unknown>;
    const specEls = Array.isArray(spec.elements) ? (spec.elements as Array<Record<string, unknown>>) : [];
    const specById = Object.fromEntries(specEls.filter((el) => el.id).map((el) => [String(el.id), el]));
    expect(specById['new-price']).toBeTruthy();
    expect(specById['savings-price']).toBeTruthy();
    expect(specById['unit-label']?.content).toMatch(/2\+1/);

    const promptBlob = JSON.stringify({
      excerpt: (genBody.creative_brief_summary as Record<string, unknown> | undefined)?.prompt_excerpt,
      gpt: genBody.gpt_image,
    });
    expect(promptBlob).not.toMatch(/ALIRKEN KAZAN/);
    expect(promptBlob).not.toMatch(/675\.000/);
    expect(promptBlob).not.toMatch(/PROJEYİ KEŞFET/);

    await expect(page.getByTestId('smb-el-headline')).toContainText('ALIRKEN KAZAN', { timeout: 20_000 });
    await expect(page.getByTestId('smb-el-discount-badge')).toContainText('35');
    await expect(page.getByTestId('smb-el-old-price')).toContainText('675');
    await expect(page.getByTestId('smb-el-cta')).toBeVisible();
    await expect(page.getByTestId('smb-el-logo')).toBeVisible();

    const preview = page.getByTestId('smb-preview-shell');
    const screenshotTarget = (await preview.count()) ? preview : page;
    await page.screenshot({
      path: resolve(screenshotDir, 'smb-golden-master-fullpage.png'),
      fullPage: true,
    });
    await screenshotTarget.screenshot({
      path: resolve(screenshotDir, 'smb-golden-master-initial.png'),
    });

    writeFileSync(
      resolve(screenshotDir, 'generate-response.json'),
      JSON.stringify(genBody, null, 2),
    );
    writeFileSync(
      resolve(screenshotDir, 'summary.json'),
      JSON.stringify(
        {
          campaignId: genBody.campaign_id || campaignPayloads[0]?.body?.id,
          postId: await artboard.getAttribute('data-selected-post-id'),
          productionMode: genBody.production_mode,
          provider: genBody.provider_route,
          providerCallCount: genBody.gpt_image_call_count ?? genBody.provider_call_count,
          foundationAssetId: genBody.master_background_asset_id || genBody.final_asset_id,
          interiorAssetId: genBody.interior_asset_id,
          logoAssetId: genBody.logo_asset_id,
          texts,
          layerIds,
          specElementIds: specEls.map((el) => el.id),
          reviseCount,
        },
        null,
        2,
      ),
    );
  });
});
