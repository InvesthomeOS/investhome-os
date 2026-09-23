'use client';

import { useMemo, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  Button,
  EmptyState,
  Input,
  SegmentedControl,
  Select,
  StatusChip,
} from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  FILE_TYPE_ICON,
  type FileCategoryKey,
  type FileRecord,
  type FileRelatedKind,
  type FileTypeKey,
  type FileViewMode,
  type FilesWorkspacePreview,
} from '../files-model';

type FilterKey = 'search' | 'category' | 'related' | 'type';

function FileTypeIcon({ type }: { type: FileTypeKey }) {
  return (
    <span className={`crm-files__type-icon is-${type}`} aria-hidden="true">
      <IhIcon name={FILE_TYPE_ICON[type]} size={14} />
      <small>{type.toUpperCase()}</small>
    </span>
  );
}

function RelatedLabel({
  kind,
  name,
  label,
}: {
  kind: FileRelatedKind;
  name: string;
  label: string;
}) {
  return (
    <span className="crm-files__related">
      <IhIcon
        name={kind === 'project' ? 'projects' : kind === 'investor' ? 'target' : 'user'}
        size={12}
      />
      <span>
        {label} · {name}
      </span>
    </span>
  );
}

function FileCard({
  file,
  t,
}: {
  file: FileRecord;
  t: ReturnType<typeof useTranslations<'crm.files'>>;
}) {
  return (
    <article className="crm-files__card" data-testid={`file-card-${file.id}`}>
      <header className="crm-files__card-header">
        <FileTypeIcon type={file.fileType} />
        <div className="crm-files__card-identity">
          <h3 title={file.name}>{file.name}</h3>
          <RelatedLabel
            kind={file.relatedKind}
            name={file.relatedName}
            label={t(`related.${file.relatedKind}`)}
          />
        </div>
        <StatusChip tone="info" className="crm-files__version">
          {file.version}
        </StatusChip>
      </header>
      <dl className="crm-files__meta">
        <div>
          <dt>{t('meta.category')}</dt>
          <dd>{t(`categories.${file.category}`)}</dd>
        </div>
        <div>
          <dt>{t('meta.size')}</dt>
          <dd>{file.size}</dd>
        </div>
        <div>
          <dt>{t('meta.updated')}</dt>
          <dd>{file.updatedAt}</dd>
        </div>
      </dl>
      <footer className="crm-files__card-footer">
        <span className="crm-files__owner">{file.owner}</span>
      </footer>
    </article>
  );
}

function FileRow({
  file,
  t,
}: {
  file: FileRecord;
  t: ReturnType<typeof useTranslations<'crm.files'>>;
}) {
  return (
    <tr data-testid={`file-row-${file.id}`}>
      <td>
        <div className="crm-files__row-name">
          <FileTypeIcon type={file.fileType} />
          <strong title={file.name}>{file.name}</strong>
        </div>
      </td>
      <td>{t(`categories.${file.category}`)}</td>
      <td>
        <RelatedLabel
          kind={file.relatedKind}
          name={file.relatedName}
          label={t(`related.${file.relatedKind}`)}
        />
      </td>
      <td>
        <StatusChip tone="info" className="crm-files__version">
          {file.version}
        </StatusChip>
      </td>
      <td>{file.size}</td>
      <td>{file.updatedAt}</td>
    </tr>
  );
}

export function CrmFilesWorkspace({ preview }: { preview: FilesWorkspacePreview }) {
  const t = useTranslations('crm.files');
  const uploadRef = useRef<HTMLInputElement>(null);
  const [view, setView] = useState<FileViewMode>('grid');
  const [toast, setToast] = useState<string | null>(null);
  const [filters, setFilters] = useState<Record<FilterKey, string>>({
    search: '',
    category: 'all',
    related: '',
    type: '',
  });
  const [files, setFiles] = useState(preview.files);

  const filtered = useMemo(() => {
    return files.filter((file) => {
      if (filters.category !== 'all' && file.category !== filters.category) return false;
      if (filters.related && file.relatedKind !== filters.related) return false;
      if (filters.type && file.fileType !== filters.type) return false;
      if (filters.search) {
        const q = filters.search.trim().toLowerCase();
        if (
          !file.name.toLowerCase().includes(q) &&
          !file.relatedName.toLowerCase().includes(q) &&
          !file.owner.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      return true;
    });
  }, [files, filters]);

  const recentFiles = useMemo(
    () => filtered.filter((f) => preview.recentIds.includes(f.id) || f.recent).slice(0, 4),
    [filtered, preview.recentIds],
  );

  const categoryCounts = useMemo(() => {
    const base: Record<string, number> = { all: files.length };
    for (const file of files) {
      base[file.category] = (base[file.category] ?? 0) + 1;
    }
    return base;
  }, [files]);

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(null), 2400);
  };

  const onUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0];
    if (!selected) return;
    const ext = selected.name.split('.').pop()?.toLowerCase() ?? 'other';
    const fileType = (['pdf', 'docx', 'xlsx', 'png', 'jpg', 'zip'].includes(ext)
      ? ext
      : 'other') as FileTypeKey;
    const next: FileRecord = {
      id: `file-upload-${Date.now()}`,
      name: selected.name,
      fileType,
      category: 'other',
      size: `${Math.max(1, Math.round(selected.size / 1024))} KB`,
      version: 'v1.0',
      updatedAt: new Date().toLocaleDateString('tr-TR'),
      relatedKind: 'customer',
      relatedName: t('upload.unassigned'),
      owner: t('upload.you'),
      recent: true,
    };
    setFiles((prev) => [next, ...prev]);
    showToast(t('upload.success', { name: selected.name }));
    event.target.value = '';
  };

  return (
    <div className="crm-files" data-testid="crm-files-workspace">
      {toast ? (
        <div className="crm-files__toast" role="status" aria-live="polite">
          {toast}
        </div>
      ) : null}

      <header className="crm-files__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="crm-files__header-actions">
          <SegmentedControl
            ariaLabel={t('viewAria')}
            value={view}
            onChange={setView}
            options={[
              { value: 'grid', label: t('view.grid') },
              { value: 'list', label: t('view.list') },
            ]}
          />
          <input
            ref={uploadRef}
            type="file"
            className="crm-files__upload-input"
            onChange={onUpload}
            aria-hidden="true"
            tabIndex={-1}
          />
          <Button type="button" size="sm" onClick={() => uploadRef.current?.click()}>
            {t('upload.cta')}
          </Button>
        </div>
      </header>

      <section className="crm-files__toolbar" aria-label={t('filters.aria')}>
        <Input
          value={filters.search}
          onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
          placeholder={t('filters.searchPlaceholder')}
          aria-label={t('filters.search')}
        />
        <Select
          value={filters.category}
          onChange={(e) => setFilters((f) => ({ ...f, category: e.target.value }))}
          aria-label={t('filters.category')}
        >
          <option value="all">{t('categories.all')}</option>
          {(
            ['contracts', 'identity', 'financial', 'marketing', 'legal', 'other'] as FileCategoryKey[]
          ).map((key) => (
            <option key={key} value={key}>
              {t(`categories.${key}`)} ({categoryCounts[key] ?? 0})
            </option>
          ))}
        </Select>
        <Select
          value={filters.related}
          onChange={(e) => setFilters((f) => ({ ...f, related: e.target.value }))}
          aria-label={t('filters.related')}
        >
          <option value="">{t('filters.anyRelated')}</option>
          <option value="customer">{t('related.customer')}</option>
          <option value="investor">{t('related.investor')}</option>
          <option value="project">{t('related.project')}</option>
        </Select>
        <Select
          value={filters.type}
          onChange={(e) => setFilters((f) => ({ ...f, type: e.target.value }))}
          aria-label={t('filters.type')}
        >
          <option value="">{t('filters.anyType')}</option>
          {(['pdf', 'docx', 'xlsx', 'png', 'jpg', 'zip', 'other'] as FileTypeKey[]).map((key) => (
            <option key={key} value={key}>
              {key.toUpperCase()}
            </option>
          ))}
        </Select>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => setFilters({ search: '', category: 'all', related: '', type: '' })}
        >
          {t('filters.clear')}
        </Button>
      </section>

      <div className="crm-files__categories" role="list" aria-label={t('categories.aria')}>
        {preview.categories.map((chip) => {
          const active = filters.category === chip.id;
          const count = chip.id === 'all' ? files.length : (categoryCounts[chip.id] ?? chip.count);
          return (
            <button
              key={chip.id}
              type="button"
              role="listitem"
              className={`crm-files__category-chip${active ? ' is-active' : ''}`}
              onClick={() => setFilters((f) => ({ ...f, category: chip.id }))}
            >
              <span>{t(`categories.${chip.id}`)}</span>
              <em>{count}</em>
            </button>
          );
        })}
      </div>

      {recentFiles.length > 0 && filters.category === 'all' && !filters.search ? (
        <section className="crm-files__recent" aria-label={t('recent.title')}>
          <h2>{t('recent.title')}</h2>
          <div className="crm-files__recent-row">
            {recentFiles.map((file) => (
              <button
                key={file.id}
                type="button"
                className="crm-files__recent-item"
                onClick={() => setFilters((f) => ({ ...f, search: file.name }))}
              >
                <FileTypeIcon type={file.fileType} />
                <span>
                  <strong>{file.name}</strong>
                  <em>{file.updatedAt}</em>
                </span>
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {filtered.length === 0 ? (
        <EmptyState title={t('empty.title')} description={t('empty.description')} />
      ) : view === 'grid' ? (
        <div className="crm-files__grid" data-testid="crm-files-grid">
          {filtered.map((file) => (
            <FileCard key={file.id} file={file} t={t} />
          ))}
        </div>
      ) : (
        <div className="crm-files__table-wrap" data-testid="crm-files-list">
          <table className="crm-files__table">
            <thead>
              <tr>
                <th>{t('columns.name')}</th>
                <th>{t('columns.category')}</th>
                <th>{t('columns.related')}</th>
                <th>{t('columns.version')}</th>
                <th>{t('columns.size')}</th>
                <th>{t('columns.updated')}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((file) => (
                <FileRow key={file.id} file={file} t={t} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
