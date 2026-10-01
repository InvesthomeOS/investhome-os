/**
 * Admin MFA reset UI contracts. No secrets. security:manage only.
 * Run: node --test src/lib/auth/__tests__/mfa-admin-reset.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

import {
  canShowMfaAdminReset,
  isSelfMfaReset,
  mfaAdminResetPath,
  parseMfaAdminResetResponse,
  postMfaResetRedirect,
  shouldExecuteMfaReset,
} from '../mfa-admin-reset.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const webSrc = join(here, '../../..');

function read(rel) {
  return readFileSync(join(webSrc, rel), 'utf8');
}

const actor = {
  id: 'admin-1',
  permissions: ['security:manage', 'users:view'],
};

describe('button visible only with security:manage', () => {
  it('shows for security:manage and super-admin wildcard', () => {
    assert.equal(canShowMfaAdminReset(actor), true);
    assert.equal(canShowMfaAdminReset({ id: 'sa', permissions: ['*:*'] }), true);
  });

  it('hides for users:manage, users:view, security:view, and signed-out', () => {
    assert.equal(canShowMfaAdminReset({ id: 'u', permissions: ['users:manage'] }), false);
    assert.equal(canShowMfaAdminReset({ id: 'u', permissions: ['users:view'] }), false);
    assert.equal(canShowMfaAdminReset({ id: 'u', permissions: ['security:view'] }), false);
    assert.equal(canShowMfaAdminReset(null), false);
    assert.equal(canShowMfaAdminReset(undefined), false);
  });
});

describe('confirmation required before reset', () => {
  it('does not execute unless confirmed is true', () => {
    assert.equal(shouldExecuteMfaReset({ confirmed: false }), false);
    assert.equal(shouldExecuteMfaReset({}), false);
    assert.equal(shouldExecuteMfaReset(null), false);
    assert.equal(shouldExecuteMfaReset({ confirmed: true }), true);
  });
});

describe('successful reset calls the existing endpoint', () => {
  it('builds POST /users/{user_id}/mfa/reset and accepts only non-secret payloads', () => {
    assert.equal(mfaAdminResetPath('user-42'), '/users/user-42/mfa/reset');
    const parsed = parseMfaAdminResetResponse({
      message: 'MFA reset. User must sign in again with password.',
      sessions_revoked: 3,
    });
    assert.equal(parsed.sessions_revoked, 3);
    assert.match(parsed.message, /MFA reset/);
    assert.throws(
      () => parseMfaAdminResetResponse({ message: 'ok', sessions_revoked: 1, recovery_codes: ['X'] }),
      /mfa_reset_leaked_secret/,
    );
    assert.throws(
      () => parseMfaAdminResetResponse({ totp_secret: 'abc', sessions_revoked: 0 }),
      /mfa_reset_leaked_secret/,
    );
  });
});

describe('self-reset redirects to login', () => {
  it('redirects only when the actor resets their own MFA', () => {
    assert.equal(isSelfMfaReset('admin-1', 'admin-1'), true);
    assert.equal(postMfaResetRedirect('admin-1', 'admin-1'), '/login');
    assert.equal(isSelfMfaReset('admin-1', 'other-9'), false);
    assert.equal(postMfaResetRedirect('admin-1', 'other-9'), null);
  });
});

describe('admin users workspace wires Reset MFA safely', () => {
  it('gates the button on security:manage, requires confirm, posts reset, redirects self', () => {
    const workspace = read('app/dashboard/admin/users/_components/users-admin-workspace.tsx');
    const api = read('lib/api/security-center.ts');
    const authApi = read('lib/api/auth.ts');
    const en = read('../messages/en.json');

    assert.match(workspace, /canShowMfaAdminReset\(currentUser\)/);
    assert.match(workspace, /data-testid="mfa-reset-button"/);
    assert.match(workspace, /data-testid="mfa-reset-confirm-dialog"/);
    assert.match(workspace, /data-testid="mfa-reset-confirm"/);
    assert.match(workspace, /data-testid="mfa-reset-cancel"/);
    assert.match(workspace, /shouldExecuteMfaReset\(\{ confirmed: true \}\)/);
    assert.match(workspace, /resetUserMfa\(mfaResetTarget\.id\)/);
    assert.match(workspace, /postMfaResetRedirect\(currentUser\.id, mfaResetTarget\.id\)/);
    assert.match(workspace, /await logout\(\)/);
    assert.match(workspace, /resetMfaConfirmSessions/);
    assert.doesNotMatch(workspace, /users:manage.*[Rr]eset MFA/);
    assert.doesNotMatch(workspace, /recovery_codes|otpauth_uri|totp_secret/);

    assert.match(api, /\/users\/\$\{userId\}\/mfa\/reset/);
    assert.match(api, /method: 'POST'/);
    assert.match(authApi, /hasPermission\(user, 'security', 'manage'\)/);

    assert.match(en, /"resetMfa": "Reset MFA"/);
    assert.match(en, /All active sessions for this user will be revoked/);
  });
});
