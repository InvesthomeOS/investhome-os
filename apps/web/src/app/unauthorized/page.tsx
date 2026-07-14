'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';

export default function UnauthorizedPage() {
  const t = useTranslations('auth');

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-card__title">{t('unauthorizedTitle')}</h1>
        <p className="auth-card__subtitle">{t('unauthorizedDescription')}</p>
        <Link className="auth-form__submit auth-form__submit--link" href="/login">
          {t('backToLogin')}
        </Link>
      </div>
    </div>
  );
}
