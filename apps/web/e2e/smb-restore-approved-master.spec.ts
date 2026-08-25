import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { expect, test } from '@playwright/test';
import { DEMO_USERS, loginAs } from './fixtures';

const POST_ID = '067c22d3-dcc3-4569-8f3c-127a0afbef98';
const MASTER = 'f1310474-d9b9-45f9-8fde-99aaddbc2431';
const screenshotDir = resolve(process.cwd(), '../artifacts/smb-restore-approved-master');

test.describe('SMB one-time approved-master restore', () => {
  test('Temple post canvas shows master raster and survives refresh with zero provider calls', async ({
    page,
  }) => {
    test.setTimeout(120_000);
    mkdirSync(screenshotDir, { recursive: true });

    let providerCalls = 0;
    page.on('request', (request) => {
      if (request.method() !== 'POST') return;
      const url = request.url();
      if (
        url.includes('/generate-ad') ||
        url.includes('/revise') ||
        url.includes('/gpt-image') ||
        url.includes('/ideogram') ||
        url.includes('/generations')
      ) {
        providerCalls += 1;
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

    const card = page.locator(
      `[data-testid="smb-post-card-${POST_ID}"], [data-testid^="smb-post-card-"][data-campaign-id="a45f7a43-cade-447e-8aa5-b6d126688ff7"]`,
    );
    await expect(card.first()).toBeVisible({ timeout: 20_000 });
    await card.first().locator('button').first().click();

    const artboard = page.getByTestId('smb-artboard');
    await expect(artboard).toHaveAttribute('data-finished-ad-canvas', 'true', { timeout: 20_000 });
    await expect(artboard).toHaveAttribute('data-selected-post-id', POST_ID);
    await expect(artboard).toHaveAttribute('data-cover-asset-id', MASTER);
    await expect(artboard).toHaveAttribute('data-master-finished-ad-asset-id', MASTER);
    const artboardImg = page.getByTestId('smb-artboard-img');
    await expect(artboardImg).toBeVisible({ timeout: 30_000 });
    await expect(artboardImg).toHaveAttribute('data-cover-asset-id', MASTER);
    await expect.poll(async () => {
      const src = (await artboardImg.getAttribute('src')) || '';
      return src.startsWith('blob:') || src.includes(MASTER) || src.length > 8;
    }).toBe(true);

    await page.screenshot({ path: resolve(screenshotDir, 'smb-restored.png'), fullPage: false });

    const before = {
      postId: (await artboard.getAttribute('data-selected-post-id')) || '',
      coverAssetId: (await artboard.getAttribute('data-cover-asset-id')) || '',
      masterFinishedAdAssetId: (await artboard.getAttribute('data-master-finished-ad-asset-id')) || '',
    };

    await page.reload();
    await expect(page.getByTestId('smb-ai-design-input')).toBeVisible({ timeout: 30_000 });
    const after = page.getByTestId('smb-artboard');
    await expect(after).toHaveAttribute('data-finished-ad-canvas', 'true', { timeout: 30_000 });
    await expect(after).toHaveAttribute('data-selected-post-id', POST_ID);
    await expect(after).toHaveAttribute('data-cover-asset-id', MASTER);
    await expect(after).toHaveAttribute('data-master-finished-ad-asset-id', MASTER);
    const afterImg = page.getByTestId('smb-artboard-img');
    await expect(afterImg).toBeVisible({ timeout: 30_000 });
    await expect(afterImg).toHaveAttribute('data-cover-asset-id', MASTER);

    await page.screenshot({
      path: resolve(screenshotDir, 'smb-restored-after-refresh.png'),
      fullPage: false,
    });

    expect(providerCalls).toBe(0);

    writeFileSync(
      resolve(screenshotDir, 'summary.json'),
      JSON.stringify(
        {
          restore_result: 'cover restored to approved master',
          cover_id: before.coverAssetId,
          master_id: before.masterFinishedAdAssetId,
          refresh: {
            post_id: (await after.getAttribute('data-selected-post-id')) || '',
            cover_asset_id: (await after.getAttribute('data-cover-asset-id')) || '',
            master_finished_ad_asset_id:
              (await after.getAttribute('data-master-finished-ad-asset-id')) || '',
          },
          provider_call_count: providerCalls,
        },
        null,
        2,
      ),
      'utf8',
    );
  });
});
