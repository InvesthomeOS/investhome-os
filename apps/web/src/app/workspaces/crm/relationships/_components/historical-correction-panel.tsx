'use client';

import { useState } from 'react';
import { useLocale } from 'next-intl';
import { useMutation, useQuery } from '@tanstack/react-query';

import { Button } from '@investhome/ui';

import {
  applyKnownCorrections,
  previewKnownCorrections,
  type KnownCorrectionPreview,
} from '@/workspaces/crm/api/relationships';

const COPY = {
  tr: {
    title: 'Geçmiş ilişki düzeltmesi',
    hint: 'Yalnızca kayıtlı veri düzeltmelerini önizler ve uygular. Normal ilişki düzenlemesi değildir.',
    preview: 'Önizle',
    apply: 'Düzeltmeyi uygula',
    confirm: 'Önizlenen geçmiş ilişki düzeltmeleri uygulansın mı?',
    loading: 'Önizleme yükleniyor…',
    failed: 'Düzeltme önizlemesi yüklenemedi. Yeniden deneyin.',
    applyFailed: 'Düzeltme uygulanamadı. Yeniden deneyin.',
    empty: 'Uygulanacak kayıtlı düzeltme yok.',
    retry: 'Yeniden dene',
    current: 'Mevcut',
    intended: 'Olacak',
    applied: 'Düzeltme uygulandı.',
  },
  en: {
    title: 'Historical relationship correction',
    hint: 'Previews and applies the stored data corrections only. This is not ordinary relationship editing.',
    preview: 'Preview',
    apply: 'Apply correction',
    confirm: 'Apply the previewed historical relationship corrections?',
    loading: 'Loading preview…',
    failed: 'The correction preview could not be loaded. Try again.',
    applyFailed: 'The correction could not be applied. Try again.',
    empty: 'There is no stored correction to apply.',
    retry: 'Retry',
    current: 'Current',
    intended: 'Intended',
    applied: 'Correction applied.',
  },
} as const;

function fieldSummary(value: Record<string, unknown> | undefined): string {
  if (!value) return '—';
  const parts = Object.entries(value)
    .filter(([, item]) => item != null && typeof item !== 'object')
    .map(([key, item]) => `${key}: ${String(item)}`);
  return parts.length ? parts.join(', ') : '—';
}

function safeDetail(detail: string | null | undefined, fallback: string): string {
  if (!detail || /traceback|exception/i.test(detail)) return fallback;
  return detail;
}

type CorrectionCopy = (typeof COPY)[keyof typeof COPY];

function CorrectionList({
  items,
  copy,
}: {
  items: KnownCorrectionPreview[];
  copy: CorrectionCopy;
}) {
  if (items.length === 0) return <p data-testid="crm-historical-correction-empty">{copy.empty}</p>;
  return (
    <ul data-testid="crm-historical-correction-results">
      {items.map((item, index) => (
        <li key={`${item.key ?? 'item'}-${index}`}>
          <strong>{item.key || '—'}</strong>
          <span> {item.status || '—'}</span>
          <p>{safeDetail(item.detail, '—')}</p>
          <p>
            {copy.current}: {fieldSummary(item.current)}
          </p>
          <p>
            {copy.intended}: {fieldSummary(item.intended)}
          </p>
        </li>
      ))}
    </ul>
  );
}

export function HistoricalCorrectionPanel() {
  const locale = useLocale();
  const copy = COPY[locale.startsWith('tr') ? 'tr' : 'en'];
  const [previewReady, setPreviewReady] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const preview = useQuery({
    queryKey: ['crm', 'corrections', 'known', 'preview'],
    queryFn: previewKnownCorrections,
    enabled: false,
  });
  const apply = useMutation({
    mutationFn: applyKnownCorrections,
    onSuccess: () => setApplyError(null),
    onError: () => setApplyError(copy.applyFailed),
  });

  const loadPreview = async () => {
    setPreviewReady(false);
    setApplyError(null);
    const result = await preview.refetch();
    if (result.data && !result.error) setPreviewReady(true);
  };

  const confirmApply = () => {
    if (!previewReady || !preview.data || apply.isPending) return;
    if (!window.confirm(copy.confirm)) return;
    apply.mutate();
  };

  return (
    <section className="crm-rel-correction" data-testid="crm-historical-correction">
      <h2>{copy.title}</h2>
      <p>{copy.hint}</p>
      <div className="crm-rel-header-actions">
        <Button type="button" size="sm" variant="secondary" data-testid="crm-historical-correction-preview" onClick={() => void loadPreview()}>
          {copy.preview}
        </Button>
        <Button
          type="button"
          size="sm"
          data-testid="crm-historical-correction-apply"
          disabled={!previewReady || !preview.data || apply.isPending}
          onClick={confirmApply}
        >
          {copy.apply}
        </Button>
      </div>
      {preview.isFetching ? <p>{copy.loading}</p> : null}
      {preview.isError ? (
        <div data-testid="crm-historical-correction-error">
          <p>{copy.failed}</p>
          <Button type="button" size="sm" onClick={() => void loadPreview()}>
            {copy.retry}
          </Button>
        </div>
      ) : null}
      {previewReady && preview.data ? <CorrectionList items={preview.data.results ?? []} copy={copy} /> : null}
      {applyError ? <p role="alert">{applyError}</p> : null}
      {apply.data ? (
        <div data-testid="crm-historical-correction-applied">
          <p>{copy.applied}</p>
          <CorrectionList items={apply.data.results ?? []} copy={copy} />
        </div>
      ) : null}
    </section>
  );
}
