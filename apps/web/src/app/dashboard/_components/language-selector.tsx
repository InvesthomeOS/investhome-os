'use client';

import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useTransition } from 'react';

import { LOCALE_COOKIE, locales, type AppLocale } from '@/i18n/config';

function setLocaleCookie(locale: AppLocale) {
  document.cookie = `${LOCALE_COOKIE}=${locale};path=/;max-age=${60 * 60 * 24 * 365};samesite=lax`;
}

export function LanguageSelector() {
  const locale = useLocale() as AppLocale;
  const router = useRouter();
  const t = useTranslations('common');
  const [isPending, startTransition] = useTransition();

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const nextLocale = event.target.value as AppLocale;

    if (nextLocale === locale || !(locales as readonly string[]).includes(nextLocale)) {
      return;
    }

    setLocaleCookie(nextLocale);
    startTransition(() => {
      router.refresh();
    });
  };

  return (
    <label className="dashboard__language">
      <span className="dashboard__language-label">{t('languageLabel')}</span>
      <select
        className="dashboard__language-select"
        value={locale}
        onChange={handleChange}
        disabled={isPending}
        aria-label={t('languageLabel')}
      >
        <option value="tr">{t('languageTurkish')}</option>
        <option value="en">{t('languageEnglish')}</option>
      </select>
    </label>
  );
}
