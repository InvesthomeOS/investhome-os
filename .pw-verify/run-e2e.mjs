/**
 * Run Playwright e2e specs from apps/web/e2e using .pw-verify's playwright install.
 */
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const webRoot = path.join(repoRoot, 'apps', 'web');
const pwVerify = path.join(repoRoot, '.pw-verify');

const result = spawnSync(
  'npx',
  ['playwright', 'test', '--config', path.join(pwVerify, 'playwright.config.ts')],
  {
    cwd: pwVerify,
    stdio: 'inherit',
    shell: true,
    env: {
      ...process.env,
      PW_BASE_URL: process.env.PW_BASE_URL || 'http://localhost:3000',
      PW_API_URL: process.env.PW_API_URL || 'http://localhost:8000',
    },
  },
);

process.exit(result.status ?? 1);
