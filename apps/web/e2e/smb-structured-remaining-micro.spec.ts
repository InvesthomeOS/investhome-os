import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { expect, test } from '@playwright/test';
import { DEMO_USERS, loginAs } from './fixtures';

const CAMPAIGN_ID = '12fbb72a-c67c-4010-b7aa-bec1049b5203';
const screenshotDir = resolve(process.cwd(), '../artifacts/structured-golden-design-v1');

test.describe('SMB structured golden remaining micro edits', () => {
  test('logo scale and CTA hide on the new Temple structured ad', async ({ page }) => {
    test.setTimeout(180_000);
    mkdirSync(screenshotDir, { recursive: true });

    const revisePayloads: Array<{ status: number; body: Record<string, unknown> | null }> = [];
    let generateAdCalls = 0;
    page.on('request', (request) => {
      if (request.method() === 'POST' && request.url().includes('/generate-ad')) generateAdCalls += 1;
    });
    page.on('response', async (response) => {
      if (response.request().method() !== 'POST') return;
      if (!response.url().includes('/revise') || response.url().includes('/undo') || response.url().includes('/redo')) {
        return;
      }
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

    const card = page.locator(
      `[data-testid^="smb-post-card-"][data-campaign-id="${CAMPAIGN_ID}"]`,
    );
    const fallback = page.locator(
      '[data-testid^="smb-post-card-"][data-finished-ad-canvas="true"]',
    );
    const target = (await card.count()) > 0 ? card.last() : fallback.last();
    await target.locator('button').first().click();

    const artboard = page.getByTestId('smb-artboard');
    await expect(artboard).toHaveAttribute('data-finished-ad-canvas', 'true', { timeout: 20_000 });
    await page.screenshot({ path: resolve(screenshotDir, 'smb-before-remaining.png'), fullPage: true });

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

    const logoRevise = await revise('Logoyu %20 küçült.', 'smb-after-logo.png');
    const ctaRevise = await revise("CTA'yı kaldır.", 'smb-after-cta-hide.png');

    const interiorAfter = (await artboard.getAttribute('data-interior-asset-id')) || '';
    const coverAfter = (await artboard.getAttribute('data-cover-asset-id')) || '';
    expect(interiorAfter).toBe(interiorBefore);
    expect(coverAfter).toBe(coverBefore);
    expect(generateAdCalls).toBe(0);

    writeFileSync(
      resolve(screenshotDir, 'remaining-revises.json'),
      JSON.stringify(
        {
          campaign_id: CAMPAIGN_ID,
          generate_ad_calls: generateAdCalls,
          interior_before: interiorBefore,
          interior_after: interiorAfter,
          cover_before: coverBefore,
          cover_after: coverAfter,
          logo_route: logoRevise?.body?.revision_route,
          logo_gpt: logoRevise?.body?.gpt_image_call_count ?? logoRevise?.body?.provider_call_count,
          cta_route: ctaRevise?.body?.revision_route,
          cta_gpt: ctaRevise?.body?.gpt_image_call_count ?? ctaRevise?.body?.provider_call_count,
          revises: revisePayloads.map((row) => ({
            status: row.status,
            route: row.body?.revision_route,
            gpt: row.body?.gpt_image_call_count ?? row.body?.provider_call_count,
          })),
        },
        null,
        2,
      ),
      'utf8',
    );
  });
});
