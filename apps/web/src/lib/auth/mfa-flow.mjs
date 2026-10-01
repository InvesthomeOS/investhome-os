/**
 * Pure MFA frontend helpers. No browser storage. Never log secrets.
 */

export const MFA_STORAGE_FORBIDDEN_KEYS = Object.freeze([
  'mfa_challenge_token',
  'mfa_challenge',
  'mfa_enrollment_challenge_token',
  'mfa_enrollment_required',
  'totp_secret',
  'otpauth_uri',
  'recovery_codes',
  'recovery_code',
]);

export function isMfaChallengeResponse(data) {
  if (!data || typeof data !== 'object') return false;
  return (
    data.mfa_required === true &&
    typeof data.mfa_challenge_token === 'string' &&
    data.mfa_challenge_token.length >= 16
  );
}

export function isMfaEnrollmentRequiredResponse(data) {
  if (!data || typeof data !== 'object') return false;
  return (
    data.mfa_enrollment_required === true &&
    typeof data.mfa_enrollment_challenge_token === 'string' &&
    data.mfa_enrollment_challenge_token.length >= 16
  );
}

export function isCurrentUserResponse(data) {
  if (!data || typeof data !== 'object') return false;
  return (
    typeof data.id === 'string' &&
    typeof data.email === 'string' &&
    data.mfa_required !== true &&
    data.mfa_enrollment_required !== true
  );
}

export function canEnterDashboard(session) {
  return Boolean(
    session &&
      session.authenticated &&
      session.user &&
      !session.mfaPending &&
      !session.enrollmentPending,
  );
}

export function parseOtpauthSecret(uri) {
  if (!uri || typeof uri !== 'string' || !uri.startsWith('otpauth://')) return null;
  const queryIndex = uri.indexOf('?');
  if (queryIndex < 0) return null;
  const params = new URLSearchParams(uri.slice(queryIndex + 1));
  const secret = params.get('secret');
  if (!secret) return null;
  return secret.replace(/\s+/g, '').toUpperCase();
}

export function formatManualSetupKey(secret) {
  if (!secret) return '';
  const compact = secret.replace(/\s+/g, '').toUpperCase();
  return compact.replace(/(.{4})/g, '$1 ').trim();
}

export function mapMfaHttpError(status) {
  if (status === 429) return 'tooManyAttempts';
  if (status === 503 || status === 502 || status === 504 || status === 0) return 'unavailable';
  if (status === 401 || status === 400) return 'invalidOrExpired';
  return 'verifyFailed';
}

export function mapEnrollHttpError(status) {
  if (status === 429) return 'tooManyAttempts';
  if (status === 503 || status === 502 || status === 504 || status === 0) return 'unavailable';
  if (status === 409) return 'alreadyEnabled';
  if (status === 400 || status === 401) return 'invalidCode';
  return 'enrollFailed';
}

export function createEmptyMfaSession() {
  return {
    user: null,
    mfaPending: null,
    enrollmentPending: null,
    authenticated: false,
    enrollStep: 'idle',
    otpauthUri: null,
    manualSetupKey: null,
    recoveryCodes: null,
  };
}

export function applyPasswordLogin(session, result) {
  if (isMfaChallengeResponse(result)) {
    return {
      ...session,
      user: null,
      authenticated: false,
      enrollmentPending: null,
      mfaPending: {
        token: result.mfa_challenge_token,
        method: result.mfa_method || 'totp',
        expiresIn: result.expires_in ?? 300,
      },
    };
  }
  if (isMfaEnrollmentRequiredResponse(result)) {
    return {
      ...session,
      user: null,
      authenticated: false,
      mfaPending: null,
      enrollmentPending: {
        token: result.mfa_enrollment_challenge_token,
        expiresIn: result.expires_in ?? 300,
      },
      enrollStep: 'required',
      otpauthUri: null,
      manualSetupKey: null,
      recoveryCodes: null,
    };
  }
  if (!isCurrentUserResponse(result)) {
    throw new Error('unexpected_login_response');
  }
  return {
    ...session,
    user: result,
    authenticated: true,
    mfaPending: null,
    enrollmentPending: null,
  };
}

export function applyMfaVerified(session, user) {
  if (!isCurrentUserResponse(user)) {
    throw new Error('unexpected_verify_response');
  }
  return {
    ...session,
    user,
    authenticated: true,
    mfaPending: null,
    enrollmentPending: null,
  };
}

export function cancelMfaChallenge(session) {
  return {
    ...session,
    mfaPending: null,
    enrollmentPending: null,
    authenticated: false,
    user: null,
    enrollStep: 'idle',
    otpauthUri: null,
    manualSetupKey: null,
    recoveryCodes: null,
  };
}

export function applyEnrollStart(session, enroll) {
  const secret = parseOtpauthSecret(enroll?.otpauth_uri);
  return {
    ...session,
    enrollStep: 'setup',
    otpauthUri: enroll?.otpauth_uri ?? null,
    manualSetupKey: secret ? formatManualSetupKey(secret) : null,
    recoveryCodes: null,
  };
}

export function applyEnrollConfirmed(session, confirm) {
  const codes = Array.isArray(confirm?.recovery_codes) ? confirm.recovery_codes.slice() : [];
  return {
    ...session,
    enrollStep: 'recovery',
    otpauthUri: null,
    manualSetupKey: null,
    recoveryCodes: codes,
    user: session.user
      ? { ...session.user, mfa_enabled: true, mfa_method: confirm?.mfa_method || 'totp' }
      : session.user,
  };
}

export function applyRequiredEnrollConfirmed(session, confirm) {
  const codes = Array.isArray(confirm?.recovery_codes) ? confirm.recovery_codes.slice() : [];
  const user = confirm?.user && isCurrentUserResponse(confirm.user) ? confirm.user : null;
  return {
    ...session,
    enrollStep: 'recovery',
    otpauthUri: null,
    manualSetupKey: null,
    recoveryCodes: codes,
    user,
    authenticated: false,
  };
}

export function acknowledgeRecoveryCodes(session) {
  return {
    ...session,
    recoveryCodes: null,
    enrollStep: 'enabled',
  };
}

export function acknowledgeRequiredEnrollment(session) {
  if (!session?.user || session.enrollStep === 'setup' || session.enrollStep === 'required') {
    return {
      ...session,
      authenticated: false,
    };
  }
  return {
    ...session,
    recoveryCodes: null,
    enrollStep: 'enabled',
    enrollmentPending: null,
    mfaPending: null,
    authenticated: true,
  };
}

export function sourceAvoidsBrowserSecretStorage(source) {
  if (!source || typeof source !== 'string') return false;
  const forbiddenWrites = /(?:localStorage|sessionStorage)\.(?:setItem|set)\s*\(/;
  if (!forbiddenWrites.test(source)) return true;
  return !MFA_STORAGE_FORBIDDEN_KEYS.some((key) => source.includes(key));
}
