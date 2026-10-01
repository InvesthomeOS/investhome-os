/**
 * Mandatory MFA enrollment frontend contracts. No secrets. No dashboard bypass.
 * Run: node --test src/lib/auth/__tests__/mfa-enforcement.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

import {
  MFA_STORAGE_FORBIDDEN_KEYS,
  acknowledgeRequiredEnrollment,
  applyEnrollStart,
  applyPasswordLogin,
  applyRequiredEnrollConfirmed,
  canEnterDashboard,
  createEmptyMfaSession,
  isCurrentUserResponse,
  isMfaEnrollmentRequiredResponse,
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

const privilegedUser = {
  id: '00000000-0000-0000-0000-000000000002',
  email: 'finance@investhome.demo',
  full_name: 'Finance User',
  mfa_enabled: true,
  mfa_method: 'totp',
};

const enrollment = {
  mfa_enrollment_required: true,
  mfa_enrollment_challenge_token: 'enrollment-token-16+',
  expires_in: 300,
};

const otpauth =
  'otpauth://totp/InvestHomeOS:finance@investhome.demo?secret=JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP&issuer=InvestHomeOS';

describe('mandatory role without MFA cannot enter dashboard after password', () => {
  it('keeps the session unauthenticated and blocks dashboard entry', () => {
    const next = applyPasswordLogin(createEmptyMfaSession(), enrollment);
    assert.equal(next.authenticated, false);
    assert.equal(next.user, null);
    assert.equal(canEnterDashboard(next), false);
    assert.equal(isCurrentUserResponse(enrollment), false);
    assert.equal(isMfaEnrollmentRequiredResponse(enrollment), true);
  });
});

describe('mandatory role is taken to MFA enrollment', () => {
  it('stores the enrollment challenge and starts setup from otpauth', () => {
    let session = applyPasswordLogin(createEmptyMfaSession(), enrollment);
    assert.equal(session.enrollmentPending.token, enrollment.mfa_enrollment_challenge_token);
    assert.equal(session.enrollStep, 'required');
    session = applyEnrollStart(session, {
      otpauth_uri: otpauth,
      issuer: 'InvestHomeOS',
      account_label: 'finance@investhome.demo',
      pending: true,
    });
    assert.equal(session.enrollStep, 'setup');
    assert.ok(session.manualSetupKey.includes('JBSW'));
    assert.equal(session.authenticated, false);
    assert.equal(canEnterDashboard(session), false);
  });
});

describe('successful enrollment creates session only after recovery ack', () => {
  it('shows recovery codes, then authenticates and allows dashboard', () => {
    let session = applyPasswordLogin(createEmptyMfaSession(), enrollment);
    session = applyEnrollStart(session, { otpauth_uri: otpauth, pending: true });
    session = applyRequiredEnrollConfirmed(session, {
      mfa_enabled: true,
      mfa_method: 'totp',
      recovery_codes: ['AAAAA-11111', 'BBBBB-22222'],
      user: privilegedUser,
    });
    assert.equal(session.authenticated, false);
    assert.deepEqual(session.recoveryCodes, ['AAAAA-11111', 'BBBBB-22222']);
    assert.equal(canEnterDashboard(session), false);
    session = acknowledgeRequiredEnrollment(session);
    assert.equal(session.authenticated, true);
    assert.equal(session.enrollmentPending, null);
    assert.equal(session.recoveryCodes, null);
    assert.equal(canEnterDashboard(session), true);
  });
});

describe('mandatory role with MFA uses existing second-step login', () => {
  it('does not treat mfa_required as enrollment', () => {
    const challenge = {
      mfa_required: true,
      mfa_challenge_token: 'challenge-token-16+',
      mfa_method: 'totp',
      expires_in: 300,
    };
    const next = applyPasswordLogin(createEmptyMfaSession(), challenge);
    assert.equal(next.enrollmentPending, null);
    assert.ok(next.mfaPending.token);
    assert.equal(canEnterDashboard(next), false);
  });
});

describe('non-mandatory role login remains unchanged', () => {
  it('authenticates optional roles from a current-user payload', () => {
    const next = applyPasswordLogin(createEmptyMfaSession(), currentUser);
    assert.equal(next.authenticated, true);
    assert.equal(next.enrollmentPending, null);
    assert.equal(canEnterDashboard(next), true);
  });
});

describe('frontend cannot bypass enrollment', () => {
  it('rejects short enrollment tokens and current-user shaped enrollment payloads', () => {
    assert.equal(
      isMfaEnrollmentRequiredResponse({ mfa_enrollment_required: true, mfa_enrollment_challenge_token: 'short' }),
      false,
    );
    assert.equal(acknowledgeRequiredEnrollment(applyPasswordLogin(createEmptyMfaSession(), enrollment)).authenticated, false);
  });

  it('does not navigate to the dashboard until enrollment is finished', () => {
    const authContext = read('lib/auth/auth-context.tsx');
    assert.match(authContext, /isMfaEnrollmentRequiredResponse\(result\)/);
    assert.match(authContext, /setEnrollmentPending/);
    const enrollBlock = authContext.match(
      /if \(isMfaEnrollmentRequiredResponse\(result\)\) \{[\s\S]*?return;[\s\S]*?\}/,
    );
    assert.ok(enrollBlock);
    assert.doesNotMatch(enrollBlock[0], /router\.replace/);
    const loginPage = read('app/login/page.tsx');
    assert.match(loginPage, /enrollmentPending \?/);
    assert.match(loginPage, /MfaRequiredEnrollForm/);
    assert.match(loginPage, /finishRequiredEnrollment/);
    const form = read('components/auth/mfa-required-enroll-form.tsx');
    assert.match(form, /startRequiredMfaEnrollment\(challengeToken\)/);
    assert.match(form, /confirmRequiredMfaEnrollment\(challengeToken, submitted\)/);
    assert.match(form, /onComplete\(user\)/);
    assert.match(form, /data-testid="mfa-enroll-required-recovery"/);
    const middleware = readFileSync(join(webSrc, 'middleware.ts'), 'utf8');
    assert.match(middleware, /isValidSessionJwt\(session\)/);
  });

  it('does not persist enrollment tokens or secrets in browser storage', () => {
    const files = [
      'lib/auth/mfa-flow.mjs',
      'lib/auth/auth-context.tsx',
      'lib/api/auth.ts',
      'app/login/page.tsx',
      'components/auth/mfa-required-enroll-form.tsx',
    ];
    for (const file of files) {
      const source = read(file);
      assert.equal(sourceAvoidsBrowserSecretStorage(source), true, file);
      assert.doesNotMatch(source, /(?:localStorage|sessionStorage)\.(?:setItem|set)\s*\(/);
      assert.doesNotMatch(source, /console\.(log|debug|info|warn)\(/);
    }
    assert.ok(MFA_STORAGE_FORBIDDEN_KEYS.includes('mfa_enrollment_challenge_token'));
    const api = read('lib/api/auth.ts');
    assert.match(api, /\/auth\/mfa\/enroll\/required/);
    assert.match(api, /\/auth\/mfa\/enroll\/required\/confirm/);
  });
});
