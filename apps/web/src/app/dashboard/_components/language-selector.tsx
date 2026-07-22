'use client';

import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useTransition } from 'react';

import { locales, type AppLocale } from '@/i18n/config';
import { useAuth } from '@/lib/auth/auth-context';
import { writeLocaleCookie } from '@/lib/i18n/locale-cookie';

export function LanguageSelector() {
  const locale = useLocale() as AppLocale;
  const router = useRouter();
  const t = useTranslations('common');
  const { setPreferredLocale } = useAuth();
  const [isPending, startTransition] = useTransition();

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const nextLocale = event.target.value as AppLocale;

    if (nextLocale === locale || !(locales as readonly string[]).includes(nextLocale)) {
      return;
    }

    // Explicit selection always wins (cookie + preferred_language sync).
    writeLocaleCookie(nextLocale);
    startTransition(() => {
      void (async () => {
        await setPreferredLocale(nextLocale);
        router.refresh();
      })();
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
