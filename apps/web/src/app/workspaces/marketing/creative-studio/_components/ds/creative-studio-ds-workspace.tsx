'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';

import { Button, KpiCard, ProgressBar, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  CONTENT_STATUS_TONE,
  buildCreativeStudioDsData,
  type ActivityItem,
  type ContentItem,
  type ProjectItem,
  type SuggestionItem,
  type ToolItem,
} from './creative-studio-ds-model';

import './creative-studio-ds.css';

function ToolCard({
  tool,
  title,
  description,
}: {
  tool: ToolItem;
  title: string;
  description: string;
}) {
  return (
    <Link href={tool.href as Route} className="cs-ds__tool" data-testid={`cs-tool-${tool.key}`}>
      <span className={`cs-ds__tool-icon is-${tool.tint}`} aria-hidden="true">
        <IhIcon name={tool.icon} size={16} />
      </span>
      <span className="cs-ds__tool-title">{title}</span>
      <span className="cs-ds__tool-desc">{description}</span>
    </Link>
  );
}

function ProjectRow({
  project,
  assetsLabel,
  updatedLabel,
  moreLabel,
}: {
  project: ProjectItem;
  assetsLabel: string;
  updatedLabel: string;
  moreLabel: string;
}) {
  return (
    <Link href={project.href as Route} className="cs-ds__project" data-testid={`cs-project-${project.id}`}>
      <span className={`cs-ds__thumb is-${project.tint}`} aria-hidden="true">
        {project.thumbLabel}
      </span>
      <div className="cs-ds__project-main">
        <span className="cs-ds__project-title">{project.name}</span>
        <span className="cs-ds__project-meta">{assetsLabel}</span>
        <div className="cs-ds__project-progress">
          <ProgressBar value={project.progress} className="cs-ds__progress" />
          <span className="cs-ds__project-pct">{project.progress}%</span>
        </div>
      </div>
      <div className="cs-ds__project-side">
        <span className="cs-ds__row-time">{updatedLabel}</span>
        <button
          type="button"
          className="cs-ds__menu-btn"
          aria-label={moreLabel}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
          }}
        >
          <IhIcon name="chevronDown" size={12} />
        </button>
      </div>
    </Link>
  );
}

function ContentRow({
  item,
  title,
  statusLabel,
  updatedLabel,
  moreLabel,
}: {
  item: ContentItem;
  title: string;
  statusLabel: string;
  updatedLabel: string;
  moreLabel: string;
}) {
  return (
    <Link href={item.href as Route} className="cs-ds__content-row" data-testid={`cs-content-${item.id}`}>
      <span className={`cs-ds__content-icon cs-ds__tool-icon is-${item.tint}`} aria-hidden="true">
        <IhIcon name={item.icon} size={13} />
      </span>
      <div className="cs-ds__content-main">
        <span className="cs-ds__content-title">{title}</span>
      </div>
      <StatusChip tone={CONTENT_STATUS_TONE[item.status]}>{statusLabel}</StatusChip>
      <span className="cs-ds__row-time">{updatedLabel}</span>
      <button
        type="button"
        className="cs-ds__menu-btn"
        aria-label={moreLabel}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
        }}
      >
        <IhIcon name="chevronDown" size={12} />
      </button>
    </Link>
  );
}

function ActivityRow({
  item,
  name,
  action,
  timeLabel,
}: {
  item: ActivityItem;
  name: string;
  action: string;
  timeLabel: string;
}) {
  return (
    <div className="cs-ds__activity">
      <span className={`cs-ds__avatar is-${item.tone}`} aria-hidden="true">
        {item.initials}
      </span>
      <div className="cs-ds__activity-main">
        <strong>{name}</strong>
        <span>{action}</span>
      </div>
      <span className="cs-ds__row-time">{timeLabel}</span>
    </div>
  );
}

function SuggestionCard({
  item,
  eyebrow,
  title,
  createLabel,
}: {
  item: SuggestionItem;
  eyebrow: string;
  title: string;
  createLabel: string;
}) {
  const router = useRouter();
  return (
    <article className="cs-ds__suggestion" data-testid={`cs-suggestion-${item.key}`}>
      <span className={`cs-ds__tool-icon is-${item.tint}`} aria-hidden="true">
        <IhIcon name={item.icon} size={16} />
      </span>
      <div className="cs-ds__suggestion-body">
        <span className="cs-ds__suggestion-eyebrow">{eyebrow}</span>
        <span className="cs-ds__suggestion-title">{title}</span>
        <div className="cs-ds__suggestion-actions">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => router.push(item.href as Route)}
          >
            {createLabel}
          </Button>
        </div>
      </div>
    </article>
  );
}

export function CreativeStudioDsWorkspace() {
  const t = useTranslations('marketing.creativeStudio.ds');
  const router = useRouter();
  const data = useMemo(() => buildCreativeStudioDsData(), []);

  return (
    <div className="cs-ds" data-testid="creative-studio-ds-workspace">
      <header className="cs-ds__header">
        <div>
          <h1>{t('title')}</h1>
          <p className="cs-ds__subtitle">
            <span className="cs-ds__subtitle-icon" aria-hidden="true">
              <IhIcon name="sparkles" size={12} />
            </span>
            {t('subtitle')}
          </p>
        </div>
        <div className="cs-ds__header-actions">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => router.push('/workspaces/marketing/ai/assistant' as Route)}
          >
            <IhIcon name="sparkles" size={13} />
            {t('actions.aiAssist')}
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => router.push('/workspaces/marketing/content/new' as Route)}
            data-testid="cs-new-project"
          >
            <IhIcon name="plus" size={13} />
            {t('actions.newProject')}
          </Button>
        </div>
      </header>

      <section className="cs-ds__section" aria-label={t('kpis.aria')}>
        <div className="cs-ds__kpi-row">
          {data.kpis.map((kpi) => (
            <KpiCard
              key={kpi.key}
              className="cs-ds__kpi"
              label={t(`kpis.${kpi.key}`)}
              value={kpi.value}
              delta={`${kpi.delta} ${t('kpis.thisWeek')}`}
              deltaTone={kpi.deltaTone}
              icon={<IhIcon name={kpi.icon} size={18} />}
            />
          ))}
        </div>
      </section>

      <div className="cs-ds__body">
        <div className="cs-ds__main">
          <section className="cs-ds__section" aria-label={t('quickStart.aria')}>
            <div className="cs-ds__section-head">
              <h2>{t('quickStart.title')}</h2>
              <Link href={'/workspaces/marketing/templates' as Route} className="cs-ds__view-all">
                {t('quickStart.allTools')}
                <IhIcon name="arrowRight" size={11} />
              </Link>
            </div>
            <div className="cs-ds__tools">
              {data.tools.map((tool) => (
                <ToolCard
                  key={tool.key}
                  tool={tool}
                  title={t(`tools.${tool.key}.title`)}
                  description={t(`tools.${tool.key}.description`)}
                />
              ))}
            </div>
          </section>

          <div className="cs-ds__columns">
            <section className="cs-ds__panel" aria-label={t('projects.aria')}>
              <div className="cs-ds__panel-head">
                <h3>{t('projects.title')}</h3>
                <Link href={'/workspaces/marketing/content' as Route} className="cs-ds__view-all">
                  {t('viewAll')}
                  <IhIcon name="arrowRight" size={11} />
                </Link>
              </div>
              <div className="cs-ds__panel-body">
                {data.projects.map((project) => (
                  <ProjectRow
                    key={project.id}
                    project={project}
                    assetsLabel={t('projects.assetCount', { count: project.assetCount })}
                    updatedLabel={t(`relative.${project.updatedLabelKey}`)}
                    moreLabel={t('more')}
                  />
                ))}
              </div>
            </section>

            <section className="cs-ds__panel" aria-label={t('recent.aria')}>
              <div className="cs-ds__panel-head">
                <h3>{t('recent.title')}</h3>
                <Link href={'/workspaces/marketing/content' as Route} className="cs-ds__view-all">
                  {t('viewAll')}
                  <IhIcon name="arrowRight" size={11} />
                </Link>
              </div>
              <div className="cs-ds__panel-body">
                {data.recentContent.map((item) => (
                  <ContentRow
                    key={item.id}
                    item={item}
                    title={t(`recent.items.${item.titleKey}`)}
                    statusLabel={t(`status.${item.status}`)}
                    updatedLabel={t(`relative.${item.updatedLabelKey}`)}
                    moreLabel={t('more')}
                  />
                ))}
              </div>
            </section>
          </div>
        </div>

        <aside className="cs-ds__rail" aria-label={t('rail.aria')}>
          <section className="cs-ds__rail-panel">
            <div className="cs-ds__panel-head">
              <h3>{t('quickActions.title')}</h3>
            </div>
            <div className="cs-ds__qa-list">
              {data.quickActions.map((action) => (
                <Link
                  key={action.key}
                  href={action.href as Route}
                  className="cs-ds__qa"
                  data-testid={`cs-qa-${action.key}`}
                >
                  <span className="cs-ds__qa-icon" aria-hidden="true">
                    <IhIcon name={action.icon} size={14} />
                  </span>
                  <span className="cs-ds__qa-text">
                    <strong>{t(`quickActions.${action.key}.title`)}</strong>
                    <span>{t(`quickActions.${action.key}.description`)}</span>
                  </span>
                </Link>
              ))}
            </div>
          </section>

          <section className="cs-ds__rail-panel">
            <div className="cs-ds__panel-head">
              <h3>{t('assistant.title')}</h3>
            </div>
            <div className="cs-ds__assistant">
              <span className="cs-ds__assistant-badge">
                <IhIcon name="sparkles" size={11} />
                {t('assistant.badge')}
              </span>
              <p>{t('assistant.prompt')}</p>
              <Button
                variant="primary"
                size="sm"
                onClick={() => router.push('/workspaces/marketing/ai/assistant' as Route)}
              >
                {t('assistant.cta')}
              </Button>
            </div>
          </section>

          <section className="cs-ds__rail-panel">
            <div className="cs-ds__panel-head">
              <h3>{t('activity.title')}</h3>
            </div>
            <div className="cs-ds__panel-body">
              {data.activities.map((item) => (
                <ActivityRow
                  key={item.id}
                  item={item}
                  name={t(`activity.people.${item.nameKey}`)}
                  action={t(`activity.actions.${item.actionKey}`)}
                  timeLabel={t(`relative.${item.timeLabelKey}`)}
                />
              ))}
            </div>
          </section>
        </aside>
      </div>

      <section className="cs-ds__section" aria-label={t('suggestions.aria')}>
        <div className="cs-ds__section-head">
          <h2>{t('suggestions.title')}</h2>
        </div>
        <div className="cs-ds__suggestions">
          {data.suggestions.map((item) => (
            <SuggestionCard
              key={item.key}
              item={item}
              eyebrow={t(`suggestions.items.${item.key}.eyebrow`)}
              title={t(`suggestions.items.${item.key}.title`)}
              createLabel={t('suggestions.create')}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
