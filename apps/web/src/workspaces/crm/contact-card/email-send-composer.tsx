'use client';

import { FormEvent, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { Button, Input, TextArea } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { parseRecipientField, partitionRecipients } from '@/lib/crm/email-recipients';
import { fetchEmailReplyContext, sendCustomerEmail } from '@/workspaces/crm/api/communication';
import { communicationQueryKeys } from '@/workspaces/crm/hooks/use-communication';

type EmailSendMode = 'reply' | 'reply_all' | 'new';

function errorText(error: unknown, t: (key: string) => string): string {
  const code = error instanceof ApiError ? error.message : '';
  if (code === 'gmail_reconnect_required') return t('gmailReconnect');
  if (code === 'gmail_account_missing') return t('gmailAccountMissing');
  if (code === 'gmail_account_not_owned') return t('gmailAccountNotOwned');
  if (code === 'crm_persist_failed') return t('gmailStoredFailed');
  if (code === 'contact_email_missing') return t('contactEmailMissing');
  if (code === 'recipient_not_allowed') return t('emailRecipientRejected');
  if (code === 'invalid_email') return t('emailInvalid');
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
  const [bcc, setBcc] = useState('');
  const [showCc, setShowCc] = useState(mode === 'reply_all' && defaultCc.trim().length > 0);
  const [showBcc, setShowBcc] = useState(false);
  const [subject, setSubject] = useState(defaultSubject);
  const [body, setBody] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!context) return;
    setTo(context.to.join(', '));
    if (mode === 'reply_all') {
      setCc(context.cc.join(', '));
      setShowCc(context.cc.length > 0);
    } else {
      setCc('');
      setShowCc(false);
    }
    setBcc('');
    setShowBcc(false);
    setSubject(context.subject || defaultSubject);
    if (context.send_block === 'gmail_reconnect_required') setError(t('gmailReconnect'));
    else if (context.send_block === 'gmail_account_missing') setError(t('gmailAccountMissing'));
    else if (context.send_block === 'gmail_account_not_owned') setError(t('gmailAccountNotOwned'));
    else setError('');
  }, [context, defaultSubject, mode, t]);

  const sendMutation = useMutation({
    mutationFn: (recipients: { to: string[]; cc: string[]; bcc: string[] }) =>
      sendCustomerEmail({
        mode,
        contact_id: contactId || context?.contact_id,
        lead_id: leadId,
        communication_id: communicationId,
        activity_id: activityId,
        to: recipients.to,
        cc: recipients.cc,
        bcc: recipients.bcc,
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
    const parsedTo = parseRecipientField(to);
    const parsedCc = showCc ? parseRecipientField(cc) : { addresses: [], invalid: [] };
    const parsedBcc = showBcc ? parseRecipientField(bcc) : { addresses: [], invalid: [] };
    if (
      parsedTo.invalid.length > 0 ||
      parsedCc.invalid.length > 0 ||
      parsedBcc.invalid.length > 0 ||
      parsedTo.addresses.length === 0
    ) {
      setError(t('emailInvalid'));
      return;
    }
    setError('');
    sendMutation.mutate(partitionRecipients(parsedTo.addresses, parsedCc.addresses, parsedBcc.addresses));
  };

  return (
    <form className="crm-email-compose" onSubmit={onSubmit} data-testid="crm-email-compose">
      {context?.from_mailbox ? (
        <p className="crm-email-compose__from">
          {t('emailFrom')}: {context.from_mailbox}
        </p>
      ) : null}
      <Input label={t('emailTo')} value={to} onChange={(event) => setTo(event.target.value)} />
      <div className="crm-email-compose__toggles">
        {showCc ? null : (
          <button type="button" data-testid="crm-email-cc-toggle" onClick={() => setShowCc(true)}>
            CC
          </button>
        )}
        {showBcc ? null : (
          <button type="button" data-testid="crm-email-bcc-toggle" onClick={() => setShowBcc(true)}>
            BCC
          </button>
        )}
      </div>
      {showCc ? (
        <div data-testid="crm-email-cc">
          <Input label={t('emailCc')} value={cc} onChange={(event) => setCc(event.target.value)} />
        </div>
      ) : null}
      {showBcc ? (
        <div data-testid="crm-email-bcc">
          <Input label={t('emailBcc')} value={bcc} onChange={(event) => setBcc(event.target.value)} />
        </div>
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
