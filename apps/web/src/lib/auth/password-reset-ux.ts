/** Pure password-reset UX helpers. No network calls and no account existence checks. */

export const PASSWORD_MIN_LENGTH = 12;
export const PASSWORD_MAX_LENGTH = 256;

export type PasswordVisibility = {
  value: string;
  visible: boolean;
};

export type ResetFailureKind =
  | 'too_short'
  | 'too_long'
  | 'invalid_chars'
  | 'common'
  | 'trivial'
  | 'identity'
  | 'policy'
  | 'malformed'
  | 'invalid_link'
  | 'expired'
  | 'used'
  | 'rate_limit'
  | 'unexpected';

const POLICY_CODES: Record<string, ResetFailureKind> = {
  password_too_short: 'too_short',
  password_too_long: 'too_long',
  password_invalid: 'invalid_chars',
  password_common: 'common',
  password_trivial: 'trivial',
  password_identity: 'identity',
  password_rejected: 'policy',
};

const RESET_CODES: Record<string, ResetFailureKind> = {
  reset_malformed: 'malformed',
  reset_invalid: 'invalid_link',
  reset_expired: 'expired',
  reset_used: 'used',
};

export function togglePasswordVisibility(state: PasswordVisibility): PasswordVisibility {
  return { value: state.value, visible: !state.visible };
}

export function classifyResetFailure(input: {
  status?: number;
  reasonCode?: string | null;
  message?: string | null;
}): ResetFailureKind {
  if (input.status === 429) return 'rate_limit';
  const code = String(input.reasonCode || '').trim();
  const policy = POLICY_CODES[code];
  if (policy) return policy;
  const reset = RESET_CODES[code];
  if (reset) return reset;
  if (input.status === 422) return 'malformed';
  if (input.status != null && input.status >= 500) return 'unexpected';
  const message = String(input.message || '').toLowerCase();
  if (message.includes('expired')) return 'expired';
  if (message.includes('already been used')) return 'used';
  if (message.includes('malformed')) return 'malformed';
  if (message.includes('does not meet') || message.includes('password')) return 'policy';
  if (input.status === 400) return 'invalid_link';
  return 'unexpected';
}

export function classifyForgotFailure(status: number): 'rate_limit' | 'unexpected' {
  if (status === 429) return 'rate_limit';
  return 'unexpected';
}
