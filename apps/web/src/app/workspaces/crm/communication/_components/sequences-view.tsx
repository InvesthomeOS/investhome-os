'use client';

import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { Alert, Button, EmptyState, ErrorState, Input, LoadingState, TextArea } from '@investhome/ui';

import { hasCrmPermission } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { createSequence } from '@/workspaces/crm/api/communication';
import { communicationQueries, communicationQueryKeys } from '@/workspaces/crm/hooks/use-communication';

export function SequencesView() {
  const t = useTranslations('crm.communication.sequences');
  const tCommon = useTranslations('common');
  const { authLoading, user, canViewCommunications } = useCrmAccess();
  const queryClient = useQueryClient();
  const canManage = hasCrmPermission(user, 'manage_sequences');

  const sequencesQuery = useQuery({
    ...communicationQueries.sequences(),
    enabled: !authLoading && canViewCommunications,
  });

  const form = useForm<{ name: string; description: string }>({
    defaultValues: { name: '', description: '' },
  });

  const createMutation = useMutation({
    mutationFn: (values: { name: string; description: string }) =>
      createSequence({
        name: values.name,
        description: values.description,
        enrollment_type: 'manual',
        steps: [
          { step_order: 0, step_type: 'send_email', wait_days: 0 },
          { step_order: 1, step_type: 'wait', wait_days: 3 },
          { step_order: 2, step_type: 'create_follow_up' },
        ],
      }),
    onSuccess: () => {
      form.reset();
      void queryClient.invalidateQueries({ queryKey: communicationQueryKeys.all });
    },
  });

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canViewCommunications) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
  }

  return (
    <div className="crm-communication-subview">
      <header className="crm-communication-subview__header">
        <h2>{t('title')}</h2>
        <p>{t('subtitle')}</p>
      </header>

      <Alert tone="info">{t('architectureNote')}</Alert>

      {canManage && (
        <form className="crm-communication-subview__form" onSubmit={form.handleSubmit((v) => createMutation.mutate(v))}>
          <h3>{t('createSequence')}</h3>
          <label className="crm-form-field">
            <span>{t('fields.name')}</span>
            <Input {...form.register('name', { required: true })} />
          </label>
          <label className="crm-form-field">
            <span>{t('fields.description')}</span>
            <TextArea rows={3} {...form.register('description')} />
          </label>
          <Button type="submit" disabled={createMutation.isPending}>{t('save')}</Button>
        </form>
      )}

      {sequencesQuery.isLoading && <LoadingState label={t('loading')} />}
      {sequencesQuery.data?.items.length === 0 && (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      )}
      {sequencesQuery.data && sequencesQuery.data.items.length > 0 && (
        <ul className="crm-communication-subview__cards">
          {sequencesQuery.data.items.map((seq) => (
            <li key={seq.id} className="crm-communication-subview__card">
              <strong>{seq.name}</strong>
              <span>{t('stepCount', { count: seq.step_count })}</span>
              <span>{seq.is_active ? t('active') : t('inactive')}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
