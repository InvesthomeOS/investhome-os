import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { expect, test } from '@playwright/test';
import { DEMO_USERS, loginAs } from './fixtures';

const INTERIOR = 'c3d11c35-d8b7-485c-b216-0a4da68b751a';
const LOGO = '7b58877e-efca-4e9a-9027-6fd18fb1b345';
const screenshotDir = resolve(process.cwd(), '../artifacts/golden-native-renderer-v1');

test.describe('SMB golden native art direction v2', () => {
  test('Temple locked INITIAL screenshot — no revisions', async ({ page }) => {
    test.setTimeout(180_000);
    mkdirSync(screenshotDir, { recursive: true });

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

    const artboard = page.getByTestId('smb-artboard');
    await expect(artboard).toHaveAttribute('data-finished-ad-canvas', 'true', { timeout: 60_000 });
    await expect(artboard).toHaveAttribute('data-generation-lifecycle', 'ready', { timeout: 60_000 });

    await expect(page.getByTestId('smb-artboard-img')).toHaveAttribute(
      'data-cover-asset-id',
      INTERIOR,
      { timeout: 20_000 },
    );
    await expect(page.getByTestId('smb-el-logo')).toHaveAttribute('data-asset-id', LOGO);
    await expect(page.getByTestId('smb-el-headline')).toHaveAttribute('data-el-type', 'TEXT');
    await expect(page.getByTestId('smb-el-cta')).toHaveAttribute('data-el-type', 'BUTTON');
    await expect(page.getByTestId('smb-el-cta')).toHaveAttribute('data-cta-style', 'MINIMAL_BUTTON');

    await page.screenshot({ path: resolve(screenshotDir, 'smb-art-direction-v2-initial.png'), fullPage: true });
    await artboard.screenshot({ path: resolve(screenshotDir, 'smb-art-direction-v2-artboard.png') });
    writeFileSync(
      resolve(screenshotDir, 'art-direction-v2-screenshot.json'),
      JSON.stringify(
        {
          interior_asset_id: INTERIOR,
          logo_asset_id: LOGO,
          screenshot: 'artifacts/golden-native-renderer-v1/smb-art-direction-v2-initial.png',
          artboard: 'artifacts/golden-native-renderer-v1/smb-art-direction-v2-artboard.png',
        },
        null,
        2,
      ),
    );
  });
});
