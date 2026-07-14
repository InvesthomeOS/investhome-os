import { cookies } from 'next/headers';
import { getRequestConfig } from 'next-intl/server';

import enMessages from '../../messages/en.json';
import trMessages from '../../messages/tr.json';
import { defaultLocale, LOCALE_COOKIE, locales, type AppLocale } from './config';
import { mergeMessages, type Messages } from './merge-messages';

function resolveLocale(raw: string | undefined): AppLocale {
  if (raw && (locales as readonly string[]).includes(raw)) {
    return raw as AppLocale;
  }

  return defaultLocale;
}

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const locale = resolveLocale(cookieStore.get(LOCALE_COOKIE)?.value);

  const messages =
    locale === defaultLocale
      ? (trMessages as Messages)
      : mergeMessages(trMessages as Messages, enMessages as Messages);

  return {
    locale,
    messages,
  };
});
