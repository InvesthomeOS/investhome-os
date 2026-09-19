'use client';

import { useEffect, useMemo, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import { Button, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { fetchPurchaseCard, type CrmLabeledValue } from '@/workspaces/crm/api/agreements';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { sortWhatsappConversation, WhatsAppThread } from '@/workspaces/crm/contact-card/whatsapp-thread';

import './contact-card.css';

const TABS = [
  { id: 'overview', label: 'Özet' },
  { id: 'history', label: 'Geçmiş' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'documents', label: 'Belgeler' },
  { id: 'payment', label: 'Ödeme' },
  { id: 'owners', label: 'Sahipler' },
] as const;

type PurchaseTab = (typeof TABS)[number]['id'];

function requestedTab(): PurchaseTab {
  if (typeof window === 'undefined') return 'overview';
  const value = new URLSearchParams(window.location.search).get('tab');
  return TABS.some((item) => item.id === value) ? (value as PurchaseTab) : 'overview';
}

function pct(value: string | null | undefined): string {
  return value ? value.replace(/\.00$/, '') : '';
}

function shortOwners(label: string | null | undefined): string {
  if (!label) return '';
  return label
    .split('+')
    .map((name) => name.trim().split(/\s+/)[0])
    .filter(Boolean)
    .join(' + ');
}

function purchaseLine(item: {
  project_label: string;
  unit_number: string | null;
  amount_label: string | null;
  owners_label: string | null;
}): string {
  const parts = [item.project_label];
  if (item.unit_number) parts.push(item.unit_number);
  if (item.amount_label) parts.push(item.amount_label.replace(' USD', ''));
  const owners = shortOwners(item.owners_label);
  if (owners.includes('+')) parts.push(owners);
  return parts.join(' · ');
}

function displayDate(value?: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return date.toLocaleDateString('tr-TR');
}

function Fact({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function FieldList({ items }: { items?: CrmLabeledValue[] | null }) {
  if (!items?.length) return null;
  return (
    <dl className="crm-contact-card__facts">
      {items.map((item) => (
        <Fact key={`${item.label}:${item.value}`} label={item.label} value={item.value} />
      ))}
    </dl>
  );
}

export function PurchaseCard({ agreementId }: { agreementId: string }) {
  const { openContact, openPurchase, closePurchase } = useContactCard();
  const router = useRouter();
  const pathname = usePathname();
  const [tab, setTab] = useState<PurchaseTab>('overview');
  const fromContactId = pathname?.match(/\/contacts\/([0-9a-fA-F-]{36})/)?.[1] || null;

  useEffect(() => {
    setTab(requestedTab());
  }, [agreementId]);
  const query = useQuery({
    queryKey: ['crm', 'purchases', agreementId, fromContactId],
    queryFn: () => fetchPurchaseCard(agreementId, fromContactId),
    enabled: Boolean(agreementId),
  });

  const card = query.data;
  const whatsappMessages = useMemo(
    () => sortWhatsappConversation(card?.history ?? []),
    [card?.history],
  );
  const viewer = useMemo(() => {
    if (!card?.participants.length) return null;
    return (
      card.participants.find((item) => item.contact_id === fromContactId) ||
      card.participants.find((item) => item.is_primary) ||
      card.participants[0]
    );
  }, [card, fromContactId]);
  const stageLabel = card?.stage && !/^[A-Z0-9_:]+$/.test(card.stage) ? card.stage : null;
  const purchaseTitle = [card?.project_label, card?.unit_number ? `Unit ${card.unit_number}` : null]
    .filter(Boolean)
    .join(' / ');

  if (query.isLoading) return <LoadingState label="Loading…" />;
  if (query.isError || !card) {
    return <ErrorState title="Satın alma" message={query.error?.message ?? 'Purchase unavailable'} />;
  }

  const backToPerson = () => {
    if (fromContactId) {
      closePurchase();
      return;
    }
    if (viewer?.contact_id) {
      router.push(`/workspaces/crm/contacts/${viewer.contact_id}`);
    }
  };

  return (
    <div className="crm-verify-detail crm-contact-card crm-purchase-card" data-testid="purchase-card">
      <header className="crm-verify-detail__hero crm-contact-card__hero">
        {viewer ? (
          <nav className="crm-purchase-card__crumb" aria-label="Konum" data-testid="purchase-breadcrumb">
            <button type="button" onClick={backToPerson}>
              {viewer.display_name}
            </button>
            <span>›</span>
            <span>Satın Aldıkları</span>
            <span>›</span>
            <strong>{purchaseTitle || card.project_label}</strong>
          </nav>
        ) : null}
        <Button
          className="crm-contact-card__back"
          type="button"
          variant="secondary"
          size="sm"
          data-testid="purchase-back-person"
          onClick={backToPerson}
        >
          {viewer ? `← ${viewer.display_name}'ya dön` : '← Kişiye dön'}
        </Button>
        <div className="crm-contact-card__hero-top">
          <div>
            <p className="crm-purchase-card__project" data-testid="purchase-card-project">
              {(card.project_label || card.project_group || '').toUpperCase()}
            </p>
            {card.unit_number ? (
              <p className="crm-purchase-card__unit" data-testid="purchase-card-unit">
                UNIT {card.unit_number}
              </p>
            ) : null}
            <h1 data-testid="purchase-card-amount">{card.amount_label || card.amount || '—'}</h1>
          </div>
          <StatusChip tone="success">{stageLabel || '—'}</StatusChip>
        </div>
        <section className="crm-purchase-card__owners" data-testid="purchase-card-owners">
          <h2>Sahipler</h2>
          <ul>
            {card.participants.map((owner) => (
              <li key={owner.contact_id}>
                <button type="button" onClick={() => openContact(owner.contact_id)}>
                  {owner.display_name}
                </button>
                <span>{pct(owner.ownership_pct) ? `— ${pct(owner.ownership_pct)}%` : ''}</span>
              </li>
            ))}
          </ul>
        </section>
        {card.related_purchases?.length ? (
          <section className="crm-purchase-card__related" data-testid="purchase-related">
            <h2>SATIN ALDIKLARI</h2>
            <div className="crm-purchase-list">
              {card.related_purchases.map((item) => (
                <article
                  key={item.agreement_id}
                  className={`crm-purchase-list__item${item.is_current ? ' is-active' : ''}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => openPurchase(item.agreement_id)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      openPurchase(item.agreement_id);
                    }
                  }}
                >
                  <strong>{purchaseLine(item)}</strong>
                  {item.is_current ? (
                    <small className="crm-purchase-list__active">AKTİF / AÇIK SATIN ALMA</small>
                  ) : null}
                </article>
              ))}
            </div>
          </section>
        ) : null}
      </header>

      <nav className="crm-contact-card__tabs" aria-label="Satın alma sekmeleri">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={tab === item.id ? 'is-active' : undefined}
            data-testid={`purchase-tab-${item.id}`}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {tab === 'overview' ? (
        <section className="crm-verify-detail__section" data-testid="purchase-overview">
          <h2>SATIN ALMA</h2>
          <dl className="crm-contact-card__facts">
            <Fact label="Proje" value={card.project_label} />
            <Fact label="Daire" value={card.unit_number} />
            <Fact label="Tutar" value={card.amount_label || card.amount} />
            <Fact label="Para birimi" value={card.currency} />
            <Fact label="Aşama" value={stageLabel} />
            <Fact label="Satın alma tarihi" value={displayDate(card.agreement_date || card.begin_date)} />
            <Fact label="Kapanış tarihi" value={displayDate(card.close_date)} />
            <Fact label="Sorumlu" value={card.responsible_name} />
          </dl>
          <FieldList items={card.extra_fields} />
          {card.comments ? <p className="crm-purchase-card__note">{card.comments}</p> : null}

          {card.llc_name || card.llc_fields?.length ? (
            <>
              <h2>Şirket / LLC</h2>
              <dl className="crm-contact-card__facts">
                <Fact label="Şirket / LLC" value={card.llc_name} />
              </dl>
              <FieldList items={card.llc_fields?.filter((item) => item.value !== card.llc_name)} />
            </>
          ) : null}

          <h2>SAHİPLER</h2>
          <div className="crm-verify-detail__records crm-purchase-card__owner-profiles">
            {card.participants.map((owner) => (
              <article key={owner.contact_id} data-testid={`purchase-owner-${owner.contact_id}`}>
                <strong>
                  <Button type="button" variant="secondary" size="sm" onClick={() => openContact(owner.contact_id)}>
                    {owner.display_name}
                  </Button>
                </strong>
                <small>
                  {owner.is_primary ? 'Ana Sahip' : 'Ortak'}
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
        </section>
      ) : null}

      {tab === 'history' ? (
        <section className="crm-verify-detail__section" data-testid="purchase-history">
          <h2>Geçmiş <span>{card.history_count}</span></h2>
          {card.history.length ? (
            <div className="crm-verify-detail__records crm-verify-detail__timeline">
              {card.history.map((entry) => (
                <article key={entry.id}>
                  <strong>{entry.title}</strong>
                  <small>
                    {new Date(entry.created_at).toLocaleString()}
                    {entry.actor_name ? ` · ${entry.actor_name}` : ''}
                  </small>
                  {entry.summary ? <p>{entry.summary}</p> : null}
                </article>
              ))}
            </div>
          ) : (
            <p data-testid="purchase-history-empty">Bu satın almaya bağlı geçmiş kaydı yok.</p>
          )}
        </section>
      ) : null}

      {tab === 'whatsapp' ? (
        <section className="crm-verify-detail__section" data-testid="purchase-whatsapp">
          <h2>WhatsApp <span>{whatsappMessages.length}</span></h2>
          {whatsappMessages.length ? (
            <WhatsAppThread messages={whatsappMessages} testId="purchase-whatsapp-thread" />
          ) : (
            <div className="crm-contact-card__wa-empty" data-testid="purchase-whatsapp-empty">
              <p>Bu satın almaya doğrudan bağlı WhatsApp yazışması bulunmuyor.</p>
              <div className="crm-purchase-card__wa-actions">
                {card.participants.length > 1 ? (
                  <>
                    {card.participants
                      .filter((owner) => owner.is_primary)
                      .map((owner) => (
                        <Button
                          key={`wa-${owner.contact_id}`}
                          type="button"
                          size="sm"
                          data-testid="open-person-whatsapp"
                          onClick={() => router.push(`/workspaces/crm/contacts/${owner.contact_id}?tab=whatsapp`)}
                        >
                          {`${owner.display_name} WhatsApp geçmişi`}
                        </Button>
                      ))}
                    {card.participants
                      .filter((owner) => !owner.is_primary)
                      .map((owner) => (
                        <Button
                          key={`person-${owner.contact_id}`}
                          type="button"
                          size="sm"
                          variant="secondary"
                          data-testid="open-coowner-person"
                          onClick={() => openContact(owner.contact_id)}
                        >
                          {`${owner.display_name} kişi kartı`}
                        </Button>
                      ))}
                  </>
                ) : viewer ? (
                  <Button
                    type="button"
                    size="sm"
                    data-testid="open-person-whatsapp"
                    onClick={() => router.push(`/workspaces/crm/contacts/${viewer.contact_id}?tab=whatsapp`)}
                  >
                    {`${viewer.display_name} WhatsApp geçmişi`}
                  </Button>
                ) : null}
              </div>
            </div>
          )}
        </section>
      ) : null}

      {tab === 'documents' ? (
        <section className="crm-verify-detail__section" data-testid="purchase-documents">
          <h2>Belgeler <span>{card.document_count}</span></h2>
          {card.documents.length ? (
            <ul className="crm-contact-card__docs">
              {card.documents.map((doc) => (
                <li key={doc.id}>
                  <a href={`/workspaces/crm/documents/${doc.id}`}>{doc.original_file_name || doc.title}</a>
                  <small>
                    {[doc.document_type, doc.source, doc.created_at ? new Date(doc.created_at).toLocaleDateString() : null]
                      .filter(Boolean)
                      .join(' · ')}
                  </small>
                  <span className="crm-contact-card__doc-actions">
                    <a href={`/workspaces/crm/documents/${doc.id}`}>Aç / Önizle</a>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p>Bu satın almaya bağlı belge yok.</p>
          )}
        </section>
      ) : null}

      {tab === 'payment' ? (
        <section className="crm-verify-detail__section" data-testid="purchase-payment">
          <h2>Ödeme</h2>
          <dl className="crm-contact-card__facts">
            <Fact label="Tutar" value={String(card.payment.amount_label || card.amount_label || '')} />
            <Fact label="Aşama" value={stageLabel} />
            <Fact label="Başlangıç" value={displayDate(String(card.payment.begin_date || card.begin_date || ''))} />
            <Fact label="Kapanış" value={displayDate(String(card.payment.close_date || card.close_date || ''))} />
            <Fact label="Kapora" value={card.payment.kapora ? String(card.payment.kapora) : null} />
            <Fact label="Peşinat" value={card.payment.deposit ? String(card.payment.deposit) : null} />
          </dl>
          <FieldList items={card.payment_fields} />
        </section>
      ) : null}

      {tab === 'owners' ? (
        <section className="crm-verify-detail__section" data-testid="purchase-owners">
          <h2>Sahipler</h2>
          <div className="crm-verify-detail__records crm-purchase-card__owner-profiles">
            {card.participants.map((owner) => (
              <article key={owner.contact_id}>
                <strong>
                  <Button type="button" variant="secondary" size="sm" onClick={() => openContact(owner.contact_id)}>
                    {owner.display_name}
                  </Button>
                </strong>
                <small>
                  {owner.is_primary ? 'Ana Sahip' : 'Ortak'}
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
        </section>
      ) : null}
    </div>
  );
}
