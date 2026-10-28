'use client';

import { FormEvent, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { Button, TextArea } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { sendCustomerWhatsapp } from '@/workspaces/crm/api/communication';
import { communicationQueryKeys } from '@/workspaces/crm/hooks/use-communication';

function errorText(error: unknown, t: (key: string) => string): string {
  const code = error instanceof ApiError ? error.message : '';
  if (code === 'whatsapp_template_required') return t('whatsappTemplateRequired');
  if (code === 'whatsapp_not_configured') return t('whatsappNotConfigured');
  if (code === 'whatsapp_phone_missing') return t('whatsappPhoneMissing');
  if (code === 'whatsapp_phone_invalid') return t('whatsappPhoneInvalid');
  if (code === 'whatsapp_phone_ambiguous') return t('whatsappPhoneAmbiguous');
  if (code === 'recipient_not_allowed') return t('whatsappRecipientRejected');
  if (code === 'crm_persist_failed') return t('whatsappStoredFailed');
  return t('sendFailed');
}

export function WhatsAppSendComposer({
  mode,
  contactId,
  leadId,
  communicationId,
  activityId,
  phones = [],
  onSent,
}: {
  mode: 'reply' | 'new';
  contactId?: string | null;
  leadId?: string | null;
  communicationId?: string | null;
  activityId?: string | null;
  phones?: string[];
  onSent?: () => void;
}) {
  const t = useTranslations('crm.communication.workspace');
  const queryClient = useQueryClient();
  const [phone, setPhone] = useState(phones.length === 1 ? phones[0] : '');
  const [body, setBody] = useState('');
  const [error, setError] = useState('');
  const needsPhone = mode === 'new' && phones.length > 1;
  const sendMutation = useMutation({
    mutationFn: () =>
      sendCustomerWhatsapp({
        contact_id: contactId,
        lead_id: leadId,
        communication_id: mode === 'reply' ? communicationId : null,
        activity_id: mode === 'reply' ? activityId : null,
        to: mode === 'new' && phone.trim() ? phone.trim() : null,
        body_text: body.trim(),
      }),
    onSuccess: async () => {
      setBody('');
      setError('');
      await queryClient.invalidateQueries({ queryKey: communicationQueryKeys.all });
      const personId = contactId;
      if (personId) {
        await queryClient.invalidateQueries({ queryKey: ['crm', 'contacts', 'timeline', personId] });
      }
      onSent?.();
    },
    onError: (sendError) => {
      setError(errorText(sendError, t));
    },
  });
  const canSubmit = Boolean(body.trim() && !sendMutation.isPending && (!needsPhone || phone.trim()));

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!canSubmit) return;
    setError('');
    sendMutation.mutate();
  };

  return (
    <form className="crm-email-compose" onSubmit={onSubmit} data-testid="crm-whatsapp-compose">
      {needsPhone ? (
        <label className="crm-email-compose__from">
          {t('whatsappPhone')}
          <select value={phone} onChange={(event) => setPhone(event.target.value)} required>
            <option value="">{t('whatsappPhoneAmbiguous')}</option>
            {phones.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <TextArea
        label={t('emailBody')}
        value={body}
        onChange={(event) => setBody(event.target.value)}
        rows={4}
        required
      />
      {error ? (
        <p className="crm-email-compose__error" role="alert" data-testid="crm-whatsapp-compose-error">
          {error}
        </p>
      ) : null}
      <div className="crm-email-compose__actions">
        <Button
          type="submit"
          size="sm"
          loading={sendMutation.isPending}
          disabled={!canSubmit}
          data-testid="crm-whatsapp-compose-send"
        >
          {sendMutation.isPending ? t('sending') : t('whatsappSend')}
        </Button>
      </div>
    </form>
  );
}
