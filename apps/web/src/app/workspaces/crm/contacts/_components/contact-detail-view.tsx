'use client';

import { useState } from 'react';
import type { Route } from 'next';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { canArchiveCrm, canUpdateCrm, canViewPrivateNotes } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { archiveContact, restoreContact } from '@/workspaces/crm/api/contacts';
import { contactQueries, contactQueryKeys } from '@/workspaces/crm/hooks/use-contacts';
import type { CrmContactDetail } from '@/workspaces/crm/types';

import { ContactJourneyTimeline } from './contact-journey-timeline';

type ContactDetailTab =
  | 'overview'
  | 'journey'
  | 'opportunities'
  | 'matches'
  | 'docs'
  | 'activity'
  | 'details';

type ContactDetailPreview = {
  contact: CrmContactDetail;
  initialTab?: ContactDetailTab;
  canViewInternalNotes?: boolean;
  referenceHandoff?: boolean;
  journeyHref?: Route;
};

type ContactDetailViewProps = {
  contactId: string;
  preview?: ContactDetailPreview;
};

type ContactDetailPresentationProps = {
  contact: CrmContactDetail;
  initialTab?: ContactDetailTab;
  canViewInternalNotes: boolean;
  canArchive?: boolean;
  canRestore?: boolean;
  onArchive?: () => void;
  onRestore?: () => void;
  referenceHandoff?: boolean;
  journeyHref?: Route;
};

type ProfileCopy = {
  back: string;
  owner: string;
  tabs: Record<ContactDetailTab, string>;
  call: string;
  whatsapp: string;
  email: string;
  schedule: string;
  matchUnits: string;
  nextAction: string;
  followUpProposal: string;
  dueToday: string;
  proposalHint: string;
  activeOpportunity: string;
  proposal: string;
  updated: string;
  preferenceSnapshot: string;
  preferenceMeta: string;
  about: string;
  source: string;
  firstContact: string;
  language: string;
  nationality: string;
  notes: string;
  turkish: string;
  turkey: string;
};

const PROFILE_COPY: Record<'en' | 'tr', ProfileCopy> = {
  en: {
    back: 'Back to leads',
    owner: 'Owner',
    tabs: {
      overview: 'Overview',
      journey: 'Journey',
      opportunities: 'Opportunities',
      matches: 'Matches',
      docs: 'Docs',
      activity: 'Activity',
      details: 'Details',
    },
    call: 'Call',
    whatsapp: 'WhatsApp',
    email: 'Email',
    schedule: 'Schedule',
    matchUnits: 'Match units',
    nextAction: 'Next action',
    followUpProposal: 'Follow up proposal',
    dueToday: 'Due today',
    proposalHint: 'Prepare proposal and send terms by end of day.',
    activeOpportunity: 'Active opportunity',
    proposal: 'Proposal',
    updated: 'Updated 2 hours ago',
    preferenceSnapshot: 'Preference snapshot',
    preferenceMeta: 'Residential  ·  Kadıköy, Ataşehir',
    about: 'About Ada',
    source: 'Source',
    firstContact: 'First contact',
    language: 'Language',
    nationality: 'Nationality',
    notes: 'Notes',
    turkish: 'Turkish',
    turkey: 'Turkey',
  },
  tr: {
    back: 'Adaylara dön',
    owner: 'Sorumlu',
    tabs: {
      overview: 'Genel Bakış',
      journey: 'Yolculuk',
      opportunities: 'Fırsatlar',
      matches: 'Eşleşmeler',
      docs: 'Belgeler',
      activity: 'Aktivite',
      details: 'Detaylar',
    },
    call: 'Ara',
    whatsapp: 'WhatsApp',
    email: 'E-posta',
    schedule: 'Planla',
    matchUnits: 'Ünite eşleştir',
    nextAction: 'Sonraki aksiyon',
    followUpProposal: 'Teklif takibi',
    dueToday: 'Bugün',
    proposalHint: 'Teklifi hazırlayın ve koşulları gün sonuna kadar gönderin.',
    activeOpportunity: 'Aktif fırsat',
    proposal: 'Teklif',
    updated: '2 saat önce güncellendi',
    preferenceSnapshot: 'Tercih özeti',
    preferenceMeta: 'Konut  ·  Kadıköy, Ataşehir',
    about: 'Ada hakkında',
    source: 'Kaynak',
    firstContact: 'İlk temas',
    language: 'Dil',
    nationality: 'Uyruk',
    notes: 'Notlar',
    turkish: 'Türkçe',
    turkey: 'Türkiye',
  },
};

const TAB_ICONS: Record<ContactDetailTab, IhIconName> = {
  overview: 'executive',
  journey: 'activity',
  opportunities: 'target',
  matches: 'inventory',
  docs: 'documents',
  activity: 'clock',
  details: 'roles',
};

function ContactDetailPresentation({
  contact,
  initialTab = 'overview',
  canViewInternalNotes,
  canArchive = false,
  canRestore = false,
  onArchive,
  onRestore,
  referenceHandoff = false,
  journeyHref = `/workspaces/crm/contacts/${contact.id}/journey` as Route,
}: ContactDetailPresentationProps) {
  const locale = useLocale();
  const router = useRouter();
  const copy = PROFILE_COPY[referenceHandoff || !locale.startsWith('tr') ? 'en' : 'tr'];
  const [activeTab, setActiveTab] = useState<ContactDetailTab>(initialTab);
  const initials = [contact.first_name, contact.last_name]
    .filter((value): value is string => Boolean(value))
    .map((value) => value.slice(0, 1))
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return (
    <div
      className={`crm-contact-detail crm-contact-profile${referenceHandoff ? ' crm-contact-profile--reference' : ''}`}
      data-testid="crm-g2-contact-detail"
    >
      <div className="crm-contact-profile__topline">
        <button type="button" className="crm-contact-profile__back" onClick={() => window.history.back()}>
          <IhIcon name="chevronLeft" size={13} />
          {copy.back}
        </button>
        <div className="crm-contact-profile__record-nav">
          <button type="button" aria-label="Previous customer"><IhIcon name="chevronLeft" size={14} /></button>
          <button type="button" aria-label="Next customer"><IhIcon name="chevronRight" size={14} /></button>
          <button
            type="button"
            aria-label={canRestore ? 'Restore customer' : canArchive ? 'Archive customer' : 'More customer actions'}
            onClick={canRestore ? onRestore : canArchive ? onArchive : undefined}
          >
            <span aria-hidden="true">⋮</span>
          </button>
        </div>
      </div>

      <header className="crm-contact-profile__hero">
        <div className="crm-contact-profile__identity">
          <span className="crm-contact-profile__portrait" aria-label={`${contact.display_name} avatar`}>
            <span aria-hidden="true">{initials || 'AY'}</span>
          </span>
          <div className="crm-contact-profile__identity-copy">
            <div className="crm-contact-profile__name-row">
              <h1>{contact.display_name}</h1>
              <span className="crm-contact-profile__tag crm-contact-profile__tag--lead">Lead</span>
              <span className="crm-contact-profile__tag crm-contact-profile__tag--buyer">Buyer</span>
            </div>
            <p><IhIcon name="meeting" size={14} /><span>{contact.primary_phone ?? '—'}</span></p>
            <p><IhIcon name="inbox" size={14} /><span>{contact.primary_email ?? '—'}</span></p>
            <p>
              <IhIcon name="user" size={14} />
              <span>{copy.owner}</span>
              <strong>{contact.owner_name ?? '—'}</strong>
            </p>
          </div>
        </div>
        <div className="crm-contact-profile__quick-actions" aria-label="Customer quick actions">
          <button type="button"><IhIcon name="meeting" size={14} />{copy.call}</button>
          <button type="button"><IhIcon name="activity" size={14} />{copy.whatsapp}</button>
          <button type="button"><IhIcon name="inbox" size={14} />{copy.email}</button>
          <button type="button"><IhIcon name="calendar" size={14} />{copy.schedule}</button>
          <button type="button" className="crm-contact-profile__match-action">
            <IhIcon name="sparkles" size={14} />{copy.matchUnits}
          </button>
        </div>
      </header>

      <div className="crm-contact-profile__tabs" role="tablist" aria-label="Customer profile sections">
        {(Object.keys(copy.tabs) as ContactDetailTab[]).map((tabId) => (
          <button
            key={tabId}
            type="button"
            role="tab"
            aria-selected={activeTab === tabId}
            className={activeTab === tabId ? 'is-active' : undefined}
            onClick={() => {
              if (tabId === 'journey') {
                router.push(journeyHref);
                return;
              }
              setActiveTab(tabId);
            }}
          >
            <IhIcon name={TAB_ICONS[tabId]} size={13} />
            {copy.tabs[tabId]}
          </button>
        ))}
      </div>

      {activeTab === 'overview' ? (
        <>
          <section className="crm-contact-profile__kpis" aria-label="Customer summary">
            <article>
              <span className="crm-contact-profile__kpi-icon crm-contact-profile__kpi-icon--a"><IhIcon name="calendar" size={20} /></span>
              <div>
                <p>{copy.nextAction}</p>
                <h2>{copy.followUpProposal}</h2>
                <span className="crm-contact-profile__status">{copy.dueToday}</span>
                <small>{copy.proposalHint}</small>
              </div>
            </article>
            <article>
              <span className="crm-contact-profile__kpi-icon crm-contact-profile__kpi-icon--b"><IhIcon name="projects" size={20} /></span>
              <div>
                <p>{copy.activeOpportunity}</p>
                <h2>North Towers A-1204</h2>
                <span className="crm-contact-profile__status crm-contact-profile__status--info">{copy.proposal}</span>
                <strong>8.750.000 TRY</strong>
                <small>{copy.updated}</small>
              </div>
            </article>
            <article>
              <span className="crm-contact-profile__kpi-icon crm-contact-profile__kpi-icon--c"><IhIcon name="settings" size={20} /></span>
              <div>
                <p>{copy.preferenceSnapshot}</p>
                <h2>2+1&nbsp;&nbsp;•&nbsp;&nbsp;8–12M TRY</h2>
                <small>{copy.preferenceMeta}</small>
                <small>New build&nbsp;&nbsp;•&nbsp;&nbsp;High floor</small>
              </div>
            </article>
          </section>

          <div className="crm-contact-profile__lower-grid">
            <ContactJourneyTimeline
              canViewInternalNotes={canViewInternalNotes}
              variant="profile"
              localeOverride={referenceHandoff ? 'en' : undefined}
              onViewFullJourney={() => router.push(journeyHref)}
            />
            <aside className="crm-contact-profile__about" aria-labelledby="crm-contact-about-title">
              <h2 id="crm-contact-about-title">{copy.about}</h2>
              <dl>
                <div><dt>{copy.source}</dt><dd>{contact.source ?? 'Website inquiry'}</dd></div>
                <div><dt>{copy.firstContact}</dt><dd>May 20, 2025</dd></div>
                <div><dt>{copy.language}</dt><dd>{copy.turkish}</dd></div>
                <div><dt>{copy.nationality}</dt><dd>{copy.turkey} <span aria-label="Turkey flag">🇹🇷</span></dd></div>
                <div><dt>{copy.notes}</dt><dd>{contact.notes ?? '—'}</dd></div>
              </dl>
            </aside>
          </div>
        </>
      ) : null}

      {activeTab === 'journey' ? (
        <ContactJourneyTimeline
          canViewInternalNotes={canViewInternalNotes}
          localeOverride={referenceHandoff ? 'en' : undefined}
        />
      ) : null}
      {!['overview', 'journey'].includes(activeTab) ? (
        <EmptyState title={copy.tabs[activeTab]} description="No profile records in this local presentation." />
      ) : null}
    </div>
  );
}

function ContactDetailLiveView({ contactId }: { contactId: string }) {
  const t = useTranslations('crm.contacts.detail');
  const tCommon = useTranslations('common');
  const { authLoading, user, canRead } = useCrmAccess();
  const queryClient = useQueryClient();
  const detailQuery = useQuery({
    ...contactQueries.detail(contactId),
    enabled: !authLoading && canRead,
  });

  const actionMutation = useMutation({
    mutationFn: async (action: 'archive' | 'restore') =>
      action === 'archive' ? archiveContact(contactId) : restoreContact(contactId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: contactQueryKeys.detail(contactId) });
    },
  });

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canRead) {
    return <EmptyState title={t('accessDenied')} description={t('accessDeniedHint')} />;
  }

  if (detailQuery.isLoading) {
    return <LoadingState label={t('loading')} />;
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <ErrorState
        title={t('loadError')}
        message={detailQuery.error?.message ?? t('loadError')}
        action={
          <Button type="button" onClick={() => void detailQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  const contact = detailQuery.data;

  return (
    <ContactDetailPresentation
      contact={contact}
      canViewInternalNotes={canViewPrivateNotes(user)}
      canArchive={canArchiveCrm(user)}
      canRestore={canUpdateCrm(user)}
      onArchive={() => actionMutation.mutate('archive')}
      onRestore={() => actionMutation.mutate('restore')}
    />
  );
}

export function ContactDetailView({ contactId, preview }: ContactDetailViewProps) {
  if (preview) {
    return (
      <ContactDetailPresentation
        contact={preview.contact}
        initialTab={preview.initialTab}
        canViewInternalNotes={preview.canViewInternalNotes ?? true}
        referenceHandoff={preview.referenceHandoff}
        journeyHref={preview.journeyHref}
      />
    );
  }

  return <ContactDetailLiveView contactId={contactId} />;
}
