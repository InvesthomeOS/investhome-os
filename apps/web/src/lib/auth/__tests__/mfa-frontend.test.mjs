/**
 * MFA frontend flow contracts. No secrets logged. No browser storage.
 * Run: node --test src/lib/auth/__tests__/mfa-frontend.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

import {
  MFA_STORAGE_FORBIDDEN_KEYS,
  acknowledgeRecoveryCodes,
  applyEnrollConfirmed,
  applyEnrollStart,
  applyMfaVerified,
  applyPasswordLogin,
  createEmptyMfaSession,
  formatManualSetupKey,
  isCurrentUserResponse,
  isMfaChallengeResponse,
  mapEnrollHttpError,
  mapMfaHttpError,
  parseOtpauthSecret,
  sourceAvoidsBrowserSecretStorage,
} from '../mfa-flow.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const webSrc = join(here, '../../..');

function read(rel) {
  return readFileSync(join(webSrc, rel), 'utf8');
}

const currentUser = {
  id: '00000000-0000-0000-0000-000000000001',
  email: 'sales@investhome.demo',
  full_name: 'Sales User',
  mfa_enabled: false,
};

const challenge = {
  mfa_required: true,
  mfa_challenge_token: 'challenge-token-16+',
  mfa_method: 'totp',
  expires_in: 300,
};

const otpauth =
  'otpauth://totp/InvestHomeOS:sales@investhome.demo?secret=JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP&issuer=InvestHomeOS';

describe('non-MFA login still authenticates', () => {
  it('treats a current-user payload as authenticated and stores no challenge', () => {
    const next = applyPasswordLogin(createEmptyMfaSession(), currentUser);
    assert.equal(next.authenticated, true);
    assert.equal(next.user.email, currentUser.email);
    assert.equal(next.mfaPending, null);
  });
});

describe('MFA login second step', () => {
  it('does not authenticate when login returns mfa_required', () => {
    const next = applyPasswordLogin(createEmptyMfaSession(), challenge);
    assert.equal(next.authenticated, false);
    assert.equal(next.user, null);
    assert.equal(next.mfaPending.token, challenge.mfa_challenge_token);
    assert.equal(isMfaChallengeResponse(challenge), true);
    assert.equal(isCurrentUserResponse(challenge), false);
  });

  it('rejects short challenge tokens', () => {
    assert.equal(isMfaChallengeResponse({ mfa_required: true, mfa_challenge_token: 'short' }), false);
  });
});

describe('valid TOTP completes login', () => {
  it('authenticates only after verify returns the current user', () => {
    const pending = applyPasswordLogin(createEmptyMfaSession(), challenge);
    const done = applyMfaVerified(pending, { ...currentUser, mfa_enabled: true });
    assert.equal(done.authenticated, true);
    assert.equal(done.mfaPending, null);
    assert.equal(done.user.mfa_enabled, true);
  });
});

describe('invalid TOTP / expired challenge / 429 / unavailable', () => {
  it('maps invalid and expired challenges to a generic key', () => {
    assert.equal(mapMfaHttpError(401), 'invalidOrExpired');
    assert.equal(mapMfaHttpError(400), 'invalidOrExpired');
  });

  it('maps 429 to tooManyAttempts', () => {
    assert.equal(mapMfaHttpError(429), 'tooManyAttempts');
  });

  it('maps backend unavailability without leaking internals', () => {
    assert.equal(mapMfaHttpError(503), 'unavailable');
    assert.equal(mapMfaHttpError(0), 'unavailable');
    assert.equal(mapMfaHttpError(500), 'verifyFailed');
  });
});

describe('recovery code login', () => {
  it('uses the same verify success path for recovery codes', () => {
    const pending = applyPasswordLogin(createEmptyMfaSession(), challenge);
    const done = applyMfaVerified(pending, { ...currentUser, mfa_enabled: true });
    assert.equal(done.authenticated, true);
    const loginPage = read('app/login/page.tsx');
    const verifyForm = read('components/auth/mfa-verify-form.tsx');
    assert.match(verifyForm, /mfa-verify-code/);
    assert.match(verifyForm, /maxLength=\{32\}/);
    assert.match(loginPage, /MfaVerifyForm/);
    assert.match(loginPage, /completeMfaLogin/);
  });
});

describe('enrollment start/confirm and one-time recovery codes', () => {
  it('derives a manual setup key from the otpauth URI', () => {
    assert.equal(parseOtpauthSecret(otpauth), 'JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP');
    assert.equal(formatManualSetupKey(parseOtpauthSecret(otpauth)), 'JBSW Y3DP EHPK 3PXP JBSW Y3DP EHPK 3PXP');
  });

  it('starts enrollment, confirms, shows recovery codes once, then clears them', () => {
    let session = applyPasswordLogin(createEmptyMfaSession(), currentUser);
    session = applyEnrollStart(session, {
      otpauth_uri: otpauth,
      issuer: 'InvestHomeOS',
      account_label: 'sales@investhome.demo',
      pending: true,
    });
    assert.equal(session.enrollStep, 'setup');
    assert.ok(session.manualSetupKey.includes('JBSW'));
    session = applyEnrollConfirmed(session, {
      mfa_enabled: true,
      mfa_method: 'totp',
      recovery_codes: ['AAAAA-11111', 'BBBBB-22222'],
    });
    assert.deepEqual(session.recoveryCodes, ['AAAAA-11111', 'BBBBB-22222']);
    assert.equal(session.enrollStep, 'recovery');
    session = acknowledgeRecoveryCodes(session);
    assert.equal(session.recoveryCodes, null);
    assert.equal(session.enrollStep, 'enabled');
  });

  it('maps enroll errors safely', () => {
    assert.equal(mapEnrollHttpError(400), 'invalidCode');
    assert.equal(mapEnrollHttpError(429), 'tooManyAttempts');
    assert.equal(mapEnrollHttpError(409), 'alreadyEnabled');
    assert.equal(mapEnrollHttpError(0), 'unavailable');
  });
});

describe('challenge stays in memory; secrets are not stored', () => {
  it('keeps the challenge on an in-memory session object only', () => {
    const writes = [];
    const storage = {
      setItem(key, value) {
        writes.push([key, value]);
      },
    };
    const session = applyPasswordLogin(createEmptyMfaSession(), challenge);
    assert.equal(session.mfaPending.token, challenge.mfa_challenge_token);
    assert.equal(writes.length, 0);
    void storage;
  });

  it('does not write MFA secrets to localStorage or sessionStorage in frontend MFA files', () => {
    const files = [
      'lib/auth/mfa-flow.mjs',
      'lib/auth/mfa-flow.ts',
      'lib/auth/auth-context.tsx',
      'lib/api/auth.ts',
      'app/login/page.tsx',
      'components/auth/mfa-verify-form.tsx',
      'components/auth/mfa-enroll-card.tsx',
      'components/auth/mfa-required-enroll-form.tsx',
      'components/auth/otpauth-qr.tsx',
      'app/dashboard/profile/page.tsx',
    ];
    for (const file of files) {
      const source = read(file);
      assert.equal(sourceAvoidsBrowserSecretStorage(source), true, file);
      assert.doesNotMatch(source, /(?:localStorage|sessionStorage)\.(?:setItem|set)\s*\(/);
      assert.doesNotMatch(source, /console\.(log|debug|info|warn)\(/);
    }
  });

  it('auth context keeps the challenge in React state and does not setUser on mfa_required', () => {
    const authContext = read('lib/auth/auth-context.tsx');
    assert.match(authContext, /useState<MfaPendingChallenge \| null>\(null\)/);
    assert.match(authContext, /isMfaChallengeResponse\(result\)/);
    assert.match(authContext, /setUser\(null\)/);
    assert.match(authContext, /completeMfaLogin/);
    assert.match(authContext, /verifyMfaLogin\(mfaPending\.token, code\)/);
    assert.doesNotMatch(authContext, /localStorage/);
    const loginApi = read('lib/api/auth.ts');
    assert.match(loginApi, /\/auth\/mfa\/enroll/);
    assert.match(loginApi, /\/auth\/mfa\/enroll\/confirm/);
    assert.match(loginApi, /\/auth\/mfa\/verify/);
  });

  it('UI shows MFA verify and enrollment surfaces with one-time recovery display', () => {
    const loginPage = read('app/login/page.tsx');
    const enroll = read('components/auth/mfa-enroll-card.tsx');
    const profile = read('app/dashboard/profile/page.tsx');
    assert.match(loginPage, /mfaPending \?/);
    assert.match(loginPage, /data-testid="login-password-form"/);
    assert.match(enroll, /data-testid="mfa-enroll-enable"/);
    assert.match(enroll, /data-testid="mfa-enroll-qr"|OtpauthQr/);
    assert.match(enroll, /data-testid="mfa-enroll-manual-key"/);
    assert.match(enroll, /data-testid="mfa-enroll-recovery"/);
    assert.match(enroll, /setRecoveryCodes\(null\)/);
    assert.match(profile, /MfaEnrollCard/);
    const qr = read('components/auth/otpauth-qr.tsx');
    assert.match(qr, /encode\(uri\)/);
    assert.doesNotMatch(qr, /https?:\/\/.*qr/);
  });

  it('forbidden storage keys stay listed for audits', () => {
    assert.ok(MFA_STORAGE_FORBIDDEN_KEYS.includes('mfa_challenge_token'));
    assert.ok(MFA_STORAGE_FORBIDDEN_KEYS.includes('recovery_codes'));
    assert.ok(MFA_STORAGE_FORBIDDEN_KEYS.includes('otpauth_uri'));
  });

  it('does not globally enforce MFA in frontend sources', () => {
    const loginPage = read('app/login/page.tsx');
    const middleware = readFileSync(join(webSrc, 'middleware.ts'), 'utf8');
    assert.doesNotMatch(loginPage, /mfa_enabled/);
    assert.doesNotMatch(middleware, /mfa_required|mfa_enabled/);
  });
});
