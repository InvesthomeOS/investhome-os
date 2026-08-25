import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { expect, test } from '@playwright/test';
import { DEMO_USERS, loginAs } from './fixtures';

const BRIEF = [
  'The Temple için premium bir sosyal medya reklamı hazırla.',
  'Tarihi karakter ile modern yaşamın birleşimini anlat.',
  'Gerçek interior ve gerçek The Temple logosunu kullan.',
  'Az metin, güçlü editoryal tasarım.',
  'Türkçe.',
  "CTA: The Temple'ı Keşfet.",
].join('\n');

const screenshotDir = resolve(process.cwd(), '../artifacts/structured-golden-design-v1');

test.describe('SMB structured golden design v1', () => {
  test('new Temple lifestyle ad + three GPT=0 structured micro edits', async ({ page }) => {
    test.setTimeout(720_000);
    mkdirSync(screenshotDir, { recursive: true });

    const generatePayloads: Array<{ status: number; body: Record<string, unknown> | null }> = [];
    const revisePayloads: Array<{ status: number; body: Record<string, unknown> | null }> = [];
    let generateAdCalls = 0;

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
      { timeout: 600_000 },
    );
    await page.getByTestId('smb-ai-generate').click();
    const generateRes = await generateWait;
    expect(generateRes.status()).toBe(200);

    const artboard = page.getByTestId('smb-artboard');
    await expect(artboard).toHaveAttribute('data-finished-ad-canvas', 'true', { timeout: 60_000 });
    await expect(artboard).toHaveAttribute('data-generation-lifecycle', 'ready', { timeout: 60_000 });
    await page.screenshot({ path: resolve(screenshotDir, 'smb-after-generate.png'), fullPage: true });

    const gen = generatePayloads[generatePayloads.length - 1];
    expect(gen?.status).toBe(200);
    const structured = (gen?.body?.structured_design_data || null) as Record<string, unknown> | null;
    expect(structured).toBeTruthy();
    const present = Array.isArray(structured?.present_slots)
      ? (structured?.present_slots as string[])
      : [];
    expect(present).toEqual(expect.arrayContaining(['headline', 'project-logo', 'cta-primary']));

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
      return last;
    }

    const interiorBefore = (await artboard.getAttribute('data-interior-asset-id')) || '';
    const coverBefore = (await artboard.getAttribute('data-cover-asset-id')) || '';

    await revise('Başlığı Zamansız Bir Yaşam yap.', 'smb-after-headline.png');
    await revise('Logoyu %20 küçült.', 'smb-after-logo.png');
    const ctaRevise = await revise("CTA'yı kaldır.", 'smb-after-cta-hide.png');

    const interiorAfter = (await artboard.getAttribute('data-interior-asset-id')) || '';
    const coverAfter = (await artboard.getAttribute('data-cover-asset-id')) || '';
    expect(interiorAfter).toBe(interiorBefore);
    expect(coverAfter).toBe(coverBefore);

    writeFileSync(
      resolve(screenshotDir, 'summary.json'),
      JSON.stringify(
        {
          generate_ad_calls: generateAdCalls,
          generate: gen,
          revises: revisePayloads,
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
