'use client';

import { KnowledgeHubShell } from '../_components/knowledge-hub-shell';
import { DocumentsWorkspace } from '../../documents/_components/documents-workspace';
import { useTranslations } from 'next-intl';

export default function KnowledgeDocumentsPage() {
  const t = useTranslations('knowledge');
  return (
    <KnowledgeHubShell title={t('nav.documents')} subtitle={t('documents.subtitle')}>
      <div className="knowledge-hub__embed-docs">
        <DocumentsWorkspace />
      </div>
    </KnowledgeHubShell>
  );
}
