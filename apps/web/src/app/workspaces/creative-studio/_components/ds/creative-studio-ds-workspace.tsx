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
  JOB_STATUS_TONE,
  buildCreativeStudioDsData,
  PREMIUM_CAMPAIGNS_ROUTE,
  QUICK_CREATIVE_ROUTE,
  toolHref,
  type ActivityItem,
  type ContentItem,
  type HeroShortcut,
  type ProjectItem,
  type RailJobItem,
  type SuggestionItem,
  type ToolItem,
} from './creative-studio-ds-model';

import './creative-studio-ds.css';

function ToolCard({
  tool,
  title,
  description,
  launchLabel,
  metaLabel,
}: {
  tool: ToolItem;
  title: string;
  description: string;
  launchLabel: string;
  metaLabel: string;
}) {
  return (
    <Link href={tool.href as Route} className="cs-ds__tool" data-testid={`cs-tool-${tool.key}`}>
      <span className={`cs-ds__tool-icon is-${tool.tint}`} aria-hidden="true">
        <IhIcon name={tool.icon} size={24} />
      </span>
      <span className="cs-ds__tool-title">{title}</span>
      <span className="cs-ds__tool-desc">{description}</span>
      <span className="cs-ds__tool-meta">{metaLabel}</span>
      <span className="cs-ds__tool-launch">
        {launchLabel}
        <IhIcon name="arrowRight" size={12} />
      </span>
    </Link>
  );
}

function HeroChip({
  item,
  label,
  href,
}: {
  item: HeroShortcut;
  label: string;
  href: string;
}) {
  return (
    <Link
      href={href as Route}
      className="cs-ds__hero-chip"
      data-testid={`cs-hero-${item.key}`}
    >
      <span className={`cs-ds__tool-icon is-${item.tint}`} aria-hidden="true">
        <IhIcon name={item.icon} size={18} />
      </span>
      <span>{label}</span>
    </Link>
  );
}

function ProjectRow({
  project,
  assetsLabel,
  jobsLabel,
  updatedLabel,
  moreLabel,
}: {
  project: ProjectItem;
  assetsLabel: string;
  jobsLabel: string;
  updatedLabel: string;
  moreLabel: string;
}) {
  return (
    <Link href={project.href as Route} className="cs-ds__project" data-testid={`cs-project-${project.id}`}>
      {project.thumbUrl ? (
        <span className="cs-ds__thumb cs-ds__thumb--photo">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={project.thumbUrl} alt="" width={48} height={48} />
        </span>
      ) : (
        <span className={`cs-ds__thumb is-${project.tint}`} aria-hidden="true">
          {project.thumbLabel}
        </span>
      )}
      <div className="cs-ds__project-main">
        <span className="cs-ds__project-title">{project.name}</span>
        <span className="cs-ds__project-meta">
          {assetsLabel}
          {project.jobsRunning > 0 ? ` · ${jobsLabel}` : ''}
        </span>
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
        <IhIcon name={item.icon} size={14} />
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

function RailJobRow({
  item,
  title,
  meta,
  statusLabel,
}: {
  item: RailJobItem;
  title: string;
  meta: string;
  statusLabel: string;
}) {
  return (
    <Link
      href={item.href as Route}
      className={`cs-ds__job cs-ds__job--${item.status}`}
      data-testid={`cs-job-${item.id}`}
    >
      <span className={`cs-ds__tool-icon is-${item.tint}`} aria-hidden="true">
        <IhIcon name={item.icon} size={14} />
      </span>
      <span className="cs-ds__job-body">
        <strong>{title}</strong>
        <span>{meta}</span>
      </span>
      <StatusChip tone={JOB_STATUS_TONE[item.status]}>{statusLabel}</StatusChip>
    </Link>
  );
}

function SuggestionLink({
  item,
  title,
  createLabel,
}: {
  item: SuggestionItem;
  title: string;
  createLabel: string;
}) {
  return (
    <Link
      href={item.href as Route}
      className="cs-ds__ai-item"
      data-testid={`cs-ai-${item.key}`}
    >
      <span className={`cs-ds__tool-icon is-${item.tint}`} aria-hidden="true">
        <IhIcon name={item.icon} size={14} />
      </span>
      <span className="cs-ds__ai-text">
        <strong>{title}</strong>
        <span>{createLabel}</span>
      </span>
    </Link>
  );
}

export function CreativeStudioDsWorkspace() {
  const t = useTranslations('creativeStudio.ds');
  const router = useRouter();
  const data = useMemo(() => buildCreativeStudioDsData(), []);

  const runningJobs = data.railJobs.filter((j) => j.status === 'running');
  const pendingJobs = data.railJobs.filter((j) => j.status === 'pending');
  const failedJobs = data.railJobs.filter((j) => j.status === 'failed');
  const continueJobs = data.railJobs.filter((j) => j.status === 'continue');

  return (
    <div className="cs-ds" data-testid="creative-studio-ds-workspace">
      <header className="cs-ds__header cs-page-header">
        <div className="cs-page-header__copy">
          <h1>
            <span className="cs-ds__title-icon" aria-hidden="true">
              <IhIcon name="sparkles" size={18} />
            </span>
            {t('title')}
          </h1>
          <p className="cs-ds__subtitle cs-page-header__subtitle">{t('subtitle')}</p>
        </div>
        <div className="cs-ds__header-actions cs-page-header__actions">
          <Button
            variant="primary"
            size="sm"
            onClick={() => router.push('/workspaces/creative-studio/produce/aiChat' as Route)}
            data-testid="cs-start-production"
          >
            <IhIcon name="plus" size={13} />
            {t('actions.startProduction')}
          </Button>
        </div>
      </header>

      <section className="cs-ds__hero" aria-label={t('hero.aria')}>
        <div className="cs-ds__hero-copy">
          <h2>{t('hero.headline')}</h2>
          <p>{t('hero.support')}</p>
        </div>
        <div className="cs-ds__paths" aria-label={t('creationPaths.aria')}>
          <Link
            href={QUICK_CREATIVE_ROUTE as Route}
            className="cs-ds__path"
            data-testid="cs-path-quick"
          >
            <span className="cs-ds__tool-icon is-sky" aria-hidden="true">
              <IhIcon name="sparkles" size={22} />
            </span>
            <span className="cs-ds__path-copy">
              <strong>{t('creationPaths.quickTitle')}</strong>
              <span>{t('creationPaths.quickDescription')}</span>
            </span>
            <span className="cs-ds__tool-launch">
              {t('creationPaths.launch')}
              <IhIcon name="arrowRight" size={12} />
            </span>
          </Link>
          <Link
            href={PREMIUM_CAMPAIGNS_ROUTE as Route}
            className="cs-ds__path"
            data-testid="cs-path-premium"
          >
            <span className="cs-ds__tool-icon is-navy" aria-hidden="true">
              <IhIcon name="target" size={22} />
            </span>
            <span className="cs-ds__path-copy">
              <strong>{t('creationPaths.premiumTitle')}</strong>
              <span>{t('creationPaths.premiumDescription')}</span>
            </span>
            <span className="cs-ds__tool-launch">
              {t('creationPaths.launch')}
              <IhIcon name="arrowRight" size={12} />
            </span>
          </Link>
        </div>
        <div className="cs-ds__hero-chips">
          {data.heroShortcuts.map((item) => (
            <HeroChip
              key={item.key}
              item={item}
              label={t(`hero.shortcuts.${item.key}`)}
              href={toolHref(item.toolKey)}
            />
          ))}
        </div>
      </section>

      <section className="cs-ds__section cs-ds__section--kpi" aria-label={t('kpis.aria')}>
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
          <section className="cs-ds__section" aria-label={t('apps.aria')}>
            <div className="cs-ds__section-head">
              <h2>{t('apps.title')}</h2>
            </div>
            <div className="cs-ds__tools">
              {data.tools.map((toolItem) => (
                <ToolCard
                  key={toolItem.key}
                  tool={toolItem}
                  title={t(`tools.${toolItem.key}.title`)}
                  description={t(`tools.${toolItem.key}.description`)}
                  launchLabel={t('apps.launch')}
                  metaLabel={t('apps.meta', {
                    drafts: toolItem.drafts,
                    last: t(`relative.${toolItem.lastProductionKey}`),
                    jobs: toolItem.runningJobs,
                  })}
                />
              ))}
            </div>
          </section>

          <div className="cs-ds__columns">
            <section className="cs-ds__panel" aria-label={t('projects.aria')}>
              <div className="cs-ds__panel-head">
                <h3>{t('projects.title')}</h3>
              </div>
              <div className="cs-ds__panel-body">
                {data.projects.length === 0 ? (
                  <p className="cs-ds__empty">{t('projects.empty')}</p>
                ) : (
                  data.projects.map((project) => (
                    <ProjectRow
                      key={project.id}
                      project={project}
                      assetsLabel={t('projects.assetCount', { count: project.assetCount })}
                      jobsLabel={t('projects.jobsRunning', { count: project.jobsRunning })}
                      updatedLabel={t(`relative.${project.updatedLabelKey}`)}
                      moreLabel={t('more')}
                    />
                  ))
                )}
              </div>
            </section>

            <section className="cs-ds__panel" aria-label={t('recent.aria')}>
              <div className="cs-ds__panel-head">
                <h3>{t('recent.title')}</h3>
              </div>
              <div className="cs-ds__panel-body">
                {data.recentContent.length === 0 ? (
                  <p className="cs-ds__empty">{t('recent.empty')}</p>
                ) : (
                  data.recentContent.map((item) => (
                    <ContentRow
                      key={item.id}
                      item={item}
                      title={t(`recent.items.${item.titleKey}`)}
                      statusLabel={t(`status.${item.status}`)}
                      updatedLabel={t(`relative.${item.updatedLabelKey}`)}
                      moreLabel={t('more')}
                    />
                  ))
                )}
              </div>
            </section>
          </div>

          <section className="cs-ds__panel cs-ds__panel--activity" aria-label={t('activity.aria')}>
            <div className="cs-ds__panel-head">
              <h3>{t('activity.title')}</h3>
            </div>
            <div className="cs-ds__panel-body cs-ds__activity-grid">
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
        </div>

        <aside className="cs-ds__rail" aria-label={t('rail.aria')}>
          <section className="cs-ds__rail-panel">
            <div className="cs-ds__panel-head">
              <h3>{t('rail.suggestions')}</h3>
            </div>
            <div className="cs-ds__ai-list">
              {data.suggestions.map((item) => (
                <SuggestionLink
                  key={item.key}
                  item={item}
                  title={t(`suggestions.items.${item.key}.title`)}
                  createLabel={t('aiPanel.create')}
                />
              ))}
            </div>
          </section>

          <section className="cs-ds__rail-panel">
            <div className="cs-ds__panel-head">
              <h3>{t('rail.running')}</h3>
            </div>
            <div className="cs-ds__job-list">
              {runningJobs.length === 0 ? (
                <p className="cs-ds__empty cs-ds__empty--rail">{t('rail.emptyRunning')}</p>
              ) : (
                runningJobs.map((item) => (
                  <RailJobRow
                    key={item.id}
                    item={item}
                    title={t(`rail.jobs.${item.titleKey}`)}
                    meta={t(`rail.meta.${item.metaKey}`)}
                    statusLabel={t(`rail.status.${item.status}`)}
                  />
                ))
              )}
            </div>
          </section>

          <section className="cs-ds__rail-panel">
            <div className="cs-ds__panel-head">
              <h3>{t('rail.pending')}</h3>
            </div>
            <div className="cs-ds__job-list">
              {pendingJobs.map((item) => (
                <RailJobRow
                  key={item.id}
                  item={item}
                  title={t(`rail.jobs.${item.titleKey}`)}
                  meta={t(`rail.meta.${item.metaKey}`)}
                  statusLabel={t(`rail.status.${item.status}`)}
                />
              ))}
            </div>
          </section>

          <section className="cs-ds__rail-panel">
            <div className="cs-ds__panel-head">
              <h3>{t('rail.failed')}</h3>
            </div>
            <div className="cs-ds__job-list">
              {failedJobs.map((item) => (
                <RailJobRow
                  key={item.id}
                  item={item}
                  title={t(`rail.jobs.${item.titleKey}`)}
                  meta={t(`rail.meta.${item.metaKey}`)}
                  statusLabel={t(`rail.status.${item.status}`)}
                />
              ))}
            </div>
          </section>

          <section className="cs-ds__rail-panel">
            <div className="cs-ds__panel-head">
              <h3>{t('rail.continue')}</h3>
            </div>
            <div className="cs-ds__job-list">
              {continueJobs.map((item) => (
                <RailJobRow
                  key={item.id}
                  item={item}
                  title={t(`rail.jobs.${item.titleKey}`)}
                  meta={t(`relative.${item.metaKey}` as 'hours2')}
                  statusLabel={t(`rail.status.${item.status}`)}
                />
              ))}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
