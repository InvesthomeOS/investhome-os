/**
 * Admin MFA reset UI helpers. No secrets. Confirmation must be explicit.
 */

export const MFA_ADMIN_RESET_FORBIDDEN_RESPONSE_KEYS = Object.freeze([
  'totp_secret',
  'totp_secret_ciphertext',
  'otpauth_uri',
  'recovery_codes',
  'secret',
  'mfa_challenge_token',
]);

export function canManageSecurity(user) {
  if (!user) {
    return false;
  }
  const permissions = Array.isArray(user.permissions) ? user.permissions : [];
  return permissions.includes('*:*') || permissions.includes('security:manage');
}

export function canShowMfaAdminReset(user) {
  return canManageSecurity(user);
}

export function mfaAdminResetPath(userId) {
  if (!userId) {
    throw new Error('mfa_reset_missing_user');
  }
  return `/users/${userId}/mfa/reset`;
}

export function isSelfMfaReset(actorId, targetUserId) {
  return Boolean(actorId && targetUserId && actorId === targetUserId);
}

export function postMfaResetRedirect(actorId, targetUserId) {
  return isSelfMfaReset(actorId, targetUserId) ? '/login' : null;
}

export function shouldExecuteMfaReset(options) {
  return Boolean(options && options.confirmed === true);
}

export function parseMfaAdminResetResponse(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error('invalid_mfa_reset_response');
  }
  for (const key of MFA_ADMIN_RESET_FORBIDDEN_RESPONSE_KEYS) {
    if (Object.prototype.hasOwnProperty.call(payload, key)) {
      throw new Error('mfa_reset_leaked_secret');
    }
  }
  const sessionsRevoked = Number(payload.sessions_revoked);
  return {
    message: typeof payload.message === 'string' ? payload.message : '',
    sessions_revoked: Number.isFinite(sessionsRevoked) ? sessionsRevoked : 0,
  };
}
