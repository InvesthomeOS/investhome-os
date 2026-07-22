'use client';

import Link from 'next/link';
import type { Route } from 'next';

export interface QuickActionDef {
  href: Route;
  label: string;
  show: boolean;
}

export function QuickActionsBar({
  title,
  actions,
  empty,
}: {
  title: string;
  actions: QuickActionDef[];
  empty: string;
}) {
  const visible = actions.filter((a) => a.show);
  return (
    <section className="ecc-quick" aria-label={title}>
      <h2 className="ecc-section-title">{title}</h2>
      {visible.length === 0 ? (
        <p className="leads__state">{empty}</p>
      ) : (
        <div className="ecc-quick__row">
          {visible.map((action) => (
            <Link key={action.label} href={action.href} className="ecc-quick__action">
              {action.label}
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}