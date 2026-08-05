'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { EmptyState } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import { makeDocumentsPreview } from '../documents-demo-data';
import type { DocumentCard } from '../documents-model';
import {
  CrmDetailActionButton,
  CrmDetailMetaGrid,
  CrmDetailPanel,
  CrmEntityDetailShell,
} from '../../_components/crm-entity-detail-shell';
import '../../_components/crm-entity-detail.css';
import '../documents.css';

const DOC_TABS = [
  'preview',
  'metadata',
  'related',
  'versions',
  'timeline',
  'activity',
  'notes',
] as const;

type DocTab = (typeof DOC_TABS)[number];

function findDocument(id: string): {
  doc: DocumentCard;
  preview: ReturnType<typeof makeDocumentsPreview>;
} | null {
  const preview = makeDocumentsPreview();
  const doc = preview.documents.find((item) => item.id === id);
  if (!doc) return null;
  return { doc, preview };
}

export function CrmDocumentDetailView({
  documentId,
  listHref = '/workspaces/crm/documents',
}: {
  documentId: string;
  listHref?: string;
}) {
  const t = useTranslations('crm.documents');
  const tDetail = useTranslations('crm.documentDetail');
  const [tab, setTab] = useState<DocTab>('preview');
  const [sharedHint, setSharedHint] = useState(false);

  const resolved = useMemo(() => findDocument(documentId), [documentId]);

  if (!resolved) {
    return (
      <EmptyState
        title={tDetail('notFoundTitle')}
        description={tDetail('notFoundDescription')}
      />
    );
  }

  const { doc, preview } = resolved;
  const tabs = DOC_TABS.map((id) => ({ id, label: tDetail(`tabs.${id}`) }));

  return (
    <CrmEntityDetailShell
      testId="crm-document-detail"
      backHref={listHref}
      backLabel={tDetail('back')}
      title={doc.name}
      subtitle={`${doc.owner} · ${doc.project}`}
      eyebrow={tDetail('eyebrow')}
      avatar={
        <span className={`crm-documents__file-icon is-${doc.fileType}`} aria-hidden="true">
          <IhIcon name="documents" size={16} />
          <small>{doc.fileType.toUpperCase()}</small>
        </span>
      }
      actions={
        <>
          <CrmDetailActionButton
            variant="primary"
            onClick={() => {
              /* presentation download */
            }}
          >
            <IhIcon name="documents" size={13} />
            {tDetail('download')}
          </CrmDetailActionButton>
          <CrmDetailActionButton onClick={() => setSharedHint(true)}>
            <IhIcon name="activity" size={13} />
            {t('share')}
          </CrmDetailActionButton>
        </>
      }
      tabs={tabs}
      activeTab={tab}
      onTabChange={(id) => setTab(id as DocTab)}
    >
      {sharedHint ? (
        <p className="crm-entity-detail__empty" role="status">
          {tDetail('shareHint')}
        </p>
      ) : null}

      {tab === 'preview' ? (
        <CrmDetailPanel title={tDetail('tabs.preview')}>
          <div className="crm-entity-detail__preview">
            <IhIcon name="documents" size={28} />
            <strong>{doc.name}</strong>
            <span>
              {doc.fileType.toUpperCase()} · {doc.size} · {doc.version}
            </span>
            <span>{tDetail('previewHint')}</span>
          </div>
        </CrmDetailPanel>
      ) : null}

      {tab === 'metadata' ? (
        <CrmDetailPanel title={tDetail('tabs.metadata')}>
          <CrmDetailMetaGrid
            items={[
              { label: t('table.name'), value: doc.name },
              { label: t('table.owner'), value: doc.owner },
              { label: t('table.project'), value: doc.project },
              { label: t('table.status'), value: t(`status.${doc.status}`) },
              { label: t('meta.size'), value: doc.size },
              { label: t('meta.version'), value: doc.version },
              { label: t('meta.date'), value: doc.date },
              { label: tDetail('fileType'), value: doc.fileType.toUpperCase() },
            ]}
          />
        </CrmDetailPanel>
      ) : null}

      {tab === 'related' ? (
        <CrmDetailPanel title={tDetail('tabs.related')}>
          <CrmDetailMetaGrid
            items={[
              { label: tDetail('relatedCustomer'), value: doc.owner },
              { label: tDetail('relatedProject'), value: doc.project },
            ]}
          />
        </CrmDetailPanel>
      ) : null}

      {tab === 'versions' ? (
        <CrmDetailPanel title={tDetail('tabs.versions')}>
          <ul className="crm-entity-detail__list">
            <li>
              <IhIcon name="documents" size={14} />
              <div>
                <strong>
                  {doc.version} · {tDetail('currentVersion')}
                </strong>
                <span>{doc.date}</span>
              </div>
            </li>
            <li>
              <IhIcon name="clock" size={14} />
              <div>
                <strong>v1.0</strong>
                <span>{tDetail('initialUpload')}</span>
              </div>
            </li>
          </ul>
        </CrmDetailPanel>
      ) : null}

      {tab === 'timeline' || tab === 'activity' ? (
        <CrmDetailPanel title={tDetail(`tabs.${tab}`)}>
          <ul className="crm-entity-detail__list">
            {preview.activities.map((item) => (
              <li key={item.id}>
                <IhIcon name="activity" size={14} />
                <div>
                  <strong>{t(`rail.activity.${item.titleKey}`)}</strong>
                  <time>{t(`rail.activity.${item.timeKey}`)}</time>
                </div>
              </li>
            ))}
          </ul>
        </CrmDetailPanel>
      ) : null}

      {tab === 'notes' ? (
        <CrmDetailPanel title={tDetail('tabs.notes')}>
          <p>{tDetail('notesBody', { name: doc.name })}</p>
        </CrmDetailPanel>
      ) : null}
    </CrmEntityDetailShell>
  );
}
