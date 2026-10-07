'use client';

import { FormEvent, useMemo, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { useLocale } from 'next-intl';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { Button, Input, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { hasPermission } from '@/lib/api/auth';
import { linkDocument } from '@/lib/api/documents';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { createTask } from '@/workspaces/crm/api/activities';
import {
  patchAgreement,
  type CrmLabeledValue,
  type CrmPurchaseCard,
  type CrmPurchaseDocument,
} from '@/workspaces/crm/api/agreements';
import { EmailCard, EmailDetail, type EmailViewEntry } from '@/workspaces/crm/contact-card/crm-email-view';
import { DocumentGallery } from '@/workspaces/crm/contact-card/document-gallery';
import { HemenKiraToggle } from '@/workspaces/crm/contact-card/hemen-kira-toggle';
import { looksLikePayloadDump, stripHtml, taskStatusLabel } from '@/workspaces/crm/contact-card/history-html';
import { UnitHistorySection } from '@/workspaces/crm/contact-card/unit-history';
import { personCardCopy } from '@/workspaces/crm/contact-card/person-card-copy';
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

function statusLabel(raw?: string | null): string | null {
  const value = (raw || '').trim();
  if (!value) return null;
  if (/deal\s*won|^won$|^kazan[ıi]ld[ıi]$/i.test(value)) return 'Satın Alındı';
  if (/^completed$|^tamamland[ıi]$/i.test(value)) return 'Tamamlandı';
  if (/^lost$|^kaybedildi$/i.test(value)) return 'Kaybedildi';
  if (/^active$|^aktif$/i.test(value)) return 'Aktif';
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
  if (!parts.length) return '•';
  return ((parts[0][0] || '') + (parts.length > 1 ? parts[parts.length - 1][0] || '' : '')).toUpperCase();
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

function kindLabel(kind: HistoryFilter) {
  if (kind === 'comment') return 'Yorum';
  if (kind === 'email') return 'E-posta';
  if (kind === 'whatsapp') return 'WhatsApp';
  if (kind === 'meeting') return 'Toplantı';
  if (kind === 'task') return 'Görev';
  if (kind === 'document') return 'Belge';
  return 'Diğer';
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
  const t = personCardCopy(useLocale());
  const queryClient = useQueryClient();
  const { user, canCreate, canManageTasks, canViewFinancial, has } = useCrmAccess();
  const canUpdate = has('update');
  const canUploadDocuments = Boolean(user && hasPermission(user, 'documents', 'update'));
  const canArchiveDocuments = Boolean(
    user && (hasPermission(user, 'documents', 'archive') || hasPermission(user, 'documents', 'delete')),
  );
  const [filter, setFilter] = useState<HistoryFilter>('all');
  const [emailFocus, setEmailFocus] = useState<EmailViewEntry | null>(null);
  const [showMore, setShowMore] = useState(false);
  const [showDocLink, setShowDocLink] = useState(false);
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [docId, setDocId] = useState('');
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDue, setTaskDue] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [amountEdit, setAmountEdit] = useState(card.amount || card.amount_label || '');
  const [amountOk, setAmountOk] = useState(false);

  const isReit = card.project_group === 'reit';
  const stage = statusLabel(card.stage) || statusLabel(card.status) || null;
  const viewer =
    card.participants.find((item) => item.contact_id === contactId) ||
    card.participants.find((item) => item.is_primary) ||
    card.participants[0] ||
    null;
  const personId = contactId || viewer?.contact_id || card.primary_contact_id;
  const address = findLabeled(card.extra_fields, /adres|address|lokasyon|location/i);
  const projectName = isReit ? 'REIT' : card.project_label;
  const unitLabel = isReit ? null : card.unit_number;
  const amount = card.amount_label || card.amount;
  const agreementDate = displayDate(card.agreement_date || card.begin_date);
  const crumbUnit = isReit ? 'REIT' : [projectName, unitLabel].filter(Boolean).join(' / ');
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
  const showDocGroups = documentGroups.length > 1;
  const canAct = Boolean(canCreate || canManageTasks);
  const canEditAmount = Boolean(canUpdate && canViewFinancial);

  const amountMutation = useMutation({
    mutationFn: async () => {
      const next = amountEdit.trim();
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
      setError(err.message);
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
    onError: (err: Error) => setError(err.message),
  });

  const docMutation = useMutation({
    mutationFn: async () => {
      if (!docId.trim()) return;
      await linkDocument(docId.trim(), 'crm_agreement', card.agreement_id);
    },
    onSuccess: () => {
      setDocId('');
      setShowDocLink(false);
      setError(null);
      onRefresh();
    },
    onError: (err: Error) => setError(err.message),
  });

  const submitTask = (event: FormEvent) => {
    event.preventDefault();
    taskMutation.mutate();
  };
  const submitDoc = (event: FormEvent) => {
    event.preventDefault();
    docMutation.mutate();
  };

  return (
    <div className="crm-pd" data-testid={pageTestId}>
      <header className="crm-pd-pagehead">
        <nav className="crm-pd-crumb" aria-label="Konum" data-testid="sales-breadcrumb">
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
            {canUploadDocuments ? (
              <Button type="button" size="sm" variant="secondary" onClick={() => setShowDocLink((value) => !value)}>
                <IhIcon name="documents" size={14} /> Belge Ekle
              </Button>
            ) : null}
            <Button type="button" size="sm" variant="secondary" onClick={() => setShowMore((value) => !value)}>
              Diğer
            </Button>
          </div>
        </div>
        {showDocLink && canUploadDocuments ? (
          <form className="crm-pd-inline-form" onSubmit={submitDoc}>
            <Input label="Mevcut belge ID" value={docId} onChange={(event) => setDocId(event.target.value)} />
            <Button type="submit" size="sm" disabled={docMutation.isPending || !docId.trim()}>
              Belgeyi bağla
            </Button>
          </form>
        ) : null}
        {showMore ? (
          <div className="crm-pd-more">
            <HemenKiraToggle agreementId={card.agreement_id} value={Boolean(card.hemen_kira)} />
            {card.related_purchases?.length ? (
              <div className="crm-pd-related" data-testid="purchase-related">
                {card.related_purchases.map((item) => (
                  <span key={item.agreement_id}>
                    {item.project_label}
                    {item.unit_number ? ` · ${item.unit_number}` : ''}
                    {item.is_historical_unit_change ? ' (daire değişikliği)' : item.is_current ? ' (açık)' : ''}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
        {error ? <p className="crm-pd-error">{error}</p> : null}
      </header>

      <section className="crm-pd-hero" data-testid="sales-header">
        <div className="crm-pd-hero__main">
          <p className="crm-pd-hero__project" data-testid="purchase-card-project">
            {projectName}
          </p>
          {address ? <p className="crm-pd-hero__address">{address}</p> : null}
          <div className="crm-pd-hero__facts">
            <div>
              <span>{t.unit}</span>
              <strong data-testid="purchase-card-unit">{unitLabel || '—'}</strong>
            </div>
            <div>
              <span>{t.amount}</span>
              <strong data-testid="purchase-card-amount">{amount || '—'}</strong>
            </div>
            <div>
              <span>{t.status}</span>
              <StatusChip tone="success">{stage || '—'}</StatusChip>
            </div>
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
        </div>
        <UnitHistorySection steps={card.unit_history} personId={personId} viewingAgreementId={card.agreement_id} />
      </section>

      <section className="crm-pd-grid">
        <Card title={t.basics} testId="purchase-overview">
          <dl className="crm-pd-info">
            <InfoRow label="Proje / Mülk" value={projectName} dash />
            <InfoRow label="Daire Numarası" value={unitLabel} dash />
            <InfoRow label={t.purchasePrice} value={amount} dash />
            {canEditAmount ? (
              <form className="crm-pd-amount-edit" onSubmit={submitAmount} data-testid="purchase-amount-edit">
                <Input
                  label={t.editAmount}
                  value={amountEdit}
                  onChange={(event) => {
                    setAmountOk(false);
                    setAmountEdit(event.target.value);
                  }}
                />
                <Button type="submit" size="sm" disabled={amountMutation.isPending}>
                  {amountMutation.isPending ? t.saving : t.saveAmount}
                </Button>
                {amountOk ? <small data-testid="purchase-amount-saved">{t.saved}</small> : null}
              </form>
            ) : null}
            <InfoRow label={t.purchaseDate} value={agreementDate} dash />
            <InfoRow label={t.status} value={stage} dash />
            <InfoRow
              label="Owner / Ortaklar"
              value={card.participants.map((item) => item.display_name).join(', ') || card.owners_label}
              dash
            />
            <InfoRow label="Şirket" value={card.llc_name} />
            {(card.llc_fields ?? [])
              .filter((item) => !isTechnicalField(item.label, item.value) && !/llc name|şirket/i.test(item.label))
              .map((item) => (
                <InfoRow key={`llc:${item.label}:${item.value}`} label={item.label} value={item.value} />
              ))}
            <InfoRow label="Sorumlu kullanıcı" value={card.responsible_name} />
            <InfoRow label="Not" value={card.comments ? stripHtml(card.comments) : null} />
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

        <Card title="Ödeme Planı / Finansal Bilgiler" testId="purchase-payment">
          {payments.length ? (
            <>
              <ul className="crm-pd-pay">
                {payments.map((row) => (
                  <li key={`${row.label}:${row.value}`}>
                    <span>{row.label}</span>
                    <strong>{row.value}</strong>
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
            <p className="crm-pd-empty">Ödeme planı bilgisi bulunmuyor</p>
          )}
        </Card>

        <Card title="Durum ve Tarihler" testId="purchase-dates">
          <dl className="crm-pd-info">
            <InfoRow label="Durum" value={stage} dash />
            <InfoRow label="Sözleşme Tarihi" value={displayDate(card.agreement_date || card.begin_date)} />
            <InfoRow label="Tahmini / Gerçek Kapanış" value={displayDate(card.close_date)} />
            {extrasDates.map((item) => (
              <InfoRow key={`${item.label}:${item.value}`} label={item.label} value={item.value} />
            ))}
          </dl>
        </Card>

        <Card
          title="Daire / Proje Bilgileri"
          action={
            <Link className="crm-pd-link" href={`/workspaces/crm/agreements?project=${encodeURIComponent(card.project_group)}`}>
              Projeyi Aç
            </Link>
          }
        >
          <dl className="crm-pd-info">
            <InfoRow label="Proje" value={projectName} dash />
            <InfoRow label="Adres" value={address} />
            <InfoRow label="Daire" value={unitLabel} dash />
            {extrasUnit.map((item) => (
              <InfoRow key={`${item.label}:${item.value}`} label={item.label} value={cleanMoneyish(item.value)} />
            ))}
          </dl>
        </Card>

        <Card
          title={`Satın Alma Belgeleri ${
            (showDocGroups ? groupedVisible.length : purchaseDocs.length)
              ? `(${showDocGroups ? groupedVisible.length : purchaseDocs.length})`
              : ''
          }`}
          testId="purchase-documents"
          action={
            canUploadDocuments ? (
              <button type="button" onClick={() => setShowDocLink(true)}>
                Belge Ekle
              </button>
            ) : null
          }
        >
          {showDocGroups ? (
            <div className="crm-pd-doc-groups">
              {documentGroups.map((group) => {
                const visible = group.documents.filter((item) => !item.hidden_from_view);
                return (
                  <div
                    key={group.agreement_id}
                    className="crm-pd-doc-group"
                    data-testid={group.is_current ? 'current-unit-documents' : `previous-unit-documents-${group.unit_number}`}
                  >
                    <h3>
                      {group.is_current ? 'Güncel Daire Belgeleri' : 'Önceki Daire Belgeleri'} — {group.unit_number}
                    </h3>
                    {visible.length ? (
                      <DocumentGallery
                        documents={group.documents}
                        entityType="crm_agreement"
                        entityId={group.agreement_id}
                        canUpload={canUploadDocuments}
                        canEditMeta={canUploadDocuments}
                        canUnlink={canUpdate}
                        canArchive={canArchiveDocuments}
                        onChanged={onRefresh}
                      />
                    ) : (
                      <p className="crm-pd-empty">Bu daire dönemine bağlı belge yok.</p>
                    )}
                  </div>
                );
              })}
            </div>
          ) : purchaseDocs.length ? (
            <DocumentGallery
              documents={purchaseDocs as CrmPurchaseDocument[]}
              entityType="crm_agreement"
              entityId={card.agreement_id}
              canUpload={canUploadDocuments}
              canEditMeta={canUploadDocuments}
              canUnlink={canUpdate}
              canArchive={canArchiveDocuments}
              onChanged={onRefresh}
            />
          ) : (
            <p className="crm-pd-empty">Bu satın almaya bağlı belge yok.</p>
          )}
          {personDocs.length ? (
            <div className="crm-pd-person-docs" data-testid="sales-person-documents">
              <h3>Kişi Belgeleri <span>{personDocs.length}</span></h3>
              <p>Pasaport / kimlik gibi kişi belgeleri bu satın almaya ait değildir.</p>
              <DocumentGallery
                documents={personDocs}
                entityType="crm_contact"
                entityId={card.primary_contact_id}
                canUpload={canUploadDocuments}
                canEditMeta={canUploadDocuments}
                canUnlink={canUpdate}
                canArchive={canArchiveDocuments}
                onChanged={onRefresh}
              />
            </div>
          ) : null}
        </Card>

        <Card
          title="İlgili Görevler"
          testId="purchase-related-tasks"
          action={
            <>
              {canAct ? (
                <button type="button" onClick={() => setShowTaskForm((value) => !value)}>
                  Görev Oluştur
                </button>
              ) : null}
              {personId ? (
                <Link className="crm-pd-link" href={`/workspaces/crm/contacts/${personId}?tab=tasks`}>
                  Tümünü Gör
                </Link>
              ) : null}
            </>
          }
        >
          {showTaskForm ? (
            <form className="crm-pd-inline-form" onSubmit={submitTask}>
              <Input label="Görev" value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} />
              <Input label="Tarih" type="datetime-local" value={taskDue} onChange={(event) => setTaskDue(event.target.value)} />
              <Button type="submit" size="sm" disabled={taskMutation.isPending || !taskTitle.trim()}>
                Kaydet
              </Button>
            </form>
          ) : null}
          {tasks.length ? (
            <table className="crm-pd-table">
              <thead>
                <tr>
                  <th>Tarih</th>
                  <th>Görev</th>
                  <th>Tip</th>
                  <th>Durum</th>
                  <th>Sorumlu</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((item) => (
                  <tr key={item.id}>
                    <td>{displayDateTime(item.created_at)}</td>
                    <td>{item.title}</td>
                    <td>{kindLabel(item.kind)}</td>
                    <td>{taskStatusLabel(item.status)}</td>
                    <td>{item.actor || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="crm-pd-empty">Bu satın almaya bağlı görev kaydı yok.</p>
          )}
        </Card>
      </section>

      <Card
        className="crm-pd-card--wide"
        title="Satın Alma Geçmişi / İletişim Akışı"
        testId="purchase-history"
      >
        <nav className="crm-pd-filters" aria-label="Geçmiş filtreleri">
          {HISTORY_FILTERS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={filter === item.id ? 'is-active' : undefined}
              onClick={() => setFilter(item.id)}
            >
              {item.label}
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
                    {kindLabel(entry.kind)}
                    {' · '}
                    {displayDateTime(entry.created_at)}
                    {entry.actor ? ` · ${entry.actor}` : ''}
                  </small>
                  <strong>{entry.kind === 'comment' ? stripHtml(entry.summary || entry.title) || 'Yorum' : entry.title}</strong>
                  {entry.kind !== 'comment' && entry.summary ? <p>{stripHtml(entry.summary)}</p> : null}
                  {entry.kind === 'document' ? (
                    <a href={`/workspaces/crm/documents/${entry.id.replace(/^doc-/, '')}`}>Aç / Önizle</a>
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
