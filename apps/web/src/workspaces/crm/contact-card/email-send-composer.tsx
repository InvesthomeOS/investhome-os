'use client';

import { FormEvent, useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { Button, Input, TextArea } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { fetchDocumentsByEntity, type Document } from '@/lib/api/documents';
import { parseRecipientField, partitionRecipients } from '@/lib/crm/email-recipients';
import { fetchEmailReplyContext, sendCustomerEmail } from '@/workspaces/crm/api/communication';
import { communicationQueryKeys } from '@/workspaces/crm/hooks/use-communication';

const EMAIL_ATTACHMENT_MAX_BYTES = 18 * 1024 * 1024;
const EMAIL_ATTACHMENT_MAX_COUNT = 10;

type ComposerAttachment = {
  key: string;
  name: string;
  size: number;
  documentId?: string;
  file?: File;
};

const ATTACHMENT_REASONS: Record<string, string> = {
  blocked_type: 'desteklenmeyen veya güvenli olmayan dosya',
  unknown_type: 'dosya türü doğrulanamadı',
  content_mismatch: 'dosya içeriği uzantısıyla uyuşmuyor',
  unsupported_type: 'desteklenmeyen dosya türü',
  mime_mismatch: 'dosya içeriği bildirilen türle uyuşmuyor',
  file_too_large: 'dosya boyutu sınırı aşıyor',
  empty_file: 'dosya boş',
  empty: 'dosya boş',
  not_linked: 'bu kişi veya sürece bağlı değil',
  not_permitted: 'ekleme yetkisi yok',
  missing: 'dosya bulunamadı',
  unreadable: 'dosya okunamadı',
  invalid: 'dosya okunamadı',
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function attachmentError(code: string): string | null {
  if (code === 'attachment_too_large') {
    return 'Eklerin toplam boyutu 18 MB sınırını aşıyor. Gönderim durduruldu.';
  }
  if (code === 'attachment_too_many') {
    return 'En fazla 10 dosya eklenebilir. E-posta gönderilmedi.';
  }
  if (!code.startsWith('attachment_failed:')) return null;
  const [, filename = 'dosya', ...rest] = code.split(':');
  const reason = ATTACHMENT_REASONS[rest.join(':')] || 'dosya eklenemedi';
  return `"${filename}" eklenemedi: ${reason}. E-posta gönderilmedi.`;
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || '');
      const comma = result.indexOf(',');
      resolve(comma >= 0 ? result.slice(comma + 1) : result);
    };
    reader.onerror = () => reject(reader.error || new Error('read_failed'));
    reader.readAsDataURL(file);
  });
}

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
  return attachmentError(code) || t('sendFailed');
}

export function EmailSendComposer({
  mode,
  contactId,
  leadId,
  agreementId,
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
  agreementId?: string | null;
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
  const [attachments, setAttachments] = useState<ComposerAttachment[]>([]);
  const attachmentsRef = useRef<ComposerAttachment[]>([]);
  const [fileMenuOpen, setFileMenuOpen] = useState(false);
  const [documentPickerOpen, setDocumentPickerOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const commitAttachments = (next: ComposerAttachment[]) => {
    attachmentsRef.current = next;
    setAttachments(next);
  };
  const documentsQuery = useQuery({
    queryKey: ['crm', 'email-attachment-documents', contactId || '', leadId || '', agreementId || ''],
    queryFn: async () => {
      const requests: Array<Promise<{ items: Document[] }>> = [];
      if (contactId) {
        requests.push(fetchDocumentsByEntity('crm_contact', contactId, { pageSize: 100 }));
        requests.push(fetchDocumentsByEntity('contact', contactId, { pageSize: 100 }));
      }
      if (leadId) requests.push(fetchDocumentsByEntity('lead', leadId, { pageSize: 100 }));
      if (agreementId) requests.push(fetchDocumentsByEntity('crm_agreement', agreementId, { pageSize: 100 }));
      const batches = await Promise.all(requests.map((request) => request.catch(() => ({ items: [] as Document[] }))));
      const byId = new Map<string, Document>();
      for (const batch of batches) {
        for (const item of batch.items) byId.set(item.id, item);
      }
      return [...byId.values()];
    },
    enabled: documentPickerOpen && Boolean(contactId || leadId || agreementId),
  });

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
    mutationFn: async (payload: {
      recipients: { to: string[]; cc: string[]; bcc: string[] };
      uploads: Array<{ filename: string; content_base64: string }>;
      documentIds: string[];
    }) =>
      sendCustomerEmail({
        mode,
        contact_id: contactId || context?.contact_id,
        lead_id: leadId,
        agreement_id: agreementId,
        communication_id: communicationId,
        activity_id: activityId,
        to: payload.recipients.to,
        cc: payload.recipients.cc,
        bcc: payload.recipients.bcc,
        subject: subject.trim(),
        body_text: body.trim(),
        document_ids: payload.documentIds,
        uploads: payload.uploads,
      }),
    onSuccess: async () => {
      setBody('');
      commitAttachments([]);
      setFileMenuOpen(false);
      setDocumentPickerOpen(false);
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
    const totalSize = attachments.reduce((sum, item) => sum + item.size, 0);
    if (attachments.length > EMAIL_ATTACHMENT_MAX_COUNT) {
      setError('En fazla 10 dosya eklenebilir. E-posta gönderilmedi.');
      return;
    }
    if (totalSize > EMAIL_ATTACHMENT_MAX_BYTES) {
      setError('Eklerin toplam boyutu 18 MB sınırını aşıyor. Gönderim durduruldu.');
      return;
    }
    const selected = attachmentsRef.current;
    const computerFiles = selected.filter((item) => item.file);
    void (async () => {
      let uploads: Array<{ filename: string; content_base64: string }> = [];
      try {
        uploads = await Promise.all(
          computerFiles.map(async (item) => ({
            filename: item.name,
            content_base64: await fileToBase64(item.file as File),
          })),
        );
      } catch {
        setError(`"${computerFiles[0]?.name || 'dosya'}" okunamadı. E-posta gönderilmedi.`);
        return;
      }
      if (computerFiles.length > 0 && uploads.length !== computerFiles.length) {
        setError('Seçilen dosya eklenemedi. E-posta gönderilmedi.');
        return;
      }
      if (uploads.some((item) => !item.content_base64)) {
        const missing = uploads.find((item) => !item.content_base64);
        setError(`"${missing?.filename || 'dosya'}" okunamadı. E-posta gönderilmedi.`);
        return;
      }
      setError('');
      sendMutation.mutate({
        recipients: partitionRecipients(parsedTo.addresses, parsedCc.addresses, parsedBcc.addresses),
        uploads,
        documentIds: selected.flatMap((item) => (item.documentId ? [item.documentId] : [])),
      });
    })();
  };

  const addFiles = (list: FileList | null) => {
    // FileList is live. Copy the File objects before clearing the input, or the
    // later state update reads an empty list and the email is sent with no attachment.
    const picked = Array.from(list ?? []);
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (!picked.length) return;
    const next = [...attachmentsRef.current];
    for (const file of picked) {
      if (next.length >= EMAIL_ATTACHMENT_MAX_COUNT) {
        setError('En fazla 10 dosya eklenebilir.');
        break;
      }
      const total = next.reduce((sum, item) => sum + item.size, 0) + file.size;
      if (total > EMAIL_ATTACHMENT_MAX_BYTES) {
        setError(`"${file.name}" eklenemedi: toplam ek boyutu 18 MB sınırını aşıyor.`);
        continue;
      }
      next.push({
        key: `file-${file.name}-${file.size}-${file.lastModified}-${next.length}`,
        name: file.name,
        size: file.size,
        file,
      });
    }
    commitAttachments(next);
    setFileMenuOpen(false);
  };

  const toggleDocument = (document: Document) => {
    const current = attachmentsRef.current;
    const existing = current.find((item) => item.documentId === document.id);
    if (existing) {
      commitAttachments(current.filter((item) => item.documentId !== document.id));
      return;
    }
    if (current.length >= EMAIL_ATTACHMENT_MAX_COUNT) {
      setError('En fazla 10 dosya eklenebilir.');
      return;
    }
    const total = current.reduce((sum, item) => sum + item.size, 0) + document.file_size;
    if (total > EMAIL_ATTACHMENT_MAX_BYTES) {
      setError(`"${document.original_file_name}" eklenemedi: toplam ek boyutu 18 MB sınırını aşıyor.`);
      return;
    }
    setError('');
    commitAttachments([
      ...current,
      {
        key: `doc-${document.id}`,
        name: document.original_file_name,
        size: document.file_size,
        documentId: document.id,
      },
    ]);
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
      <div className="crm-email-compose__files">
        <button type="button" onClick={() => setFileMenuOpen((open) => !open)}>
          Dosya Ekle
        </button>
        {fileMenuOpen ? (
          <div className="crm-email-compose__file-menu">
            <button type="button" onClick={() => fileInputRef.current?.click()}>
              Bilgisayardan Yükle
            </button>
            <button
              type="button"
              onClick={() => {
                setDocumentPickerOpen((open) => !open);
                setFileMenuOpen(false);
              }}
            >
              CRM Belgelerinden Seç
            </button>
          </div>
        ) : null}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          hidden
          onChange={(event) => addFiles(event.target.files)}
        />
        {attachments.length ? (
          <div>
            <strong>Ekler</strong>
            <ul className="crm-email-compose__attachments">
              {attachments.map((item) => (
                <li key={item.key}>
                  <span>{item.name}</span>
                  <span>{formatSize(item.size)}</span>
                  <button
                    type="button"
                    onClick={() =>
                      commitAttachments(attachmentsRef.current.filter((row) => row.key !== item.key))
                    }
                  >
                    Kaldır
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {documentPickerOpen ? (
          <div className="crm-email-compose__picker">
            {documentsQuery.isLoading ? <p>Belgeler yükleniyor…</p> : null}
            {documentsQuery.isError ? <p>Belgeler yüklenemedi.</p> : null}
            {documentsQuery.data && documentsQuery.data.length === 0 ? <p>Bağlı belge yok.</p> : null}
            {(documentsQuery.data || []).map((document) => (
              <label key={document.id}>
                <input
                  type="checkbox"
                  checked={attachments.some((item) => item.documentId === document.id)}
                  onChange={() => toggleDocument(document)}
                />
                <span>{document.original_file_name}</span>
                <span>{formatSize(document.file_size)}</span>
              </label>
            ))}
          </div>
        ) : null}
      </div>
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
