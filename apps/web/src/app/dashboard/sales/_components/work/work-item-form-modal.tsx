'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Dialog } from '@investhome/ui';

import type { WorkItem, WorkItemInput, WorkItemType } from '@/lib/api/work-items';
import { useWorkItemLabels } from '@/lib/i18n/work-item-labels';

interface WorkItemFormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: WorkItemInput) => Promise<void>;
  initial?: Partial<WorkItem> | null;
  defaultLeadId?: string | null;
  defaultOpportunityId?: string | null;
}

export function WorkItemFormModal({
  open,
  onClose,
  onSubmit,
  initial,
  defaultLeadId,
  defaultOpportunityId,
}: WorkItemFormModalProps) {
  const t = useTranslations('work');
  const { typeOptions, priorityOptions, getTypeLabel, getPriorityLabel } = useWorkItemLabels();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [workItemType, setWorkItemType] = useState<WorkItemType>('task');
  const [priority, setPriority] = useState('medium');
  const [dueAt, setDueAt] = useState('');
  const [isPrivate, setIsPrivate] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setTitle(initial?.title ?? '');
    setDescription(initial?.description ?? '');
    setWorkItemType(initial?.work_item_type ?? 'task');
    setPriority(initial?.priority ?? 'medium');
    setDueAt(initial?.due_at ? initial.due_at.slice(0, 16) : '');
    setIsPrivate(initial?.is_private ?? false);
  }, [open, initial]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await onSubmit({
        title,
        description: description || null,
        work_item_type: workItemType,
        priority: priority as WorkItemInput['priority'],
        due_at: dueAt ? new Date(dueAt).toISOString() : null,
        is_private: isPrivate,
        lead_id: initial?.lead_id ?? defaultLeadId ?? undefined,
        opportunity_id: initial?.opportunity_id ?? defaultOpportunityId ?? undefined,
      });
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title={initial ? t('form.editTitle') : t('form.createTitle')}>
      <form className="sales-work-form" onSubmit={handleSubmit}>
        <label>
          {t('form.title')}
          <input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>
        <label>
          {t('form.type')}
          <select value={workItemType} onChange={(e) => setWorkItemType(e.target.value as WorkItemType)}>
            {typeOptions.map((type) => (
              <option key={type} value={type}>{getTypeLabel(type)}</option>
            ))}
          </select>
        </label>
        <label>
          {t('form.priority')}
          <select value={priority} onChange={(e) => setPriority(e.target.value)}>
            {priorityOptions.map((p) => (
              <option key={p} value={p}>{getPriorityLabel(p)}</option>
            ))}
          </select>
        </label>
        <label>
          {t('form.due')}
          <input type="datetime-local" value={dueAt} onChange={(e) => setDueAt(e.target.value)} />
        </label>
        <label>
          {t('form.description')}
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
        </label>
        <label className="sales-work-form__checkbox">
          <input type="checkbox" checked={isPrivate} onChange={(e) => setIsPrivate(e.target.checked)} />
          {t('form.private')}
        </label>
        <div className="sales-work-form__actions">
          <Button type="button" variant="secondary" onClick={onClose}>{t('form.cancel')}</Button>
          <Button type="submit" variant="primary" disabled={saving}>{t('form.save')}</Button>
        </div>
      </form>
    </Dialog>
  );
}
