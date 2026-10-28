/**
 * Login and reset-password UX contracts.
 * Run: node --test src/lib/auth/__tests__/password-reset-ux.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

import { classifyForgotFailure, classifyResetFailure, togglePasswordVisibility } from '../password-reset-ux.ts';

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = join(here, '../../../..');

function read(rel) {
  return readFileSync(join(webRoot, rel), 'utf8');
}

const login = read('src/app/login/page.tsx');
const reset = read('src/app/reset-password/page.tsx');
const field = read('src/components/auth/password-field.tsx');
const turkish = read('messages/tr.json');
const FORGOT_SUCCESS =
  'Şifre sıfırlama talebiniz alındı. E-posta adresiniz sistemde kayıtlıysa sıfırlama bağlantısı gönderilecektir.';
const RATE_LIMIT = 'Çok fazla deneme yapıldı. Lütfen kısa bir süre sonra tekrar deneyin.';

describe('forgot password link', () => {
  it('renders one text link and not a second button', () => {
    assert.equal((login.match(/data-testid="forgot-password-link"/g) || []).length, 1);
    assert.equal((login.match(/t\('forgotPassword'\)/g) || []).length, 1);
    assert.match(login, /className="auth-form__text-link"/);
    assert.doesNotMatch(login, /auth-form__hint/);
    assert.doesNotMatch(login, /auth-form__submit--link/);
    const linkAt = login.indexOf('data-testid="forgot-password-link"');
    const passwordAt = login.indexOf('testId="login-password"');
    const submitAt = login.indexOf('className="auth-form__submit"');
    assert.ok(passwordAt < linkAt && linkAt < submitAt);
  });
});

describe('password visibility', () => {
  it('toggles visibility without changing the entered value', () => {
    const shown = togglePasswordVisibility({ value: 'correct-horse-battery', visible: false });
    assert.equal(shown.visible, true);
    assert.equal(shown.value, 'correct-horse-battery');
    const hidden = togglePasswordVisibility(shown);
    assert.equal(hidden.visible, false);
    assert.equal(hidden.value, 'correct-horse-battery');
  });

  it('uses an in-field button that does not submit', () => {
    assert.match(field, /useState\(false\)/);
    assert.match(field, /type=\{visible \? 'text' : 'password'\}/);
    assert.match(field, /type="button"/);
    assert.match(field, /aria-pressed=\{visible\}/);
    assert.match(field, /aria-label=\{visible \? hideLabel : showLabel\}/);
    assert.doesNotMatch(field, /type="submit"/);
    assert.match(login, /testId="login-password"/);
    assert.match(reset, /testId="reset-new-password"/);
    assert.match(reset, /testId="reset-confirm-password"/);
  });
});

describe('reset and forgot messages', () => {
  it('shows the mismatch message before calling the API', () => {
    const mismatch = reset.indexOf("t('resetMismatch')");
    const request = reset.indexOf('await completePasswordReset');
    assert.ok(mismatch > -1 && mismatch < request);
    assert.match(reset, /password !== confirm/);
  });

  it('maps each password-policy reason instead of one generic length warning', () => {
    assert.equal(classifyResetFailure({ status: 400, reasonCode: 'password_too_short' }), 'too_short');
    assert.equal(classifyResetFailure({ status: 400, reasonCode: 'password_common' }), 'common');
    assert.equal(classifyResetFailure({ status: 400, reasonCode: 'password_trivial' }), 'trivial');
    assert.equal(classifyResetFailure({ status: 400, reasonCode: 'password_identity' }), 'identity');
    assert.match(reset, /resetErrors\.tooShort/);
    assert.match(reset, /resetErrors\.common/);
    assert.match(reset, /resetErrors\.identity/);
    assert.match(reset, /resetRules\.length/);
    assert.doesNotMatch(reset, /invite\.ruleLength/);
    assert.doesNotMatch(reset, /uppercase|lowercase|büyük harf|küçük harf|özel karakter/);
  });

  it('keeps invalid, expired, used, malformed, and server errors distinct', () => {
    assert.equal(classifyResetFailure({ status: 400, reasonCode: 'reset_invalid' }), 'invalid_link');
    assert.equal(classifyResetFailure({ status: 400, reasonCode: 'reset_expired' }), 'expired');
    assert.equal(classifyResetFailure({ status: 400, reasonCode: 'reset_used' }), 'used');
    assert.equal(classifyResetFailure({ status: 400, reasonCode: 'reset_malformed' }), 'malformed');
    assert.equal(classifyResetFailure({ status: 422 }), 'malformed');
    assert.equal(classifyResetFailure({ status: 500 }), 'unexpected');
    assert.notEqual(
      classifyResetFailure({ status: 400, reasonCode: 'reset_expired' }),
      classifyResetFailure({ status: 400, reasonCode: 'reset_used' }),
    );
  });

  it('shows the enumeration-safe success copy once and a rate-limit message for 429', () => {
    assert.equal(classifyForgotFailure(429), 'rate_limit');
    assert.equal(classifyForgotFailure(500), 'unexpected');
    assert.equal(classifyResetFailure({ status: 429 }), 'rate_limit');
    assert.match(login, /classifyForgotFailure/);
    assert.match(login, /t\('rateLimited'\)/);
    assert.match(login, /t\('forgotSent'\)/);
    assert.doesNotMatch(login, /\.catch\(\(\) => setForgotMessage\(t\('forgotSent'\)\)\)/);
    assert.equal((turkish.match(new RegExp(FORGOT_SUCCESS.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length, 1);
    assert.equal((turkish.match(new RegExp(RATE_LIMIT.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length, 1);
  });
});

describe('MFA flow stays independent', () => {
  it('keeps the existing login MFA branches and leaves reset password free of MFA', () => {
    assert.match(login, /<MfaVerifyForm/);
    assert.match(login, /<MfaRequiredEnrollForm/);
    assert.match(login, /mfaPending/);
    assert.match(login, /enrollmentPending/);
    assert.doesNotMatch(reset, /MfaVerifyForm|MfaRequiredEnrollForm|mfaPending|enrollmentPending/);
  });
});
