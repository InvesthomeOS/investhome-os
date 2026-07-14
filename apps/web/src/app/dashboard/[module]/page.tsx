import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';

import { isModuleName, MODULE_SECTIONS } from '@/lib/modules';

interface ModulePageProps {
  params: Promise<{ module: string }>;
}

export default async function ModulePage({ params }: ModulePageProps) {
  const { module } = await params;

  if (!isModuleName(module)) {
    notFound();
  }

  if (module === 'leads') {
    redirect('/dashboard/leads');
  }

  const section = MODULE_SECTIONS[module];

  return (
    <main className="dashboard">
      <header className="dashboard__header">
        <div>
          <Link href="/dashboard" className="dashboard__back">
            ← Dashboard
          </Link>
          <h1 className="dashboard__title">{section.title}</h1>
        </div>
      </header>

      <section className="dashboard__panel">
        <p className="dashboard__panel-description">{section.description}</p>
        <p className="dashboard__placeholder">
          Module workspace placeholder — API integration and live data are not yet
          implemented for this section.
        </p>
      </section>
    </main>
  );
}
