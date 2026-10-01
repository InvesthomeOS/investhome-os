const MIN_SECRET_LENGTH = 32;

const FORBIDDEN_SECRETS = new Set([
  'dev-only-change-in-production-use-long-random-string',
  'replace-with-long-random-secret-at-least-32-chars',
  'investhome-portal-demo-session-secret',
  'replace-with-long-random-portal-secret',
  'dev-only-portal-session-secret-change-me',
  'replace-with-32-char-encryption-key',
]);

function requireSecret(name: string): void {
  const value = (process.env[name] || '').trim();
  if (!value || value.length < MIN_SECRET_LENGTH || FORBIDDEN_SECRETS.has(value)) {
    throw new Error(
      `${name} is required (>=${MIN_SECRET_LENGTH} chars) and must not be a published default`,
    );
  }
}

export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME === 'edge') {
    return;
  }
  requireSecret('JWT_SECRET');
  requireSecret('PORTAL_SESSION_SECRET');
}
