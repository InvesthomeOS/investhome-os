'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';

import { useAuth } from '@/lib/auth/auth-context';

import { LanguageSelector } from './language-selector';
import { OperationalStatus } from './operational-status';

export function DashboardHeaderActions() {
  const t = useTranslations('auth');
  const { user, logout, loading } = useAuth();

  return (
    <div className="dashboard__header-actions">
      <LanguageSelector />
      <OperationalStatus />
      {!loading && user && (
        <div className="dashboard__user-menu">
          <Link className="dashboard__user-link" href="/dashboard/profile">
            {user.full_name}
          </Link>
          <button className="dashboard__logout" type="button" onClick={() => void logout()}>
            {t('logout')}
          </button>
        </div>
      )}
    </div>
  );
}
