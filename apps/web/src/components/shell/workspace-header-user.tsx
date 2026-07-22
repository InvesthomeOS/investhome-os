'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';

import { IhIcon } from '@/components/icons/ih-icons';
import { useAuth } from '@/lib/auth/auth-context';

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return 'IH';
  const first = parts[0] ?? '';
  if (parts.length === 1) return first.slice(0, 2).toUpperCase() || 'IH';
  const second = parts[1] ?? '';
  return `${first.charAt(0)}${second.charAt(0)}`.toUpperCase() || 'IH';
}

/** Shared header profile cluster for all workspace shells. */
export function WorkspaceHeaderUser() {
  const t = useTranslations('auth');
  const { user, logout, loading } = useAuth();

  if (loading || !user) {
    return null;
  }

  return (
    <div className="app-header__user">
      <span className="app-header__avatar" aria-hidden="true">
        {initials(user.full_name)}
      </span>
      <div className="app-header__user-meta">
        <Link className="app-header__user-name" href="/dashboard/profile">
          {user.full_name}
        </Link>
      </div>
      <button
        className="app-header__logout"
        type="button"
        onClick={() => void logout()}
        aria-label={t('logout')}
        title={t('logout')}
      >
        <IhIcon name="logout" size={16} />
      </button>
    </div>
  );
}
