'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { usePathname } from 'next/navigation';

import { MODULE_NAMES, type ModuleName } from '@investhome/shared';

import { MODULE_SECTIONS } from '@/lib/modules';

function moduleHref(module: ModuleName): Route {
  return `/dashboard/${module}` as Route;
}

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <aside className="dashboard-shell__sidebar">
      <div className="dashboard-shell__brand">
        <Link href="/dashboard" className="dashboard-shell__brand-link">
          <span className="dashboard__eyebrow">Investhome OS</span>
          <span className="dashboard-shell__brand-title">Operations</span>
        </Link>
      </div>

      <nav className="dashboard-shell__nav" aria-label="Module navigation">
        {MODULE_NAMES.map((module) => {
          const href = moduleHref(module);
          const isActive = pathname === href || pathname.startsWith(`${href}/`);
          const section = MODULE_SECTIONS[module];
          const isImplemented = module === 'leads';

          return (
            <Link
              key={module}
              href={href}
              className={`dashboard-shell__nav-link${isActive ? ' dashboard-shell__nav-link--active' : ''}`}
              aria-current={isActive ? 'page' : undefined}
            >
              <span>{section.title}</span>
              {!isImplemented && <span className="dashboard-shell__nav-badge">Soon</span>}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
