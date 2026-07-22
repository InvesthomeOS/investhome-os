'use client';

import { useMemo, useState } from 'react';

import {
  buildDocumentFolders,
  getDocumentsInFolder,
} from '../../_data/document-calculations';
import { DOCUMENT_CATEGORY_LABELS } from '../../_data/documents';
import type { FolderGroupMode, InvestorDocument } from '../../_data/document-types';
import { DocumentGrid } from './document-grid';

const GROUP_LABELS: Record<FolderGroupMode, string> = {
  investment: 'By Investment',
  entity: 'By Entity',
  category: 'By Category',
  year: 'By Year',
};

export interface DocumentFolderViewProps {
  documents: InvestorDocument[];
  selectedIds: string[];
  onToggleSelect: (id: string) => void;
  onPreview: (doc: InvestorDocument) => void;
  onDownload: (doc: InvestorDocument) => void;
}

export function DocumentFolderView({
  documents,
  selectedIds,
  onToggleSelect,
  onPreview,
  onDownload,
}: DocumentFolderViewProps) {
  const [groupMode, setGroupMode] = useState<FolderGroupMode>('investment');
  const [folderKey, setFolderKey] = useState<string | null>(null);

  const folders = useMemo(
    () => buildDocumentFolders(documents, groupMode, folderKey),
    [documents, groupMode, folderKey],
  );

  const folderDocs = useMemo(() => {
    if (!folderKey) return [];
    return getDocumentsInFolder(documents, groupMode, folderKey);
  }, [documents, groupMode, folderKey]);

  const folderName = useMemo(() => {
    if (!folderKey) return null;
    if (groupMode === 'category') return DOCUMENT_CATEGORY_LABELS[folderKey as keyof typeof DOCUMENT_CATEGORY_LABELS] ?? folderKey;
    return folderKey;
  }, [folderKey, groupMode]);

  return (
    <div className="inv-docs__folder-view">
      <div className="inv-docs__folder-toolbar">
        <div className="inv-docs__folder-modes" role="tablist" aria-label="Folder grouping">
          {(Object.keys(GROUP_LABELS) as FolderGroupMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              role="tab"
              aria-selected={groupMode === mode}
              className={`inv-docs__folder-mode${groupMode === mode ? ' inv-docs__folder-mode--active' : ''}`}
              onClick={() => {
                setGroupMode(mode);
                setFolderKey(null);
              }}
            >
              {GROUP_LABELS[mode]}
            </button>
          ))}
        </div>
      </div>

      <nav className="inv-docs__breadcrumbs" aria-label="Folder breadcrumbs">
        <button type="button" onClick={() => setFolderKey(null)}>
          All Folders
        </button>
        {folderKey ? (
          <>
            <span aria-hidden="true"> / </span>
            <span aria-current="page">{folderName}</span>
          </>
        ) : null}
      </nav>

      {!folderKey ? (
        <div className="inv-docs__folder-grid">
          {folders.map((folder) => (
            <button
              key={folder.id}
              type="button"
              className="inv-docs__folder-card"
              onClick={() => setFolderKey(folder.groupKey)}
            >
              <span className="inv-docs__folder-icon" aria-hidden="true">
                📁
              </span>
              <span className="inv-docs__folder-name">{folder.name}</span>
              <span className="inv-docs__folder-count">{folder.documentCount} documents</span>
            </button>
          ))}
        </div>
      ) : (
        <DocumentGrid
          documents={folderDocs}
          selectedIds={selectedIds}
          onToggleSelect={onToggleSelect}
          onPreview={onPreview}
          onDownload={onDownload}
        />
      )}
    </div>
  );
}
