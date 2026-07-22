'use client';

import type { Project } from '@/lib/api/projects';
import { formatCurrency, formatLocation, formatShortDate } from '@/lib/api/projects';

import {
  initials,
  projectCompletion,
  projectValue,
  toPortfolioType,
  type PortfolioLayout,
  type ProjectPortfolioType,
} from './project-types';

interface PortfolioViewProps {
  projects: Project[];
  locale: string;
  layout: PortfolioLayout;
  typeLabel: (t: ProjectPortfolioType) => string;
  statusLabel: (s: string) => string;
  onOpen: (project: Project) => void;
}

export function PortfolioView({
  projects,
  locale,
  layout,
  typeLabel,
  statusLabel,
  onOpen,
}: PortfolioViewProps) {
  if (projects.length === 0) {
    return <div className="proj-g4__empty" data-testid="proj-g4-portfolio-empty">—</div>;
  }

  if (layout === 'grid') {
    return (
      <div className="proj-g4__grid" data-testid="proj-g4-portfolio">
        {projects.map((project) => {
          const type = toPortfolioType(project);
          const value = projectValue(project);
          const completion = projectCompletion(project);
          return (
            <button
              key={project.id}
              type="button"
              className="proj-g4__grid-card"
              onClick={() => onOpen(project)}
              data-testid={`proj-g4-card-${project.id}`}
            >
              <div className="proj-g4__card-top">
                <h3>{project.project_name}</h3>
                <span className="proj-g4__card-badge">{typeLabel(type)}</span>
              </div>
              <p className="proj-g4__card-company">
                {project.project_code} · {formatLocation(project) || '—'}
              </p>
              <div className="proj-g4__card-value">
                <strong>{formatCurrency(String(value), locale)}</strong>
                <span>{completion}%</span>
              </div>
              <div className="proj-g4__prob" aria-hidden>
                <i style={{ width: `${completion}%` }} />
              </div>
              <div className="proj-g4__card-meta">
                <div className="proj-g4__who">
                  <span className="proj-g4__avatar">
                    {initials(
                      project.project_manager?.full_name ??
                        project.assigned_project_manager ??
                        '?',
                    )}
                  </span>
                  <span>
                    {project.project_manager?.full_name ??
                      project.assigned_project_manager ??
                      '—'}
                  </span>
                </div>
                <span>{formatShortDate(project.target_completion_date, locale)}</span>
              </div>
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className="proj-g4__list-wrap" data-testid="proj-g4-portfolio">
      <table className="proj-g4__table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Project</th>
            <th>Type</th>
            <th>Status</th>
            <th>Location</th>
            <th>Value</th>
            <th>%</th>
            <th>Target</th>
            <th>PM</th>
          </tr>
        </thead>
        <tbody>
          {projects.map((project) => {
            const type = toPortfolioType(project);
            return (
              <tr
                key={project.id}
                onClick={() => onOpen(project)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onOpen(project);
                  }
                }}
                tabIndex={0}
                data-testid={`proj-g4-row-${project.id}`}
              >
                <td>{project.project_code}</td>
                <td>
                  <strong>{project.project_name}</strong>
                </td>
                <td>{typeLabel(type)}</td>
                <td>{statusLabel(project.project_status)}</td>
                <td>{formatLocation(project) || '—'}</td>
                <td>{formatCurrency(String(projectValue(project)), locale)}</td>
                <td>{projectCompletion(project)}%</td>
                <td>{formatShortDate(project.target_completion_date, locale)}</td>
                <td>
                  {project.project_manager?.full_name ?? project.assigned_project_manager ?? '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
