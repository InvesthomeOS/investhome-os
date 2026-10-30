'use client';

import { useLocale } from 'next-intl';

import { EmptyState } from '@investhome/ui';

import { CrmModuleShell } from '../../_components/crm-module-shell';

export function SearchUnavailable() {
  const tr = !useLocale().startsWith('en');
  return (
    <CrmModuleShell titleKey="modules.search.title" descriptionKey="modules.search.description">
      <div data-testid="crm-search-unavailable">
        <EmptyState
          title={tr ? 'Arama burada yok' : 'Search is not available here'}
          description={
            tr
              ? 'Gelişmiş arama ve kayıtlı arama bu ekranda yok. Kayıt aramak için Ctrl+K veya Cmd+K kullanın.'
              : 'Advanced search and saved search are not available on this screen. Use Ctrl+K or Cmd+K to search records.'
          }
        />
      </div>
    </CrmModuleShell>
  );
}
