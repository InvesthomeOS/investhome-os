import type { LocaleText } from './types';

export function lt(locale: string, text: LocaleText): string {
  return locale === 'en' ? text.en : text.tr;
}

export function L(en: string, tr: string): LocaleText {
  return { en, tr };
}
