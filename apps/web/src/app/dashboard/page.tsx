import Link from 'next/link';
import type { Route } from 'next';
import { getTranslations } from 'next-intl/server';

import { MODULE_NAMES } from '@investhome/shared';

import { DashboardHeaderActions } from './_components/dashboard-header-actions';

export default async function DashboardPage() {
  const t = await getTranslations('dashboard');
  const tNav = await getTranslations('navigation');

  return (
    <main className="dashboard">
      <header className="dashboard__header">
        <div>
          <p className="dashboard__eyebrow">{t('eyebrow')}</p>
          <h1 className="dashboard__title">{t('title')}</h1>
        </div>
        <DashboardHeaderActions />
      </header>

      <section className="dashboard__grid">
        {MODULE_NAMES.map((module) => (
          <Link
            key={module}
            href={`/dashboard/${module}` as Route}
            className="dashboard__card-link"
          >
            <article className="dashboard__card">
              <h2>{tNav(`modules.${module}.title`)}</h2>
              <p>{tNav(`modules.${module}.description`)}</p>
            </article>
          </Link>
        ))}
      </section>
    </main>
  );
}
