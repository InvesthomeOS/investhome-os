'use client';

import { FormEvent, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { Button, Input, TextArea } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { fetchEmailReplyContext, sendCustomerEmail } from '@/workspaces/crm/api/communication';
import { communicationQueryKeys } from '@/workspaces/crm/hooks/use-communication';

type EmailSendMode = 'reply' | 'reply_all' | 'new';

function splitAddresses(value: string): string[] {
  return value
    .split(/[,;]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function errorText(error: unknown, t: (key: string) => string): string {
  const code = error instanceof ApiError ? error.message : '';
  if (code === 'gmail_reconnect_required') return t('gmailReconnect');
  if (code === 'gmail_account_missing') return t('gmailAccountMissing');
  if (code === 'crm_persist_failed') return t('gmailStoredFailed');
  if (code === 'contact_email_missing') return t('contactEmailMissing');
  if (code === 'recipient_not_allowed') return t('emailRecipientRejected');
  return t('sendFailed');
}

export function EmailSendComposer({
  mode,
  contactId,
  leadId,
  communicationId,
  activityId,
  defaultTo = '',
  defaultCc = '',
  defaultSubject = '',
  onSent,
}: {
  mode: EmailSendMode;
  contactId?: string | null;
  leadId?: string | null;
  communicationId?: string | null;
  activityId?: string | null;
  defaultTo?: string;
  defaultCc?: string;
  defaultSubject?: string;
  onSent?: () => void;
}) {
  const t = useTranslations('crm.communication.workspace');
  const queryClient = useQueryClient();
  const reply = mode !== 'new';
  const contextQuery = useQuery({
    queryKey: ['crm', 'communications', 'email-reply', communicationId || '', activityId || ''],
    queryFn: () =>
      fetchEmailReplyContext({
        communication_id: communicationId,
        activity_id: activityId,
      }),
    enabled: reply && Boolean(communicationId || activityId),
  });
  const context = contextQuery.data;
  const [to, setTo] = useState(defaultTo);
  const [cc, setCc] = useState(mode === 'reply_all' ? defaultCc : '');
  const [subject, setSubject] = useState(defaultSubject);
  const [body, setBody] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!context) return;
    setTo(context.to.join(', '));
    setCc(mode === 'reply_all' ? context.cc.join(', ') : '');
    setSubject(context.subject || defaultSubject);
    if (context.send_block === 'gmail_reconnect_required') setError(t('gmailReconnect'));
    else if (context.send_block === 'gmail_account_missing') setError(t('gmailAccountMissing'));
    else setError('');
  }, [context, defaultSubject, mode, t]);

  const sendMutation = useMutation({
    mutationFn: () =>
      sendCustomerEmail({
        mode,
        contact_id: contactId || context?.contact_id,
        lead_id: leadId,
        communication_id: communicationId,
        activity_id: activityId,
        to: splitAddresses(to),
        cc: mode === 'reply_all' ? splitAddresses(cc) : [],
        subject: subject.trim(),
        body_text: body.trim(),
      }),
    onSuccess: async () => {
      setBody('');
      setError('');
      await queryClient.invalidateQueries({ queryKey: communicationQueryKeys.all });
      if (contactId || context?.contact_id) {
        await queryClient.invalidateQueries({
          queryKey: ['crm', 'contacts', 'timeline', contactId || context?.contact_id],
        });
      }
      onSent?.();
    },
    onError: (sendError) => {
      setError(errorText(sendError, t));
    },
  });

  const blocked = Boolean(context?.send_block);
  const canSubmit = Boolean(subject.trim() && body.trim() && !sendMutation.isPending && !blocked);

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!canSubmit) return;
    setError('');
    sendMutation.mutate();
  };

  return (
    <form className="crm-email-compose" onSubmit={onSubmit} data-testid="crm-email-compose">
      {context?.from_mailbox ? (
        <p className="crm-email-compose__from">
          {t('emailFrom')}: {context.from_mailbox}
        </p>
      ) : null}
      <Input label={t('emailTo')} value={to} onChange={(event) => setTo(event.target.value)} />
      {mode === 'reply_all' ? (
        <Input label={t('emailCc')} value={cc} onChange={(event) => setCc(event.target.value)} />
      ) : null}
      <Input label={t('emailSubject')} value={subject} onChange={(event) => setSubject(event.target.value)} required />
      <TextArea
        label={t('emailBody')}
        value={body}
        onChange={(event) => setBody(event.target.value)}
        rows={6}
        required
      />
      {contextQuery.isError ? <p className="crm-email-compose__error">{t('emailReplyUnavailable')}</p> : null}
      {error ? (
        <p className="crm-email-compose__error" role="alert" data-testid="crm-email-compose-error">
          {error}
        </p>
      ) : null}
      <div className="crm-email-compose__actions">
        <Button type="submit" size="sm" loading={sendMutation.isPending} disabled={!canSubmit} data-testid="crm-email-compose-send">
          {sendMutation.isPending ? t('emailSending') : t('emailSend')}
        </Button>
      </div>
    </form>
  );
}
