'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { useQuery } from '@tanstack/react-query';

import { canReadCompany } from '@/lib/company/company-permissions';
import { companyQueries } from '@/lib/query/company-queries';
import { useAuth } from '@/lib/auth/auth-context';

function resolveSearchHref(entityType: string, entityId: string): string {
  switch (entityType) {
    case 'managed_company':
    case 'company':
      return `/company/companies/${entityId}`;
    case 'branch':
      return `/company/branches/${entityId}`;
    case 'company_department':
    case 'department':
      return `/company/departments`;
    case 'team':
      return `/company/teams`;
    case 'user':
      return `/company/employees`;
    case 'document':
      return `/dashboard/documents?id=${entityId}`;
    case 'project':
      return `/dashboard/projects?id=${entityId}`;
    case 'office':
      return `/dashboard/settings?tab=offices`;
    default:
      return '/company';
  }
}

export function CompanySearchTrigger() {
  const t = useTranslations('company');
  const { user } = useAuth();
  const canSearch = canReadCompany(user);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');

  const searchQuery = useQuery({
    ...companyQueries.search(query),
    enabled: open && query.trim().length > 1,
  });

  const entityLabels = useMemo(
    () =>
      ({
        managed_company: t('search.entities.company'),
        company: t('search.entities.companyProfile'),
        branch: t('search.entities.branch'),
        company_department: t('search.entities.department'),
        department: t('search.entities.organization'),
        team: t('search.entities.team'),
        user: t('search.entities.employee'),
        document: t('search.entities.document'),
        project: t('search.entities.project'),
        office: t('search.entities.office'),
      }) as Record<string, string>,
    [t],
  );

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        if (canSearch) {
          setOpen(true);
        }
      }
      if (event.key === 'Escape') {
        setOpen(false);
      }
    },
    [canSearch],
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  if (!canSearch) {
    return null;
  }

  const isMac = typeof navigator !== 'undefined' && navigator.platform.toLowerCase().includes('mac');
  const shortcut = isMac ? '⌘K' : 'Ctrl+K';

  return (
    <>
      <button type="button" className="global-search-trigger" onClick={() => setOpen(true)}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.5" />
          <path d="M20 20 16.5 16.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        <span className="global-search-trigger__label">{t('search.placeholder')}</span>
        <kbd className="global-search-trigger__kbd">{shortcut}</kbd>
      </button>

      {open && (
        <div className="global-search-overlay" role="presentation" onClick={() => setOpen(false)}>
          <div
            className="global-search-palette company-search-palette"
            role="dialog"
            aria-label={t('search.title')}
            onClick={(event) => event.stopPropagation()}
          >
            <input
              className="global-search-palette__input"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t('search.placeholder')}
              autoFocus
            />
            <div className="global-search-palette__results">
              {query.trim().length <= 1 ? (
                <p className="global-search-palette__hint">{t('search.hint')}</p>
              ) : searchQuery.isLoading ? (
                <p className="global-search-palette__hint">{t('search.loading')}</p>
              ) : searchQuery.isError ? (
                <p className="global-search-palette__hint">{t('search.error')}</p>
              ) : searchQuery.data && searchQuery.data.total === 0 ? (
                <p className="global-search-palette__hint">{t('search.empty')}</p>
              ) : (
                searchQuery.data?.groups.map((group) => (
                  <section key={group.entity_type} className="global-search-palette__group">
                    <h3 className="global-search-palette__group-title">
                      {entityLabels[group.entity_type] ?? group.entity_type}
                    </h3>
                    <ul className="global-search-palette__list">
                      {group.items.map((item) => (
                        <li key={item.entity_id} className="global-search-palette__item">
                          <Link
                            href={resolveSearchHref(group.entity_type, item.entity_id) as Route}
                            className="global-search-palette__item-link"
                            onClick={() => setOpen(false)}
                          >
                            <span className="global-search-palette__item-title">{item.title}</span>
                            {item.subtitle ? (
                              <span className="global-search-palette__item-subtitle">{item.subtitle}</span>
                            ) : null}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </section>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
