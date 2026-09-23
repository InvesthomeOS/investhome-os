'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';

import { Button, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { crmLabel } from '@/lib/crm/crm-labels';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { relationshipQueries } from '@/workspaces/crm/hooks/use-relationships';

import './relationships-workspace.css';

type Props = { relationshipId: string };

const TYPE_LABELS: Record<string, string> = {
  contact_company: 'Kişi ↔ Şirket',
  investor: 'Kişi ↔ Proje / Yatırım',
  colleague: 'Kişi ↔ Kişi',
  partner: 'Ortaklık / Co-owner',
  company_project: 'Şirket ↔ Proje',
};

export function RelationshipDetailView({ relationshipId }: Props) {
  const t = useTranslations('crm.relationships.detail');
  const tTypes = useTranslations('crm.relationships.types');
  const tCategories = useTranslations('crm.relationships.categories');
  const tStatuses = useTranslations('crm.relationships.filters');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { openContact, openPurchase } = useContactCard();
  const { authLoading, canRead } = useCrmAccess();

  const detailQuery = useQuery({
    ...relationshipQueries.detail(relationshipId),
    enabled: !authLoading && canRead && Boolean(relationshipId),
  });

  if (authLoading) return <LoadingState label={tCommon('loading')} />;
  if (!canRead) return <ErrorState title={t('accessDenied')} message={t('accessDenied')} />;
  if (detailQuery.isLoading) return <LoadingState label={t('loading')} />;
  if (detailQuery.isError || !detailQuery.data) {
    return (
      <ErrorState
        title={t('loadFailed')}
        message={detailQuery.error?.message ?? t('loadFailed')}
        action={
          <Button type="button" onClick={() => void detailQuery.refetch()}>
            {t('loadFailed')}
          </Button>
        }
      />
    );
  }

  const rel = detailQuery.data;
  const typeLabel = TYPE_LABELS[rel.relationship_type] || crmLabel(tTypes, rel.relationship_type);

  const openEntity = (entityType: string, entityId: string) => {
    if (entityType === 'contact') openContact(entityId);
    else if (entityType === 'company') router.push(`/workspaces/crm/companies/${entityId}`);
    else if (rel.linked_agreement_id) openPurchase(rel.linked_agreement_id);
    else if (entityType === 'project') router.push(`/dashboard/projects/${entityId}`);
  };

  return (
    <div className="crm-relationship-detail" data-testid="crm-relationship-detail">
      <header className="crm-workspace-header">
        <div>
          <Link href="/workspaces/crm/relationships">{t('back')}</Link>
          <h1>
            {rel.source_display_name} → {rel.target_display_name}
          </h1>
          <p>{typeLabel}</p>
        </div>
      </header>

      <section className="crm-detail-overview">
        <div className="crm-detail-grid">
          <div>
            <h3>{t('source')}</h3>
            <button type="button" className="crm-rel-link" onClick={() => openEntity(rel.source_entity_type, rel.source_entity_id)}>
              {rel.source_display_name}
            </button>
          </div>
          <div>
            <h3>{t('target')}</h3>
            <button type="button" className="crm-rel-link" onClick={() => openEntity(rel.target_entity_type, rel.target_entity_id)}>
              {rel.target_display_name}
            </button>
          </div>
          <div>
            <h3>{t('category')}</h3>
            <StatusChip>{crmLabel(tCategories, rel.category)}</StatusChip>
          </div>
          <div>
            <h3>{t('status')}</h3>
            <StatusChip tone={rel.status === 'active' ? 'success' : 'default'}>
              {crmLabel(tStatuses, rel.status)}
            </StatusChip>
          </div>
          <div>
            <h3>Sorumlu</h3>
            <p>{rel.owner_name || '—'}</p>
          </div>
          <div>
            <h3>Bağlı Proje / Yatırım</h3>
            {rel.linked_agreement_id ? (
              <button type="button" className="crm-rel-link" onClick={() => openPurchase(rel.linked_agreement_id as string)}>
                {rel.linked_project_label || rel.linked_agreement_label}
              </button>
            ) : (
              <p>{rel.linked_project_label || '—'}</p>
            )}
          </div>
        </div>
        <div>
          <h3>{t('notes')}</h3>
          <p>{rel.notes || '—'}</p>
        </div>
      </section>
    </div>
  );
}
