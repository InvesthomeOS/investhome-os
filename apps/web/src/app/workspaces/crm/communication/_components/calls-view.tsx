'use client';

import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { Button, EmptyState, ErrorState, Input, LoadingState, Select, TextArea } from '@investhome/ui';

import { canCreateCommunications } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { createCommunication } from '@/workspaces/crm/api/communication';
import { communicationQueries, communicationQueryKeys } from '@/workspaces/crm/hooks/use-communication';
import { callLogSchema, type CallLogFormValues } from '@/workspaces/crm/schemas/communication';

export function CallsView() {
  const t = useTranslations('crm.communication.calls');
  const tCommon = useTranslations('common');
  const { authLoading, user, canViewCommunications } = useCrmAccess();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);

  const callsQuery = useQuery({
    ...communicationQueries.calls({ page, page_size: 25 }),
    enabled: !authLoading && canViewCommunications,
  });

  const form = useForm<CallLogFormValues>({
    resolver: zodResolver(callLogSchema) as never,
    defaultValues: {
      subject: '',
      recipient_entity_type: 'contact',
      recipient_entity_id: '',
      call_direction: 'outbound',
    },
  });

  const createMutation = useMutation({
    mutationFn: (values: CallLogFormValues) =>
      createCommunication({
        channel: 'phone',
        direction: values.call_direction,
        status: 'sent',
        subject: values.subject,
        body: values.body,
        recipient_entity_type: values.recipient_entity_type,
        recipient_entity_id: values.recipient_entity_id,
        call_duration_seconds: values.call_duration_seconds,
        call_outcome: values.call_outcome,
        call_direction: values.call_direction,
      }),
    onSuccess: () => {
      form.reset();
      void queryClient.invalidateQueries({ queryKey: communicationQueryKeys.all });
    },
  });

  const columns = useMemo(
    () => [
      { key: 'subject', header: t('columns.subject') },
      { key: 'status', header: t('columns.status') },
      { key: 'created_at', header: t('columns.date') },
    ],
    [t],
  );

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canViewCommunications) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
  }

  return (
    <div className="crm-communication-subview">
      <header className="crm-communication-subview__header">
        <div>
          <h2>{t('title')}</h2>
          <p>{t('subtitle')}</p>
        </div>
        <p className="crm-communication__provider-note">{t('clickToCallNote')}</p>
      </header>

      {canCreateCommunications(user) && (
        <form
          className="crm-communication-subview__form"
          onSubmit={form.handleSubmit((v) => createMutation.mutate(v))}
        >
          <h3>{t('logCall')}</h3>
          <div className="crm-form-row">
            <label className="crm-form-field">
              <span>{t('fields.subject')}</span>
              <Input {...form.register('subject')} />
            </label>
            <label className="crm-form-field">
              <span>{t('fields.contactId')}</span>
              <Input {...form.register('recipient_entity_id')} placeholder="UUID" />
            </label>
          </div>
          <div className="crm-form-row">
            <label className="crm-form-field">
              <span>{t('fields.direction')}</span>
              <Select {...form.register('call_direction')}>
                <option value="outbound">{t('direction.outbound')}</option>
                <option value="inbound">{t('direction.inbound')}</option>
              </Select>
            </label>
            <label className="crm-form-field">
              <span>{t('fields.duration')}</span>
              <Input type="number" {...form.register('call_duration_seconds', { valueAsNumber: true })} />
            </label>
          </div>
          <label className="crm-form-field">
            <span>{t('fields.outcome')}</span>
            <Select {...form.register('call_outcome')}>
              <option value="">{t('fields.selectOutcome')}</option>
              <option value="connected">{t('outcomes.connected')}</option>
              <option value="no_answer">{t('outcomes.noAnswer')}</option>
              <option value="voicemail">{t('outcomes.voicemail')}</option>
              <option value="busy">{t('outcomes.busy')}</option>
            </Select>
          </label>
          <label className="crm-form-field">
            <span>{t('fields.notes')}</span>
            <TextArea rows={3} {...form.register('body')} />
          </label>
          <Button type="submit" disabled={createMutation.isPending}>
            {t('saveCallLog')}
          </Button>
        </form>
      )}

      <section className="crm-communication-subview__list">
        <h3>{t('callHistory')}</h3>
        {callsQuery.isLoading && <LoadingState label={t('loading')} />}
        {callsQuery.data?.items.length === 0 && (
          <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
        )}
        {callsQuery.data && callsQuery.data.items.length > 0 && (
          <table className="crm-contacts-table">
            <thead>
              <tr>
                {columns.map((c) => (
                  <th key={c.key}>{c.header}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {callsQuery.data.items.map((row) => (
                <tr key={row.id}>
                  <td>{row.subject ?? '—'}</td>
                  <td>{row.status}</td>
                  <td>{new Date(row.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {callsQuery.data && callsQuery.data.pages > 1 && (
          <div className="crm-communication-subview__pagination">
            <Button type="button" variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              ←
            </Button>
            <span>{page} / {callsQuery.data.pages}</span>
            <Button
              type="button"
              variant="secondary"
              disabled={page >= callsQuery.data.pages}
              onClick={() => setPage((p) => p + 1)}
            >
              →
            </Button>
          </div>
        )}
      </section>
    </div>
  );
}
