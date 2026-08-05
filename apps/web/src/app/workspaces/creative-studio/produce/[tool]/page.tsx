'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useParams, useRouter } from 'next/navigation';

import { Button, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  ADS_BUILDER_ROUTE,
  ARCHITECTURAL_STUDIO_ROUTE,
  BLOG_BUILDER_ROUTE,
  BROCHURE_BUILDER_ROUTE,
  EMAIL_BUILDER_ROUTE,
  IMAGE_BUILDER_ROUTE,
  LANDING_PAGE_BUILDER_ROUTE,
  AI_CHAT_ROUTE,
  MEDIA_LIBRARY_ROUTE,
  TEMPLATES_ROUTE,
  PRESENTATION_BUILDER_ROUTE,
  PROPOSAL_BUILDER_ROUTE,
  SOCIAL_MEDIA_BUILDER_ROUTE,
  TOOL_WORKFLOWS,
  VIDEO_BUILDER_ROUTE,
  WEBSITE_BUILDER_ROUTE,
  resolveToolKey,
  type ToolKey,
} from '../../_components/ds/creative-studio-ds-model';

import '../../_components/ds/creative-studio-ds.css';

const CS_HOME = '/workspaces/creative-studio';

/**
 * Shared AI production workflow shell.
 * Tool-specific canvases come later — this is the stable foundation only.
 */
export default function CreativeStudioProducePage() {
  const params = useParams<{ tool: string }>();
  const router = useRouter();
  const toolParam = params.tool ?? '';
  const t = useTranslations('creativeStudio.ds');
  const [project, setProject] = useState('temple');
  const [brief, setBrief] = useState('');
  const [generating, setGenerating] = useState(false);
  const [saved, setSaved] = useState(false);
  const [activeStep, setActiveStep] = useState(0);

  const toolKey: ToolKey | null = resolveToolKey(toolParam);
  const steps = useMemo(() => (toolKey ? TOOL_WORKFLOWS[toolKey] : []), [toolKey]);

  useEffect(() => {
    if (toolKey === 'websiteBuilder') {
      router.replace(WEBSITE_BUILDER_ROUTE as Route);
      return;
    }
    if (toolKey === 'landingPages') {
      router.replace(LANDING_PAGE_BUILDER_ROUTE as Route);
      return;
    }
    if (toolKey === 'blogStudio') {
      router.replace(BLOG_BUILDER_ROUTE as Route);
      return;
    }
    if (toolKey === 'emailStudio') {
      router.replace(EMAIL_BUILDER_ROUTE as Route);
      return;
    }
    if (toolKey === 'videoStudio') {
      router.replace(VIDEO_BUILDER_ROUTE as Route);
      return;
    }
    if (toolKey === 'imageStudio') {
      router.replace(IMAGE_BUILDER_ROUTE as Route);
      return;
    }
    if (toolKey === 'presentationStudio') {
      router.replace(PRESENTATION_BUILDER_ROUTE as Route);
      return;
    }
    if (toolKey === 'proposalStudio') {
      router.replace(PROPOSAL_BUILDER_ROUTE as Route);
      return;
    }
    if (toolKey === 'socialStudio') {
      router.replace(SOCIAL_MEDIA_BUILDER_ROUTE as Route);
      return;
    }
    if (toolKey === 'adsBuilder') {
      router.replace(ADS_BUILDER_ROUTE as Route);
      return;
    }
    if (toolKey === 'brochureStudio') {
      router.replace(BROCHURE_BUILDER_ROUTE as Route);
      return;
    }
    if (toolKey === 'mediaLibrary') {
      router.replace(MEDIA_LIBRARY_ROUTE as Route);
      return;
    }
    if (toolKey === 'templates') {
      router.replace(TEMPLATES_ROUTE as Route);
      return;
    }
    if (toolKey === 'aiChat') {
      router.replace(AI_CHAT_ROUTE as Route);
      return;
    }
    if (toolKey === 'architecturalStudio') {
      router.replace(ARCHITECTURAL_STUDIO_ROUTE as Route);
    }
  }, [router, toolKey]);

  if (!toolKey) {
    return (
      <main className="dashboard" data-testid="cs-produce-missing">
        <div className="cs-ds cs-ds--produce">
          <p className="cs-ds__empty">{t('workflow.unknown')}</p>
          <Link href={CS_HOME as Route} className="cs-ds__back">
            <IhIcon name="chevronLeft" size={12} />
            {t('workflow.back')}
          </Link>
        </div>
      </main>
    );
  }

  const toolTitle = t(`tools.${toolKey}.title`);
  const newProduction = t('workflow.newProduction');

  return (
    <main className="dashboard" data-testid="cs-produce-page">
      <div className="cs-ds cs-ds--produce" data-testid={`cs-produce-${toolKey}`}>
        <header className="cs-ds__header">
          <div>
            <Link href={CS_HOME as Route} className="cs-ds__back">
              <IhIcon name="chevronLeft" size={12} />
              {t('workflow.back')}
            </Link>
            <nav aria-label={t('workflow.breadcrumbAria')}>
              <ol className="cs-ds__breadcrumb">
                <li>
                  <Link href={CS_HOME as Route}>{t('title')}</Link>
                </li>
                <li className="cs-ds__breadcrumb-sep" aria-hidden="true">
                  /
                </li>
                <li>
                  <Link href={`/workspaces/creative-studio/produce/${toolKey}` as Route}>
                    {toolTitle}
                  </Link>
                </li>
                <li className="cs-ds__breadcrumb-sep" aria-hidden="true">
                  /
                </li>
                <li className="cs-ds__breadcrumb-current" aria-current="page">
                  {newProduction}
                </li>
              </ol>
            </nav>
            <h1>{toolTitle}</h1>
            <p className="cs-ds__subtitle">{t('workflow.subtitle')}</p>
          </div>
          <StatusChip tone="info">{t('workflow.badge')}</StatusChip>
        </header>

        <div className="cs-ds__wf-toolbar" role="toolbar" aria-label={t('workflow.toolbarAria')}>
          <div className="cs-ds__wf-toolbar-left">
            <div className="cs-ds__wf-project">
              <Select
                id="cs-wf-project"
                label={t('workflow.fields.project')}
                value={project}
                onChange={(e) => setProject(e.target.value)}
              >
                <option value="temple">THE TEMPLE Residences</option>
                <option value="309h">309 H ST NE</option>
                <option value="uniloft">UNILOFT DC</option>
                <option value="campus">The Campus 3224</option>
              </Select>
            </div>
            <StatusChip tone={saved ? 'success' : 'default'}>
              {saved ? t('workflow.saved') : t('workflow.draft')}
            </StatusChip>
            <StatusChip tone="warning">{t('workflow.approvalPending')}</StatusChip>
          </div>
          <div className="cs-ds__wf-toolbar-right">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setSaved(true)}
              data-testid="cs-wf-save"
            >
              {t('workflow.saveDraft')}
            </Button>
            <Button variant="secondary" size="sm" data-testid="cs-wf-versions">
              {t('workflow.versions')}
            </Button>
            <Button variant="secondary" size="sm" data-testid="cs-wf-preview">
              {t('workflow.preview')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              disabled={generating}
              data-testid="cs-wf-generate"
              onClick={() => {
                setGenerating(true);
                window.setTimeout(() => setGenerating(false), 1200);
              }}
            >
              <IhIcon name="sparkles" size={13} />
              {generating ? t('workflow.generating') : t('workflow.generate')}
            </Button>
          </div>
        </div>

        <ol className="cs-ds__wf-steps" aria-label={t('workflow.stepsAria')}>
          {steps.map((id, index) => (
            <li key={id}>
              <button
                type="button"
                className={`cs-ds__wf-step${index === activeStep ? ' is-active' : ''}${index < activeStep ? ' is-done' : ''}`}
                onClick={() => setActiveStep(index)}
              >
                <span className="cs-ds__wf-step-index">{index + 1}</span>
                <span>{t(`workflow.steps.${id}`)}</span>
              </button>
            </li>
          ))}
        </ol>

        <div className="cs-ds__wf-layout">
          <aside className="cs-ds__wf-panel" aria-label={t('workflow.briefAria')}>
            <div className="cs-ds__wf-panel-head">
              <h2>{t('workflow.briefTitle')}</h2>
            </div>
            <div className="cs-ds__wf-panel-body">
              <div className="cs-ds__wf-chat">
                <div className="cs-ds__wf-msg cs-ds__wf-msg--ai">{t('workflow.briefWelcome')}</div>
                {brief.trim() ? (
                  <div className="cs-ds__wf-msg cs-ds__wf-msg--user">{brief.trim()}</div>
                ) : null}
              </div>
              <div className="cs-ds__wf-chat-input">
                <label className="sr-only" htmlFor="cs-wf-brief">
                  {t('workflow.briefLabel')}
                </label>
                <textarea
                  id="cs-wf-brief"
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                  placeholder={t('workflow.briefPlaceholder')}
                  rows={3}
                />
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    if (!brief.trim()) setBrief(t('workflow.briefSample'));
                  }}
                >
                  {t('workflow.sendBrief')}
                </Button>
              </div>
            </div>
          </aside>

          <section className="cs-ds__wf-panel" aria-label={t('workflow.canvasAria')}>
            <div className="cs-ds__wf-panel-head">
              <h2>{t('workflow.canvasTitle')}</h2>
              <StatusChip tone="default">{t(`workflow.steps.${steps[activeStep] ?? steps[0]}`)}</StatusChip>
            </div>
            <div className="cs-ds__wf-panel-body">
              <div className="cs-ds__wf-canvas">
                <div className="cs-ds__wf-canvas-icon" aria-hidden="true">
                  <IhIcon name="sparkles" size={24} />
                </div>
                <h3>{t('workflow.canvasHeading', { tool: toolTitle })}</h3>
                <p>{t('workflow.canvasHelp')}</p>
              </div>
            </div>
          </section>

          <aside className="cs-ds__wf-panel" aria-label={t('workflow.propsAria')}>
            <div className="cs-ds__wf-panel-head">
              <h2>{t('workflow.propsTitle')}</h2>
            </div>
            <div className="cs-ds__wf-panel-body">
              <div className="cs-ds__wf-props">
                <div className="cs-ds__wf-prop">
                  <label htmlFor="cs-wf-lang">{t('workflow.fields.language')}</label>
                  <select id="cs-wf-lang" defaultValue="tr">
                    <option value="tr">{t('workflow.options.language.a')}</option>
                    <option value="en">{t('workflow.options.language.b')}</option>
                    <option value="bi">{t('workflow.options.language.c')}</option>
                  </select>
                </div>
                <div className="cs-ds__wf-prop">
                  <label htmlFor="cs-wf-tone">{t('workflow.fields.tone')}</label>
                  <select id="cs-wf-tone" defaultValue="a">
                    <option value="a">{t('workflow.options.tone.a')}</option>
                    <option value="b">{t('workflow.options.tone.b')}</option>
                    <option value="c">{t('workflow.options.tone.c')}</option>
                  </select>
                </div>
                <div className="cs-ds__wf-prop">
                  <label>{t('workflow.fields.project')}</label>
                  <span>
                    {project === 'temple'
                      ? 'THE TEMPLE Residences'
                      : project === '309h'
                        ? '309 H ST NE'
                        : project === 'uniloft'
                          ? 'UNILOFT DC'
                          : 'The Campus 3224'}
                  </span>
                </div>
                <div className="cs-ds__wf-prop">
                  <label>{t('workflow.approvalLabel')}</label>
                  <span>{t('workflow.approvalPending')}</span>
                </div>
                <div className="cs-ds__wf-prop">
                  <label>{t('workflow.versionLabel')}</label>
                  <span>{t('workflow.versionCurrent')}</span>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}
