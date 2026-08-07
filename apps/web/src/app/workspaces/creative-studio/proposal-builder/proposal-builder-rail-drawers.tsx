'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

import {
  AI_SOURCES,
  AI_SUGGESTIONS,
  BRAND_KIT,
  COMPONENT_LIBRARY,
  CONTENT_SECTION_SUGGESTIONS,
  DIGITAL_EXPORTS,
  DOCUMENT_EXPORTS,
  DOCUMENT_RATIOS,
  EXPORT_QUALITY_OPTIONS,
  HISTORY_ITEMS,
  LANGUAGE_OPTIONS,
  MERGE_FIELDS,
  PROPOSAL_TYPES,
  PROPOSAL_TYPES_MORE,
  QUICK_ACTIONS,
  SCORE_FACTORS,
  SIGNATURE_STATES,
  STYLE_OPTIONS,
  scoreTone,
  type DocumentRatio,
  type ExportQuality,
  type FinancialSettings,
  type PageKind,
  type PageMargins,
  type PageOrientation,
  type PrbLeftRailId,
  type PrbPage,
  type PrbRightRailId,
  type ProposalBrief,
  type ProposalScores,
  type ProposalType,
  type QuickActionKey,
  type SignatureState,
  type SuggestionKey,
} from './proposal-builder-model';
import { PrbZoomControls } from './prb-zoom-controls';

type LocalRailProps = {
  side: 'left' | 'right';
  items: { id: string; icon: IhIconName; label: string }[];
  activeId: string;
  onSelect: (id: string) => void;
};

export function PrbLocalRail({ side, items, activeId, onSelect }: LocalRailProps) {
  return (
    <div
      className={`prb-ws__local-rail prb-ws__local-rail--${side} cs-local-rail`}
      role="tablist"
      aria-orientation="vertical"
      data-testid={`prb-local-rail-${side}`}
    >
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={activeId === item.id}
          className={`prb-ws__local-rail-btn cs-local-rail-btn${activeId === item.id ? ' is-active' : ''}`}
          title={item.label}
          aria-label={item.label}
          data-testid={`prb-local-rail-${side}-${item.id}`}
          onClick={() => onSelect(item.id)}
        >
          <IhIcon name={item.icon} size={15} />
        </button>
      ))}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="prb-ws__field">
      <span>{label}</span>
      {children}
    </label>
  );
}

export type PrbLeftRailDrawerProps = {
  id: PrbLeftRailId;
  brief: ProposalBrief;
  setBrief: (updater: (prev: ProposalBrief) => ProposalBrief) => void;
  financials: FinancialSettings;
  setFinancials: (updater: (prev: FinancialSettings) => FinancialSettings) => void;
  aiInstructions: string;
  setAiInstructions: (v: string) => void;
  showMoreTypes: boolean;
  setShowMoreTypes: (v: boolean | ((p: boolean) => boolean)) => void;
  pages: PrbPage[];
  selectedPageId: string;
  setSelectedPageId: (id: string) => void;
  setPages: (updater: (prev: PrbPage[]) => PrbPage[]) => void;
  enabledSources: Set<string>;
  setEnabledSources: (updater: (prev: Set<string>) => Set<string>) => void;
  onApplyType: (type: ProposalType) => void;
  onAddPage: () => void;
  onGenerate: () => void;
  generating: boolean;
  markDirty: () => void;
  onToast: (msg: string) => void;
};

export function PrbLeftRailDrawer(props: PrbLeftRailDrawerProps) {
  const { id } = props;
  if (id === 'content') return <ContentDrawer {...props} />;
  if (id === 'pages') return <PagesDrawer {...props} />;
  if (id === 'design') return <DesignDrawer {...props} />;
  if (id === 'components') return <ComponentsDrawer {...props} />;
  if (id === 'data') return <DataDrawer {...props} />;
  if (id === 'media') return <MediaDrawer {...props} />;
  if (id === 'brand') return <BrandDrawer {...props} />;
  return <SettingsDrawer {...props} />;
}

function ContentDrawer({
  pages,
  selectedPageId,
  setSelectedPageId,
  onAddPage,
  onToast,
}: PrbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.proposalBuilder');
  const [tab, setTab] = useState<'sections' | 'customize'>('sections');

  return (
    <div className="prb-ws__rail-panel" data-testid="prb-rail-left-content">
      <div className="prb-ws__rail-panel-head">
        <h2>{t('rails.content.title')}</h2>
        <StatusChip tone="info">{t('left.ready')}</StatusChip>
      </div>
      <div className="prb-ws__rail-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'sections'}
          className={`prb-ws__rail-tab${tab === 'sections' ? ' is-active' : ''}`}
          onClick={() => setTab('sections')}
        >
          {t('rails.content.sections')}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'customize'}
          className={`prb-ws__rail-tab${tab === 'customize' ? ' is-active' : ''}`}
          onClick={() => setTab('customize')}
        >
          {t('rails.content.customize')}
        </button>
      </div>
      <div className="prb-ws__rail-panel-body prb-ws__left-stack">
        {tab === 'sections' ? (
          <>
            <p className="prb-ws__section-label">{t('rails.content.suggested')}</p>
            <p className="prb-ws__muted">{t('rails.content.sectionsHelp')}</p>
            <div className="prb-ws__section-suggest-list">
              {CONTENT_SECTION_SUGGESTIONS.map((item) => {
                const existing = pages.find((p) => p.kind === item.kind);
                return (
                  <button
                    key={item.kind}
                    type="button"
                    className={`prb-ws__section-suggest${existing?.id === selectedPageId ? ' is-active' : ''}`}
                    data-testid={`prb-section-suggest-${item.kind}`}
                    onClick={() => {
                      if (existing) {
                        setSelectedPageId(existing.id);
                        return;
                      }
                      onToast(t('toasts.sectionMissing'));
                    }}
                  >
                    <span className="prb-ws__section-suggest-icon">
                      <IhIcon name={item.icon} size={14} />
                    </span>
                    <span className="prb-ws__section-suggest-copy">
                      <strong>{t(`pages.${item.kind}.title`)}</strong>
                      <em>{t(`pages.${item.kind}.body`)}</em>
                    </span>
                    <span className="prb-ws__section-suggest-add" aria-hidden="true">
                      <IhIcon name="plus" size={12} />
                    </span>
                  </button>
                );
              })}
            </div>
          </>
        ) : (
          <div className="prb-ws__panel-card">
            <p className="prb-ws__section-label">{t('rails.content.customizeTitle')}</p>
            <p className="prb-ws__muted">{t('rails.content.customizeHelp')}</p>
            <div className="prb-ws__chip-row">
              {(['tone', 'density', 'emphasis'] as const).map((key) => (
                <span key={key} className="prb-ws__chip is-good">
                  {t(`rails.content.customizeOptions.${key}`)}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
      {tab === 'sections' ? (
        <div className="prb-ws__left-footer">
          <Button
            variant="secondary"
            size="sm"
            data-testid="prb-add-custom-section"
            onClick={onAddPage}
            className="prb-ws__generate-btn"
          >
            <IhIcon name="plus" size={12} />
            {t('rails.content.addCustom')}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function PagesDrawer({
  pages,
  selectedPageId,
  setSelectedPageId,
  setPages,
  onAddPage,
  markDirty,
}: PrbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.proposalBuilder');

  return (
    <div className="prb-ws__rail-panel" data-testid="prb-rail-left-pages">
      <div className="prb-ws__rail-panel-head">
        <h2>{t('rails.pages.title')}</h2>
        <StatusChip tone="info">{t('right.pagesCount', { count: pages.length })}</StatusChip>
      </div>
      <div className="prb-ws__rail-panel-body prb-ws__left-stack">
        <div className="prb-ws__pages-list" data-testid="prb-pages-list">
          {pages.map((page, index) => (
            <button
              key={page.id}
              type="button"
              draggable
              className={`prb-ws__pages-row${selectedPageId === page.id ? ' is-active' : ''}`}
              data-testid={`prb-pages-row-${page.id}`}
              onClick={() => setSelectedPageId(page.id)}
              onDragStart={(e) => e.dataTransfer.setData('text/prb-page', page.id)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                const fromId = e.dataTransfer.getData('text/prb-page');
                if (!fromId || fromId === page.id) return;
                setPages((prev) => {
                  const from = prev.findIndex((p) => p.id === fromId);
                  const to = prev.findIndex((p) => p.id === page.id);
                  if (from < 0 || to < 0 || from === to) return prev;
                  const next = [...prev];
                  const [moved] = next.splice(from, 1);
                  if (!moved) return prev;
                  next.splice(to, 0, moved);
                  return next;
                });
                markDirty();
              }}
            >
              <span className="prb-ws__pages-num">{index + 1}</span>
              <span className="prb-ws__pages-copy">
                <strong>{t(`pages.${page.kind}.title`)}</strong>
                <em>{t(`pageStatus.${page.status}`)}</em>
              </span>
            </button>
          ))}
        </div>
        <Button variant="secondary" size="sm" onClick={onAddPage} data-testid="prb-pages-add">
          <IhIcon name="plus" size={12} />
          {t('rails.pages.add')}
        </Button>
      </div>
    </div>
  );
}

function DesignDrawer({ brief, setBrief, markDirty }: PrbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.proposalBuilder');

  return (
    <div className="prb-ws__rail-panel" data-testid="prb-rail-left-design">
      <div className="prb-ws__rail-panel-head">
        <h2>{t('rails.design.title')}</h2>
      </div>
      <div className="prb-ws__rail-panel-body prb-ws__left-stack">
        <Field label={t('brief.style')}>
          <select
            value={brief.style}
            onChange={(e) => {
              setBrief((prev) => ({ ...prev, style: e.target.value }));
              markDirty();
            }}
          >
            {STYLE_OPTIONS.map((style) => (
              <option key={style} value={style}>
                {t(`styles.${style}`)}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t('brief.language')}>
          <select
            value={brief.language}
            onChange={(e) => {
              setBrief((prev) => ({ ...prev, language: e.target.value }));
              markDirty();
            }}
          >
            {LANGUAGE_OPTIONS.map((lang) => (
              <option key={lang} value={lang}>
                {t(`languages.${lang}`)}
              </option>
            ))}
          </select>
        </Field>
        <p className="prb-ws__muted">{t('rails.design.help')}</p>
        <div className="prb-ws__design-swatches" aria-hidden="true">
          <span style={{ background: '#075b75' }} />
          <span style={{ background: '#58aebb' }} />
          <span style={{ background: '#1e2b33' }} />
          <span style={{ background: '#e8eef1' }} />
        </div>
      </div>
    </div>
  );
}

function ComponentsDrawer({ onToast }: PrbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.proposalBuilder');

  return (
    <div className="prb-ws__rail-panel" data-testid="prb-rail-left-components">
      <div className="prb-ws__rail-panel-head">
        <h2>{t('rails.components.title')}</h2>
      </div>
      <div className="prb-ws__rail-panel-body prb-ws__left-stack">
        <p className="prb-ws__muted">{t('rails.components.help')}</p>
        <div className="prb-ws__component-grid">
          {COMPONENT_LIBRARY.map((item) => (
            <button
              key={item.key}
              type="button"
              className="prb-ws__component-card"
              data-testid={`prb-component-${item.key}`}
              onClick={() => onToast(t(`rails.components.toasts.${item.key}`))}
            >
              <IhIcon name={item.icon} size={14} />
              <span>{t(`rails.components.items.${item.key}`)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function DataDrawer({ financials, setFinancials, markDirty }: PrbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.proposalBuilder');

  return (
    <div className="prb-ws__rail-panel" data-testid="prb-rail-left-data">
      <div className="prb-ws__rail-panel-head">
        <h2>{t('rails.data.title')}</h2>
      </div>
      <div className="prb-ws__rail-panel-body prb-ws__left-stack">
        <p className="prb-ws__muted">{t('rails.data.help')}</p>
        {(
          ['currency', 'amount', 'roi', 'irr', 'cashFlow', 'paymentSchedule', 'scenario'] as const
        ).map((field) => (
          <Field key={field} label={t(`financial.${field}`)}>
            <input
              value={financials[field]}
              onChange={(e) => {
                setFinancials((prev) => ({ ...prev, [field]: e.target.value }));
                markDirty();
              }}
            />
          </Field>
        ))}
        <p className="prb-ws__section-label">{t('personalization.title')}</p>
        <div className="prb-ws__merge-grid">
          {MERGE_FIELDS.map((key) => (
            <span key={key} className="prb-ws__merge-chip">
              {`{{${key}}}`}
              <em>{t(`personalization.fields.${key}`)}</em>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function MediaDrawer({ enabledSources, setEnabledSources, markDirty }: PrbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.proposalBuilder');

  return (
    <div className="prb-ws__rail-panel" data-testid="prb-rail-left-media">
      <div className="prb-ws__rail-panel-head">
        <h2>{t('rails.media.title')}</h2>
      </div>
      <div className="prb-ws__rail-panel-body prb-ws__left-stack">
        <p className="prb-ws__muted">{t('sources.help')}</p>
        <div className="prb-ws__sources-list">
          {AI_SOURCES.map((key) => {
            const on = enabledSources.has(key);
            return (
              <button
                key={key}
                type="button"
                className="prb-ws__source-row"
                data-testid={`prb-source-${key}`}
                onClick={() => {
                  setEnabledSources((prev) => {
                    const next = new Set(prev);
                    if (next.has(key)) next.delete(key);
                    else next.add(key);
                    return next;
                  });
                  markDirty();
                }}
              >
                <span className="prb-ws__source-check" aria-hidden="true">
                  {on ? '✓' : '○'}
                </span>
                <span>{t(`aiSources.items.${key}`)}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function BrandDrawer({ brief, setBrief, markDirty }: PrbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.proposalBuilder');

  return (
    <div className="prb-ws__rail-panel" data-testid="prb-rail-left-brand">
      <div className="prb-ws__rail-panel-head">
        <h2>{t('rails.brand.title')}</h2>
        <StatusChip tone="success">{t('rails.brand.compliant')}</StatusChip>
      </div>
      <div className="prb-ws__rail-panel-body prb-ws__left-stack">
        <p className="prb-ws__muted">{t('rails.brand.help')}</p>
        <div className="prb-ws__chip-row">
          {BRAND_KIT.map((key) => (
            <span key={key} className="prb-ws__chip is-good">
              {t(`brandKit.${key}`)}
            </span>
          ))}
        </div>
        <Field label={t('brief.style')}>
          <select
            value={brief.style}
            onChange={(e) => {
              setBrief((prev) => ({ ...prev, style: e.target.value }));
              markDirty();
            }}
          >
            {STYLE_OPTIONS.map((style) => (
              <option key={style} value={style}>
                {t(`styles.${style}`)}
              </option>
            ))}
          </select>
        </Field>
      </div>
    </div>
  );
}

function SettingsDrawer({
  brief,
  setBrief,
  aiInstructions,
  setAiInstructions,
  showMoreTypes,
  setShowMoreTypes,
  onApplyType,
  onGenerate,
  generating,
  markDirty,
  onToast,
}: PrbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.proposalBuilder');
  const typeOptions = showMoreTypes
    ? [...PROPOSAL_TYPES, ...PROPOSAL_TYPES_MORE]
    : PROPOSAL_TYPES;

  return (
    <div className="prb-ws__rail-panel" data-testid="prb-rail-left-settings">
      <div className="prb-ws__rail-panel-head">
        <h2>{t('rails.settings.title')}</h2>
      </div>
      <div className="prb-ws__rail-panel-body prb-ws__left-stack">
        <p className="prb-ws__section-label">{t('brief.proposalType')}</p>
        <div className="prb-ws__type-grid" data-testid="prb-proposal-types">
          {typeOptions.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`prb-ws__type-card${brief.proposalType === item.key ? ' is-active' : ''}`}
              data-testid={`prb-type-${item.key}`}
              onClick={() => onApplyType(item.key)}
            >
              <IhIcon name={item.icon} size={14} />
              <span>{t(`proposalTypes.${item.key}`)}</span>
            </button>
          ))}
        </div>
        <button
          type="button"
          className="prb-ws__link-btn"
          onClick={() => setShowMoreTypes((v) => !v)}
        >
          {showMoreTypes ? t('brief.showFewerTypes') : t('brief.showMoreTypes')}
        </button>
        <Field label={t('brief.audience')}>
          <input
            value={brief.audience}
            onChange={(e) => {
              setBrief((prev) => ({ ...prev, audience: e.target.value }));
              markDirty();
            }}
          />
        </Field>
        <Field label={t('brief.goal')}>
          <input
            value={brief.goal}
            onChange={(e) => {
              setBrief((prev) => ({ ...prev, goal: e.target.value }));
              markDirty();
            }}
          />
        </Field>
        <Field label={t('brief.topic')}>
          <textarea
            rows={3}
            maxLength={200}
            value={brief.topic}
            onChange={(e) => {
              setBrief((prev) => ({ ...prev, topic: e.target.value }));
              markDirty();
            }}
          />
        </Field>
        <Field label={t('brief.cta')}>
          <input
            value={brief.cta}
            onChange={(e) => {
              setBrief((prev) => ({ ...prev, cta: e.target.value }));
              markDirty();
            }}
          />
        </Field>
        <Field label={t('instructions.label')}>
          <textarea rows={4} value={aiInstructions} onChange={(e) => setAiInstructions(e.target.value)} />
        </Field>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onToast(t('toasts.personalized'))}
        >
          {t('personalization.generateVariant')}
        </Button>
        <Button
          variant="primary"
          size="sm"
          disabled={generating}
          data-testid="prb-generate"
          onClick={onGenerate}
        >
          <IhIcon name="sparkles" size={12} />
          {generating ? t('generating') : t('generate')}
        </Button>
      </div>
    </div>
  );
}

export type PrbRightRailDrawerProps = {
  id: PrbRightRailId;
  scores: ProposalScores;
  pages: PrbPage[];
  minutes: number;
  completeness: number;
  appliedSuggestions: Set<SuggestionKey>;
  onApplySuggestion: (key: SuggestionKey) => void;
  onQuickAction: (key: QuickActionKey) => void;
  signatureState: SignatureState;
  setSignatureState: (s: SignatureState) => void;
  exportQuality: ExportQuality;
  setExportQuality: (q: ExportQuality) => void;
  includeNotes: boolean;
  setIncludeNotes: (v: boolean) => void;
  includeWatermark: boolean;
  setIncludeWatermark: (v: boolean) => void;
  includePageNumbers: boolean;
  setIncludePageNumbers: (v: boolean) => void;
  docRatio: DocumentRatio;
  setDocRatio: (r: DocumentRatio) => void;
  orientation: PageOrientation;
  setOrientation: (o: PageOrientation) => void;
  margins: PageMargins;
  setMargins: (updater: (prev: PageMargins) => PageMargins) => void;
  bgColor: boolean;
  setBgColor: (v: boolean) => void;
  bgImage: boolean;
  setBgImage: (v: boolean) => void;
  showHeader: boolean;
  setShowHeader: (v: boolean) => void;
  showFooter: boolean;
  setShowFooter: (v: boolean) => void;
  onDownload: () => void;
  onToast: (msg: string) => void;
  onChooseAsset?: () => void;
};

export function PrbRightRailDrawer(props: PrbRightRailDrawerProps) {
  const { id } = props;
  if (id === 'page') return <PageSettingsDrawer {...props} />;
  if (id === 'score') return <ScoreDrawer {...props} />;
  if (id === 'suggestions') return <SuggestionsDrawer {...props} />;
  if (id === 'signature') return <SignatureDrawer {...props} />;
  if (id === 'export') return <ExportDrawer {...props} />;
  return <HistoryDrawer {...props} />;
}

function PageSettingsDrawer({
  docRatio,
  setDocRatio,
  orientation,
  setOrientation,
  margins,
  setMargins,
  bgColor,
  setBgColor,
  bgImage,
  setBgImage,
  includePageNumbers,
  setIncludePageNumbers,
  showHeader,
  setShowHeader,
  showFooter,
  setShowFooter,
  onToast,
  onChooseAsset,
}: PrbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.proposalBuilder');
  const tPicker = useTranslations('creativeStudio.mediaPicker');

  function updateMargin(edge: keyof Omit<PageMargins, 'linked'>, value: number) {
    setMargins((prev) => {
      if (prev.linked) {
        return { ...prev, top: value, bottom: value, left: value, right: value };
      }
      return { ...prev, [edge]: value };
    });
  }

  return (
    <div className="prb-ws__rail-panel" data-testid="prb-rail-right-page">
      <div className="prb-ws__rail-panel-head">
        <h2>{t('rails.page.title')}</h2>
      </div>
      <div className="prb-ws__rail-panel-body prb-ws__right-stack">
        <p className="prb-ws__section-label">{t('rails.page.settingsTitle')}</p>
        <Field label={t('rails.page.size')}>
          <select
            value={docRatio}
            onChange={(e) => setDocRatio(e.target.value as DocumentRatio)}
            data-testid="prb-page-size"
          >
            {DOCUMENT_RATIOS.map((ratio) => (
              <option key={ratio} value={ratio}>
                {t(`documentRatios.${ratio}`)}
              </option>
            ))}
          </select>
        </Field>
        <div className="prb-ws__field">
          <span>{t('rails.page.orientation')}</span>
          <div className="prb-ws__orient-toggle" role="group" aria-label={t('rails.page.orientation')}>
            <button
              type="button"
              className={`prb-ws__orient-btn${orientation === 'portrait' ? ' is-active' : ''}`}
              aria-pressed={orientation === 'portrait'}
              data-testid="prb-orient-portrait"
              onClick={() => setOrientation('portrait')}
              title={t('rails.page.portrait')}
              aria-label={t('rails.page.portrait')}
            >
              <span className="prb-ws__orient-glyph prb-ws__orient-glyph--portrait" aria-hidden="true" />
            </button>
            <button
              type="button"
              className={`prb-ws__orient-btn${orientation === 'landscape' ? ' is-active' : ''}`}
              aria-pressed={orientation === 'landscape'}
              data-testid="prb-orient-landscape"
              onClick={() => setOrientation('landscape')}
              title={t('rails.page.landscape')}
              aria-label={t('rails.page.landscape')}
            >
              <span className="prb-ws__orient-glyph prb-ws__orient-glyph--landscape" aria-hidden="true" />
            </button>
          </div>
        </div>
        <div className="prb-ws__field">
          <span>{t('rails.page.marginsMm')}</span>
          <div className="prb-ws__margin-grid">
            {(['top', 'bottom', 'left', 'right'] as const).map((edge) => (
              <label key={edge} className="prb-ws__margin-field">
                <span>{t(`rails.page.marginEdges.${edge}`)}</span>
                <input
                  type="number"
                  min={0}
                  max={80}
                  value={margins[edge]}
                  data-testid={`prb-margin-${edge}`}
                  onChange={(e) => updateMargin(edge, Number(e.target.value) || 0)}
                />
              </label>
            ))}
            <button
              type="button"
              className={`prb-ws__margin-link${margins.linked ? ' is-active' : ''}`}
              aria-pressed={margins.linked}
              data-testid="prb-margin-link"
              title={t('rails.page.linkMargins')}
              onClick={() => setMargins((prev) => ({ ...prev, linked: !prev.linked }))}
            >
              <IhIcon name="refresh" size={12} />
            </button>
          </div>
        </div>
        <div className="prb-ws__field">
          <span>{t('rails.page.background')}</span>
          <div className="prb-ws__bg-opts">
            <label className="prb-ws__check">
              <input type="checkbox" checked={bgColor} onChange={(e) => setBgColor(e.target.checked)} />
              <span>{t('rails.page.bgColor')}</span>
            </label>
            <label className="prb-ws__check">
              <input type="checkbox" checked={bgImage} onChange={(e) => setBgImage(e.target.checked)} />
              <span>{t('rails.page.bgImage')}</span>
            </label>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                if (onChooseAsset) onChooseAsset();
                else onToast(t('rails.page.uploadToast'));
              }}
            >
              {tPicker('chooseAsset')}
            </Button>
          </div>
        </div>
        <div className="prb-ws__toggle-stack">
          <label className="prb-ws__toggle-row">
            <span>{t('rails.page.pageNumber')}</span>
            <input
              type="checkbox"
              checked={includePageNumbers}
              onChange={(e) => setIncludePageNumbers(e.target.checked)}
            />
          </label>
          <label className="prb-ws__toggle-row">
            <span>{t('rails.page.header')}</span>
            <input type="checkbox" checked={showHeader} onChange={(e) => setShowHeader(e.target.checked)} />
          </label>
          <label className="prb-ws__toggle-row">
            <span>{t('rails.page.footer')}</span>
            <input type="checkbox" checked={showFooter} onChange={(e) => setShowFooter(e.target.checked)} />
          </label>
        </div>
      </div>
    </div>
  );
}

function ScoreDrawer({ scores, pages, minutes, completeness }: PrbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.proposalBuilder');

  return (
    <div className="prb-ws__rail-panel" data-testid="prb-rail-right-score">
      <div className="prb-ws__rail-panel-head">
        <h2>{t('rails.score.title')}</h2>
        <StatusChip tone={scoreTone(scores.overall)}>{t('right.excellent')}</StatusChip>
      </div>
      <div className="prb-ws__rail-panel-body prb-ws__right-stack">
        <div className="prb-ws__panel-card prb-ws__score-hero-card" data-testid="prb-overall-score">
          <div
            className="prb-ws__score-ring"
            style={{ ['--score' as string]: scores.overall }}
            aria-label={t('right.overallScore')}
          >
            <strong>{scores.overall}</strong>
            <span>/ 100</span>
          </div>
          <div>
            <p className="prb-ws__score-hero-title">{t('right.overallScore')}</p>
            <div className="prb-ws__readiness">
              <div>
                <strong>{t('right.pagesCount', { count: pages.length })}</strong>
                <span> · {t('right.readingTime', { minutes })}</span>
              </div>
              <div>
                {t('right.completeness', { pct: completeness })} · {t('right.investorReady')}
              </div>
            </div>
          </div>
        </div>
        <div className="prb-ws__panel-card">
          {SCORE_FACTORS.map((factor) => (
            <div key={factor.key} className={`prb-ws__score-factor is-${factor.tone}`}>
              <span aria-hidden="true">{factor.tone === 'good' ? '✓' : '△'}</span>
              <span>{t(`right.scoreFactors.${factor.key}`)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SuggestionsDrawer({
  appliedSuggestions,
  onApplySuggestion,
  onQuickAction,
}: PrbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.proposalBuilder');

  return (
    <div className="prb-ws__rail-panel" data-testid="prb-rail-right-suggestions">
      <div className="prb-ws__rail-panel-head">
        <h2>{t('rails.suggestions.title')}</h2>
      </div>
      <div className="prb-ws__rail-panel-body prb-ws__right-stack">
        <div className="prb-ws__suggestions" data-testid="prb-suggestions">
          {AI_SUGGESTIONS.map((key, index) => (
            <div key={key} className="prb-ws__suggestion-card">
              <span className={`prb-ws__suggestion-dot is-tone-${(index % 3) + 1}`} aria-hidden="true" />
              <span>{t(`suggestions.${key}`)}</span>
              <Button
                variant="secondary"
                size="sm"
                disabled={appliedSuggestions.has(key)}
                onClick={() => onApplySuggestion(key)}
              >
                {appliedSuggestions.has(key) ? t('right.applied') : t('right.apply')}
              </Button>
            </div>
          ))}
        </div>
        <p className="prb-ws__section-label">{t('right.quickActionsTitle')}</p>
        <div className="prb-ws__quick-grid">
          {QUICK_ACTIONS.slice(0, 6).map((action) => (
            <button
              key={action.key}
              type="button"
              className="prb-ws__quick-btn"
              onClick={() => onQuickAction(action.key)}
            >
              <IhIcon name={action.icon} size={13} />
              <span>{t(`quickActions.${action.key}`)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function SignatureDrawer({ signatureState, setSignatureState }: PrbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.proposalBuilder');

  return (
    <div className="prb-ws__rail-panel" data-testid="prb-rail-right-signature">
      <div className="prb-ws__rail-panel-head">
        <h2>{t('rails.signature.title')}</h2>
      </div>
      <div className="prb-ws__rail-panel-body prb-ws__right-stack">
        <p className="prb-ws__muted">{t('rails.signature.help')}</p>
        <div className="prb-ws__sig-row" data-testid="prb-signature">
          {SIGNATURE_STATES.map((state) => (
            <button
              key={state}
              type="button"
              className={`prb-ws__sig-chip${signatureState === state ? ' is-active' : ''}`}
              onClick={() => setSignatureState(state)}
            >
              {t(`signature.${state}`)}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function ExportDrawer({
  exportQuality,
  setExportQuality,
  includeNotes,
  setIncludeNotes,
  includeWatermark,
  setIncludeWatermark,
  includePageNumbers,
  setIncludePageNumbers,
  onDownload,
  onToast,
}: PrbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.proposalBuilder');

  return (
    <div className="prb-ws__rail-panel" data-testid="prb-rail-right-export">
      <div className="prb-ws__rail-panel-head">
        <h2>{t('rails.export.title')}</h2>
      </div>
      <div className="prb-ws__rail-panel-body prb-ws__right-stack">
        <div className="prb-ws__export-group" data-testid="prb-export-digital">
          <p className="prb-ws__export-group-label">{t('right.exportDigital')}</p>
          <div className="prb-ws__export-grid prb-ws__export-primary">
            {DIGITAL_EXPORTS.map((key) => (
              <button
                key={key}
                type="button"
                className="prb-ws__export-chip is-primary"
                onClick={() => onToast(t(`right.exports.${key}`))}
              >
                {t(`right.exports.${key}`)}
              </button>
            ))}
          </div>
        </div>
        <div className="prb-ws__export-group" data-testid="prb-export-document">
          <p className="prb-ws__export-group-label">{t('right.exportDocument')}</p>
          <div className="prb-ws__export-grid">
            {DOCUMENT_EXPORTS.map((key) => (
              <button
                key={key}
                type="button"
                className="prb-ws__export-chip"
                onClick={() => onToast(t(`right.exports.${key}`))}
              >
                {t(`right.exports.${key}`)}
              </button>
            ))}
          </div>
        </div>
        <Field label={t('right.exportQuality')}>
          <select
            value={exportQuality}
            onChange={(e) => setExportQuality(e.target.value as ExportQuality)}
          >
            {EXPORT_QUALITY_OPTIONS.map((q) => (
              <option key={q} value={q}>
                {t(`right.quality.${q}`)}
              </option>
            ))}
          </select>
        </Field>
        <label className="prb-ws__check">
          <input type="checkbox" checked={includeNotes} onChange={(e) => setIncludeNotes(e.target.checked)} />
          <span>{t('right.includeNotes')}</span>
        </label>
        <label className="prb-ws__check">
          <input
            type="checkbox"
            checked={includeWatermark}
            onChange={(e) => setIncludeWatermark(e.target.checked)}
          />
          <span>{t('right.includeWatermark')}</span>
        </label>
        <label className="prb-ws__check">
          <input
            type="checkbox"
            checked={includePageNumbers}
            onChange={(e) => setIncludePageNumbers(e.target.checked)}
          />
          <span>{t('right.includePageNumbers')}</span>
        </label>
        <Button variant="primary" size="sm" data-testid="prb-download" onClick={onDownload}>
          {t('right.download')}
        </Button>
      </div>
    </div>
  );
}

function HistoryDrawer({ onToast }: PrbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.proposalBuilder');

  return (
    <div className="prb-ws__rail-panel" data-testid="prb-rail-right-history">
      <div className="prb-ws__rail-panel-head">
        <h2>{t('rails.history.title')}</h2>
      </div>
      <div className="prb-ws__rail-panel-body prb-ws__right-stack">
        <div className="prb-ws__history-list">
          {HISTORY_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className="prb-ws__history-row"
              onClick={() => onToast(t('rails.history.restored'))}
            >
              <strong>{t(`rails.history.items.${item.labelKey}`)}</strong>
              <span>{item.time}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ─── Zoom toolbar ─────────────────────────────────────────────── */

export type PrbZoomToolbarProps = {
  engine: {
    mode: string;
    zoomPercent: number;
    autoFit: boolean;
    fitToView: () => void;
    actualSize: () => void;
    setPercent: (n: number) => void;
    setAutoFit: (v: boolean) => void;
  };
  canvasLocked: boolean;
  onToggleLock: () => void;
  isFullscreen: boolean;
  onToggleFullscreen: () => void;
};

const ZOOM_STEP = 10;
const ZOOM_MIN = 10;
const ZOOM_MAX = 400;

export function PrbZoomToolbar({
  engine,
  canvasLocked,
  onToggleLock,
  isFullscreen,
  onToggleFullscreen,
}: PrbZoomToolbarProps) {
  const t = useTranslations('creativeStudio.ds.proposalBuilder');
  const percent = Math.round(engine.zoomPercent);

  function zoomBy(delta: number) {
    if (canvasLocked) return;
    engine.setPercent(Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, percent + delta)));
  }

  return (
    <div
      className="prb-ws__zoom-bar"
      role="toolbar"
      aria-label={t('canvas.zoomBarAria')}
      data-testid="prb-zoom-bar"
    >
      <div className="prb-ws__zoom-bar-modes" role="group">
        <button
          type="button"
          className={`prb-ws__fit-btn${engine.mode === 'fit' ? ' is-active' : ''}`}
          aria-pressed={engine.mode === 'fit'}
          data-testid="prb-ftv-fit"
          disabled={canvasLocked}
          onClick={() => engine.fitToView()}
        >
          {t('canvas.fitModes.fit')}
        </button>
        <button
          type="button"
          className={`prb-ws__fit-btn${engine.mode === 'actual' ? ' is-active' : ''}`}
          aria-pressed={engine.mode === 'actual'}
          data-testid="prb-ftv-actual"
          disabled={canvasLocked}
          onClick={() => engine.actualSize()}
        >
          {t('canvas.fitModes.actual')}
        </button>
      </div>

      <PrbZoomControls
        percent={percent}
        disabledOut={percent <= ZOOM_MIN || canvasLocked}
        disabledIn={percent >= ZOOM_MAX || canvasLocked}
        onZoomOut={() => zoomBy(-ZOOM_STEP)}
        onZoomIn={() => zoomBy(ZOOM_STEP)}
        onReset={() => {
          if (!canvasLocked) engine.actualSize();
        }}
      />

      <label className="prb-ws__auto-fit" data-testid="prb-auto-fit">
        <input
          type="checkbox"
          checked={engine.autoFit}
          disabled={canvasLocked}
          onChange={(e) => engine.setAutoFit(e.target.checked)}
        />
        <span>{t('canvas.autoFit')}</span>
      </label>

      <button
        type="button"
        className={`prb-ws__fit-btn${canvasLocked ? ' is-active' : ''}`}
        aria-pressed={canvasLocked}
        data-testid="prb-lock-canvas"
        onClick={onToggleLock}
      >
        {t('canvas.lockCanvas')}
      </button>

      <button
        type="button"
        className={`prb-ws__fit-btn${isFullscreen ? ' is-active' : ''}`}
        aria-pressed={isFullscreen}
        data-testid="prb-fullscreen-zoom"
        onClick={onToggleFullscreen}
      >
        {t('canvas.fullscreenShort')}
      </button>
    </div>
  );
}
