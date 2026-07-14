export type AuthProvider = 'local' | 'oidc' | 'saml';

export interface AuthSession {
  userId: string;
  email: string;
  roles: string[];
  issuedAt: string;
  expiresAt: string;
}

export interface AuthContext {
  session: AuthSession | null;
  isAuthenticated: boolean;
}

export const AUTH_SESSION_COOKIE = 'ih_session' as const;
