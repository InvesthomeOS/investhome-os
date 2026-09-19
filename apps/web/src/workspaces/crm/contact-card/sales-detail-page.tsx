'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import { Button, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { fetchPurchaseCard, type CrmPurchaseCard, type CrmPurchaseDocument } from '@/workspaces/crm/api/agreements';
import { isWhatsappEntry } from '@/workspaces/crm/contact-card/whatsapp-thread';

import './contact-card.css';
import './sales-detail.css';

const FILTERS = [
  { id: 'all', label: 'Tümü' },
  { id: 'comment', label: 'Yorumlar' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'email', label: 'E-posta' },
  { id: 'task', label: 'Görevler' },
  { id: 'document', label: 'Belgeler' },
] as const;

type TimelineFilter = (typeof FILTERS)[number]['id'];

type TimelineItem = {
  id: string;
  kind: TimelineFilter | 'meeting' | 'stage' | 'note' | 'other';
  title: string;
  summary?: string | null;
  actor?: string | null;
  created_at: string;
};

function pct(value: string | null | undefined): string {
  return value ? value.replace(/\.00$/, '') : '';
}

function displayDate(value?: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return date.toLocaleDateString('tr-TR');
}

function displayDateTime(value?: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('tr-TR');
}

const HIDDEN_FIELD = /deal|purchase card|project context|final_invoice|\bprimary\b|\bsecondary\b/i;

function visibleField(label: string, value?: string | null): boolean {
  if (!value) return false;
  return !HIDDEN_FIELD.test(label) && !HIDDEN_FIELD.test(value);
}

function Fact({ label, value }: { label: string; value?: string | null }) {
  if (!visibleField(label, value)) return null;
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function displayStage(stage?: string | null): string | null {
  if (!stage) return null;
  const value = stage.trim();
  if (!value) return null;
  if (/^(deal won|won)$/i.test(value)) return 'Kazanıldı';
  if (/^lost$/i.test(value)) return 'Kaybedildi';
  if (/final_invoice|c\d+:|[a-z0-9_]+:[a-z0-9_]+/i.test(value) && !/[çğıöşü]/i.test(value)) return null;
  if (/^[A-Z0-9_:]+$/.test(value)) return null;
  if (HIDDEN_FIELD.test(value)) return null;
  return value;
}

function ownerRole(isPrimary: boolean): string {
  return isPrimary ? 'Ana Sahip' : 'Ortak';
}

function timelineKind(activityType: string, title: string, imported?: boolean): TimelineItem['kind'] {
  const type = activityType.toLowerCase();
  if (imported || type === 'comment') return 'comment';
  if (type === 'whatsapp') return 'whatsapp';
  if (type === 'email') return 'email';
  if (type === 'task') return 'task';
  if (type.includes('meeting')) return 'meeting';
  if (type === 'system_event' || type === 'automation_event' || title.startsWith('Durum ')) return 'stage';
  if (type === 'note') return 'note';
  return 'other';
}

function kindLabel(kind: TimelineItem['kind']): string {
  if (kind === 'comment') return 'Yorum';
  if (kind === 'whatsapp') return 'WhatsApp';
  if (kind === 'email') return 'E-posta';
  if (kind === 'task') return 'Görev';
  if (kind === 'meeting') return 'Toplantı';
  if (kind === 'stage') return 'Aşama';
  if (kind === 'document') return 'Belge';
  if (kind === 'note') return 'Not';
  return 'Kayıt';
}

function matchesFilter(item: TimelineItem, filter: TimelineFilter): boolean {
  if (filter === 'all') return true;
  return item.kind === filter;
}

function buildTimeline(card: CrmPurchaseCard): TimelineItem[] {
  const items: TimelineItem[] = card.history.map((entry) => ({
    id: entry.id,
    kind: isWhatsappEntry(entry) ? 'whatsapp' : timelineKind(entry.activity_type, entry.title, entry.imported_historical_comment),
    title: entry.title,
    summary: entry.summary,
    actor: entry.actor_name,
    created_at: entry.created_at,
  }));
  for (const doc of card.documents) {
    items.push({
      id: `doc-${doc.id}`,
      kind: 'document',
      title: doc.original_file_name || doc.title,
      summary: [doc.document_type, doc.source].filter(Boolean).join(' · ') || 'Belge',
      created_at: doc.created_at || card.begin_date || card.agreement_date || new Date().toISOString(),
    });
  }
  return items.sort((a, b) => b.created_at.localeCompare(a.created_at));
}

function Documents({ documents }: { documents: CrmPurchaseDocument[] }) {
  if (!documents.length) {
    return <p>Bu satın almaya bağlı belge yok.</p>;
  }
  const groups = [
    { title: 'Satış Belgeleri', items: documents.filter((doc) => doc.source === 'Satış belgesi') },
    { title: 'E-posta / Aktivite Ekleri', items: documents.filter((doc) => doc.source === 'E-posta / Aktivite eki') },
    {
      title: 'Diğer',
      items: documents.filter((doc) => doc.source !== 'Satış belgesi' && doc.source !== 'E-posta / Aktivite eki'),
    },
  ].filter((group) => group.items.length);
  const sections = groups.length > 1 ? groups : [{ title: null, items: documents }];
  return (
    <div className="crm-sales-page__doc-groups">
      {sections.map((group) => (
        <div key={group.title || 'all'}>
          {group.title ? <h3>{group.title} <span>{group.items.length}</span></h3> : null}
          <ul className="crm-contact-card__docs">
            {group.items.map((doc) => (
              <li key={doc.id}>
                <a href={`/workspaces/crm/documents/${doc.id}`}>{doc.original_file_name || doc.title}</a>
                <small>
                  {[doc.document_type, doc.source, doc.created_at ? new Date(doc.created_at).toLocaleDateString('tr-TR') : null]
                    .filter(Boolean)
                    .join(' · ')}
                </small>
                <span className="crm-contact-card__doc-actions">
                  <a href={`/workspaces/crm/documents/${doc.id}`}>Aç / Önizle</a>
                </span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

export function SalesDetailPage({ contactId, agreementId }: { contactId: string; agreementId: string }) {
  const router = useRouter();
  const [filter, setFilter] = useState<TimelineFilter>('all');
  const query = useQuery({
    queryKey: ['crm', 'sales-detail', agreementId, contactId],
    queryFn: () => fetchPurchaseCard(agreementId, contactId),
    enabled: Boolean(agreementId),
  });

  const card = query.data;
  const isReit = card?.project_group === 'reit';
  const timeline = useMemo(() => (card ? buildTimeline(card) : []), [card]);
  const filtered = useMemo(() => timeline.filter((item) => matchesFilter(item, filter)), [timeline, filter]);
  const viewer = useMemo(() => {
    if (!card?.participants.length) return null;
    return (
      card.participants.find((item) => item.contact_id === contactId) ||
      card.participants.find((item) => item.is_primary) ||
      card.participants[0]
    );
  }, [card, contactId]);
  const stageLabel = displayStage(card?.stage);
  const headerNames = (card?.participants || []).map((item) => item.display_name).join(' + ') || card?.primary_contact_name || viewer?.display_name;
  const unitLabel = card?.unit_number && card.project_group !== 'reit' ? `Daire ${card.unit_number}` : null;
  const crumbPurchase = card?.project_group === 'reit'
    ? 'REIT'
    : card?.project_group === '1812_h_pl'
      ? ['1812 H Place', card.unit_number].filter(Boolean).join(' · ')
      : [card?.project_label, unitLabel].filter(Boolean).join(' / ');
  const waPerson = viewer;
  const comms = timeline.filter((item) => item.kind === 'whatsapp' || item.kind === 'email' || item.kind === 'comment' || item.kind === 'task' || item.kind === 'meeting' || item.kind === 'stage' || item.kind === 'note' || item.kind === 'other');

  if (query.isLoading) return <LoadingState label="Yükleniyor…" />;
  if (query.isError || !card) {
    return <ErrorState title={isReit ? 'Yatırım Detayı' : 'Satın Alma Detayı'} message={query.error?.message ?? 'Kayıt bulunamadı'} />;
  }

  const personUrl = `/workspaces/crm/contacts/${contactId}`;
  const backLabel = viewer ? `← ${viewer.display_name}'ya dön` : '← Kişiye dön';
  const whatsappEmpty = !timeline.some((item) => item.kind === 'whatsapp');
  const historyEmpty = comms.length === 0;

  return (
    <main className="dashboard crm-module-shell crm-sales-page" data-testid="sales-detail-page">
      <nav className="crm-sales-page__crumb" aria-label="Konum" data-testid="sales-breadcrumb">
        <Link href="/workspaces/crm/contacts">Kişiler</Link>
        <span>›</span>
        <Link href={personUrl}>{viewer?.display_name || 'Kişi'}</Link>
        <span>›</span>
        <Link href={personUrl}>{isReit ? 'Yatırımları / Satın Aldıkları' : 'Satın Aldıkları'}</Link>
        <span>›</span>
        <strong>{crumbPurchase}</strong>
      </nav>

      <Button className="crm-contact-card__back" type="button" variant="secondary" size="sm" onClick={() => router.push(personUrl)}>
        {backLabel}
      </Button>

      <header className="crm-verify-detail__hero crm-sales-page__hero" data-testid="sales-header">
        <p className="crm-sales-page__owners-line">{headerNames}</p>
        <div className="crm-contact-card__hero-top">
          <div>
            <p className="crm-purchase-card__project">
              {(isReit ? 'REIT' : card.project_group === '1812_h_pl' ? '1812 H PLACE' : card.project_label || '').toUpperCase()}
            </p>
            {card.unit_number && !isReit ? <p className="crm-purchase-card__unit">{`DAİRE ${card.unit_number}`}</p> : null}
            <h1>{card.amount_label || card.amount || '—'}</h1>
          </div>
          {stageLabel ? <StatusChip tone="success">{stageLabel}</StatusChip> : null}
        </div>
      </header>

      <div className="crm-sales-page__grid">
        <section className="crm-sales-page__col" data-testid="sales-left">
          <article className="crm-verify-detail__section">
            <h2>{isReit ? 'Yatırım Bilgileri' : 'Satış / Satın Alma Bilgileri'}</h2>
            <dl className="crm-contact-card__facts">
              <Fact label="Proje" value={isReit ? 'REIT' : card.project_label} />
              <Fact label="Daire" value={isReit ? null : card.unit_number} />
              <Fact label={isReit ? 'Yatırım tutarı' : 'Satın alma tutarı'} value={card.amount_label || card.amount} />
              <Fact label="Para birimi" value={card.currency} />
              <Fact label="Aşama" value={stageLabel} />
              <Fact label="Başlangıç tarihi" value={displayDate(card.begin_date || card.agreement_date)} />
              <Fact label="Kapanış tarihi" value={displayDate(card.close_date)} />
              <Fact label="Sorumlu kişi" value={card.responsible_name} />
            </dl>
            {card.comments ? <p className="crm-purchase-card__note">{card.comments}</p> : null}
          </article>

          <article className="crm-verify-detail__section" data-testid="sales-owners">
            <h2>Sahipler</h2>
            <div className="crm-verify-detail__records crm-purchase-card__owner-profiles">
              {card.participants.map((owner) => (
                <article key={owner.contact_id}>
                  <strong>
                    <Button type="button" variant="secondary" size="sm" onClick={() => router.push(`/workspaces/crm/contacts/${owner.contact_id}`)}>
                      {owner.display_name}
                    </Button>
                  </strong>
                  <small>
                    {ownerRole(owner.is_primary)}
                    {pct(owner.ownership_pct) ? ` · ${pct(owner.ownership_pct)}%` : ''}
                  </small>
                  <dl className="crm-contact-card__facts crm-contact-card__facts--compact">
                    <Fact label="Telefon" value={owner.phone} />
                    <Fact label="E-posta" value={owner.email} />
                    <Fact label="Adres" value={owner.address} />
                    <Fact label="Şirket" value={owner.company} />
                    <Fact label="Pozisyon" value={owner.position} />
                    <Fact label="Sorumlu" value={owner.responsible} />
                  </dl>
                </article>
              ))}
            </div>
          </article>

          <article className="crm-verify-detail__section" data-testid="sales-payment">
            <h2>Ödeme</h2>
            <dl className="crm-contact-card__facts">
              <Fact label="Tutar" value={String(card.payment.amount_label || card.amount_label || '')} />
              <Fact label="Aşama" value={stageLabel} />
              <Fact label="Başlangıç" value={displayDate(String(card.payment.begin_date || card.begin_date || ''))} />
              <Fact label="Kapanış" value={displayDate(String(card.payment.close_date || card.close_date || ''))} />
            </dl>
            {card.payment_fields?.length ? (
              <dl className="crm-contact-card__facts">
                {card.payment_fields.map((item) => (
                  <Fact key={`${item.label}:${item.value}`} label={item.label} value={item.value} />
                ))}
              </dl>
            ) : (
              <p className="crm-contact-card__muted">Bu satın alma için ayrı ödeme alanı doldurulmamış.</p>
            )}
          </article>

          {card.llc_name || card.llc_fields?.length ? (
            <article className="crm-verify-detail__section" data-testid="sales-llc">
              <h2>Şirket / LLC</h2>
              <dl className="crm-contact-card__facts">
                <Fact label="Şirket / LLC" value={card.llc_name} />
              </dl>
              {card.llc_fields?.filter((item) => item.value !== card.llc_name).length ? (
                <dl className="crm-contact-card__facts">
                  {card.llc_fields
                    .filter((item) => item.value !== card.llc_name)
                    .map((item) => (
                      <Fact key={`${item.label}:${item.value}`} label={item.label} value={item.value} />
                    ))}
                </dl>
              ) : null}
            </article>
          ) : null}

          {card.extra_fields?.length ? (
            <article className="crm-verify-detail__section">
              <h2>Diğer bilgiler</h2>
              <dl className="crm-contact-card__facts">
                {card.extra_fields.map((item) => (
                  <Fact key={`${item.label}:${item.value}`} label={item.label} value={item.value} />
                ))}
              </dl>
            </article>
          ) : null}

          <article className="crm-verify-detail__section" data-testid="sales-documents">
            <h2>Belgeler <span>{card.document_count}</span></h2>
            <Documents documents={card.documents} />
          </article>
        </section>

        <section className="crm-sales-page__col crm-sales-page__timeline-col" data-testid="sales-timeline">
          <article className="crm-verify-detail__section">
            <h2>Geçmiş / İletişim Akışı <span>{filtered.length}</span></h2>
            <nav className="crm-contact-card__tabs" aria-label="Geçmiş filtreleri">
              {FILTERS.map((item) => (
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

            {filter === 'whatsapp' && whatsappEmpty ? (
              <div className="crm-contact-card__wa-empty" data-testid="sales-whatsapp-empty">
                <p>Bu satın almaya doğrudan bağlı WhatsApp yazışması bulunmuyor.</p>
                {waPerson ? (
                  <Button type="button" size="sm" onClick={() => router.push(`${personUrl}?tab=whatsapp`)}>
                    {waPerson.display_name} kişisinin genel WhatsApp geçmişini aç
                  </Button>
                ) : null}
              </div>
            ) : null}

            {filter !== 'whatsapp' && historyEmpty && filter !== 'document' && !filtered.length ? (
              <p data-testid="sales-history-empty">Bu satın almaya doğrudan bağlı geçmiş kaydı yok.</p>
            ) : null}

            {filtered.length ? (
              <div className="crm-verify-detail__records crm-verify-detail__timeline crm-sales-page__timeline">
                {filtered.map((entry) => (
                  <article key={entry.id} data-kind={entry.kind}>
                    <small>
                      {kindLabel(entry.kind)}
                      {' · '}
                      {displayDateTime(entry.created_at)}
                      {entry.actor ? ` · ${entry.actor}` : ''}
                    </small>
                    <strong>{entry.title}</strong>
                    {entry.summary ? <p>{entry.summary}</p> : null}
                    {entry.kind === 'document' ? (
                      <span className="crm-contact-card__doc-actions">
                        <a href={`/workspaces/crm/documents/${entry.id.replace(/^doc-/, '')}`}>Aç / Önizle</a>
                      </span>
                    ) : null}
                  </article>
                ))}
              </div>
            ) : filter === 'document' ? (
              <p>Bu satın almaya bağlı belge yok.</p>
            ) : null}

            {filter === 'all' && whatsappEmpty && waPerson ? (
              <div className="crm-contact-card__wa-empty">
                <p>Bu satın almaya doğrudan bağlı WhatsApp yazışması bulunmuyor.</p>
                <Button type="button" size="sm" onClick={() => router.push(`${personUrl}?tab=whatsapp`)}>
                  {waPerson.display_name} kişisinin genel WhatsApp geçmişini aç
                </Button>
              </div>
            ) : null}
          </article>
        </section>
      </div>
    </main>
  );
}
