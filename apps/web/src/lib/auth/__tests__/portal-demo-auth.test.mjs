/**
 * Portal demo credential removal contracts.
 * Run: node --test src/lib/auth/__tests__/portal-demo-auth.test.mjs
 */

import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  authenticatePortalDemo,
  isPortalDemoAuthEnabled,
  listPortalDemoAccounts,
} from '../../../app/portal/_lib/portal-demo-auth.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = join(here, '../../../..');
const webSrc = join(webRoot, 'src');

function read(rel) {
  return readFileSync(join(webSrc, rel), 'utf8');
}

function collectSourceFiles(dir, files = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      if (entry === '__tests__' || entry === 'e2e' || entry === 'node_modules') continue;
      collectSourceFiles(full, files);
      continue;
    }
    if (/\.(ts|tsx|mjs|js|json)$/.test(entry)) {
      files.push(full);
    }
  }
  return files;
}

const localDemoEnv = {
  NODE_ENV: 'development',
  PORTAL_DEMO_AUTH: 'true',
  PORTAL_DEMO_EMAIL: 'local.investor@example.test',
  PORTAL_DEMO_PASSWORD: 'local-only-password',
  PORTAL_DEMO_INVESTOR_ID: 'portal-inv-a',
};

describe('production has no hardcoded/default portal credentials', () => {
  it('keeps Portal123! and demo password stores out of production-capable source', () => {
    const files = [
      ...collectSourceFiles(join(webSrc, 'app/portal')),
      ...collectSourceFiles(join(webSrc, 'app/api/portal')),
      join(webRoot, 'messages/portal-en.json'),
      join(webRoot, 'messages/portal-tr.json'),
    ];
    for (const file of files) {
      const source = readFileSync(file, 'utf8');
      assert.doesNotMatch(source, /Portal123!/, file);
      assert.doesNotMatch(source, /DEMO_PORTAL_PASSWORD/, file);
      assert.doesNotMatch(source, /PORTAL_DEMO_USERS/, file);
    }
    const demoAuth = read('app/portal/_lib/portal-demo-auth.mjs');
    assert.doesNotMatch(demoAuth, /investor\.a@investhome\.demo/);
    assert.doesNotMatch(demoAuth, /password:\s*['"]/);
  });
});

describe('login form is not prefilled', () => {
  it('starts email and password empty and shows no credential hint', () => {
    const login = read('app/portal/login/page.tsx');
    assert.match(login, /useState\(''\)/);
    assert.equal((login.match(/useState\(''\)/g) || []).length >= 2, true);
    assert.doesNotMatch(login, /investor\.a@investhome\.demo/);
    assert.doesNotMatch(login, /Portal123!/);
    assert.doesNotMatch(login, /portal-login-hint/);
    assert.doesNotMatch(login, /login\.hint/);
    const en = readFileSync(join(webRoot, 'messages/portal-en.json'), 'utf8');
    const tr = readFileSync(join(webRoot, 'messages/portal-tr.json'), 'utf8');
    assert.doesNotMatch(en, /"hint"/);
    assert.doesNotMatch(tr, /"hint"/);
    assert.doesNotMatch(en, /Portal123!/);
    assert.doesNotMatch(tr, /Portal123!/);
  });
});

describe('local-only demo gate cannot activate in production', () => {
  it('stays off in production even when demo env vars are set', () => {
    const production = {
      NODE_ENV: 'production',
      PORTAL_DEMO_AUTH: 'true',
      PORTAL_DEMO_EMAIL: localDemoEnv.PORTAL_DEMO_EMAIL,
      PORTAL_DEMO_PASSWORD: localDemoEnv.PORTAL_DEMO_PASSWORD,
    };
    assert.equal(isPortalDemoAuthEnabled(production), false);
    assert.deepEqual(listPortalDemoAccounts(production), []);
    assert.equal(
      authenticatePortalDemo(localDemoEnv.PORTAL_DEMO_EMAIL, localDemoEnv.PORTAL_DEMO_PASSWORD, production),
      null,
    );
  });

  it('requires an explicit local flag and env credentials', () => {
    assert.equal(isPortalDemoAuthEnabled({ NODE_ENV: 'development' }), false);
    assert.equal(
      authenticatePortalDemo(
        localDemoEnv.PORTAL_DEMO_EMAIL,
        localDemoEnv.PORTAL_DEMO_PASSWORD,
        { NODE_ENV: 'development', PORTAL_DEMO_AUTH: 'true' },
      ),
      null,
    );
    const session = authenticatePortalDemo(
      localDemoEnv.PORTAL_DEMO_EMAIL,
      localDemoEnv.PORTAL_DEMO_PASSWORD,
      localDemoEnv,
    );
    assert.equal(session.investorId, 'portal-inv-a');
    assert.equal(session.email, localDemoEnv.PORTAL_DEMO_EMAIL);
    assert.ok(session.issuedAt);
    assert.equal(
      authenticatePortalDemo(localDemoEnv.PORTAL_DEMO_EMAIL, 'wrong-password', localDemoEnv),
      null,
    );
  });
});
