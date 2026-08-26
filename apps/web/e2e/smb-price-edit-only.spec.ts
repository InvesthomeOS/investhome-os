import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { DEMO_USERS, loginAs } from './fixtures';
import { expect, test } from '@playwright/test';

const TEMPLE_PROJECT_ID = 'd50708cb-60b3-465a-8b16-6d30f802af8d';
const CAMPAIGN_ID = 'e67f94ea-a52f-4bde-9fd6-1c126cc5a2b5';
const POST_ID = 'ad357b88-36ab-469a-a4ac-45700fade56d';
const COVER_V2 = '19ed9f2c-3378-4eb4-9387-ed78b9f3768f';
const SOURCE_DAY_004 = '299bd265-a0ea-486d-866d-1947f103fd57';

const PROMPT = [
  "Liste fiyatı 675.000 USD aynı kalsın ve üzeri çizili gösterilsin.",
  "%35 lansman indirimi sonrası satış fiyatını 438.750 USD olarak ekle.",
  "Ayrıca 'Kazancınız 236.250 USD' bilgisini ekle.",
  "Bunun dışında tasarımda hiçbir şeyi değiştirme.",
  "Dış cephe görseli, ALIRKEN KAZAN başlığı, 2+1 bilgisi, %35,",
  "The Temple logosu, CTA, renkler, tipografi, görsel yerleşimi",
  "ve genel tasarım birebir aynı kalsın.",
].join('\n');

const screenshotDir = resolve(process.cwd(), '../artifacts/price-edit-only-v1');

test.describe('PRICE_EDIT_ONLY — one real Temple price revision', () => {
  test('edit prices on approved v2 exterior without replacing the hero', async ({ page }) => {
    test.setTimeout(180_000);
    mkdirSync(screenshotDir, { recursive: true });

    const revisePayloads: Array<{ status: number; body: Record<string, unknown> | null }> = [];
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
    await page.setViewportSize({ width: 1600, height: 1000 });
    await page.goto('/workspaces/creative-studio/social-media-builder');
    await expect(page.getByTestId('smb-ai-design-input')).toBeVisible({ timeout: 30_000 });

    const projectSelect = page.locator('#smb-project');
    await expect.poll(async () => projectSelect.locator('option').count(), { timeout: 30_000 }).toBeGreaterThan(1);
    await projectSelect.selectOption(TEMPLE_PROJECT_ID);
    const workspace = page.getByTestId('smb-workspace');
    await expect(workspace).toHaveAttribute('data-construction-project-id', TEMPLE_PROJECT_ID, {
      timeout: 45_000,
    });
    await expect(workspace).toHaveAttribute('data-load-status', 'ready', { timeout: 45_000 });

    const card = page.locator(`[data-testid="smb-post-card-${POST_ID}"]`);
    await expect(card).toBeVisible({ timeout: 30_000 });
    await card.locator('button').first().click();

    const artboard = page.getByTestId('smb-artboard');
    await expect(artboard).toHaveAttribute('data-finished-ad-canvas', 'true', { timeout: 20_000 });
    await expect(artboard).toHaveAttribute('data-campaign-id', CAMPAIGN_ID, { timeout: 20_000 });
    const artboardImg = artboard.locator('img').first();
    await expect
      .poll(async () => artboardImg.evaluate((el) => (el as HTMLImageElement).naturalWidth), { timeout: 30_000 })
      .toBeGreaterThan(200);

    const coverBefore = (await artboard.getAttribute('data-cover-asset-id')) || '';
    const sourceBefore = (await artboard.getAttribute('data-interior-asset-id')) || '';
    expect(coverBefore).toBe(COVER_V2);
    expect(sourceBefore).toBe(SOURCE_DAY_004);

    await page.screenshot({ path: resolve(screenshotDir, 'smb-before.png'), fullPage: false });

    await page.getByTestId('smb-ai-design-input').fill(PROMPT);
    const submit = page.getByTestId('smb-ai-revision-submit');
    await expect(submit).toBeEnabled();
    await submit.click();

    await expect.poll(() => revisePayloads.length, { timeout: 120_000 }).toBe(1);
    const revise = revisePayloads[0];
    expect(revise?.status, JSON.stringify(revise?.body)?.slice(0, 1200)).toBe(200);
    expect(revise?.body?.revision_route).toBe('PRICE_EDIT_ONLY');
    expect(Number(revise?.body?.gpt_image_call_count ?? 1)).toBe(0);
    const intents = (revise?.body?.revision_intents as string[]) || [];
    expect(intents).not.toContain('ASSET_CHANGE');
    expect(intents).not.toContain('VISUAL_CHANGE');
    expect(String(revise?.body?.interior_asset_id || '')).toBe(SOURCE_DAY_004);
    expect(String(revise?.body?.final_asset_id || '')).not.toBe(coverBefore);

    const masterCreative = (revise?.body?.master_creative as Record<string, unknown>) || {};
    expect(masterCreative.current_version).toBe(3);
    expect(String(masterCreative.source_visual_asset_id || '')).toBe(SOURCE_DAY_004);

    await expect
      .poll(async () => (await artboard.getAttribute('data-cover-asset-id')) || '', { timeout: 60_000 })
      .not.toBe(coverBefore);

    await page.screenshot({ path: resolve(screenshotDir, 'smb-after.png'), fullPage: false });
    await page.screenshot({ path: resolve(screenshotDir, 'smb-after-fullpage.png'), fullPage: true });

    writeFileSync(
      resolve(screenshotDir, 'summary.json'),
      JSON.stringify(
        {
          campaignId: CAMPAIGN_ID,
          postId: POST_ID,
          coverBefore,
          coverAfter: await artboard.getAttribute('data-cover-asset-id'),
          sourceBefore,
          sourceAfter: await artboard.getAttribute('data-interior-asset-id'),
          http: revise?.status,
          revisionRoute: revise?.body?.revision_route,
          intents,
          gptImageCallCount: revise?.body?.gpt_image_call_count,
          interpretedPlan: revise?.body?.interpreted_plan,
          revisionHistory: revise?.body?.revision_history,
          masterCreative,
          qualityGuard: revise?.body?.quality_guard,
        },
        null,
        2,
      ),
    );
  });
});
