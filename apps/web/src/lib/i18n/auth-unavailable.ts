import { defaultLocale, locales, type AppLocale } from '@/i18n/config';

/** Edge-safe copy of auth.serviceUnavailable. Keep in sync with the message catalogs. */
export const AUTH_SERVICE_UNAVAILABLE: Record<AppLocale, string> = {
  tr: 'Kimlik doğrulama hizmeti geçici olarak kullanılamıyor.',
  en: 'Authentication service is temporarily unavailable.',
};

export function authServiceUnavailableMessage(locale: string | undefined): string {
  if (locale && (locales as readonly string[]).includes(locale)) {
    return AUTH_SERVICE_UNAVAILABLE[locale as AppLocale];
  }
  return AUTH_SERVICE_UNAVAILABLE[defaultLocale];
}

/** Edge-safe copy of auth.sessionLoadFailed. Keep in sync with the message catalogs. */
export const AUTH_SESSION_LOAD_FAILED: Record<AppLocale, string> = {
  tr: 'Oturum yüklenemedi.',
  en: 'Unable to load session.',
};

export function authSessionLoadFailedMessage(locale: string | undefined): string {
  if (locale && (locales as readonly string[]).includes(locale)) {
    return AUTH_SESSION_LOAD_FAILED[locale as AppLocale];
  }
  return AUTH_SESSION_LOAD_FAILED[defaultLocale];
}
