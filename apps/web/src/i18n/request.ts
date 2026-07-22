import { cookies } from 'next/headers';
import { getRequestConfig } from 'next-intl/server';

import enMessages from '../../messages/en.json';
import trMessages from '../../messages/tr.json';
import siteEnMessages from '../../messages/site-en.json';
import siteTrMessages from '../../messages/site-tr.json';
import portalEnMessages from '../../messages/portal-en.json';
import portalTrMessages from '../../messages/portal-tr.json';
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

  // English fills gaps for Turkish; locale-specific strings override the base catalog.
  // Public site catalogs (site-en / site-tr) merge last so P7 strings always win.
  // Portal G9 catalogs merge after site so investor-portal copy is available.
  const base =
    locale === defaultLocale
      ? mergeMessages(enMessages as Messages, trMessages as Messages)
      : mergeMessages(trMessages as Messages, enMessages as Messages);
  const withSite =
    locale === defaultLocale
      ? mergeMessages(base, siteTrMessages as Messages)
      : mergeMessages(base, siteEnMessages as Messages);
  const withPortal =
    locale === defaultLocale
      ? mergeMessages(withSite, portalTrMessages as Messages)
      : mergeMessages(withSite, portalEnMessages as Messages);

  return {
    locale,
    messages: withPortal,
  };
});
