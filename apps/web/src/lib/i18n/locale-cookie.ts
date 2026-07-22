import { LOCALE_COOKIE, locales, type AppLocale } from '@/i18n/config';

export function readLocaleCookie(): AppLocale | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${LOCALE_COOKIE}=`));
  if (!match) return null;
  const value = match.split('=').slice(1).join('=');
  return (locales as readonly string[]).includes(value) ? (value as AppLocale) : null;
}

export function writeLocaleCookie(locale: AppLocale) {
  document.cookie = `${LOCALE_COOKIE}=${locale};path=/;max-age=${60 * 60 * 24 * 365};samesite=lax`;
}

/**
 * Resolve active locale with explicit product precedence:
 * 1. existing locale cookie (explicit selection / prior choice)
 * 2. preferred_language from user profile
 * 3. defaultLocale handled by next-intl request config
 */
export function resolveClientLocale(preferredLanguage?: string | null): AppLocale | null {
  const cookieLocale = readLocaleCookie();
  if (cookieLocale) return cookieLocale;
  if (preferredLanguage === 'tr' || preferredLanguage === 'en') {
    return preferredLanguage;
  }
  return null;
}
