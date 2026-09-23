'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { crmQueries } from '@/lib/query/crm-queries';

export function CrmContactsList() {
  const t = useTranslations('crm');
  const tCommon = useTranslations('common');
  const { authLoading, canRead: canView } = useCrmAccess();

  const contactsQuery = useQuery({
    ...crmQueries.contacts({ page: 1, pageSize: 25 }),
    enabled: !authLoading && canView,
  });

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canView) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
  }

  if (contactsQuery.isLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (contactsQuery.isError) {
    return (
      <ErrorState
        title={t('loadFailed')}
        message={contactsQuery.error?.message ?? t('loadFailed')}
        action={
          <Button type="button" onClick={() => void contactsQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  const data = contactsQuery.data;
  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        title={t('emptyContacts')}
        description={t('emptyContactsHint')}
      />
    );
  }

  return (
    <>
      <p className="crm-dashboard__list-item-meta">
        {t('contactsSummary', { total: data.total, page: data.page, pages: data.pages })}
      </p>
      <table className="crm-contacts-table">
        <thead>
          <tr>
            <th>{t('fields.displayName')}</th>
            <th>{t('fields.contactType')}</th>
            <th>{t('fields.email')}</th>
            <th>{t('fields.phone')}</th>
            <th>{t('fields.status')}</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((contact) => (
            <tr key={contact.id}>
              <td>{contact.display_name}</td>
              <td>{t(`contactTypes.${contact.contact_type}` as 'contactTypes.prospect')}</td>
              <td>{contact.primary_email ?? '—'}</td>
              <td>{contact.primary_phone ?? '—'}</td>
              <td>{t(`statuses.${contact.status}` as 'statuses.active')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
