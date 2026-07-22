'use client';

import { useEffect, useState } from 'react';

import type { ConstructionStage, ConstructionTask, TaskPriority } from './construction-domain';
import { CONSTRUCTION_STAGES } from './construction-domain';
import { upsertTask } from './ops-store';

type DrawerTab = 'overview' | 'details' | 'activity' | 'comments' | 'ai';

interface TaskDrawerProps {
  task: ConstructionTask | null;
  stageLabel: (s: ConstructionStage) => string;
  priorityLabel: (p: string) => string;
  labels: Record<string, string>;
  canUpdate: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export function TaskDrawer({
  task,
  stageLabel,
  priorityLabel,
  labels,
  canUpdate,
  onClose,
  onSaved,
}: TaskDrawerProps) {
  const [tab, setTab] = useState<DrawerTab>('overview');
  const [draft, setDraft] = useState<ConstructionTask | null>(null);

  useEffect(() => {
    setTab('overview');
    setDraft(task ? { ...task } : null);
  }, [task]);

  if (!task || !draft) return null;

  const save = () => {
    upsertTask({ ...draft, updatedAt: new Date().toISOString() });
    onSaved();
  };

  return (
    <div className="proj-g4-drawer" role="dialog" aria-modal="true" data-testid="proj-g4-task-drawer">
      <button type="button" className="proj-g4__btn proj-g4__btn--ghost" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0 }} aria-label={labels.close} onClick={onClose} />
      <div className="proj-g4-drawer__panel" onClick={(e) => e.stopPropagation()}>
        <header className="proj-g4-drawer__header">
          <div>
            <p className="proj-g4__eyebrow">{draft.key}</p>
            <h2>{draft.title}</h2>
            <p className="proj-g4__subtitle">{draft.projectName}</p>
          </div>
          <button type="button" className="proj-g4__btn" onClick={onClose}>
            {labels.close}
          </button>
        </header>

        <div className="proj-g4-drawer__actions">
          <span className="proj-g4__data-tag proj-g4__data-tag--demo">{labels.demoTag}</span>
          {canUpdate ? (
            <button type="button" className="proj-g4__btn proj-g4__btn--primary" onClick={save}>
              {labels.save}
            </button>
          ) : null}
        </div>

        <nav className="proj-g4-drawer__tabs" aria-label={labels.tabs}>
          {(['overview', 'details', 'activity', 'comments', 'ai'] as const).map((id) => (
            <button
              key={id}
              type="button"
              className={`proj-g4-drawer__tab${tab === id ? ' is-active' : ''}`}
              onClick={() => setTab(id)}
            >
              {labels[`tab_${id}`] ?? id}
            </button>
          ))}
        </nav>

        <div className="proj-g4-drawer__body">
          {tab === 'overview' ? (
            <>
              <dl className="proj-g4-drawer__grid">
                <div>
                  <dt>{labels.stage}</dt>
                  <dd>{stageLabel(draft.stage)}</dd>
                </div>
                <div>
                  <dt>{labels.priority}</dt>
                  <dd>{priorityLabel(draft.priority)}</dd>
                </div>
                <div>
                  <dt>{labels.assignee}</dt>
                  <dd>{draft.assignee}</dd>
                </div>
                <div>
                  <dt>{labels.due}</dt>
                  <dd>{draft.dueDate ?? '—'}</dd>
                </div>
              </dl>
              <div className="proj-g4-drawer__section">
                <h3>{labels.description}</h3>
                <p style={{ fontSize: '0.78rem', color: 'var(--proj-muted)', margin: 0 }}>
                  {draft.description || '—'}
                </p>
              </div>
            </>
          ) : null}

          {tab === 'details' && canUpdate ? (
            <>
              <label className="proj-g4-drawer__field">
                {labels.title}
                <input
                  value={draft.title}
                  onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                />
              </label>
              <label className="proj-g4-drawer__field">
                {labels.stage}
                <select
                  value={draft.stage}
                  onChange={(e) =>
                    setDraft({ ...draft, stage: e.target.value as ConstructionStage })
                  }
                >
                  {CONSTRUCTION_STAGES.map((s) => (
                    <option key={s} value={s}>
                      {stageLabel(s)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="proj-g4-drawer__field">
                {labels.priority}
                <select
                  value={draft.priority}
                  onChange={(e) =>
                    setDraft({ ...draft, priority: e.target.value as TaskPriority })
                  }
                >
                  {(['low', 'medium', 'high', 'urgent'] as const).map((p) => (
                    <option key={p} value={p}>
                      {priorityLabel(p)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="proj-g4-drawer__field">
                {labels.assignee}
                <input
                  value={draft.assignee}
                  onChange={(e) => setDraft({ ...draft, assignee: e.target.value })}
                />
              </label>
              <label className="proj-g4-drawer__field">
                {labels.due}
                <input
                  type="date"
                  value={draft.dueDate ?? ''}
                  onChange={(e) => setDraft({ ...draft, dueDate: e.target.value || null })}
                />
              </label>
              <label className="proj-g4-drawer__field">
                {labels.description}
                <textarea
                  rows={4}
                  value={draft.description}
                  onChange={(e) => setDraft({ ...draft, description: e.target.value })}
                />
              </label>
            </>
          ) : null}

          {tab === 'activity' ? (
            <p className="proj-g4__banner proj-g4__banner--gap">{labels.activityGap}</p>
          ) : null}

          {tab === 'comments' ? (
            <p className="proj-g4__banner proj-g4__banner--gap">{labels.commentsGap}</p>
          ) : null}

          {tab === 'ai' ? (
            <p className="proj-g4__banner proj-g4__banner--info">{labels.aiHint}</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
