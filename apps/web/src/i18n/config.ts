export const locales = ['tr', 'en'] as const;
export type AppLocale = (typeof locales)[number];

export const defaultLocale: AppLocale = 'tr';

export const LOCALE_COOKIE = 'investhome.locale';
