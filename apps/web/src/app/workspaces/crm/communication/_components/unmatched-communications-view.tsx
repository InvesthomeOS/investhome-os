'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { Button, EmptyState, ErrorState, Input, LoadingState, Select } from '@investhome/ui';

import { canUpdateCrm } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { fetchAgreements } from '@/workspaces/crm/api/agreements';
import {
  confirmUnmatchedCommunication,
  ignoreUnmatchedCommunication,
  type UnmatchedCommunication,
} from '@/workspaces/crm/api/communication';
import { fetchContacts } from '@/workspaces/crm/api/contacts';
import { communicationQueries, communicationQueryKeys } from '@/workspaces/crm/hooks/use-communication';

function formatWhen(value: string | null) {
  if (!value) return '—';
  return new Date(value).toLocaleString('tr-TR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function channelLabel(channel: string, t: (key: string) => string) {
  if (channel === 'whatsapp') return t('channels.whatsapp');
  if (channel === 'email') return t('channels.email');
  if (channel === 'phone' || channel === 'call') return t('channels.call');
  return channel;
}

function MatchRow({ item }: { item: UnmatchedCommunication }) {
  const t = useTranslations('crm.communication.unmatched');
  const { user } = useCrmAccess();
  const queryClient = useQueryClient();
  const canMatch = canUpdateCrm(user) || Boolean(user);
  const [contactId, setContactId] = useState(item.suggested_matches[0]?.contact_id ?? '');
  const [agreementId, setAgreementId] = useState('');
  const [search, setSearch] = useState('');

  const contactsQuery = useQuery({
    queryKey: ['crm', 'contacts', 'unmatched-search', search],
    queryFn: () => fetchContacts({ search, page_size: 8 }),
    enabled: search.trim().length >= 2,
  });

  const agreementsQuery = useQuery({
    queryKey: ['crm', 'agreements', 'unmatched', contactId],
    queryFn: () => fetchAgreements({ contact_id: contactId, page_size: 20 }),
    enabled: Boolean(contactId),
  });

  const matchMutation = useMutation({
    mutationFn: () =>
      confirmUnmatchedCommunication(item.id, {
        contact_id: contactId,
        agreement_id: agreementId || null,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: communicationQueryKeys.all });
    },
  });

  const ignoreMutation = useMutation({
    mutationFn: () => ignoreUnmatchedCommunication(item.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: communicationQueryKeys.all });
    },
  });

  const searchHits = contactsQuery.data?.items ?? [];
  const purchases = agreementsQuery.data?.items ?? [];

  return (
    <article className="crm-live-comm__card" data-testid="unmatched-communication-row">
      <header className="crm-live-comm__card-head">
        <strong>{item.sender || t('unknownSender')}</strong>
        <span>{channelLabel(item.channel, t)}</span>
        <time>{formatWhen(item.occurred_at)}</time>
      </header>
      <p className="crm-live-comm__subject">{item.subject || t('noSubject')}</p>
      {item.preview ? <p className="crm-live-comm__preview">{item.preview}</p> : null}
      <p className="crm-live-comm__meta">
        {t('matchStatus')}: {t(`status.${item.match_status}`)}
      </p>

      {item.suggested_matches.length > 0 ? (
        <div className="crm-live-comm__suggestions">
          <span>{t('suggestions')}</span>
          {item.suggested_matches.map((suggestion) => (
            <button
              key={suggestion.contact_id}
              type="button"
              className={
                contactId === suggestion.contact_id
                  ? 'crm-live-comm__chip crm-live-comm__chip--active'
                  : 'crm-live-comm__chip'
              }
              onClick={() => setContactId(suggestion.contact_id)}
            >
              {suggestion.display_name}
            </button>
          ))}
        </div>
      ) : (
        <p className="crm-live-comm__hint">{t('noSuggestions')}</p>
      )}

      {canMatch ? (
        <form
          className="crm-live-comm__match-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (!contactId) return;
            matchMutation.mutate();
          }}
        >
          <label className="crm-form-field">
            <span>{t('searchPerson')}</span>
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={t('searchPlaceholder')}
            />
          </label>
          {searchHits.length > 0 ? (
            <Select value={contactId} onChange={(event) => setContactId(event.target.value)}>
              <option value="">{t('selectPerson')}</option>
              {searchHits.map((contact) => (
                <option key={contact.id} value={contact.id}>
                  {contact.display_name}
                </option>
              ))}
            </Select>
          ) : null}
          {purchases.length > 0 ? (
            <label className="crm-form-field">
              <span>{t('purchase')}</span>
              <Select value={agreementId} onChange={(event) => setAgreementId(event.target.value)}>
                <option value="">{t('noPurchase')}</option>
                {purchases.map((agreement) => (
                  <option key={agreement.id} value={agreement.id}>
                    {agreement.project_group_label || agreement.unit_number || agreement.id}
                  </option>
                ))}
              </Select>
            </label>
          ) : null}
          <div className="crm-live-comm__actions">
            <Button type="submit" disabled={!contactId || matchMutation.isPending}>
              {t('confirm')}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => ignoreMutation.mutate()}
              disabled={ignoreMutation.isPending}
            >
              {t('ignore')}
            </Button>
          </div>
          {matchMutation.isError ? <p className="crm-live-comm__error">{t('matchFailed')}</p> : null}
        </form>
      ) : null}
    </article>
  );
}

export function UnmatchedCommunicationsView() {
  const t = useTranslations('crm.communication.unmatched');
  const tCommon = useTranslations('common');
  const { authLoading, canViewCommunications } = useCrmAccess();
  const [page, setPage] = useState(1);

  const query = useQuery({
    ...communicationQueries.unmatched({ page }),
    enabled: !authLoading && canViewCommunications,
  });

  const pages = useMemo(() => {
    const total = query.data?.total ?? 0;
    const size = query.data?.page_size ?? 30;
    return Math.max(1, Math.ceil(total / size));
  }, [query.data]);

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canViewCommunications) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
  }

  const items = query.data?.items ?? [];

  return (
    <div className="crm-communication-subview" data-testid="crm-unmatched-communications">
      <header className="crm-communication-subview__header">
        <h2>{t('title')}</h2>
        <p>{t('subtitle')}</p>
      </header>

      {query.isLoading ? (
        <LoadingState label={t('loading')} />
      ) : items.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <div className="crm-live-comm__stack">
          {items.map((item) => (
            <MatchRow key={item.id} item={item} />
          ))}
        </div>
      )}

      {pages > 1 ? (
        <div className="crm-communication-subview__pagination">
          <Button type="button" variant="secondary" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>
            {t('previous')}
          </Button>
          <span>
            {page} / {pages}
          </span>
          <Button
            type="button"
            variant="secondary"
            disabled={page >= pages}
            onClick={() => setPage((value) => value + 1)}
          >
            {t('next')}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
