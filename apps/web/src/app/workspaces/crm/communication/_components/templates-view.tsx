'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { Button, EmptyState, ErrorState, Input, LoadingState, Select, TextArea } from '@investhome/ui';

import { canManageTemplates } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { createTemplate } from '@/workspaces/crm/api/communication';
import { communicationQueries, communicationQueryKeys } from '@/workspaces/crm/hooks/use-communication';
import { templateFormSchema, type TemplateFormValues } from '@/workspaces/crm/schemas/communication';

export function TemplatesView() {
  const t = useTranslations('crm.communication.templates');
  const tCommon = useTranslations('common');
  const { authLoading, user, canViewCommunications } = useCrmAccess();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');

  const templatesQuery = useQuery({
    ...communicationQueries.templates({ search }),
    enabled: !authLoading && canViewCommunications,
  });

  const form = useForm<TemplateFormValues>({
    resolver: zodResolver(templateFormSchema) as never,
    defaultValues: { name: '', template_type: 'email', body: '', is_shared: false },
  });

  const createMutation = useMutation({
    mutationFn: createTemplate,
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

      <Input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder={t('searchPlaceholder')}
        aria-label={t('searchPlaceholder')}
      />

      {canManageTemplates(user) && (
        <form className="crm-communication-subview__form" onSubmit={form.handleSubmit((v) => createMutation.mutate(v))}>
          <h3>{t('createTemplate')}</h3>
          <label className="crm-form-field">
            <span>{t('fields.name')}</span>
            <Input {...form.register('name')} />
          </label>
          <label className="crm-form-field">
            <span>{t('fields.type')}</span>
            <Select {...form.register('template_type')}>
              <option value="email">{t('types.email')}</option>
              <option value="whatsapp">{t('types.whatsapp')}</option>
              <option value="sms">{t('types.sms')}</option>
              <option value="call_script">{t('types.callScript')}</option>
              <option value="meeting_agenda">{t('types.meetingAgenda')}</option>
              <option value="internal">{t('types.internal')}</option>
              <option value="follow_up">{t('types.followUp')}</option>
            </Select>
          </label>
          <label className="crm-form-field">
            <span>{t('fields.subject')}</span>
            <Input {...form.register('subject')} />
          </label>
          <label className="crm-form-field">
            <span>{t('fields.body')}</span>
            <TextArea rows={6} {...form.register('body')} />
          </label>
          <p className="crm-communication__composer-note">{t('variablesHint')}</p>
          <Button type="submit" disabled={createMutation.isPending}>{t('save')}</Button>
        </form>
      )}

      {templatesQuery.isLoading && <LoadingState label={t('loading')} />}
      {templatesQuery.data?.items.length === 0 && (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      )}
      {templatesQuery.data && templatesQuery.data.items.length > 0 && (
        <ul className="crm-communication-subview__cards">
          {templatesQuery.data.items.map((tpl) => (
            <li key={tpl.id} className="crm-communication-subview__card">
              <strong>{tpl.name}</strong>
              <span>{tpl.template_type}</span>
              {tpl.subject && <p>{tpl.subject}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
