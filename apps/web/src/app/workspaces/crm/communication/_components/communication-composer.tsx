'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { Alert, Button, Dialog, Input, Select, TextArea } from '@investhome/ui';

import { createCommunication } from '@/workspaces/crm/api/communication';
import { communicationQueryKeys } from '@/workspaces/crm/hooks/use-communication';
import {
  communicationComposeDefaults,
  communicationComposeSchema,
  type CommunicationComposeValues,
} from '@/workspaces/crm/schemas/communication';
import { CRM_COMM_CHANNELS, type CrmCommChannel } from '@/workspaces/crm/types';

type CommunicationComposerProps = {
  open: boolean;
  onClose: () => void;
  defaultRecipientEntityId?: string;
};

export function CommunicationComposer({ open, onClose, defaultRecipientEntityId }: CommunicationComposerProps) {
  const t = useTranslations('crm.communication');
  const tChannels = useTranslations('crm.communication.channels');
  const queryClient = useQueryClient();

  const form = useForm<CommunicationComposeValues>({
    resolver: zodResolver(communicationComposeSchema) as never,
    defaultValues: {
      ...communicationComposeDefaults,
      recipient_entity_type: defaultRecipientEntityId ? 'contact' : undefined,
      recipient_entity_id: defaultRecipientEntityId ?? '',
    },
  });

  useEffect(() => {
    if (open) {
      form.reset({
        ...communicationComposeDefaults,
        recipient_entity_id: defaultRecipientEntityId ?? '',
        recipient_entity_type: defaultRecipientEntityId ? 'contact' : undefined,
      });
    }
  }, [open, defaultRecipientEntityId, form]);

  const mutation = useMutation({
    mutationFn: (values: CommunicationComposeValues) =>
      createCommunication({
        channel: values.channel as CrmCommChannel,
        subject: values.subject || undefined,
        body: values.body,
        body_html: values.body_html,
        status: values.scheduled_at ? 'scheduled' : 'draft',
        scheduled_at: values.scheduled_at,
        visibility: values.visibility,
        priority: values.priority,
        recipient_entity_type: values.recipient_entity_type,
        recipient_entity_id: values.recipient_entity_id || undefined,
      }),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: communicationQueryKeys.all });
      if (result.warnings?.length) {
        form.setError('root', { message: result.warnings.join(', ') });
        return;
      }
      onClose();
    },
  });

  const onSubmit = form.handleSubmit((values) => mutation.mutate(values));

  return (
    <Dialog open={open} onClose={onClose} title={t('compose')}>
      <form className="crm-communication__composer" onSubmit={onSubmit}>
        {form.formState.errors.root && (
          <Alert tone="warning">{form.formState.errors.root.message}</Alert>
        )}
        <label className="crm-form-field">
          <span>{t('fields.channel')}</span>
          <Select {...form.register('channel')}>
            {CRM_COMM_CHANNELS.map((ch) => (
              <option key={ch} value={ch}>
                {tChannels(ch)}
              </option>
            ))}
          </Select>
        </label>
        <label className="crm-form-field">
          <span>{t('fields.subject')}</span>
          <Input {...form.register('subject')} />
        </label>
        <label className="crm-form-field">
          <span>{t('fields.recipientEntityId')}</span>
          <Input {...form.register('recipient_entity_id')} placeholder="UUID" />
        </label>
        <label className="crm-form-field">
          <span>{t('fields.body')}</span>
          <TextArea rows={8} {...form.register('body')} />
          {form.formState.errors.body && (
            <span className="crm-form-error">{form.formState.errors.body.message}</span>
          )}
        </label>
        <label className="crm-form-field">
          <span>{t('fields.scheduleAt')}</span>
          <Input type="datetime-local" {...form.register('scheduled_at')} />
        </label>
        <p className="crm-communication__composer-note">{t('composerDraftNote')}</p>
        <div className="crm-modal__footer">
          <Button type="button" variant="secondary" onClick={onClose}>
            {t('cancel')}
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? t('saving') : t('saveDraft')}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
