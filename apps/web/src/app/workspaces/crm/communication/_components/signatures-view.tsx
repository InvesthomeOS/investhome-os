'use client';

import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { Button, EmptyState, ErrorState, Input, LoadingState, TextArea } from '@investhome/ui';

import { hasCrmPermission } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { createSignature } from '@/workspaces/crm/api/communication';
import { communicationQueries, communicationQueryKeys } from '@/workspaces/crm/hooks/use-communication';

export function SignaturesView() {
  const t = useTranslations('crm.communication.signatures');
  const tCommon = useTranslations('common');
  const { authLoading, user, canViewCommunications } = useCrmAccess();
  const queryClient = useQueryClient();
  const canManage = hasCrmPermission(user, 'manage_signatures');

  const signaturesQuery = useQuery({
    ...communicationQueries.signatures(),
    enabled: !authLoading && canViewCommunications,
  });

  const form = useForm<{ name: string; body_html: string }>({
    defaultValues: { name: '', body_html: '' },
  });

  const createMutation = useMutation({
    mutationFn: createSignature,
    onSuccess: () => {
      form.reset();
      void queryClient.invalidateQueries({ queryKey: communicationQueryKeys.signatures });
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

      {canManage && (
        <form className="crm-communication-subview__form" onSubmit={form.handleSubmit((v) => createMutation.mutate({ ...v, scope: 'personal' }))}>
          <h3>{t('createSignature')}</h3>
          <label className="crm-form-field">
            <span>{t('fields.name')}</span>
            <Input {...form.register('name', { required: true })} />
          </label>
          <label className="crm-form-field">
            <span>{t('fields.body')}</span>
            <TextArea rows={5} {...form.register('body_html', { required: true })} />
          </label>
          <Button type="submit" disabled={createMutation.isPending}>{t('save')}</Button>
        </form>
      )}

      {signaturesQuery.isLoading && <LoadingState label={t('loading')} />}
      {signaturesQuery.data?.items.length === 0 && (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      )}
      {signaturesQuery.data && signaturesQuery.data.items.length > 0 && (
        <ul className="crm-communication-subview__cards">
          {signaturesQuery.data.items.map((sig) => (
            <li key={sig.id} className="crm-communication-subview__card">
              <strong>{sig.name}</strong>
              <span>{sig.scope}</span>
              {sig.is_default && <span>{t('default')}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
