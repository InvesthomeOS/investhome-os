'use client';

import { FormEvent, useEffect, useMemo, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { useTranslations, useLocale } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, Input, Select, StatusChip, TextArea } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { hasPermission } from '@/lib/api/auth';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { uiError } from '@/lib/i18n/ui-error';
import { createTask } from '@/workspaces/crm/api/activities';
import { cancelAgreement, fetchProjectUnits, returnAgreementToPipeline } from '@/workspaces/crm/api/crm-operations';
import { phaseFieldVisible, unitIdentifier, unitSelectionLabel, unitsForPhase } from '@/workspaces/crm/project-phase-unit.mjs';
import {
  changeAgreementUnit,
  patchAgreement,
  type CrmLabeledValue,
  type CrmPurchaseCard,
} from '@/workspaces/crm/api/agreements';
import { EmailCard, EmailDetail, type EmailViewEntry } from '@/workspaces/crm/contact-card/crm-email-view';
import { DocumentGallery } from '@/workspaces/crm/contact-card/document-gallery';
import { HemenKiraToggle } from '@/workspaces/crm/contact-card/hemen-kira-toggle';
import { looksLikePayloadDump, stripHtml, taskStatusLabel } from '@/workspaces/crm/contact-card/history-html';
import { AgreementOwnersEditor } from '@/workspaces/crm/contact-card/agreement-owners-editor';
import { UnitHistorySection } from '@/workspaces/crm/contact-card/unit-history';
import { personCardCopy } from '@/workspaces/crm/contact-card/person-card-copy';
import { currencyPrefix, formatAgreementAmount, numericAmount } from '@/workspaces/crm/money';
import { isWhatsappEntry } from '@/workspaces/crm/contact-card/whatsapp-thread';

import './contact-card.css';
import './sales-detail.css';

const HISTORY_FILTERS = [
  { id: 'all', label: 'Tümü' },
  { id: 'comment', label: 'Yorumlar' },
  { id: 'email', label: 'E-posta' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'meeting', label: 'Toplantı' },
  { id: 'task', label: 'Görev' },
  { id: 'document', label: 'Belge' },
  { id: 'other', label: 'Diğer' },
] as const;

type HistoryFilter = (typeof HISTORY_FILTERS)[number]['id'];

type TimelineItem = {
  id: string;
  kind: HistoryFilter;
  title: string;
  summary?: string | null;
  actor?: string | null;
  status?: string | null;
  created_at: string;
  email?: EmailViewEntry;
};

function pct(value?: string | null) {
  return value ? value.replace(/\.00$/, '') : '';
}

function displayDate(value?: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
  return date.toLocaleDateString('tr-TR', { day: 'numeric', month: 'short', year: 'numeric' });
}

function displayDateTime(value?: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('tr-TR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function statusLabel(
  raw: string | null | undefined,
  label: (key: 'purchased' | 'completed' | 'lost' | 'active') => string,
): string | null {
  const value = (raw || '').trim();
  if (!value) return null;
  if (/deal\s*won|^won$|^kazan[ıi]ld[ıi]$/i.test(value)) return label('purchased');
  if (/^completed$|^tamamland[ıi]$/i.test(value)) return label('completed');
  if (/^lost$|^kaybedildi$/i.test(value)) return label('lost');
  if (/^active$|^aktif$/i.test(value)) return label('active');
  if (/^[A-Z0-9_:]+$/.test(value)) return null;
  if (/final_invoice|c\d+:/i.test(value)) return null;
  return value;
}

function isTechnicalField(label: string, value?: string | null): boolean {
  if (!value) return true;
  const field = label.trim();
  const raw = value.trim();
  if (!field || !raw) return true;
  if (/^\{[\s\S]*\}$/.test(raw) || raw.startsWith('[{')) return true;
  if (looksLikePayloadDump(raw)) return true;
  if (/ownership percentage|sahiplik/i.test(field)) return true;
  if (/deal|purchase card|project context|final_invoice|\bprimary\b|\bsecondary\b/i.test(field)) return true;
  if (/durumu|status|zoom|yüz yüze|potential|yatırım modeli/i.test(field) && /^\d{1,5}$/.test(raw)) return true;
  if (/tc id|vatandaşlık|iban|swift|banka/i.test(field)) return true;
  if (/önceki daire|daire değiş/i.test(field)) return true;
  return false;
}

function findLabeled(items: CrmLabeledValue[] | null | undefined, match: RegExp): string | null {
  const hit = (items ?? []).find((item) => match.test(item.label) && !isTechnicalField(item.label, item.value));
  return hit?.value?.trim() || null;
}

function cleanMoneyish(value: string) {
  return value.replace(/\|/g, ' ').replace(/\s+/g, ' ').trim();
}

function initials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const first = parts[0];
  if (!first) return '•';
  const last = parts.length > 1 ? parts[parts.length - 1] : undefined;
  return `${first[0] ?? ''}${last?.[0] ?? ''}`.toUpperCase();
}

function InfoRow({ label, value, dash = false }: { label: string; value?: string | null; dash?: boolean }) {
  const text = (value || '').trim();
  if (!text && !dash) return null;
  return (
    <div className="crm-pd-info__row">
      <dt>{label}</dt>
      <dd>{text || '—'}</dd>
    </div>
  );
}

function Card({
  title,
  action,
  children,
  testId,
  className,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  testId?: string;
  className?: string;
}) {
  return (
    <article className={`crm-pd-card${className ? ` ${className}` : ''}`} data-testid={testId}>
      <div className="crm-pd-card__head">
        <h2>{title}</h2>
        {action ? <div className="crm-pd-card__actions">{action}</div> : null}
      </div>
      <div className="crm-pd-card__body">{children}</div>
    </article>
  );
}

function kindFromActivity(type: string, title: string, imported?: boolean): HistoryFilter {
  const value = type.toLowerCase();
  if (imported || value === 'comment' || value === 'note' || value === 'internal_discussion') return 'comment';
  if (value === 'email') return 'email';
  if (value === 'whatsapp') return 'whatsapp';
  if (value.includes('meeting')) return 'meeting';
  if (value === 'task' || value === 'follow_up' || value === 'reminder') return 'task';
  if (value === 'document') return 'document';
  return 'other';
}

function kindLabel(kind: HistoryFilter, label: (key: HistoryFilter) => string) {
  return label(kind);
}

function buildTimeline(card: CrmPurchaseCard): TimelineItem[] {
  const items: TimelineItem[] = card.history
    .filter((entry) => !looksLikePayloadDump(entry.summary) && !looksLikePayloadDump(entry.title))
    .map((entry) => {
      const kind = isWhatsappEntry(entry)
        ? 'whatsapp'
        : kindFromActivity(entry.activity_type, entry.title, entry.imported_historical_comment);
      return {
        id: entry.id,
        kind,
        title: kind === 'comment' && /^not\b/i.test(entry.title) ? 'Yorum' : entry.title,
        summary: entry.summary,
        actor: entry.actor_name,
        status: entry.status,
        created_at: entry.created_at,
        email: kind === 'email' ? entry : undefined,
      };
    });
  for (const doc of card.documents.filter((item) => !item.hidden_from_view)) {
    items.push({
      id: `doc-${doc.id}`,
      kind: 'document',
      title: doc.original_file_name || doc.title,
      summary: [doc.document_type, doc.source].filter(Boolean).join(' · ') || 'Belge',
      created_at: doc.created_at || card.begin_date || card.agreement_date || card.close_date || new Date(0).toISOString(),
    });
  }
  return items.sort((a, b) => b.created_at.localeCompare(a.created_at));
}

function unitFields(extra: CrmLabeledValue[] | undefined) {
  return (extra ?? []).filter((item) => {
    if (isTechnicalField(item.label, item.value)) return false;
    return /adres|address|lokasyon|tip|type|brüt|brut|net alan|sqft|m2|m²|kat|floor|balkon|teras|otopark|parking|oda|bedroom/i.test(
      item.label,
    );
  });
}

function dateFields(extra: CrmLabeledValue[] | undefined) {
  return (extra ?? []).filter((item) => {
    if (isTechnicalField(item.label, item.value)) return false;
    return /tarih|date|kapanış|kapaniş|teslim|tapu|kira başlang|closing|deed/i.test(item.label);
  });
}

function paymentRows(card: CrmPurchaseCard): Array<{ label: string; value: string }> {
  const rows: Array<{ label: string; value: string }> = [];
  const deposit = card.payment.kapora || card.payment.deposit;
  if (deposit) rows.push({ label: 'Kapora / Depozito', value: cleanMoneyish(String(deposit)) });
  for (const item of card.payment_fields ?? []) {
    if (isTechnicalField(item.label, item.value)) continue;
    if (/ödeme notu|payment notes|payment_plan/i.test(item.label)) continue;
    rows.push({ label: item.label, value: cleanMoneyish(item.value) });
  }
  const paid = findLabeled(card.payment_fields, /ödenen|paid|tahsil/i);
  const remaining = findLabeled([...(card.payment_fields ?? []), ...(card.extra_fields ?? [])], /kalan|remaining|bakiye/i);
  if (paid && !rows.some((row) => /ödenen/i.test(row.label))) rows.push({ label: 'Ödenen', value: paid });
  if (remaining && !rows.some((row) => /kalan/i.test(row.label))) rows.push({ label: 'Kalan', value: remaining });
  return rows;
}

export function PurchaseDetailView({
  card,
  contactId,
  onOpenContact,
  onBack,
  onRefresh,
  pageTestId = 'sales-detail-page',
}: {
  card: CrmPurchaseCard;
  contactId: string | null;
  onOpenContact: (id: string) => void;
  onBack: () => void;
  onRefresh: () => void;
  pageTestId?: string;
}) {
  const tCard = useTranslations('crm.contactCard.ui');
  const tCommon = useTranslations('common');
  const tTask = useTranslations('crm.contactCard.taskStatus');
  const tFilters = useTranslations('crm.contactCard.filters');
  const tStage = useTranslations('crm.contactCard.purchaseStatus');
  const t = personCardCopy(useLocale());
  const queryClient = useQueryClient();
  const { user, canCreate, canManageTasks, canViewFinancial, has } = useCrmAccess();
  const canUpdate = has('update');
  const canEditOwnership = has('edit_ownership');
  const canUploadDocuments = Boolean(user && hasPermission(user, 'documents', 'update'));
  const canArchiveDocuments = Boolean(
    user && (hasPermission(user, 'documents', 'archive') || hasPermission(user, 'documents', 'delete')),
  );
  const [filter, setFilter] = useState<HistoryFilter>('all');
  const [emailFocus, setEmailFocus] = useState<EmailViewEntry | null>(null);
  const [showMore, setShowMore] = useState(false);
  const [showCancel, setShowCancel] = useState(false);
  const [cancelPending, setCancelPending] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [cancelNote, setCancelNote] = useState('');
  const [cancelDate, setCancelDate] = useState('');
  const [returnStage, setReturnStage] = useState('');
  const [returnPending, setReturnPending] = useState(false);
  const [showOwnersEdit, setShowOwnersEdit] = useState(false);
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDue, setTaskDue] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [amountEdit, setAmountEdit] = useState(numericAmount(card.amount));
  const [amountOk, setAmountOk] = useState(false);
  const [unitDraft, setUnitDraft] = useState(card.unit_number || '');
  const [unitPhaseId, setUnitPhaseId] = useState(card.phase_id || '');
  const [unitAssetId, setUnitAssetId] = useState(card.inventory_asset_id || '');
  const [unitConfirm, setUnitConfirm] = useState(false);

  const isReit = card.project_group === 'reit';
  const isCancelled = card.status === 'cancelled';
  const canEditUnit = canUpdate && !isReit && !isCancelled;
  const unitCatalog = useQuery({
    queryKey: ['purchase-unit-catalog', card.project_group],
    queryFn: () => fetchProjectUnits(card.project_group),
    enabled: canEditUnit && !isReit,
  });
  const stage = statusLabel(card.stage, tStage) || statusLabel(card.status, tStage) || null;
  const viewer =
    card.participants.find((item) => item.contact_id === contactId) ||
    card.participants.find((item) => item.is_primary) ||
    card.participants[0] ||
    null;
  const personId = contactId || viewer?.contact_id || card.primary_contact_id;
  const address = findLabeled(card.extra_fields, /adres|address|lokasyon|location/i);
  const projectName = isReit ? 'REIT' : card.project_label;
  const catalogPhases = unitCatalog.data?.phases;
  const usesPhases = Boolean(unitCatalog.data?.uses_phases);
  const phasedEmpty = !isReit && usesPhases && !phaseFieldVisible(catalogPhases);
  const phaseRequired = !isReit && usesPhases && phaseFieldVisible(catalogPhases);
  const phaseLabel =
    card.phase_name ||
    catalogPhases?.find((phase) => phase.id === (card.phase_id || unitPhaseId))?.name ||
    '';
  const showPhase = phaseRequired || Boolean(phaseLabel);
  const unitIdentity = isReit ? null : card.unit_number;
  const unitLabel = isReit ? null : showPhase ? unitIdentity : card.unit_display || card.unit_number;
  const amount = formatAgreementAmount(card.amount, card.currency) || card.amount_label || card.amount;
  const amountPrefix = currencyPrefix(card.currency);
  const agreementDate = displayDate(card.agreement_date || card.begin_date);
  const crumbUnit = isReit
    ? 'REIT'
    : [projectName, showPhase ? phaseLabel : null, unitIdentity || unitLabel].filter(Boolean).join(' · ');
  const phaseOptions = unitsForPhase(unitCatalog.data?.items, unitPhaseId, usesPhases ? catalogPhases : []);
  const payments = paymentRows(card);
  const extrasUnit = unitFields(card.extra_fields);
  const extrasDates = dateFields(card.extra_fields);
  const timeline = useMemo(() => buildTimeline(card), [card]);
  const filtered = timeline.filter((item) => (filter === 'all' ? true : item.kind === filter));
  const tasks = timeline.filter((item) => item.kind === 'task' || item.kind === 'meeting');
  const purchaseDocs = card.documents.filter((item) => !item.hidden_from_view);
  const personDocs = (card.person_documents ?? []).filter((item) => !item.hidden_from_view);
  const documentGroups = (card.document_groups ?? []).filter((group) => group.unit_number);
  const groupedVisible = documentGroups.flatMap((group) => group.documents.filter((item) => !item.hidden_from_view));
  const allDocuments = [...purchaseDocs, ...groupedVisible, ...personDocs];
  const allDocumentCount = new Set(allDocuments.map((item) => item.id)).size;
  useEffect(() => {
    setUnitDraft(card.unit_number || '');
    setUnitPhaseId(card.phase_id || '');
    setUnitAssetId(card.inventory_asset_id || '');
  }, [card.agreement_id, card.inventory_asset_id, card.phase_id, card.unit_number]);

  useEffect(() => {
    if (unitPhaseId || !card.phase_name) return;
    const match = (catalogPhases ?? []).find((phase) => phase.name === card.phase_name);
    if (match) setUnitPhaseId(match.id);
  }, [card.phase_name, catalogPhases, unitPhaseId]);

  const canAct = Boolean(canCreate || canManageTasks);
  const canEditAmount = Boolean(canUpdate && canViewFinancial && !isCancelled);
  const canOpenCancel = Boolean(canUpdate && !isCancelled);
  const canReturnToPipeline = Boolean(canUpdate && isCancelled && !card.pipeline_returned_at);
  const showMoreMenu = canOpenCancel || canReturnToPipeline;

  const unitMutation = useMutation({
    mutationFn: () =>
      changeAgreementUnit(card.agreement_id, unitIdentifier(unitDraft), {
        phase_id: unitPhaseId || null,
        inventory_asset_id: unitAssetId || null,
      }),
    onSuccess: () => {
      setUnitConfirm(false);
      setError(null);
      onRefresh();
      void queryClient.invalidateQueries({ queryKey: ['crm'] });
    },
    onError: (err: Error) => setError(uiError(err, tCommon('actionFailed'))),
  });

  const amountMutation = useMutation({
    mutationFn: async () => {
      const next = numericAmount(amountEdit);
      if (!next) throw new Error(t.amountRequired);
      await patchAgreement(card.agreement_id, { amount: next });
    },
    onSuccess: () => {
      setError(null);
      setAmountOk(true);
      onRefresh();
      void queryClient.invalidateQueries({ queryKey: ['crm'] });
    },
    onError: (err: Error) => {
      setAmountOk(false);
      setError(uiError(err, tCommon('actionFailed')));
    },
  });

  const submitAmount = (event: FormEvent) => {
    event.preventDefault();
    if (amountMutation.isPending) return;
    amountMutation.mutate();
  };

  const taskMutation = useMutation({
    mutationFn: async () => {
      if (!taskTitle.trim() || !personId) return;
      await createTask({
        title: taskTitle.trim(),
        contact_id: personId,
        agreement_id: card.agreement_id,
        entity_type: 'contact',
        entity_id: personId,
        assigned_user_id: user?.id,
        due_date: taskDue || undefined,
        metadata_json: { follow_up_kind: 'task', purchase_agreement_id: card.agreement_id },
      });
    },
    onSuccess: () => {
      setTaskTitle('');
      setTaskDue('');
      setShowTaskForm(false);
      setError(null);
      onRefresh();
      void queryClient.invalidateQueries({ queryKey: ['crm'] });
    },
    onError: (err: Error) => setError(uiError(err, tCommon('actionFailed'))),
  });

  const submitTask = (event: FormEvent) => {
    event.preventDefault();
    taskMutation.mutate();
  };
  return (
    <div className="crm-pd" data-testid={pageTestId}>
      <header className="crm-pd-pagehead">
        <nav className="crm-pd-crumb" aria-label={tCard('k90e4d14c18')} data-testid="sales-breadcrumb">
          <Link href="/workspaces/crm">CRM</Link>
          <span>›</span>
          <Link href="/workspaces/crm/contacts">{t.people}</Link>
          <span>›</span>
          <button type="button" onClick={onBack}>
            {viewer?.display_name || card.primary_contact_name || t.person}
          </button>
          <span>›</span>
          <span>{t.purchases}</span>
          <span>›</span>
          <strong>{crumbUnit}</strong>
        </nav>
        <div className="crm-pd-pagehead__row">
          <div>
            <button type="button" className="crm-pd-back" onClick={onBack}>
              <IhIcon name="chevronLeft" size={14} /> {viewer ? `${viewer.display_name}` : t.backToPerson}
            </button>
            <h1>{t.purchaseDetail}</h1>
          </div>
          <div className="crm-pd-pagehead__actions">
            {showMoreMenu ? (
              <Button type="button" size="sm" variant="secondary" data-testid="purchase-more" onClick={() => setShowMore((value) => !value)}>{tCard('k00793b714f')}</Button>
            ) : null}
          </div>
        </div>
        {showMore && showMoreMenu ? (
          <div className="crm-pd-more" data-testid="purchase-more-menu">
            {!isCancelled ? (
              <HemenKiraToggle agreementId={card.agreement_id} value={Boolean(card.hemen_kira)} />
            ) : null}
            {canOpenCancel ? (
              <Button type="button" size="sm" variant="secondary" data-testid="cancel-agreement" onClick={() => { setShowMore(false); setShowCancel(true); }}>
                Anlaşmayı İptal Et
              </Button>
            ) : null}
            {canReturnToPipeline ? (
              <form
                data-testid="return-pipeline-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  if (!returnStage || returnPending) return;
                  setReturnPending(true);
                  void returnAgreementToPipeline(card.agreement_id, returnStage)
                    .then(async () => {
                      setReturnStage('');
                      setShowMore(false);
                      await queryClient.invalidateQueries({ queryKey: ['crm'] });
                      onRefresh();
                    })
                    .finally(() => setReturnPending(false));
                }}
              >
                <Select label="Pipeline aşaması" value={returnStage} onChange={(event) => setReturnStage(event.target.value)}>
                  <option value="">Seçin</option>
                  <option value="yeni">Yeni</option>
                  <option value="contacted">İletişime geçildi</option>
                  <option value="following">Takip</option>
                  <option value="proposal">Teklif</option>
                  <option value="qualified">Potansiyel</option>
                  <option value="negotiation">Görüşme</option>
                  <option value="long_term">Uzun vade</option>
                </Select>
                <Button type="submit" size="sm" variant="secondary" disabled={!returnStage || returnPending}>Pipeline&apos;a geri döndür</Button>
              </form>
            ) : null}
          </div>
        ) : null}
        {card.related_purchases?.length ? (
              <div className="crm-pd-related" data-testid="purchase-related">
                {card.related_purchases.map((item) => (
                  <span key={item.agreement_id}>
                    {item.project_label}
                    {item.unit_number ? ` · ${item.unit_number}` : ''}
                    {item.is_historical_unit_change ? ' (daire değişikliği)' : item.is_current && !isCancelled ? ' (açık)' : isCancelled && item.agreement_id === card.agreement_id ? ' (iptal)' : ''}
                  </span>
                ))}
              </div>
            ) : null}
        {error ? <p className="crm-pd-error">{error}</p> : null}
      </header>
      {showCancel ? (
        <div className="crm-pd-modal" role="presentation" onClick={() => { if (!cancelPending) setShowCancel(false); }}>
          <form
            className="crm-pd-modal__panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="cancel-agreement-title"
            data-testid="cancel-agreement-dialog"
            onClick={(event) => event.stopPropagation()}
            onSubmit={(event) => {
              event.preventDefault();
              const reason = cancelReason.trim();
              if (!reason || cancelPending) return;
              setCancelPending(true);
              setError(null);
              void cancelAgreement(card.agreement_id, {
                reason,
                note: cancelNote.trim() || null,
                cancelled_on: cancelDate || null,
              })
                .then(async () => {
                  setShowCancel(false);
                  setCancelReason('');
                  setCancelNote('');
                  setCancelDate('');
                  await queryClient.invalidateQueries({ queryKey: ['crm'] });
                  onRefresh();
                })
                .catch((err: Error) => setError(uiError(err, tCommon('actionFailed'))))
                .finally(() => setCancelPending(false));
            }}
          >
            <h2 id="cancel-agreement-title">Anlaşmayı İptal Et</h2>
            <Input label="İptal nedeni" value={cancelReason} onChange={(event) => setCancelReason(event.target.value)} required />
            <Input label="İptal tarihi" type="date" value={cancelDate} onChange={(event) => setCancelDate(event.target.value)} />
            <TextArea label="Not" value={cancelNote} onChange={(event) => setCancelNote(event.target.value)} />
            <div className="crm-pd-modal__actions">
              <Button type="button" size="sm" variant="secondary" disabled={cancelPending} onClick={() => setShowCancel(false)}>Vazgeç</Button>
              <Button type="submit" size="sm" variant="danger" data-state={cancelPending || !cancelReason.trim() ? 'disabled' : 'enabled'} disabled={cancelPending || !cancelReason.trim()}>Anlaşmayı İptal Et</Button>
            </div>
          </form>
        </div>
      ) : null}

      <section className="crm-pd-hero" data-testid="sales-header">
        <div className="crm-pd-hero__main">
          <p className="crm-pd-hero__project" data-testid="purchase-card-project">
            {projectName}
          </p>
          {address ? <p className="crm-pd-hero__address">{address}</p> : null}
          <div className="crm-pd-hero__facts">
            {showPhase ? (
              <div>
                <span>Faz</span>
                <strong data-testid="purchase-card-phase">{phaseLabel || '—'}</strong>
              </div>
            ) : null}
            <div>
              <span>{showPhase ? 'Daire / Ünite' : t.unit}</span>
              <strong data-testid="purchase-card-unit">{unitLabel || '—'}</strong>
            </div>
            <div>
              <span>{t.amount}</span>
              <strong data-testid="purchase-card-amount">{amount || '—'}</strong>
            </div>
            <div>
              <span>{t.status}</span>
              <StatusChip tone={isCancelled ? 'default' : 'success'}>{isCancelled ? 'İptal Edildi' : stage || '—'}</StatusChip>
            </div>
            {isCancelled ? (
              <div data-testid="purchase-cancellation">
                <span>İptal tarihi</span>
                <strong>{displayDate(card.cancelled_at) || '—'}</strong>
              </div>
            ) : null}
            <div>
              <span>{t.purchaseDate}</span>
              <strong>{agreementDate || '—'}</strong>
            </div>
          </div>
        </div>
        <div className="crm-pd-hero__owners" data-testid="purchase-card-owners">
          <span>{t.owners}</span>
          <ul>
            {card.participants.map((owner) => (
              <li key={owner.contact_id}>
                <button type="button" onClick={() => onOpenContact(owner.contact_id)}>
                  <em>{initials(owner.display_name)}</em>
                  <strong>{owner.display_name}</strong>
                  {pct(owner.ownership_pct) ? <small>{pct(owner.ownership_pct)}%</small> : null}
                </button>
              </li>
            ))}
          </ul>
          {isCancelled ? <p data-testid="purchase-ownership-inactive">Sahiplik artık aktif değil.</p> : null}
          {canEditOwnership && !isCancelled ? (
            <>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => setShowOwnersEdit((value) => !value)}
              >
                {showOwnersEdit ? 'Sahip Düzenlemeyi Kapat' : 'Sahipleri Düzenle'}
              </Button>
              {showOwnersEdit ? (
                <AgreementOwnersEditor card={card} onChanged={onRefresh} />
              ) : null}
            </>
          ) : null}
        </div>
        <UnitHistorySection steps={card.unit_history} personId={personId} viewingAgreementId={card.agreement_id} />
      </section>

      <section className="crm-pd-grid">
        <Card title={t.basics} testId="purchase-overview" className="crm-pd-card--wide">
          <dl className="crm-pd-info">
            <InfoRow label="Proje" value={projectName} dash />
            {showPhase ? <InfoRow label="Faz" value={phaseLabel} dash /> : null}
            {isCancelled ? <InfoRow label="İptal nedeni" value={card.cancellation_reason} dash /> : null}
            {isCancelled && card.cancellation_note ? <InfoRow label="İptal notu" value={card.cancellation_note} /> : null}
            <InfoRow label={showPhase ? 'Daire / Ünite' : tCard('k91977ddb0e')} value={unitLabel} dash />
            {phasedEmpty ? (
              <p data-testid="phased-project-empty">Bu proje fazlı olarak tanımlı. Önce Projeler &gt; Fazlar bölümünden faz oluşturun.</p>
            ) : null}
            {canEditUnit && !phasedEmpty ? (
              <form
                className="crm-pd-unit-form"
                data-testid="purchase-unit-edit"
                onSubmit={(event) => {
                  event.preventDefault();
                  if (phaseRequired && !unitPhaseId) {
                    setError('Faz seçin.');
                    return;
                  }
                  const unchanged =
                    unitDraft.trim() === (card.unit_number || '') &&
                    (unitPhaseId || '') === (card.phase_id || '') &&
                    (unitAssetId || '') === (card.inventory_asset_id || '');
                  if (!unitDraft.trim() || unchanged) return;
                  setError(null);
                  setUnitConfirm(true);
                }}
              >
                {phaseRequired ? (
                  <Select
                    label="Faz"
                    value={unitPhaseId}
                    onChange={(event) => {
                      setUnitPhaseId(event.target.value);
                      setUnitAssetId('');
                      setUnitDraft('');
                    }}
                  >
                    <option value="">Seçin</option>
                    {(catalogPhases ?? []).map((phase) => (
                      <option key={phase.id} value={phase.id}>{phase.name}</option>
                    ))}
                  </Select>
                ) : null}
                {!phaseRequired || unitPhaseId ? (
                  <>
                    <Select
                      label="Daire / Ünite"
                      value={unitAssetId}
                      onChange={(event) => {
                        const selected = phaseOptions.find(
                          (item) => item.inventory_asset_id === event.target.value || item.id === event.target.value,
                        );
                        setUnitAssetId(selected?.inventory_asset_id || event.target.value);
                        if (selected?.unit_number) setUnitDraft(unitIdentifier(selected.unit_number));
                        if (selected?.phase_id) setUnitPhaseId(selected.phase_id);
                      }}
                    >
                      <option value="">Seçin</option>
                      {phaseOptions.map((item) => (
                        <option key={item.id} value={item.inventory_asset_id || item.id}>
                          {unitSelectionLabel(item)}
                        </option>
                      ))}
                    </Select>
                    {phaseRequired && unitPhaseId && phaseOptions.length === 0 ? (
                      <p data-testid="phase-units-empty">Bu faza henüz ünite atanmadı.</p>
                    ) : null}
                  </>
                ) : null}
                {!phaseRequired || unitPhaseId ? (
                  <Input label="Daire / Ünite" value={unitDraft} onChange={(event) => { setUnitDraft(event.target.value); setUnitAssetId(''); }} />
                ) : null}
                <div className="crm-pd-unit-form__actions">
                  <Button type="submit" size="sm">{tCard('k068551b70a')}</Button>
                </div>
              </form>
            ) : null}
            {unitConfirm ? (
              <div role="dialog" aria-modal="true" data-testid="change-unit-confirm">
                <p>
                  {phaseLabel ? `${phaseLabel} · ` : ''}Daire {card.unit_number || '—'} → {unitDraft.trim()} olacak. Kişi kaydı ve geçmişi durur.
                </p>
                <Button type="button" size="sm" disabled={unitMutation.isPending} onClick={() => unitMutation.mutate()}>{tCard('kd93b11b3fd')}</Button>
                <Button type="button" size="sm" variant="ghost" onClick={() => setUnitConfirm(false)}>
                  Vazgeç
                </Button>
              </div>
            ) : null}
            <InfoRow label={t.purchasePrice} value={amount} dash />
            {canEditAmount ? (
              <form className="crm-pd-amount-edit" onSubmit={submitAmount} data-testid="purchase-amount-edit">
                <div className="crm-pd-money">
                  {amountPrefix ? <span data-testid="purchase-amount-prefix">{amountPrefix}</span> : null}
                  <Input
                    label={t.editAmount}
                    value={amountEdit}
                    inputMode="decimal"
                    onChange={(event) => {
                      setAmountOk(false);
                      setAmountEdit(numericAmount(event.target.value));
                    }}
                  />
                </div>
                <Button type="submit" size="sm" disabled={amountMutation.isPending}>
                  {amountMutation.isPending ? t.saving : t.saveAmount}
                </Button>
                {amountOk ? <small data-testid="purchase-amount-saved">{t.saved}</small> : null}
              </form>
            ) : null}
            <InfoRow label={t.purchaseDate} value={agreementDate} dash />
            <InfoRow label={t.status} value={stage} dash />
            <InfoRow
              label={tCard('kf0d45053be')}
              value={card.participants.map((item) => item.display_name).join(', ') || card.owners_label}
              dash
            />
            <InfoRow label={tCard('k0904d198dd')} value={card.llc_name} />
            {(card.llc_fields ?? [])
              .filter((item) => !isTechnicalField(item.label, item.value) && !/llc name|şirket/i.test(item.label))
              .map((item) => (
                <InfoRow key={`llc:${item.label}:${item.value}`} label={item.label} value={item.value} />
              ))}
            <InfoRow label={tCard('k4368875e76')} value={card.responsible_name} />
            <InfoRow label={tCard('kd10aec6ad4')} value={card.comments ? stripHtml(card.comments) : null} />
            {(card.extra_fields ?? [])
              .filter((item) => {
                if (isTechnicalField(item.label, item.value)) return false;
                if (/adres|address|lokasyon|location/i.test(item.label)) return false;
                if (extrasUnit.some((row) => row.label === item.label)) return false;
                if (extrasDates.some((row) => row.label === item.label)) return false;
                return true;
              })
              .map((item) => (
                <InfoRow key={`extra:${item.label}:${item.value}`} label={item.label} value={item.value} />
              ))}
          </dl>
        </Card>

        <Card title={tCard('keb7e02fca9')} testId="purchase-payment">
          {payments.length ? (
            <>
              <ul className="crm-pd-pay">
                {payments.map((row) => (
                  <li key={`${row.label}:${row.value}`}>
                    <span>
                      {row.label === 'Ödenen'
                        ? tCard('paid')
                        : row.label === 'Kalan'
                          ? tCard('remaining')
                          : row.label === 'Kapora / Depozito'
                            ? tCard('deposit')
                            : row.label}
                    </span>
                    <strong>{formatAgreementAmount(row.value, card.currency) || row.value}</strong>
                  </li>
                ))}
              </ul>
              {amount ? (
                <p className="crm-pd-pay__total">
                  {t.amount}: <strong>{amount}</strong>
                </p>
              ) : null}
            </>
          ) : (
            <p className="crm-pd-empty">{tCard('kabef6d6563')}</p>
          )}
        </Card>

        <Card title={tCard('k4ced93a1b1')} testId="purchase-dates">
          <dl className="crm-pd-info">
            <InfoRow label={tCard('kf7c81d57e2')} value={stage} dash />
            <InfoRow label={tCard('k77bfbbeef2')} value={displayDate(card.agreement_date || card.begin_date)} />
            <InfoRow label={tCard('ke387f6e700')} value={displayDate(card.close_date)} />
            {extrasDates.map((item) => (
              <InfoRow key={`${item.label}:${item.value}`} label={item.label} value={item.value} />
            ))}
          </dl>
        </Card>

        <Card
          title={tCard('k780d7a72db')}
          action={
            <Link className="ih-btn ih-btn--ghost ih-btn--sm" href={`/workspaces/crm/agreements?project=${encodeURIComponent(card.project_group)}`}>
              Projeyi Aç
            </Link>
          }
        >
          <dl className="crm-pd-info">
            <InfoRow label={tCard('k22a7a2f2ea')} value={projectName} dash />
            <InfoRow label={tCard('kfdd5dc6cb9')} value={address} />
            <InfoRow label={tCard('k863ba1e79c')} value={unitLabel} dash />
            {extrasUnit.map((item) => (
              <InfoRow key={`${item.label}:${item.value}`} label={item.label} value={cleanMoneyish(item.value)} />
            ))}
          </dl>
        </Card>

        <Card
          title={`Belgeler${allDocumentCount ? ` (${allDocumentCount})` : ''}`}
          testId="purchase-documents"
          className="crm-pd-card--wide"
        >
          {personId ? (
            <DocumentGallery
              documents={allDocuments}
              entityType="crm_contact"
              entityId={personId}
              canUpload={canUploadDocuments}
              canEditMeta={canUploadDocuments}
              canUnlink={false}
              canArchive={canArchiveDocuments}
              onChanged={onRefresh}
            />
          ) : (
            <p className="crm-pd-empty">Kişi kaydı bulunamadı.</p>
          )}
        </Card>

        <Card
          title={tCard('kee87b9f9b8')}
          testId="purchase-related-tasks"
          className="crm-pd-card--wide"
          action={
            <div className="crm-pd-task-actions">
              {canAct ? (
                <Button type="button" size="sm" variant="secondary" onClick={() => setShowTaskForm((value) => !value)}>
                  Görev Oluştur
                </Button>
              ) : null}
              {personId ? (
                <Link className="ih-btn ih-btn--ghost ih-btn--sm" href={`/workspaces/crm/contacts/${personId}?tab=tasks&agreement=${card.agreement_id}`}>
                  Tümünü Gör
                </Link>
              ) : null}
            </div>
          }
        >
          {showTaskForm ? (
            <form className="crm-pd-inline-form" onSubmit={submitTask}>
              <Input label={tCard('k7d4cc3d67f')} value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} />
              <Input label={tCard('k06fda6345b')} type="datetime-local" value={taskDue} onChange={(event) => setTaskDue(event.target.value)} />
              <Button type="submit" size="sm" disabled={taskMutation.isPending || !taskTitle.trim()}>
                Kaydet
              </Button>
            </form>
          ) : null}
          {tasks.length ? (
            <table className="crm-pd-table">
              <thead>
                <tr>
                  <th>{tCard('k06fda6345b')}</th>
                  <th>{tCard('k7d4cc3d67f')}</th>
                  <th>{tCard('k81be10b716')}</th>
                  <th>{tCard('kf7c81d57e2')}</th>
                  <th>{tCard('k9edaf12d30')}</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((item) => (
                  <tr key={item.id}>
                    <td>{displayDateTime(item.created_at)}</td>
                    <td>{item.title}</td>
                    <td>{kindLabel(item.kind, tFilters)}</td>
                    <td>{taskStatusLabel(item.status, tTask)}</td>
                    <td>{item.actor || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="crm-pd-empty">{tCard('k57df130e9c')}</p>
          )}
        </Card>
      </section>

      <Card
        className="crm-pd-card--wide"
        title={tCard('k033367fa8f')}
        testId="purchase-history"
      >
        <nav className="crm-pd-filters" aria-label={tCard('k33ebd88002')}>
          {HISTORY_FILTERS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={filter === item.id ? 'is-active' : undefined}
              onClick={() => setFilter(item.id)}
            >
              {tFilters(item.id)}
            </button>
          ))}
        </nav>
        {filtered.length ? (
          <div className="crm-pd-stream">
            {filtered.map((entry) =>
              entry.kind === 'email' && entry.email ? (
                <EmailCard
                  key={entry.id}
                  entry={entry.email}
                  locale="tr-TR"
                  onOpen={() => setEmailFocus(entry.email || null)}
                />
              ) : (
                <article key={entry.id} className="crm-pd-stream__item" data-kind={entry.kind}>
                  <small>
                    {kindLabel(entry.kind, tFilters)}
                    {' · '}
                    {displayDateTime(entry.created_at)}
                    {entry.actor ? ` · ${entry.actor}` : ''}
                  </small>
                  <strong>{entry.kind === 'comment' ? stripHtml(entry.summary || entry.title) || 'Yorum' : entry.title}</strong>
                  {entry.kind !== 'comment' && entry.summary ? <p>{stripHtml(entry.summary)}</p> : null}
                  {entry.kind === 'document' ? (
                    <a href={`/workspaces/crm/documents/${entry.id.replace(/^doc-/, '')}`}>{tCard('kcede6c7499')}</a>
                  ) : null}
                </article>
              ),
            )}
          </div>
        ) : (
          <p className="crm-pd-empty" data-testid="sales-history-empty">
            Bu satın almaya doğrudan bağlı geçmiş kaydı yok.
          </p>
        )}
      </Card>

      {emailFocus ? <EmailDetail entry={emailFocus} locale="tr-TR" onClose={() => setEmailFocus(null)} /> : null}
    </div>
  );
}
