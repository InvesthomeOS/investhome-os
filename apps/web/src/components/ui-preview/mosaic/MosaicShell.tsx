'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

import { MosaicAvatar } from './MosaicAvatar';

const NAV: Array<{ href: Route; label: string; icon: 'dash' | 'leads' | 'cust' }> = [
  { href: '/ui-preview/mosaic/dashboard' as Route, label: 'Dashboard', icon: 'dash' },
  { href: '/ui-preview/mosaic/leads' as Route, label: 'Leads', icon: 'leads' },
  { href: '/ui-preview/mosaic/customer' as Route, label: 'Customer', icon: 'cust' },
];

type Props = {
  title: string;
  children: ReactNode;
  actions?: ReactNode;
};

function NavIcon({ name }: { name: 'dash' | 'leads' | 'cust' }) {
  if (name === 'dash') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
        <path d="M0 0h7v7H0V0Zm9 0h7v7H9V0ZM0 9h7v7H0V9Zm9 0h7v7H9V9Z" opacity="0.85" />
      </svg>
    );
  }
  if (name === 'leads') {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
        <path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm-5.5 6a5.5 5.5 0 0 1 11 0H2.5Z" />
      </svg>
    );
  }
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
      <path d="M8 1a3 3 0 1 1 0 6 3 3 0 0 1 0-6ZM2 14c0-3.3 2.7-5 6-5s6 1.7 6 5v1H2v-1Z" />
    </svg>
  );
}

export function MosaicShell({ title, children, actions }: Props) {
  const pathname = usePathname();

  return (
    <div className="mosaic-root" data-testid="mosaic-preview-root">
      <aside className="mosaic-sidebar" aria-label="Mosaic preview navigation">
        <div className="mosaic-sidebar__brand">
          <span className="mosaic-logo" aria-hidden>
            <svg width="28" height="28" viewBox="0 0 32 32" fill="currentColor">
              <path d="M31.956 14.8C31.372 6.92 25.08.628 17.2.044V5.76a9.04 9.04 0 0 0 9.04 9.04h5.716ZM14.8 26.24v5.716C6.92 31.372.63 25.08.044 17.2H5.76a9.04 9.04 0 0 1 9.04 9.04Zm11.44-9.04h5.716c-.584 7.88-6.876 14.172-14.756 14.756V26.24a9.04 9.04 0 0 1 9.04-9.04ZM.044 14.8C.63 6.92 6.92.628 14.8.044V5.76a9.04 9.04 0 0 1-9.04 9.04H.044Z" />
            </svg>
          </span>
          <div>
            <strong>Investhome OS</strong>
            <span>Mosaic Lite eval</span>
          </div>
        </div>

        <p className="mosaic-sidebar__section">Pages</p>
        <nav className="mosaic-sidebar__nav">
          {NAV.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`mosaic-nav-link${active ? ' is-active' : ''}`}
                data-testid={`mosaic-nav-${item.label.toLowerCase()}`}
              >
                <NavIcon name={item.icon} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="mosaic-sidebar__foot">
          <p className="mosaic-sidebar__section">Preview</p>
          <p className="mosaic-sidebar__note">
            Isolated visual evaluation. Demo data only — not connected to production APIs.
          </p>
        </div>
      </aside>

      <div className="mosaic-main">
        <header className="mosaic-header">
          <div className="mosaic-header__left">
            <h1>{title}</h1>
          </div>
          <div className="mosaic-header__right">
            <button type="button" className="mosaic-icon-btn" aria-label="Search">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
                <path d="M7 14c-3.86 0-7-3.14-7-7s3.14-7 7-7 7 3.14 7 7-3.14 7-7 7ZM7 2C4.243 2 2 4.243 2 7s2.243 5 5 5 5-2.243 5-5-2.243-5-5-5Z" />
                <path d="m13.314 11.9 2.393 2.393a.999.999 0 1 1-1.414 1.414L11.9 13.314a8.019 8.019 0 0 0 1.414-1.414Z" />
              </svg>
            </button>
            <button type="button" className="mosaic-icon-btn" aria-label="Notifications">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
                <path d="M8 0a1 1 0 0 1 1 1v.07A5.005 5.005 0 0 1 13 6v3.586l1.707 1.707A1 1 0 0 1 14 13H2a1 1 0 0 1-.707-1.707L3 9.586V6a5.005 5.005 0 0 1 4-4.93V1a1 1 0 0 1 1-1Zm0 15a2 2 0 0 1-1.995-1.85L6 13h4a2 2 0 0 1-2 2Z" />
              </svg>
            </button>
            <div className="mosaic-header__user">
              <MosaicAvatar name="Super Admin" size="sm" tone="violet" />
              <span>Super Admin</span>
            </div>
          </div>
        </header>

        <div className="mosaic-toolbar">
          <div className="mosaic-toolbar__meta">
            <span className="mosaic-pill mosaic-pill--violet">Preview</span>
            <span className="mosaic-muted">cruip/tailwind-dashboard-template · scoped CSS</span>
          </div>
          {actions ? <div className="mosaic-toolbar__actions">{actions}</div> : null}
        </div>

        <main className="mosaic-content">{children}</main>
      </div>
    </div>
  );
}
