import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { DEMO_USERS, expect, loginAs, test } from './fixtures';

const REVISION_PROMPT = [
  'Üstteki küçük açıklama metnini tamamen kaldır.',
  'Ana başlığı %10 büyüt.',
  'Soldaki iki özellik metnini %15 büyüt ve okunabilirliğini artır.',
  'Diğer tüm tasarım öğelerini, görseli, renkleri, logoyu, CTA’yı',
  've mevcut yerleşimi kesinlikle değiştirme.',
].join('\n');

const GENERATE_BRIEF =
  'The Temple için premium bir sosyal medya gönderisi hazırla. Tarihi karakter ile modern yaşamı birleştir. Premium, sade ve Türkçe olsun.';

const screenshotDir = resolve(process.cwd(), '../artifacts/smb-revision-execution-lock');

test.describe('SMB Revision Intelligence v3 — real canvas', () => {
  test('LAYER_ONLY revision updates DOM text layers, not the baked raster', async ({ page }) => {
    test.setTimeout(240_000);
    mkdirSync(screenshotDir, { recursive: true });

    let revisePayload: Record<string, unknown> | null = null;
    page.on('response', async (response) => {
      if (!response.url().includes('/revise') || response.request().method() !== 'POST') return;
      try {
        revisePayload = (await response.json()) as Record<string, unknown>;
      } catch {
        /* ignore non-JSON */
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
        if (value && (label.includes('temple') || label.includes('residence'))) {
          await projectSelect.selectOption(value);
          break;
        }
      }
      if (!(await projectSelect.inputValue()) && n > 1) {
        const fallback = await options.nth(1).getAttribute('value');
        if (fallback) await projectSelect.selectOption(fallback);
      }
    }

    const finished = page.locator('[data-finished-ad-canvas="true"]');
    if ((await finished.count()) === 0) {
      await page.getByTestId('smb-ai-design-input').fill(GENERATE_BRIEF);
      await page.getByTestId('smb-ai-design-submit').click();
      await expect(finished).toBeVisible({ timeout: 180_000 });
    }

    const kicker = page.locator(
      '[data-testid="smb-el-unit-label"], [data-testid="smb-el-subheadline"], [data-testid="smb-el-eyebrow"], [data-testid="smb-el-top-description"]',
    );
    const headline = page.locator('[data-testid="smb-el-headline"]');
    const feature1 = page.locator(
      '[data-testid="smb-el-support-message-1"], [data-testid="smb-el-feature-1"]',
    );
    const feature2 = page.locator(
      '[data-testid="smb-el-support-message-2"], [data-testid="smb-el-feature-2"]',
    );

    const fontOf = async (locator: ReturnType<typeof page.locator>) => {
      if ((await locator.count()) === 0) return 0;
      return Number(
        await locator.first().evaluate((el) => {
          const attr = el.getAttribute('data-font-size');
          if (attr) return parseFloat(attr);
          return parseFloat(getComputedStyle(el).fontSize);
        }),
      );
    };

    const headlineBefore = await fontOf(headline);
    const f1Before = await fontOf(feature1);
    const f2Before = await fontOf(feature2);

    await page.getByTestId('smb-ai-design-input').fill(REVISION_PROMPT);
    const submit = page.locator(
      '[data-testid="smb-ai-revision-submit"], [data-testid="smb-ai-design-submit"]',
    );
    await submit.first().click();

    await expect(page.locator('[data-editable-finished-ad="true"]')).toBeVisible({
      timeout: 120_000,
    });
    await expect(page.locator('[data-hide-os-layers="false"]')).toBeVisible();
    await expect(page.locator('[data-testid="smb-el-headline"]')).toBeVisible();
    await expect(kicker).toHaveCount(0);

    const headlineAfter = await fontOf(page.locator('[data-testid="smb-el-headline"]'));
    if (headlineBefore > 0) {
      expect(headlineAfter).toBeCloseTo(headlineBefore * 1.1, 0);
    } else {
      expect(headlineAfter).toBeGreaterThan(0);
    }

    const f1AfterEl = page.locator(
      '[data-testid="smb-el-support-message-1"], [data-testid="smb-el-feature-1"]',
    );
    const f2AfterEl = page.locator(
      '[data-testid="smb-el-support-message-2"], [data-testid="smb-el-feature-2"]',
    );
    await expect(f1AfterEl.first()).toBeVisible();
    await expect(f2AfterEl.first()).toBeVisible();
    const f1After = await fontOf(f1AfterEl);
    const f2After = await fontOf(f2AfterEl);
    if (f1Before > 0) expect(f1After).toBeCloseTo(f1Before * 1.15, 0);
    if (f2Before > 0) expect(f2After).toBeCloseTo(f2Before * 1.15, 0);

    expect(revisePayload).not.toBeNull();
    expect(revisePayload?.revision_route).toBe('LAYER_ONLY');
    expect(
      revisePayload?.gpt_image_call_count ?? revisePayload?.provider_call_count ?? 0,
    ).toBe(0);

    writeFileSync(
      resolve(screenshotDir, 'e2e-revise-response.json'),
      JSON.stringify(
        {
          revision_route: revisePayload?.revision_route,
          production_mode: revisePayload?.production_mode,
          gpt_image_call_count: revisePayload?.gpt_image_call_count,
          provider_call_count: revisePayload?.provider_call_count,
          interpreted_plan: revisePayload?.interpreted_plan,
          layer_ids: Array.isArray(revisePayload?.editable_layers)
            ? (revisePayload?.editable_layers as Array<{ id?: string }>).map((row) => row?.id)
            : [],
          headline_before: headlineBefore,
          headline_after: headlineAfter,
          feature1_before: f1Before,
          feature1_after: f1After,
          feature2_before: f2Before,
          feature2_after: f2After,
        },
        null,
        2,
      ),
      'utf8',
    );

    await page.screenshot({
      path: resolve(screenshotDir, 'e2e-after.png'),
      fullPage: false,
    });
  });
});
