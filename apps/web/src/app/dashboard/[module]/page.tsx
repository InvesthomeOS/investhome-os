import Link from 'next/link';
import type { Route } from 'next';
import { notFound, redirect } from 'next/navigation';
import { getTranslations } from 'next-intl/server';

import { isModuleName } from '@/lib/modules';

interface ModulePageProps {
  params: Promise<{ module: string }>;
}

export default async function ModulePage({ params }: ModulePageProps) {
  const { module } = await params;

  if (!isModuleName(module)) {
    notFound();
  }

  if (module === 'leads') {
    redirect('/dashboard/leads' as Route);
  }

  const t = await getTranslations('navigation');
  const tDashboard = await getTranslations('dashboard');
  const tCommon = await getTranslations('common');

  return (
    <main className="dashboard">
      <header className="dashboard__header">
        <div>
          <Link href="/dashboard" className="dashboard__back">
            {tCommon('backToDashboard')}
          </Link>
          <h1 className="dashboard__title">{t(`modules.${module}.title`)}</h1>
        </div>
      </header>

      <section className="dashboard__panel">
        <p className="dashboard__panel-description">{t(`modules.${module}.description`)}</p>
        <p className="dashboard__placeholder">{tDashboard('placeholder.description')}</p>
      </section>
    </main>
  );
}
