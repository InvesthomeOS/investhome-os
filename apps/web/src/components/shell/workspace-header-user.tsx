'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { useEffect, useId, useRef, useState } from 'react';

import { IhIcon } from '@/components/icons/ih-icons';
import { useAuth } from '@/lib/auth/auth-context';

function initials(name: string): string {
  const parts = name
    .trim()
    .split(/\s+/)
    .map((part) => part.replace(/[^\p{L}\p{N}]/gu, ''))
    .filter(Boolean);
  if (parts.length === 0) return 'IH';
  const first = parts[0] ?? '';
  if (parts.length === 1) return first.slice(0, 2).toUpperCase() || 'IH';
  const second = parts[1] ?? '';
  return `${first.charAt(0)}${second.charAt(0)}`.toUpperCase() || 'IH';
}

type WorkspaceHeaderUserProps = {
  /**
   * `screenshot` keeps the Dashboard home chrome look and opens an account menu.
   * Logout always uses the shared auth-context flow.
   */
  variant?: 'default' | 'screenshot';
};

/** Shared header profile cluster for all workspace shells. */
export function WorkspaceHeaderUser({ variant = 'default' }: WorkspaceHeaderUserProps) {
  const t = useTranslations('auth');
  const tShot = useTranslations('screenshotDashboard');
  const { user, logout, loading } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!menuOpen || variant !== 'screenshot') return;

    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [menuOpen, variant]);

  if (loading || !user) {
    return null;
  }

  if (variant === 'screenshot') {
    const roleLabel =
      user.job_title?.trim() || user.roles[0]?.name || tShot('header.profileRole');

    return (
      <div className="screenshot-header__profile-wrap" ref={rootRef}>
        <button
          type="button"
          className="screenshot-header__profile"
          aria-expanded={menuOpen}
          aria-haspopup="menu"
          aria-controls={menuId}
          aria-label={tShot('header.accountMenu')}
          data-testid="dashboard-user-menu"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span className="screenshot-header__avatar" aria-hidden="true">
            {initials(user.full_name)}
          </span>
          <span className="screenshot-header__identity">
            <strong>{user.full_name}</strong>
            <small>{roleLabel}</small>
          </span>
          <IhIcon name="chevronDown" size={13} />
        </button>
        {menuOpen ? (
          <div
            id={menuId}
            className="screenshot-header__account-menu"
            role="menu"
            data-testid="dashboard-user-menu-panel"
          >
            <Link
              role="menuitem"
              className="screenshot-header__account-item"
              href="/dashboard/profile"
              onClick={() => setMenuOpen(false)}
            >
              {tShot('header.profile')}
            </Link>
            <button
              type="button"
              role="menuitem"
              className="screenshot-header__account-item screenshot-header__account-item--logout"
              data-testid="dashboard-user-logout"
              onClick={() => {
                setMenuOpen(false);
                void logout();
              }}
            >
              {t('logout')}
            </button>
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className="app-header__user" data-testid="workspace-header-user">
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
        data-testid="workspace-header-logout"
      >
        <IhIcon name="logout" size={16} />
      </button>
    </div>
  );
}
