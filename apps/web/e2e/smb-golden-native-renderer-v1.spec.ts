import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { expect, test } from '@playwright/test';
import { DEMO_USERS, loginAs } from './fixtures';

const BRIEF = [
  'The Temple için premium bir sosyal medya reklamı hazırla.',
  'Tarihi karakter ile modern yaşamın birleşimini anlat.',
  'Gerçek interior görselini ve gerçek The Temple logosunu kullan.',
  'Az metinli, güçlü, editoryal ve yüksek segment olsun.',
  'Türkçe.',
  "CTA: The Temple'ı Keşfet.",
].join('\n');

const screenshotDir = resolve(process.cwd(), '../artifacts/golden-native-renderer-v1');

test.describe('SMB golden native renderer v1 POC', () => {
  test('Temple 4-layer native generate + three GPT=0 real-layer edits', async ({ page }) => {
    test.setTimeout(720_000);
    mkdirSync(screenshotDir, { recursive: true });

    const generatePayloads: Array<{ status: number; body: Record<string, unknown> | null }> = [];
    const revisePayloads: Array<{ status: number; body: Record<string, unknown> | null }> = [];
    let generateAdCalls = 0;

    await page.route('**/generate-ad', async (route) => {
      const request = route.request();
      if (request.method() !== 'POST') {
        await route.continue();
        return;
      }
      let body: Record<string, unknown> = {};
      try {
        body = JSON.parse(request.postData() || '{}') as Record<string, unknown>;
      } catch {
        body = {};
      }
      body.production_mode = 'golden_native_v1';
      await route.continue({
        postData: JSON.stringify(body),
        headers: {
          ...request.headers(),
          'content-type': 'application/json',
        },
      });
    });

    page.on('request', (request) => {
      if (request.method() !== 'POST') return;
      if (request.url().includes('/generate-ad')) generateAdCalls += 1;
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
      if (url.includes('/revise') && !url.includes('/undo') && !url.includes('/redo')) {
        revisePayloads.push({ status: response.status(), body });
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
      { timeout: 180_000 },
    );
    await page.getByTestId('smb-ai-generate').click();
    const generateRes = await generateWait;
    expect(generateRes.status()).toBe(200);

    const artboard = page.getByTestId('smb-artboard');
    await expect(artboard).toHaveAttribute('data-finished-ad-canvas', 'true', { timeout: 60_000 });
    await expect(artboard).toHaveAttribute('data-generation-lifecycle', 'ready', { timeout: 60_000 });
    await page.screenshot({ path: resolve(screenshotDir, 'smb-initial.png'), fullPage: true });

    const gen = generatePayloads[generatePayloads.length - 1];
    expect(gen?.status).toBe(200);
    expect(gen?.body?.production_mode).toBe('golden_native_v1');
    expect(gen?.body?.gpt_image_call_count ?? gen?.body?.provider_call_count).toBe(0);
    const spec = (gen?.body?.design_spec || null) as Record<string, unknown> | null;
    expect(spec).toBeTruthy();
    const elements = Array.isArray(spec?.elements) ? (spec?.elements as Array<Record<string, unknown>>) : [];
    expect(elements.map((el) => el.id)).toEqual(['master_background', 'logo', 'headline', 'cta']);

    async function revise(instruction: string, file: string) {
      await page.getByTestId('smb-ai-design-input').fill(instruction);
      const reviseWait = page.waitForResponse(
        (res) =>
          res.url().includes('/revise') &&
          res.request().method() === 'POST' &&
          !res.url().includes('/undo') &&
          !res.url().includes('/redo'),
        { timeout: 90_000 },
      );
      await page.getByTestId('smb-ai-revision-submit').click();
      const reviseRes = await reviseWait;
      expect(reviseRes.status()).toBe(200);
      await page.screenshot({ path: resolve(screenshotDir, file), fullPage: true });
      const last = revisePayloads[revisePayloads.length - 1];
      expect(last?.body?.gpt_image_call_count ?? last?.body?.provider_call_count).toBe(0);
      expect(last?.body?.revision_route).toMatch(/MICRO_EDIT|LAYER_ONLY/);
      expect(last?.body?.production_mode).toBe('golden_native_v1');
      return last;
    }

    const interiorBefore = (await artboard.getAttribute('data-interior-asset-id')) || '';
    const coverBefore = (await artboard.getAttribute('data-cover-asset-id')) || '';

    const headlineRevise = await revise('Başlığı Zamansız Bir Yaşam yap.', 'smb-headline-changed.png');
    const logoRevise = await revise('Logoyu %20 küçült.', 'smb-logo-minus-20.png');
    const ctaRevise = await revise("CTA'yı kaldır.", 'smb-cta-removed.png');

    const interiorAfter = (await artboard.getAttribute('data-interior-asset-id')) || '';
    const coverAfter = (await artboard.getAttribute('data-cover-asset-id')) || '';
    expect(interiorAfter).toBe(interiorBefore);
    expect(coverAfter).toBe(coverBefore);
    expect(coverAfter).toBe(String(gen?.body?.interior_asset_id || coverAfter));

    writeFileSync(
      resolve(screenshotDir, 'summary.json'),
      JSON.stringify(
        {
          generate_ad_calls: generateAdCalls,
          generate: {
            production_mode: gen?.body?.production_mode,
            gpt_image_call_count: gen?.body?.gpt_image_call_count,
            provider_call_count: gen?.body?.provider_call_count,
            interior_asset_id: gen?.body?.interior_asset_id,
            logo_asset_id: gen?.body?.logo_asset_id,
            layer_ids: elements.map((el) => el.id),
          },
          revises: revisePayloads.map((row) => ({
            status: row.status,
            gpt_image_call_count: row.body?.gpt_image_call_count,
            revision_route: row.body?.revision_route,
            production_mode: row.body?.production_mode,
          })),
          last_headline_route: headlineRevise?.body?.revision_route,
          last_logo_route: logoRevise?.body?.revision_route,
          last_cta_route: ctaRevise?.body?.revision_route,
          interior_before: interiorBefore,
          interior_after: interiorAfter,
          cover_before: coverBefore,
          cover_after: coverAfter,
        },
        null,
        2,
      ),
      'utf8',
    );
  });
});
