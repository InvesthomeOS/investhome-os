'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { fetchTemplates } from '@/workspaces/marketing/api/templates';

export function TemplatesWorkspace() {
  const t = useTranslations('marketing.templates');
  const listQuery = useQuery({ queryKey: ['marketing', 'templates', 'list'], queryFn: () => fetchTemplates() });

  return (
    <main className="dashboard marketing-module-shell">
      <header className="dashboard__header marketing-content__header">
        <div>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('subtitle')}</p>
        </div>
        <Link href={'/workspaces/marketing/templates/new' as Route}>
          <Button type="button">{t('create')}</Button>
        </Link>
      </header>

      {listQuery.isLoading ? (
        <LoadingState label={t('loading')} />
      ) : listQuery.isError ? (
        <ErrorState title={t('loadFailed')} message={listQuery.error instanceof ApiError ? listQuery.error.message : t('loadFailed')} />
      ) : listQuery.data?.total === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <ul className="marketing-templates__list">
          {listQuery.data?.items.map((template) => (
            <li key={template.id}>
              <Link href={`/workspaces/marketing/templates/${template.id}` as Route}>{template.name}</Link>
              <span>{template.template_type}</span>
              <span>{template.status}</span>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
