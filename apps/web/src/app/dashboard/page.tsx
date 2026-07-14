import Link from 'next/link';
import type { Route } from 'next';

import { APP_NAME, MODULE_NAMES } from '@investhome/shared';

import { OperationalStatus } from './_components/operational-status';
import { MODULE_SECTIONS } from '@/lib/modules';

export default function DashboardPage() {
  return (
    <main className="dashboard">
      <header className="dashboard__header">
        <div>
          <p className="dashboard__eyebrow">Investhome OS</p>
          <h1 className="dashboard__title">{APP_NAME} Dashboard</h1>
        </div>
        <OperationalStatus />
      </header>

      <section className="dashboard__grid">
        {MODULE_NAMES.map((module) => {
          const section = MODULE_SECTIONS[module];

          return (
            <Link
              key={module}
              href={`/dashboard/${module}` as Route}
              className="dashboard__card-link"
            >
              <article className="dashboard__card">
                <h2>{section.title}</h2>
                <p>{section.description}</p>
              </article>
            </Link>
          );
        })}
      </section>
    </main>
  );
}
