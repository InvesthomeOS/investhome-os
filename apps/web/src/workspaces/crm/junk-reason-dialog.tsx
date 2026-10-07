'use client';

import { useEffect, useState } from 'react';

import { Button, Dialog, Select, TextArea } from '@investhome/ui';

import { CRM_LEAD_JUNK_REASONS } from '@/workspaces/crm/api/crm-leads';

const COPY = {
  tr: {
    title: 'Junk Sebebi',
    field: 'Sebep',
    detail: 'Açıklama',
    detailPh: 'Kısa açıklama yazın',
    cancel: 'İptal',
    move: "Junk'a Taşı",
    required: 'Junk sebebi gerekli',
    detailRequired: 'Diğer için kısa açıklama gerekli',
    any: 'Seçin',
  },
  en: {
    title: 'Junk Reason',
    field: 'Reason',
    detail: 'Explanation',
    detailPh: 'Add a short explanation',
    cancel: 'Cancel',
    move: 'Move to Junk',
    required: 'Junk reason is required',
    detailRequired: 'A short explanation is required for Other',
    any: 'Select',
  },
};

export type CrmJunkReasonPayload = {
  junk_reason: string;
  junk_reason_detail?: string;
};

export function CrmJunkReasonDialog({
  open,
  locale,
  pending = false,
  onCancel,
  onConfirm,
}: {
  open: boolean;
  locale: 'tr' | 'en';
  pending?: boolean;
  onCancel: () => void;
  onConfirm: (payload: CrmJunkReasonPayload) => void;
}) {
  const t = COPY[locale];
  const [reason, setReason] = useState('');
  const [detail, setDetail] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setReason('');
    setDetail('');
    setError(null);
  }, [open]);

  const submit = () => {
    if (!reason) {
      setError(t.required);
      return;
    }
    if (reason === 'other' && detail.trim().length < 3) {
      setError(t.detailRequired);
      return;
    }
    onConfirm({
      junk_reason: reason,
      junk_reason_detail: reason === 'other' ? detail.trim() : undefined,
    });
  };

  return (
    <Dialog open={open} onClose={onCancel} title={t.title} ariaLabel={t.title}>
      <div data-testid="crm-junk-reason-dialog">
        <Select
          label={t.field}
          value={reason}
          onChange={(event) => {
            setReason(event.target.value);
            setError(null);
          }}
          data-testid="crm-junk-reason-select"
        >
          <option value="">{t.any}</option>
          {CRM_LEAD_JUNK_REASONS.map((item) => (
            <option key={item.code} value={item.code}>
              {item[locale]}
            </option>
          ))}
        </Select>
        {reason === 'other' ? (
          <TextArea
            label={t.detail}
            value={detail}
            rows={3}
            placeholder={t.detailPh}
            onChange={(event) => {
              setDetail(event.target.value);
              setError(null);
            }}
            data-testid="crm-junk-reason-detail"
          />
        ) : null}
        {error ? <p className="crm-ops-conflict">{error}</p> : null}
        <div className="crm-ops-taskform__actions" style={{ marginTop: 12 }}>
          <Button type="button" size="sm" variant="secondary" onClick={onCancel} disabled={pending}>
            {t.cancel}
          </Button>
          <Button type="button" size="sm" onClick={submit} disabled={pending}>
            {t.move}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
