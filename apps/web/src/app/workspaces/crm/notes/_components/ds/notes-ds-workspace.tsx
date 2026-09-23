'use client';

import type { Route } from 'next';
import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  Button,
  ErrorState,
  Input,
  Select,
  StatusChip,
} from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { canDeleteCrm, canUpdateCrm } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import {
  activityMutations,
  activityQueries,
  activityQueryKeys,
} from '@/workspaces/crm/hooks/use-activities';
import { addActivityComment } from '@/workspaces/crm/api/activities';

import { ActivityFormModal } from '../../../_components/activity-form-modal';

import {
  CATEGORY_ICON,
  CATEGORY_TONE,
  EMPTY_NOTES_FILTERS,
  NOTES_CATEGORIES,
  NOTES_ENTITY_KINDS,
  NOTES_EXPLORER_TABS,
  NOTES_SORT_KEYS,
  PRIORITY_TONE,
  STATUS_TONE,
  countByTab,
  enrichNoteWithDetail,
  filterNoteRows,
  makeNotesFixture,
  mergeNotesData,
  renderNoteBodyHtml,
  uniqueOwners,
  uniqueTags,
  type NoteRow,
  type NotesAttachment,
  type NotesAvatarTone,
  type NotesCategoryKey,
  type NotesDsFilters,
  type NotesEntityKind,
  type NotesExplorerTab,
  type NotesSortKey,
  type NotesViewMode,
  type NotesViewerTab,
} from './notes-ds-model';

import './notes-ds.css';

const PAGE_SIZE = 12;

function Avatar({
  initials,
  tone,
  size = 'sm',
}: {
  initials: string;
  tone: NotesAvatarTone;
  size?: 'sm' | 'lg';
}) {
  return (
    <span className={`notes-ds__avatar is-${tone}${size === 'lg' ? ' is-lg' : ''}`} aria-hidden="true">
      {initials}
    </span>
  );
}

function AttachmentCard({
  attachment,
  onDownload,
}: {
  attachment: NotesAttachment;
  onDownload?: () => void;
}) {
  const t = useTranslations('crm.notes.ds');
  const kindLabel = t(`attachments.kinds.${attachment.kind}`);
  return (
    <div className="notes-ds__attachment">
      <span className="notes-ds__attachment-icon" aria-hidden="true">
        {attachment.kind === 'pdf'
          ? 'PDF'
          : attachment.kind === 'docx'
            ? 'DOC'
            : attachment.kind === 'xlsx'
              ? 'XLS'
              : attachment.kind === 'zip'
                ? 'ZIP'
                : attachment.kind === 'image'
                  ? 'IMG'
                  : 'FILE'}
      </span>
      <div className="notes-ds__list-item-main" style={{ minWidth: 0 }}>
        <span className="notes-ds__attachment-name">{attachment.name}</span>
        <span className="notes-ds__attachment-meta">
          {kindLabel} · {attachment.sizeLabel} · {attachment.dateLabel}
        </span>
      </div>
      <div className="notes-ds__attachment-actions">
        <Button type="button" variant="secondary" size="sm" onClick={onDownload}>
          {t('attachments.download')}
        </Button>
        <Button type="button" variant="secondary" size="sm">
          {t('attachments.preview')}
        </Button>
        <button type="button" className="notes-ds__ghost-btn" aria-label={t('attachments.more')}>
          <IhIcon name="chevronDown" size={12} />
        </button>
      </div>
    </div>
  );
}

function InfoPanel({
  note,
  onClose,
  onEdit,
  onShare,
  onCopy,
  onDelete,
  onDownloadPdf,
}: {
  note: NoteRow | null;
  onClose?: () => void;
  onEdit: () => void;
  onShare: () => void;
  onCopy: () => void;
  onDelete: () => void;
  onDownloadPdf: () => void;
}) {
  const t = useTranslations('crm.notes.ds');
  const router = useRouter();

  if (!note) {
    return (
      <div className="notes-ds__info">
        <div className="notes-ds__empty">
          <IhIcon name="documents" size={22} />
          <strong>{t('info.emptyTitle')}</strong>
          <p>{t('info.emptyDescription')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="notes-ds__info">
      {onClose ? (
        <div className="notes-ds__card-head">
          <h3>{t('info.title')}</h3>
          <button type="button" className="notes-ds__ghost-btn" onClick={onClose} aria-label={t('info.close')}>
            <IhIcon name="chevronRight" size={13} />
          </button>
        </div>
      ) : null}

      <section className="notes-ds__card" aria-label={t('info.title')}>
        <div className="notes-ds__card-head">
          <h3>{t('info.title')}</h3>
        </div>
        <div className="notes-ds__badge-row">
          <StatusChip tone={STATUS_TONE[note.status]}>{t(`statuses.${note.status}`)}</StatusChip>
          <StatusChip tone={PRIORITY_TONE[note.priority]}>{t(`priorities.${note.priority}`)}</StatusChip>
        </div>
      </section>

      <section className="notes-ds__card" aria-label={t('info.createdBy')}>
        <div className="notes-ds__card-head">
          <h3>{t('info.createdBy')}</h3>
        </div>
        <div className="notes-ds__person">
          <Avatar initials={note.createdByInitials} tone={avatarToneSafe(note.createdBy)} />
          <div style={{ minWidth: 0 }}>
            <div className="notes-ds__person-name">{note.createdBy}</div>
            <div className="notes-ds__person-role">{note.dateLabel}</div>
          </div>
        </div>
      </section>

      <section className="notes-ds__card" aria-label={t('info.updatedBy')}>
        <div className="notes-ds__card-head">
          <h3>{t('info.updatedBy')}</h3>
        </div>
        <div className="notes-ds__person">
          <Avatar initials={note.updatedByInitials} tone={avatarToneSafe(note.updatedBy)} />
          <div style={{ minWidth: 0 }}>
            <div className="notes-ds__person-name">{note.updatedBy}</div>
            <div className="notes-ds__person-role">{note.updatedLabel}</div>
          </div>
        </div>
      </section>

      {note.relatedEntity ? (
        <section className="notes-ds__card" aria-label={t('info.entity')}>
          <div className="notes-ds__card-head">
            <h3>{t('info.entity')}</h3>
          </div>
          <button
            type="button"
            className="notes-ds__entity-link"
            onClick={() => {
              if (note.relatedEntity?.href) router.push(note.relatedEntity.href as Route);
            }}
          >
            <span>
              <span className="notes-ds__entity-name">{note.relatedEntity.name}</span>
              <StatusChip tone="info">{t(`entityTypes.${note.relatedEntity.kind}`)}</StatusChip>
            </span>
            <IhIcon name="chevronRight" size={13} />
          </button>
        </section>
      ) : null}

      <section className="notes-ds__card" aria-label={t('info.people')}>
        <div className="notes-ds__card-head">
          <h3>{t('info.people')}</h3>
        </div>
        {note.relatedPeople.length === 0 ? (
          <div className="notes-ds__empty" style={{ padding: '12px 8px' }}>
            <strong>{t('info.noPeople')}</strong>
            <p>{t('info.noPeopleHint')}</p>
          </div>
        ) : (
          <div className="notes-ds__people">
            {note.relatedPeople.map((person) => (
              <div key={person.id} className="notes-ds__person">
                <Avatar initials={person.initials} tone={person.avatarTone} />
                <div style={{ minWidth: 0 }}>
                  <div className="notes-ds__person-name">{person.name}</div>
                  {person.role ? <div className="notes-ds__person-role">{person.role}</div> : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="notes-ds__card" aria-label={t('info.tags')}>
        <div className="notes-ds__card-head">
          <h3>{t('info.tags')}</h3>
        </div>
        {note.tags.length === 0 ? (
          <div className="notes-ds__empty" style={{ padding: '12px 8px' }}>
            <strong>{t('info.noTags')}</strong>
            <p>{t('info.noTagsHint')}</p>
          </div>
        ) : (
          <div className="notes-ds__tags">
            {note.tags.map((tag) => (
              <span key={tag} className="notes-ds__tag">
                {tag}
              </span>
            ))}
          </div>
        )}
      </section>

      <section className="notes-ds__card" aria-label={t('info.quickActions')}>
        <div className="notes-ds__card-head">
          <h3>{t('info.quickActions')}</h3>
        </div>
        <div className="notes-ds__actions">
          <Button type="button" variant="secondary" size="sm" onClick={onEdit}>
            {t('actions.edit')}
          </Button>
          <Button type="button" variant="secondary" size="sm" onClick={onShare}>
            {t('actions.share')}
          </Button>
          <Button type="button" variant="secondary" size="sm" onClick={onDownloadPdf}>
            {t('actions.downloadPdf')}
          </Button>
          <Button type="button" variant="secondary" size="sm" onClick={onCopy}>
            {t('actions.copy')}
          </Button>
          <Button type="button" variant="danger" size="sm" onClick={onDelete}>
            {t('actions.delete')}
          </Button>
        </div>
      </section>
    </div>
  );
}

function avatarToneSafe(name: string): NotesAvatarTone {
  const tones: NotesAvatarTone[] = ['navy', 'cyan', 'green', 'amber', 'violet', 'rose'];
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) hash = (hash + name.charCodeAt(i) * (i + 1)) % 97;
  return tones[hash % tones.length]!;
}

function NotesDsWorkspaceInner() {
  const t = useTranslations('crm.notes.ds');
  const tRoot = useTranslations('crm.notes');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { authLoading, user, canRead: canView, canCreate } = useCrmAccess();
  const canUpdate = canUpdateCrm(user);
  const canDelete = canDeleteCrm(user);

  const fixture = useMemo(() => makeNotesFixture(), []);
  const [filters, setFilters] = useState<NotesDsFilters>(EMPTY_NOTES_FILTERS);
  const [searchDraft, setSearchDraft] = useState('');
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [selectedId, setSelectedId] = useState<string | null>(fixture[0]?.id ?? null);
  const [viewerTab, setViewerTab] = useState<NotesViewerTab>('note');
  const [infoOpen, setInfoOpen] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [commentDraft, setCommentDraft] = useState('');
  const [favoriteIds, setFavoriteIds] = useState<Set<string>>(
    () => new Set(fixture.filter((r) => r.isFavorite).map((r) => r.id)),
  );
  const [menuOpen, setMenuOpen] = useState(false);

  const notesQuery = useQuery({
    ...activityQueries.notes({ page_size: 50, sort_by: 'updated_at', sort_dir: 'desc' }),
    enabled: !authLoading && canView,
    retry: false,
  });

  const detailQuery = useQuery({
    ...activityQueries.detail(selectedId ?? ''),
    enabled:
      !authLoading &&
      canView &&
      Boolean(selectedId) &&
      !selectedId?.startsWith('note-fixture'),
    retry: false,
  });

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFilters((prev) => ({ ...prev, search: searchDraft }));
      setVisibleCount(PAGE_SIZE);
    }, 220);
    return () => window.clearTimeout(timer);
  }, [searchDraft]);

  const merged = useMemo(
    () => mergeNotesData(notesQuery.data?.items, fixture, locale),
    [notesQuery.data?.items, fixture, locale],
  );

  const rowsWithFavorites = useMemo(
    () =>
      merged.rows.map((row) => ({
        ...row,
        isFavorite: favoriteIds.has(row.id) || row.isFavorite,
        isImportant: favoriteIds.has(row.id) || row.isImportant,
      })),
    [merged.rows, favoriteIds],
  );

  const tabCounts = useMemo(() => countByTab(rowsWithFavorites), [rowsWithFavorites]);
  const owners = useMemo(() => uniqueOwners(rowsWithFavorites), [rowsWithFavorites]);
  const tags = useMemo(() => uniqueTags(rowsWithFavorites), [rowsWithFavorites]);
  const filtered = useMemo(() => filterNoteRows(rowsWithFavorites, filters), [rowsWithFavorites, filters]);
  const visibleRows = filtered.slice(0, visibleCount);
  const hasMore = visibleCount < filtered.length;

  useEffect(() => {
    if (!selectedId) {
      if (visibleRows[0]) setSelectedId(visibleRows[0].id);
      return;
    }
    if (filtered.every((r) => r.id !== selectedId)) {
      setSelectedId(visibleRows[0]?.id ?? null);
    }
  }, [selectedId, filtered, visibleRows]);

  const selectedBase = rowsWithFavorites.find((r) => r.id === selectedId) ?? null;
  const selectedNote: NoteRow | null = useMemo(() => {
    if (!selectedBase) return null;
    if (merged.usingFixture || selectedBase.source === 'fixture') return selectedBase;
    return enrichNoteWithDetail(selectedBase, detailQuery.data, locale);
  }, [selectedBase, merged.usingFixture, detailQuery.data, locale]);

  const patchFilters = useCallback((patch: Partial<NotesDsFilters>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setVisibleCount(PAGE_SIZE);
  }, []);

  const toggleFavorite = (id: string) => {
    setFavoriteIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    if (!id.startsWith('note-fixture')) {
      void activityMutations.update(id, { is_favorite: !favoriteIds.has(id) }).catch(() => undefined);
    }
  };

  const deleteMutation = useMutation({
    mutationFn: (id: string) => activityMutations.delete(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: activityQueryKeys.all });
      setSelectedId(null);
      setInfoOpen(false);
    },
  });

  const commentMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: string }) => addActivityComment(id, { body }),
    onSuccess: async () => {
      setCommentDraft('');
      await queryClient.invalidateQueries({ queryKey: activityQueryKeys.detail(selectedId ?? '') });
    },
  });

  const handleCopy = async () => {
    if (!selectedNote) return;
    const text = `${selectedNote.title}\n\n${selectedNote.body}`;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* ignore */
    }
  };

  const handleShare = async () => {
    if (!selectedNote) return;
    const url = `${window.location.origin}/workspaces/crm/notes?id=${selectedNote.id}`;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      /* ignore */
    }
  };

  const handleDownloadPdf = () => {
    if (!selectedNote) return;
    const blob = new Blob(
      [`${selectedNote.title}\n\n${selectedNote.body}\n\n— ${selectedNote.owner}`],
      { type: 'text/plain;charset=utf-8' },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedNote.title.replace(/[^\w\-]+/g, '_').slice(0, 48)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDelete = () => {
    if (!selectedNote || selectedNote.source === 'fixture') return;
    if (!canDelete) return;
    deleteMutation.mutate(selectedNote.id);
  };

  if (authLoading) {
    return (
      <div className="notes-ds" data-testid="notes-ds-workspace">
        <div className="notes-ds__skeleton" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="notes-ds__skeleton-row" />
          ))}
        </div>
      </div>
    );
  }

  if (!canView) {
    return <ErrorState title={tRoot('accessDenied')} message={tRoot('accessDeniedHint')} />;
  }

  if (notesQuery.isError && !merged.usingFixture) {
    return (
      <ErrorState
        title={tRoot('loadFailed')}
        message={notesQuery.error?.message ?? tRoot('loadFailed')}
        action={
          <Button type="button" onClick={() => void notesQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  const loadingList = notesQuery.isLoading && !merged.usingFixture;
  const bodyHtml = selectedNote ? renderNoteBodyHtml(selectedNote.body) : '';

  return (
    <div className="notes-ds" data-testid="notes-ds-workspace">
      <header className="notes-ds__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="notes-ds__header-actions">
          {merged.usingFixture ? <span className="notes-ds__demo-badge">{t('demoBadge')}</span> : null}
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => router.push('/workspaces/crm/dashboard' as Route)}
            data-testid="notes-ds-copilot"
          >
            <IhIcon name="sparkles" size={13} />
            {t('actions.copilot')}
          </Button>
          {canCreate ? (
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={() => setFormOpen(true)}
              data-testid="notes-ds-create"
            >
              <IhIcon name="plus" size={13} />
              {t('actions.create')}
            </Button>
          ) : null}
        </div>
      </header>

      <section className="notes-ds__toolbar" aria-label={t('filters.aria')}>
        <div className="notes-ds__toolbar-search">
          <Input
            label={t('filters.search')}
            value={searchDraft}
            onChange={(e) => setSearchDraft(e.target.value)}
            placeholder={t('filters.searchPlaceholder')}
            data-testid="notes-ds-search"
          />
        </div>
        <Select
          label={t('filters.category')}
          value={filters.category}
          onChange={(e) => patchFilters({ category: e.target.value as NotesCategoryKey | '' })}
        >
          <option value="">{t('filters.allCategories')}</option>
          {NOTES_CATEGORIES.map((key) => (
            <option key={key} value={key}>
              {t(`categories.${key}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.owner')}
          value={filters.owner}
          onChange={(e) => patchFilters({ owner: e.target.value })}
        >
          <option value="">{t('filters.allOwners')}</option>
          {owners.map((owner) => (
            <option key={owner} value={owner}>
              {owner}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.entityType')}
          value={filters.entityType}
          onChange={(e) => patchFilters({ entityType: e.target.value as NotesEntityKind | '' })}
        >
          <option value="">{t('filters.allEntityTypes')}</option>
          {NOTES_ENTITY_KINDS.map((key) => (
            <option key={key} value={key}>
              {t(`entityTypes.${key}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.tag')}
          value={filters.tag}
          onChange={(e) => patchFilters({ tag: e.target.value })}
        >
          <option value="">{t('filters.allTags')}</option>
          {tags.map((tag) => (
            <option key={tag} value={tag}>
              {tag}
            </option>
          ))}
        </Select>
        <Input
          label={t('filters.dateFrom')}
          type="date"
          value={filters.dateFrom}
          onChange={(e) => patchFilters({ dateFrom: e.target.value })}
        />
        <Input
          label={t('filters.dateTo')}
          type="date"
          value={filters.dateTo}
          onChange={(e) => patchFilters({ dateTo: e.target.value })}
        />
        <Select
          label={t('filters.view')}
          value={filters.view}
          onChange={(e) => patchFilters({ view: e.target.value as NotesViewMode })}
        >
          <option value="list">{t('views.list')}</option>
          <option value="compact">{t('views.compact')}</option>
        </Select>
        <Select
          label={t('filters.sort')}
          value={filters.sort}
          onChange={(e) => patchFilters({ sort: e.target.value as NotesSortKey })}
        >
          {NOTES_SORT_KEYS.map((key) => (
            <option key={key} value={key}>
              {t(`sort.${key}`)}
            </option>
          ))}
        </Select>
        <div className="notes-ds__toolbar-actions">
          <button
            type="button"
            className="notes-ds__icon-btn"
            aria-label={t('filters.reset')}
            title={t('filters.reset')}
            onClick={() => {
              setFilters(EMPTY_NOTES_FILTERS);
              setSearchDraft('');
              setVisibleCount(PAGE_SIZE);
            }}
          >
            <IhIcon name="refresh" size={13} />
          </button>
        </div>
      </section>

      <div className="notes-ds__workspace">
        {/* LEFT — Explorer */}
        <section className="notes-ds__panel notes-ds__panel--explorer" aria-label={t('explorer.title')}>
          <div className="notes-ds__panel-head">
            <h2>
              <IhIcon name="documents" size={14} />
              {t('explorer.titleWithCount', { count: filtered.length })}
            </h2>
            <div className="notes-ds__panel-head-actions">
              {canCreate ? (
                <button
                  type="button"
                  className="notes-ds__ghost-btn"
                  aria-label={t('actions.create')}
                  onClick={() => setFormOpen(true)}
                >
                  <IhIcon name="plus" size={13} />
                </button>
              ) : null}
            </div>
          </div>

          <div className="notes-ds__tabs" role="tablist" aria-label={t('explorer.tabsAria')}>
            {NOTES_EXPLORER_TABS.map((tab) => (
              <button
                key={tab}
                type="button"
                role="tab"
                aria-selected={filters.tab === tab}
                className={`notes-ds__tab${filters.tab === tab ? ' is-active' : ''}`}
                onClick={() => patchFilters({ tab: tab as NotesExplorerTab })}
              >
                {t(`explorer.tabs.${tab}`)}
                <span className="notes-ds__tab-count">{tabCounts[tab]}</span>
              </button>
            ))}
          </div>

          <div className="notes-ds__list">
            {loadingList ? (
              <div className="notes-ds__skeleton" aria-hidden="true">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="notes-ds__skeleton-row" />
                ))}
              </div>
            ) : visibleRows.length === 0 ? (
              <div className="notes-ds__empty">
                <IhIcon name="empty" size={22} />
                <strong>{t('explorer.emptyTitle')}</strong>
                <p>{t('explorer.emptyDescription')}</p>
                {canCreate ? (
                  <Button type="button" variant="primary" size="sm" onClick={() => setFormOpen(true)}>
                    <IhIcon name="plus" size={12} />
                    {t('actions.create')}
                  </Button>
                ) : null}
              </div>
            ) : (
              visibleRows.map((row) => {
                const selected = row.id === selectedId;
                return (
                  <button
                    key={row.id}
                    type="button"
                    className={`notes-ds__row${selected ? ' is-selected' : ''}${filters.view === 'compact' ? ' is-compact' : ''}`}
                    onClick={() => {
                      setSelectedId(row.id);
                      setViewerTab('note');
                      setMenuOpen(false);
                    }}
                    data-testid={`notes-ds-row-${row.id}`}
                  >
                    <span className={`notes-ds__row-icon is-${row.category}`} aria-hidden="true">
                      <IhIcon name={CATEGORY_ICON[row.category]} size={13} />
                    </span>
                    <div className="notes-ds__row-main">
                      <div className="notes-ds__row-top">
                        <span className="notes-ds__row-title">{row.title}</span>
                        {row.isFavorite ? (
                          <IhIcon name="sparkles" size={11} aria-hidden="true" />
                        ) : null}
                      </div>
                      <p className="notes-ds__row-sub">
                        {[
                          row.relatedPerson,
                          row.relatedEntity && row.relatedEntity.name !== row.title
                            ? row.relatedEntity.name
                            : null,
                        ]
                          .filter(Boolean)
                          .join(' · ') ||
                          (row.relatedEntity
                            ? t(`entityTypes.${row.relatedEntity.kind}`)
                            : t(`categories.${row.category}`))}
                      </p>
                    </div>
                    <div className="notes-ds__row-side">
                      <span className="notes-ds__row-time">{row.updatedLabel}</span>
                      <StatusChip tone={CATEGORY_TONE[row.category]}>
                        {row.isImportant
                          ? t('explorer.importantBadge')
                          : t(`categories.${row.category}`)}
                      </StatusChip>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          {hasMore ? (
            <div className="notes-ds__list-foot">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => setVisibleCount((n) => n + PAGE_SIZE)}
                data-testid="notes-ds-load-more"
              >
                {t('explorer.loadMore')}
                <IhIcon name="chevronDown" size={12} />
              </Button>
            </div>
          ) : null}
        </section>

        {/* CENTER — Viewer */}
        <section className="notes-ds__panel notes-ds__panel--viewer" aria-label={t('viewer.title')}>
          {!selectedNote ? (
            <div className="notes-ds__empty">
              <IhIcon name="documents" size={22} />
              <strong>{t('viewer.emptyTitle')}</strong>
              <p>{t('viewer.emptyDescription')}</p>
            </div>
          ) : (
            <>
              <div className="notes-ds__viewer-head">
                <div className="notes-ds__viewer-title-row">
                  <span className="notes-ds__viewer-doc" aria-hidden="true">
                    <IhIcon name={CATEGORY_ICON[selectedNote.category]} size={16} />
                  </span>
                  <h2 className="notes-ds__viewer-title">{selectedNote.title}</h2>
                  <div className="notes-ds__viewer-actions">
                    <button
                      type="button"
                      className={`notes-ds__ghost-btn${selectedNote.isFavorite ? ' is-active' : ''}`}
                      aria-label={t('viewer.favorite')}
                      onClick={() => toggleFavorite(selectedNote.id)}
                    >
                      <IhIcon name="sparkles" size={13} />
                    </button>
                    <button
                      type="button"
                      className="notes-ds__info-toggle notes-ds__ghost-btn"
                      aria-label={t('info.open')}
                      onClick={() => setInfoOpen(true)}
                    >
                      <IhIcon name="user" size={13} />
                    </button>
                    <div style={{ position: 'relative' }}>
                      <button
                        type="button"
                        className="notes-ds__ghost-btn"
                        aria-label={t('viewer.menu')}
                        onClick={() => setMenuOpen((v) => !v)}
                      >
                        <IhIcon name="chevronDown" size={13} />
                      </button>
                      {menuOpen ? (
                        <div
                          className="notes-ds__card"
                          style={{
                            position: 'absolute',
                            right: 0,
                            top: '110%',
                            zIndex: 5,
                            minWidth: 160,
                            background: '#fff',
                          }}
                        >
                          {canUpdate ? (
                            <Button type="button" variant="secondary" size="sm" onClick={() => setFormOpen(true)}>
                              {t('actions.edit')}
                            </Button>
                          ) : null}
                          <Button type="button" variant="secondary" size="sm" onClick={() => void handleCopy()}>
                            {t('actions.copy')}
                          </Button>
                          <Button type="button" variant="secondary" size="sm" onClick={() => void handleShare()}>
                            {t('actions.share')}
                          </Button>
                        </div>
                      ) : null}
                    </div>
                  </div>
                </div>
                <div className="notes-ds__viewer-meta">
                  <span className="notes-ds__meta-item">
                    <Avatar initials={selectedNote.ownerInitials} tone={selectedNote.ownerTone} />
                    {selectedNote.owner}
                  </span>
                  {selectedNote.relatedEntity ? (
                    <span className="notes-ds__meta-item">
                      <IhIcon name="projects" size={12} />
                      {selectedNote.relatedEntity.name}
                    </span>
                  ) : null}
                  <span className="notes-ds__meta-item">
                    <IhIcon name="clock" size={12} />
                    {selectedNote.dateLabel}
                  </span>
                </div>
              </div>

              <div className="notes-ds__viewer-tabs" role="tablist" aria-label={t('viewer.tabsAria')}>
                {(
                  [
                    ['note', t('viewer.tabs.note')],
                    ['details', t('viewer.tabs.details')],
                    [
                      'relations',
                      t('viewer.tabs.relations', { count: selectedNote.relatedPeople.length }),
                    ],
                    ['tags', t('viewer.tabs.tags', { count: selectedNote.tags.length })],
                    ['history', t('viewer.tabs.history')],
                  ] as Array<[NotesViewerTab, string]>
                ).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={viewerTab === key}
                    className={`notes-ds__tab${viewerTab === key ? ' is-active' : ''}`}
                    onClick={() => setViewerTab(key)}
                  >
                    {label}
                  </button>
                ))}
              </div>

              <div className="notes-ds__viewer-body">
                {viewerTab === 'note' ? (
                  <>
                    {selectedNote.body ? (
                      <div
                        className="notes-ds__prose"
                        dangerouslySetInnerHTML={{ __html: bodyHtml }}
                      />
                    ) : (
                      <div className="notes-ds__empty">
                        <strong>{t('viewer.noBody')}</strong>
                        <p>{t('viewer.noBodyHint')}</p>
                      </div>
                    )}

                    <section className="notes-ds__section" aria-label={t('viewer.actionItems')}>
                      <div className="notes-ds__section-head">
                        <h3>{t('viewer.actionItems')}</h3>
                        <StatusChip tone="info">
                          {selectedNote.actionItems.filter((a) => a.done).length}/
                          {selectedNote.actionItems.length}
                        </StatusChip>
                      </div>
                      {selectedNote.actionItems.length === 0 ? (
                        <div className="notes-ds__empty" style={{ padding: '14px 8px' }}>
                          <strong>{t('viewer.noActions')}</strong>
                          <p>{t('viewer.noActionsHint')}</p>
                        </div>
                      ) : (
                        <div className="notes-ds__checklist">
                          {selectedNote.actionItems.map((item) => (
                            <div
                              key={item.id}
                              className={`notes-ds__check-item${item.done ? ' is-done' : ''}`}
                            >
                              <span className="notes-ds__check-box" aria-hidden="true" />
                              <span className="notes-ds__check-title">{item.title}</span>
                              <span className="notes-ds__check-meta">
                                {item.assigneeInitials ? (
                                  <Avatar
                                    initials={item.assigneeInitials}
                                    tone={avatarToneSafe(item.assignee ?? item.assigneeInitials)}
                                  />
                                ) : null}
                                {item.dueLabel ?? '—'}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </section>

                    <section className="notes-ds__section" aria-label={t('viewer.attachments')}>
                      <div className="notes-ds__section-head">
                        <h3>{t('viewer.attachments')}</h3>
                      </div>
                      {selectedNote.attachments.length === 0 ? (
                        <div className="notes-ds__empty" style={{ padding: '14px 8px' }}>
                          <strong>{t('viewer.noAttachments')}</strong>
                          <p>{t('viewer.noAttachmentsHint')}</p>
                        </div>
                      ) : (
                        <div className="notes-ds__attachments">
                          {selectedNote.attachments.map((att) => (
                            <AttachmentCard
                              key={att.id}
                              attachment={att}
                              onDownload={() => {
                                if (att.url) window.open(att.url, '_blank', 'noopener,noreferrer');
                              }}
                            />
                          ))}
                        </div>
                      )}
                    </section>

                    <section className="notes-ds__comments" aria-label={t('viewer.comments')}>
                      <div className="notes-ds__section-head">
                        <h3>{t('viewer.comments')}</h3>
                      </div>
                      {selectedNote.comments.length === 0 ? (
                        <div className="notes-ds__empty" style={{ padding: '12px 8px' }}>
                          <strong>{t('viewer.noComments')}</strong>
                          <p>{t('viewer.noCommentsHint')}</p>
                        </div>
                      ) : (
                        selectedNote.comments.map((comment) => (
                          <div key={comment.id} className="notes-ds__comment">
                            <Avatar initials={comment.authorInitials} tone={comment.avatarTone} />
                            <div className="notes-ds__comment-body">
                              <div className="notes-ds__comment-head">
                                <span className="notes-ds__comment-author">{comment.author}</span>
                                <span className="notes-ds__comment-time">{comment.timestamp}</span>
                              </div>
                              <p className="notes-ds__comment-text">{comment.body}</p>
                            </div>
                          </div>
                        ))
                      )}
                      <div className="notes-ds__comment-compose">
                        <Avatar initials="SA" tone="navy" />
                        <Input
                          label={t('viewer.commentPlaceholder')}
                          value={commentDraft}
                          onChange={(e) => setCommentDraft(e.target.value)}
                          placeholder={t('viewer.commentPlaceholder')}
                        />
                        <Button
                          type="button"
                          variant="primary"
                          size="sm"
                          disabled={!commentDraft.trim() || selectedNote.source === 'fixture'}
                          onClick={() => {
                            if (!commentDraft.trim() || selectedNote.source === 'fixture') return;
                            commentMutation.mutate({ id: selectedNote.id, body: commentDraft.trim() });
                          }}
                        >
                          {t('viewer.sendComment')}
                        </Button>
                      </div>
                    </section>
                  </>
                ) : null}

                {viewerTab === 'details' ? (
                  <div className="notes-ds__detail-grid">
                    <dl className="notes-ds__dl">
                      <div className="notes-ds__dl-row">
                        <dt>{t('info.status')}</dt>
                        <dd>
                          <StatusChip tone={STATUS_TONE[selectedNote.status]}>
                            {t(`statuses.${selectedNote.status}`)}
                          </StatusChip>
                        </dd>
                      </div>
                      <div className="notes-ds__dl-row">
                        <dt>{t('info.priority')}</dt>
                        <dd>
                          <StatusChip tone={PRIORITY_TONE[selectedNote.priority]}>
                            {t(`priorities.${selectedNote.priority}`)}
                          </StatusChip>
                        </dd>
                      </div>
                      <div className="notes-ds__dl-row">
                        <dt>{t('info.visibility')}</dt>
                        <dd>{t(`visibility.${selectedNote.visibility}`)}</dd>
                      </div>
                      <div className="notes-ds__dl-row">
                        <dt>{t('info.category')}</dt>
                        <dd>{t(`categories.${selectedNote.category}`)}</dd>
                      </div>
                      <div className="notes-ds__dl-row">
                        <dt>{t('info.owner')}</dt>
                        <dd>{selectedNote.owner}</dd>
                      </div>
                      <div className="notes-ds__dl-row">
                        <dt>{t('info.updated')}</dt>
                        <dd>{selectedNote.dateLabel}</dd>
                      </div>
                    </dl>
                  </div>
                ) : null}

                {viewerTab === 'relations' ? (
                  selectedNote.relatedPeople.length === 0 && !selectedNote.relatedEntity ? (
                    <div className="notes-ds__empty">
                      <strong>{t('info.noPeople')}</strong>
                      <p>{t('info.noPeopleHint')}</p>
                    </div>
                  ) : (
                    <div className="notes-ds__people">
                      {selectedNote.relatedEntity ? (
                        <button
                          type="button"
                          className="notes-ds__entity-link"
                          onClick={() => {
                            if (selectedNote.relatedEntity?.href) {
                              router.push(selectedNote.relatedEntity.href as Route);
                            }
                          }}
                        >
                          <span>
                            <span className="notes-ds__entity-name">{selectedNote.relatedEntity.name}</span>
                            <StatusChip tone="info">
                              {t(`entityTypes.${selectedNote.relatedEntity.kind}`)}
                            </StatusChip>
                          </span>
                          <IhIcon name="chevronRight" size={13} />
                        </button>
                      ) : null}
                      {selectedNote.relatedPeople.map((person) => (
                        <div key={person.id} className="notes-ds__person">
                          <Avatar initials={person.initials} tone={person.avatarTone} />
                          <div style={{ minWidth: 0 }}>
                            <div className="notes-ds__person-name">{person.name}</div>
                            {person.role ? <div className="notes-ds__person-role">{person.role}</div> : null}
                          </div>
                        </div>
                      ))}
                    </div>
                  )
                ) : null}

                {viewerTab === 'tags' ? (
                  selectedNote.tags.length === 0 ? (
                    <div className="notes-ds__empty">
                      <strong>{t('info.noTags')}</strong>
                      <p>{t('info.noTagsHint')}</p>
                    </div>
                  ) : (
                    <div className="notes-ds__tags">
                      {selectedNote.tags.map((tag) => (
                        <span key={tag} className="notes-ds__tag">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )
                ) : null}

                {viewerTab === 'history' ? (
                  <div className="notes-ds__history">
                    {selectedNote.history.map((entry) => (
                      <div key={entry.id} className="notes-ds__history-item">
                        <div className="notes-ds__history-label">{t(`history.${entry.label}`)}</div>
                        <div className="notes-ds__history-meta">
                          {entry.actor} · {entry.timestamp}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            </>
          )}
        </section>

        {/* RIGHT — Details (drawer on narrow) */}
        <div className={`notes-ds__drawer${infoOpen ? ' is-open' : ''}`}>
          <button
            type="button"
            className="notes-ds__drawer-backdrop"
            aria-label={t('info.close')}
            onClick={() => setInfoOpen(false)}
          />
          <aside className="notes-ds__panel notes-ds__panel--info" aria-label={t('info.title')}>
            <InfoPanel
              note={selectedNote}
              onClose={infoOpen ? () => setInfoOpen(false) : undefined}
              onEdit={() => setFormOpen(true)}
              onShare={() => void handleShare()}
              onCopy={() => void handleCopy()}
              onDelete={handleDelete}
              onDownloadPdf={handleDownloadPdf}
            />
          </aside>
        </div>
      </div>

      <ActivityFormModal open={formOpen} onClose={() => setFormOpen(false)} mode="note" defaultType="note" />
    </div>
  );
}

export function NotesDsWorkspace() {
  return (
    <Suspense
      fallback={
        <div className="notes-ds" data-testid="notes-ds-workspace">
          <div className="notes-ds__skeleton" aria-hidden="true">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="notes-ds__skeleton-row" />
            ))}
          </div>
        </div>
      }
    >
      <NotesDsWorkspaceInner />
    </Suspense>
  );
}
