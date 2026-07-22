import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

import { test, expect } from '@playwright/test';

/** Absolute artifacts dir via import.meta.url (repo-relative walk). */
function resolveArtifactsDir(): string {
  let dir = path.dirname(fileURLToPath(import.meta.url));
  for (let i = 0; i < 8; i++) {
    if (fs.existsSync(path.join(dir, 'pnpm-workspace.yaml')) || fs.existsSync(path.join(dir, 'docker-compose.yml'))) {
      return path.join(dir, 'artifacts', 'ecosystem-g15a');
    }
    dir = path.dirname(dir);
  }
  return path.join(path.dirname(fileURLToPath(import.meta.url)), '../../../artifacts/ecosystem-g15a');
}

const ARTIFACTS = resolveArtifactsDir();

const REQUIRED_SHOTS = [
  '01-platform-overview.png',
  '02-module-registry.png',
  '03-module-detail.png',
  '04-dependency-map.png',
  '05-feature-flags.png',
  '06-feature-flag-detail.png',
  '07-entitlements.png',
  '08-entitlement-detail.png',
  '09-external-users.png',
  '10-external-user-detail.png',
  '11-api-clients.png',
  '12-api-client-detail.png',
  '13-api-scope-catalog.png',
  '14-webhooks.png',
  '15-webhook-delivery-detail.png',
  '16-integration-registry.png',
  '17-integration-detail.png',
  '18-platform-health.png',
  '19-kill-switch-confirmation.png',
  '20-platform-audit.png',
  '21-turkish.png',
  '22-english.png',
  '23-tablet.png',
  '24-permission-denied.png',
  '25-disabled-module-state.png',
  '26-expired-access-state.png',
  '27-failed-webhook.png',
] as const;

test.describe('G15A screenshot capture', () => {
  test('run capture script and verify 27 PNGs on disk', async () => {
    const script = path.join(ARTIFACTS, 'capture-screenshots.mjs');
    expect(fs.existsSync(script), `capture script missing at ${script}`).toBeTruthy();

    const result = spawnSync(process.execPath, [script], {
      cwd: path.resolve(ARTIFACTS, '../..'),
      env: { ...process.env, PLAYWRIGHT_BASE_URL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000' },
      encoding: 'utf8',
      timeout: 300_000,
    });
    // eslint-disable-next-line no-console
    console.log(result.stdout);
    if (result.stderr) {
      // eslint-disable-next-line no-console
      console.error(result.stderr);
    }
    expect(result.status, `capture exit ${result.status}`).toBe(0);

    for (const name of REQUIRED_SHOTS) {
      const file = path.join(ARTIFACTS, name);
      expect(fs.existsSync(file), `${file} missing`).toBeTruthy();
      expect(fs.statSync(file).size, `${name} >10KB`).toBeGreaterThan(10_000);
    }
  });
});
