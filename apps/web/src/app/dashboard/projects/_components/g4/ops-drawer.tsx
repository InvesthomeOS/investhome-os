'use client';

import { useEffect, useState } from 'react';
import type { Route } from 'next';
import Link from 'next/link';

import { EntityActivityTimeline } from '@/app/dashboard/_components/entity-activity-timeline';
import { EntityDocumentsPanel } from '@/app/dashboard/_components/entity-documents-panel';
import { ContextualAiActions } from '@/components/ai/contextual-ai-actions';
import {
  formatCurrency,
  formatLocation,
  formatShortDate,
  type Project,
  type ProjectStatus,
} from '@/lib/api/projects';
import { projectDetailHref } from '@/lib/projects/project-detail-tabs';

import {
  portfolioTypeAsStatus,
  PROJECT_PORTFOLIO_TYPES,
  projectCompletion,
  projectValue,
  toPortfolioType,
  type ProjectPortfolioType,
} from './project-types';

type DrawerTab =
  | 'overview'
  | 'board'
  | 'tasks'
  | 'timeline'
  | 'milestones'
  | 'budget'
  | 'contractors'
  | 'permits'
  | 'inspections'
  | 'issues'
  | 'documents'
  | 'change_orders'
  | 'activity'
  | 'ai'
  | 'audit';

const TABS: DrawerTab[] = [
  'overview',
  'board',
  'tasks',
  'timeline',
  'milestones',
  'budget',
  'contractors',
  'permits',
  'inspections',
  'issues',
  'documents',
  'change_orders',
  'activity',
  'ai',
  'audit',
];

interface OpsDrawerProps {
  project: Project | null;
  locale: string;
  canUpdate: boolean;
  typeLabel: (t: ProjectPortfolioType) => string;
  statusLabel: (s: string) => string;
  labels: Record<string, string>;
  onClose: () => void;
  onEdit: (project: Project) => void;
  onArchive: (project: Project) => void;
  onStatusChange: (project: Project, status: ProjectStatus) => Promise<void>;
}

export function OpsDrawer({
  project,
  locale,
  canUpdate,
  typeLabel,
  statusLabel,
  labels,
  onClose,
  onEdit,
  onArchive,
  onStatusChange,
}: OpsDrawerProps) {
  const [tab, setTab] = useState<DrawerTab>('overview');
  const [nextType, setNextType] = useState<ProjectPortfolioType>('development');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!project) return;
    setTab('overview');
    setNextType(toPortfolioType(project));
  }, [project]);

  if (!project) return null;

  const type = toPortfolioType(project);
  const value = projectValue(project);
  const completion = projectCompletion(project);

  const applyType = async () => {
    if (!canUpdate) return;
    setSaving(true);
    try {
      await onStatusChange(project, portfolioTypeAsStatus(nextType));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="proj-g4-drawer" role="dialog" aria-modal="true" data-testid="proj-g4-drawer">
      <button
        type="button"
        className="proj-g4__btn proj-g4__btn--ghost"
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0 }}
        aria-label={labels.close}
        onClick={onClose}
      />
      <div className="proj-g4-drawer__panel" onClick={(e) => e.stopPropagation()}>
        <header className="proj-g4-drawer__header">
          <div>
            <p className="proj-g4__eyebrow">{project.project_code}</p>
            <h2>{project.project_name}</h2>
            <p className="proj-g4__subtitle">
              {typeLabel(type)} · {statusLabel(project.project_status)} · {completion}%
            </p>
          </div>
          <button type="button" className="proj-g4__btn" onClick={onClose}>
            {labels.close}
          </button>
        </header>

        <div className="proj-g4-drawer__actions">
          <Link
            href={projectDetailHref(project.id, 'overview') as Route}
            className="proj-g4__btn proj-g4__btn--primary"
          >
            {labels.openFull}
          </Link>
          {canUpdate ? (
            <button type="button" className="proj-g4__btn" onClick={() => onEdit(project)}>
              {labels.edit}
            </button>
          ) : null}
          <button type="button" className="proj-g4__btn" onClick={() => onArchive(project)}>
            {labels.archive}
          </button>
        </div>

        <nav className="proj-g4-drawer__tabs" aria-label={labels.tabs}>
          {TABS.map((id) => (
            <button
              key={id}
              type="button"
              className={`proj-g4-drawer__tab${tab === id ? ' is-active' : ''}`}
              onClick={() => setTab(id)}
              data-testid={`proj-g4-drawer-tab-${id}`}
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
                  <dt>{labels.location}</dt>
                  <dd>{formatLocation(project) || '—'}</dd>
                </div>
                <div>
                  <dt>{labels.value}</dt>
                  <dd>{formatCurrency(String(value), locale)}</dd>
                </div>
                <div>
                  <dt>{labels.target}</dt>
                  <dd>{formatShortDate(project.target_completion_date, locale)}</dd>
                </div>
                <div>
                  <dt>{labels.manager}</dt>
                  <dd>
                    {project.project_manager?.full_name ??
                      project.assigned_project_manager ??
                      '—'}
                  </dd>
                </div>
              </dl>
              <div className="proj-g4-drawer__section">
                <h3>{labels.stage}</h3>
                <label className="proj-g4-drawer__field">
                  {labels.portfolioType}
                  <select
                    value={nextType}
                    disabled={!canUpdate || saving}
                    onChange={(e) => setNextType(e.target.value as ProjectPortfolioType)}
                  >
                    {PROJECT_PORTFOLIO_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {typeLabel(t)}
                      </option>
                    ))}
                  </select>
                </label>
                {canUpdate ? (
                  <button
                    type="button"
                    className="proj-g4__btn proj-g4__btn--primary"
                    disabled={saving}
                    onClick={() => void applyType()}
                  >
                    {labels.applyStage}
                  </button>
                ) : null}
              </div>
              <div className="proj-g4-drawer__section">
                <h3>{labels.description}</h3>
                <p style={{ fontSize: '0.78rem', margin: 0, color: 'var(--proj-muted)' }}>
                  {project.description || project.notes || '—'}
                </p>
              </div>
            </>
          ) : null}

          {tab === 'documents' ? (
            <EntityDocumentsPanel entityType="project" entityId={project.id} />
          ) : null}

          {tab === 'activity' || tab === 'audit' ? (
            <EntityActivityTimeline entityType="project" entityId={project.id} />
          ) : null}

          {tab === 'ai' ? (
            <>
              <p className="proj-g4__banner proj-g4__banner--info">{labels.aiHint}</p>
              <ContextualAiActions module="projects" />
            </>
          ) : null}

          {[
            'board',
            'tasks',
            'timeline',
            'milestones',
            'budget',
            'contractors',
            'permits',
            'inspections',
            'issues',
            'change_orders',
          ].includes(tab) ? (
            <div className="proj-g4-drawer__section">
              <p className="proj-g4__banner proj-g4__banner--gap">
                {labels.useWorkspaceView}
              </p>
              <Link
                href={`/dashboard/projects?view=${tab === 'board' ? 'board' : tab}&id=${project.id}` as Route}
                className="proj-g4__btn proj-g4__btn--primary"
              >
                {labels.openView}
              </Link>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
