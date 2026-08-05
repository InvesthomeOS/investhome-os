'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Dialog, EmptyState, Input, Select, StatusChip } from '@investhome/ui';

import {
  TAG_COLOR_HEX,
  type TagColorKey,
  type TagRecord,
  type TagsWorkspacePreview,
} from '../tags-model';

const COLOR_KEYS: TagColorKey[] = ['navy', 'cyan', 'green', 'amber', 'rose', 'violet', 'slate'];
const CATEGORY_KEYS = ['lifecycle', 'interest', 'priority', 'source', 'custom'] as const;

type Draft = {
  id?: string;
  name: string;
  color: TagColorKey;
  category: TagRecord['category'];
  description: string;
};

const emptyDraft = (): Draft => ({
  name: '',
  color: 'navy',
  category: 'custom',
  description: '',
});

function ColorBadge({ color, label }: { color: TagColorKey; label: string }) {
  return (
    <span className="crm-tags__badge" style={{ backgroundColor: TAG_COLOR_HEX[color] }}>
      {label}
    </span>
  );
}

export function CrmTagsWorkspace({ preview }: { preview: TagsWorkspacePreview }) {
  const t = useTranslations('crm.tags');
  const [tags, setTags] = useState(preview.tags);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [color, setColor] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [draft, setDraft] = useState<Draft>(emptyDraft());
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const filtered = useMemo(() => {
    return tags.filter((tag) => {
      if (category && tag.category !== category) return false;
      if (color && tag.color !== color) return false;
      if (search) {
        const q = search.trim().toLowerCase();
        if (!tag.name.toLowerCase().includes(q) && !tag.description.toLowerCase().includes(q)) {
          return false;
        }
      }
      return true;
    });
  }, [tags, search, category, color]);

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(null), 2400);
  };

  const openCreate = () => {
    setDraft(emptyDraft());
    setDialogOpen(true);
  };

  const openEdit = (tag: TagRecord) => {
    setDraft({
      id: tag.id,
      name: tag.name,
      color: tag.color,
      category: tag.category,
      description: tag.description,
    });
    setDialogOpen(true);
  };

  const saveTag = () => {
    if (!draft.name.trim()) return;
    if (draft.id) {
      setTags((prev) =>
        prev.map((tag) =>
          tag.id === draft.id
            ? {
                ...tag,
                name: draft.name.trim(),
                color: draft.color,
                category: draft.category,
                description: draft.description.trim(),
              }
            : tag,
        ),
      );
      showToast(t('toast.updated'));
    } else {
      setTags((prev) => [
        {
          id: `tag-${Date.now()}`,
          name: draft.name.trim(),
          color: draft.color,
          category: draft.category,
          description: draft.description.trim() || t('form.defaultDescription'),
          usageCount: 0,
        },
        ...prev,
      ]);
      showToast(t('toast.created'));
    }
    setDialogOpen(false);
  };

  const confirmDelete = () => {
    if (!deleteId) return;
    setTags((prev) => prev.filter((tag) => tag.id !== deleteId));
    setDeleteId(null);
    showToast(t('toast.deleted'));
  };

  return (
    <div className="crm-tags" data-testid="crm-tags-workspace">
      {toast ? (
        <div className="crm-tags__toast" role="status" aria-live="polite">
          {toast}
        </div>
      ) : null}

      <header className="crm-tags__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <Button type="button" size="sm" onClick={openCreate}>
          {t('create')}
        </Button>
      </header>

      <section className="crm-tags__toolbar" aria-label={t('filters.aria')}>
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('filters.searchPlaceholder')}
          aria-label={t('filters.search')}
        />
        <Select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          aria-label={t('filters.category')}
        >
          <option value="">{t('filters.anyCategory')}</option>
          {CATEGORY_KEYS.map((key) => (
            <option key={key} value={key}>
              {t(`categories.${key}`)}
            </option>
          ))}
        </Select>
        <Select value={color} onChange={(e) => setColor(e.target.value)} aria-label={t('filters.color')}>
          <option value="">{t('filters.anyColor')}</option>
          {COLOR_KEYS.map((key) => (
            <option key={key} value={key}>
              {t(`colors.${key}`)}
            </option>
          ))}
        </Select>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => {
            setSearch('');
            setCategory('');
            setColor('');
          }}
        >
          {t('filters.clear')}
        </Button>
      </section>

      {filtered.length === 0 ? (
        <EmptyState title={t('empty.title')} description={t('empty.description')} />
      ) : (
        <ul className="crm-tags__list" aria-label={t('listAria')}>
          {filtered.map((tag) => (
            <li key={tag.id} className="crm-tags__row" data-testid={`tag-row-${tag.id}`}>
              <ColorBadge color={tag.color} label={tag.name} />
              <div className="crm-tags__copy">
                <strong>{tag.name}</strong>
                <span>{tag.description}</span>
                <em>
                  {t(`categories.${tag.category}`)} · {t('usageCount', { count: tag.usageCount })}
                </em>
              </div>
              <StatusChip tone="default" className="crm-tags__usage">
                {tag.usageCount}
              </StatusChip>
              <div className="crm-tags__actions">
                <Button type="button" variant="secondary" size="sm" onClick={() => openEdit(tag)}>
                  {t('edit')}
                </Button>
                <Button type="button" variant="secondary" size="sm" onClick={() => setDeleteId(tag.id)}>
                  {t('delete')}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        title={draft.id ? t('form.editTitle') : t('form.createTitle')}
        footer={
          <>
            <Button type="button" variant="secondary" onClick={() => setDialogOpen(false)}>
              {t('form.cancel')}
            </Button>
            <Button type="button" onClick={saveTag} disabled={!draft.name.trim()}>
              {t('form.save')}
            </Button>
          </>
        }
      >
        <div className="crm-tags__form">
          <label className="crm-tags__field">
            <span>{t('form.name')}</span>
            <Input
              value={draft.name}
              onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
            />
          </label>
          <label className="crm-tags__field">
            <span>{t('form.color')}</span>
            <Select
              value={draft.color}
              onChange={(e) => setDraft((d) => ({ ...d, color: e.target.value as TagColorKey }))}
            >
              {COLOR_KEYS.map((key) => (
                <option key={key} value={key}>
                  {t(`colors.${key}`)}
                </option>
              ))}
            </Select>
          </label>
          <label className="crm-tags__field">
            <span>{t('form.category')}</span>
            <Select
              value={draft.category}
              onChange={(e) =>
                setDraft((d) => ({ ...d, category: e.target.value as TagRecord['category'] }))
              }
            >
              {CATEGORY_KEYS.map((key) => (
                <option key={key} value={key}>
                  {t(`categories.${key}`)}
                </option>
              ))}
            </Select>
          </label>
          <label className="crm-tags__field">
            <span>{t('form.description')}</span>
            <Input
              value={draft.description}
              onChange={(e) => setDraft((d) => ({ ...d, description: e.target.value }))}
            />
          </label>
          <div className="crm-tags__preview">
            <span>{t('form.preview')}</span>
            <ColorBadge color={draft.color} label={draft.name || t('form.namePlaceholder')} />
          </div>
        </div>
      </Dialog>

      <Dialog
        open={Boolean(deleteId)}
        onClose={() => setDeleteId(null)}
        title={t('deleteConfirm.title')}
        footer={
          <>
            <Button type="button" variant="secondary" onClick={() => setDeleteId(null)}>
              {t('form.cancel')}
            </Button>
            <Button type="button" onClick={confirmDelete}>
              {t('delete')}
            </Button>
          </>
        }
      >
        <p>{t('deleteConfirm.message')}</p>
      </Dialog>
    </div>
  );
}
