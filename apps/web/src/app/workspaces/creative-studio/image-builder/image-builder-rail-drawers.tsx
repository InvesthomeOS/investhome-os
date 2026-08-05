'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

import {
  ASPECT_RATIOS,
  BLEED_OPTIONS,
  COLOR_PROFILES,
  COLLECTIONS,
  DIGITAL_FORMATS,
  DIGITAL_PRESETS,
  IB_AI_TOOLS,
  IB_BG_TOOLS,
  IB_EDIT_TOOLS,
  IB_ELEMENT_CATEGORIES,
  IB_MODEL_OPTIONS,
  IB_QUALITY_OPTIONS,
  IB_TEXT_ALIGN,
  IB_UPSCALE_OPTIONS,
  PRINT_DPI_OPTIONS,
  PRINT_FORMATS,
  PRINT_PRESETS,
  PRINT_RESOLUTIONS,
  PRINT_UNITS,
  STYLE_OPTIONS,
  applyPrintPreset,
  formatFileSize,
  type AspectRatio,
  type BleedKey,
  type ColorProfileKey,
  type DigitalPresetKey,
  type IbAiToolKey,
  type IbBgTool,
  type IbEditTool,
  type IbHistoryItem,
  type IbImageDetails,
  type IbLayer,
  type IbLeftRailId,
  type IbRightRailId,
  type ImageBrief,
  type PrintDpiKey,
  type PrintExportState,
  type PrintFormatKey,
  type PrintPresetKey,
  type PrintUnitKey,
  type PrintValidation,
  type PrintResolutionKey,
} from './image-builder-model';
import { IbZoomControls } from './ib-zoom-controls';

export type IbLocalRailProps = {
  side: 'left' | 'right';
  items: { id: string; icon: IhIconName; label: string }[];
  activeId: string;
  onSelect: (id: string) => void;
};

export function IbLocalRail({ side, items, activeId, onSelect }: IbLocalRailProps) {
  return (
    <div
      className={`ib-ws__local-rail ib-ws__local-rail--${side} cs-local-rail`}
      role="tablist"
      aria-orientation="vertical"
      data-testid={`ib-local-rail-${side}`}
    >
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={activeId === item.id}
          className={`ib-ws__local-rail-btn cs-local-rail-btn${activeId === item.id ? ' is-active' : ''}`}
          title={item.label}
          aria-label={item.label}
          data-testid={`ib-local-rail-${side}-${item.id}`}
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
    <label className="ib-ws__field">
      <span>{label}</span>
      {children}
    </label>
  );
}

/* ─── Left drawers ─────────────────────────────────────────────── */

export type IbLeftRailDrawerProps = {
  id: IbLeftRailId;
  brief: ImageBrief;
  setBrief: (updater: (prev: ImageBrief) => ImageBrief) => void;
  aspectRatio: AspectRatio;
  setAspectRatio: (v: AspectRatio) => void;
  model: string;
  setModel: (v: string) => void;
  quality: string;
  setQuality: (v: string) => void;
  imageCount: number;
  setImageCount: (v: number) => void;
  editTool: IbEditTool;
  setEditTool: (v: IbEditTool) => void;
  variationStrength: number;
  setVariationStrength: (v: number) => void;
  variationSeed: string;
  setVariationSeed: (v: string) => void;
  similarity: number;
  setSimilarity: (v: number) => void;
  upscaleFactor: string;
  setUpscaleFactor: (v: string) => void;
  faceEnhance: boolean;
  setFaceEnhance: (v: boolean) => void;
  sharpen: boolean;
  setSharpen: (v: boolean) => void;
  bgTool: IbBgTool;
  setBgTool: (v: IbBgTool) => void;
  textContent: string;
  setTextContent: (v: string) => void;
  textFont: string;
  setTextFont: (v: string) => void;
  textSize: number;
  setTextSize: (v: number) => void;
  textAlign: string;
  setTextAlign: (v: string) => void;
  layers: IbLayer[];
  setLayers: (updater: (prev: IbLayer[]) => IbLayer[]) => void;
  selectedLayerId: string;
  setSelectedLayerId: (id: string) => void;
  generating: boolean;
  onGenerate: () => void;
  onToast: (msg: string) => void;
  markDirty: () => void;
};

export function IbLeftRailDrawer(props: IbLeftRailDrawerProps) {
  const { id } = props;
  if (id === 'generate') return <GenerateDrawer {...props} />;
  if (id === 'edit') return <EditDrawer {...props} />;
  if (id === 'variation') return <VariationDrawer {...props} />;
  if (id === 'upscale') return <UpscaleDrawer {...props} />;
  if (id === 'background') return <BackgroundDrawer {...props} />;
  if (id === 'text') return <TextDrawer {...props} />;
  if (id === 'elements') return <ElementsDrawer {...props} />;
  return (
    <LayersPanel
      layers={props.layers}
      setLayers={props.setLayers}
      selectedLayerId={props.selectedLayerId}
      setSelectedLayerId={props.setSelectedLayerId}
      onToast={props.onToast}
      side="left"
      showReorder={false}
    />
  );
}

function GenerateDrawer({
  brief,
  setBrief,
  aspectRatio,
  setAspectRatio,
  model,
  setModel,
  quality,
  setQuality,
  imageCount,
  setImageCount,
  generating,
  onGenerate,
  onToast,
  markDirty,
}: IbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.imageBuilder');

  return (
    <div className="ib-ws__rail-panel" data-testid="ib-rail-left-generate">
      <div className="ib-ws__rail-panel-head">
        <h2>{t('rails.generate.title')}</h2>
        <StatusChip tone="info">{t('left.ready')}</StatusChip>
      </div>
      <div className="ib-ws__rail-panel-body ib-ws__left-stack">
        <Field label={t('rails.generate.model')}>
          <select
            value={model}
            onChange={(e) => {
              setModel(e.target.value);
              markDirty();
            }}
            data-testid="ib-model"
          >
            {IB_MODEL_OPTIONS.map((m) => (
              <option key={m} value={m}>
                {t(`rails.generate.models.${m}`)}
              </option>
            ))}
          </select>
        </Field>

        <Field label={t('rails.generate.prompt')}>
          <textarea
            rows={4}
            value={brief.prompt}
            onChange={(e) => {
              setBrief((prev) => ({ ...prev, prompt: e.target.value }));
              markDirty();
            }}
            data-testid="ib-prompt"
          />
        </Field>

        <Button
          variant="secondary"
          size="sm"
          data-testid="ib-prompt-assist"
          onClick={() => onToast(t('toasts.promptAssist'))}
        >
          <IhIcon name="sparkles" size={12} />
          {t('rails.generate.promptAssist')}
        </Button>

        <div>
          <p className="ib-ws__section-label">{t('rails.generate.aspectRatio')}</p>
          <div className="ib-ws__segment" data-testid="ib-aspect-ratio">
            {ASPECT_RATIOS.map((ratio) => (
              <button
                key={ratio}
                type="button"
                className={`ib-ws__segment-btn${aspectRatio === ratio ? ' is-active' : ''}`}
                aria-pressed={aspectRatio === ratio}
                onClick={() => {
                  setAspectRatio(ratio);
                  markDirty();
                }}
              >
                {ratio}
              </button>
            ))}
          </div>
        </div>

        <Field label={t('rails.generate.style')}>
          <select
            value={brief.style}
            onChange={(e) => {
              setBrief((prev) => ({ ...prev, style: e.target.value }));
              markDirty();
            }}
          >
            {STYLE_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {t(`styles.${s}`)}
              </option>
            ))}
          </select>
        </Field>

        <Field label={t('rails.generate.quality')}>
          <select
            value={quality}
            onChange={(e) => {
              setQuality(e.target.value);
              markDirty();
            }}
            data-testid="ib-quality"
          >
            {IB_QUALITY_OPTIONS.map((q) => (
              <option key={q} value={q}>
                {t(`rails.generate.qualities.${q}`)}
              </option>
            ))}
          </select>
        </Field>

        <Field label={t('rails.generate.imageCount')}>
          <input
            type="number"
            min={1}
            max={8}
            value={imageCount}
            onChange={(e) => {
              setImageCount(Math.max(1, Math.min(8, Number(e.target.value) || 1)));
              markDirty();
            }}
            data-testid="ib-image-count"
          />
        </Field>
      </div>
      <div className="ib-ws__left-footer">
        <Button
          variant="primary"
          size="md"
          className="ib-ws__generate-btn"
          disabled={generating}
          data-testid="ib-generate"
          onClick={onGenerate}
        >
          <IhIcon name="sparkles" size={14} />
          {generating ? t('generating') : t('rails.generate.generate')}
        </Button>
      </div>
    </div>
  );
}

function EditDrawer({ editTool, setEditTool, onToast }: IbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.imageBuilder');

  return (
    <div className="ib-ws__rail-panel" data-testid="ib-rail-left-edit">
      <div className="ib-ws__rail-panel-head">
        <h2>{t('rails.edit.title')}</h2>
      </div>
      <div className="ib-ws__rail-panel-body">
        <p className="ib-ws__section-label">{t('rails.edit.tools')}</p>
        <div className="ib-ws__tool-grid" data-testid="ib-edit-tools">
          {IB_EDIT_TOOLS.map((tool) => (
            <button
              key={tool.key}
              type="button"
              className={`ib-ws__tool-card${editTool === tool.key ? ' is-active' : ''}`}
              aria-pressed={editTool === tool.key}
              data-testid={`ib-edit-${tool.key}`}
              onClick={() => {
                setEditTool(tool.key);
                onToast(t(`rails.edit.toolsList.${tool.key}`));
              }}
            >
              <IhIcon name={tool.icon} size={16} />
              <span>{t(`rails.edit.toolsList.${tool.key}`)}</span>
            </button>
          ))}
        </div>
        <p className="ib-ws__muted">{t('rails.edit.hint')}</p>
      </div>
    </div>
  );
}

function VariationDrawer({
  variationStrength,
  setVariationStrength,
  variationSeed,
  setVariationSeed,
  similarity,
  setSimilarity,
  markDirty,
  onToast,
}: IbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.imageBuilder');

  return (
    <div className="ib-ws__rail-panel" data-testid="ib-rail-left-variation">
      <div className="ib-ws__rail-panel-head">
        <h2>{t('rails.variation.title')}</h2>
      </div>
      <div className="ib-ws__rail-panel-body ib-ws__left-stack">
        <Field label={`${t('rails.variation.strength')}: ${variationStrength}%`}>
          <input
            type="range"
            min={0}
            max={100}
            value={variationStrength}
            data-testid="ib-variation-strength"
            onChange={(e) => {
              setVariationStrength(Number(e.target.value));
              markDirty();
            }}
          />
        </Field>
        <Field label={t('rails.variation.seed')}>
          <input
            value={variationSeed}
            data-testid="ib-variation-seed"
            onChange={(e) => {
              setVariationSeed(e.target.value);
              markDirty();
            }}
          />
        </Field>
        <Field label={`${t('rails.variation.similarity')}: ${similarity}%`}>
          <input
            type="range"
            min={0}
            max={100}
            value={similarity}
            data-testid="ib-similarity"
            onChange={(e) => {
              setSimilarity(Number(e.target.value));
              markDirty();
            }}
          />
        </Field>
        <Button
          variant="primary"
          size="sm"
          data-testid="ib-apply-variation"
          onClick={() => onToast(t('toasts.variationApplied'))}
        >
          {t('rails.variation.apply')}
        </Button>
      </div>
    </div>
  );
}

function UpscaleDrawer({
  upscaleFactor,
  setUpscaleFactor,
  faceEnhance,
  setFaceEnhance,
  sharpen,
  setSharpen,
  markDirty,
  onToast,
}: IbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.imageBuilder');

  return (
    <div className="ib-ws__rail-panel" data-testid="ib-rail-left-upscale">
      <div className="ib-ws__rail-panel-head">
        <h2>{t('rails.upscale.title')}</h2>
      </div>
      <div className="ib-ws__rail-panel-body ib-ws__left-stack">
        <p className="ib-ws__section-label">{t('rails.upscale.factor')}</p>
        <div className="ib-ws__segment" data-testid="ib-upscale-factor">
          {IB_UPSCALE_OPTIONS.map((f) => (
            <button
              key={f}
              type="button"
              className={`ib-ws__segment-btn${upscaleFactor === f ? ' is-active' : ''}`}
              aria-pressed={upscaleFactor === f}
              onClick={() => {
                setUpscaleFactor(f);
                markDirty();
              }}
            >
              {f}
            </button>
          ))}
        </div>
        <label className="ib-ws__check">
          <input
            type="checkbox"
            checked={faceEnhance}
            data-testid="ib-face-enhance"
            onChange={(e) => {
              setFaceEnhance(e.target.checked);
              markDirty();
            }}
          />
          <span>{t('rails.upscale.faceEnhance')}</span>
        </label>
        <label className="ib-ws__check">
          <input
            type="checkbox"
            checked={sharpen}
            data-testid="ib-sharpen"
            onChange={(e) => {
              setSharpen(e.target.checked);
              markDirty();
            }}
          />
          <span>{t('rails.upscale.sharpen')}</span>
        </label>
        <Button
          variant="primary"
          size="sm"
          data-testid="ib-apply-upscale"
          onClick={() => onToast(t('toasts.upscaled'))}
        >
          {t('rails.upscale.apply')}
        </Button>
      </div>
    </div>
  );
}

function BackgroundDrawer({ bgTool, setBgTool, onToast }: IbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.imageBuilder');

  return (
    <div className="ib-ws__rail-panel" data-testid="ib-rail-left-background">
      <div className="ib-ws__rail-panel-head">
        <h2>{t('rails.background.title')}</h2>
      </div>
      <div className="ib-ws__rail-panel-body">
        <div className="ib-ws__tool-grid" data-testid="ib-bg-tools">
          {IB_BG_TOOLS.map((tool) => (
            <button
              key={tool.key}
              type="button"
              className={`ib-ws__tool-card${bgTool === tool.key ? ' is-active' : ''}`}
              aria-pressed={bgTool === tool.key}
              data-testid={`ib-bg-${tool.key}`}
              onClick={() => {
                setBgTool(tool.key);
                onToast(t(`rails.background.tools.${tool.key}`));
              }}
            >
              <IhIcon name={tool.icon} size={16} />
              <span>{t(`rails.background.tools.${tool.key}`)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function TextDrawer({
  textContent,
  setTextContent,
  textFont,
  setTextFont,
  textSize,
  setTextSize,
  textAlign,
  setTextAlign,
  markDirty,
  onToast,
}: IbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.imageBuilder');

  return (
    <div className="ib-ws__rail-panel" data-testid="ib-rail-left-text">
      <div className="ib-ws__rail-panel-head">
        <h2>{t('rails.text.title')}</h2>
      </div>
      <div className="ib-ws__rail-panel-body ib-ws__left-stack">
        <Button
          variant="secondary"
          size="sm"
          data-testid="ib-add-text"
          onClick={() => onToast(t('toasts.textAdded'))}
        >
          <IhIcon name="plus" size={12} />
          {t('rails.text.add')}
        </Button>
        <Field label={t('rails.text.content')}>
          <input
            value={textContent}
            onChange={(e) => {
              setTextContent(e.target.value);
              markDirty();
            }}
          />
        </Field>
        <Field label={t('rails.text.font')}>
          <select
            value={textFont}
            onChange={(e) => {
              setTextFont(e.target.value);
              markDirty();
            }}
          >
            <option value="Inter">Inter</option>
            <option value="Georgia">Georgia</option>
            <option value="Helvetica">Helvetica</option>
          </select>
        </Field>
        <Field label={t('rails.text.size')}>
          <input
            type="number"
            min={8}
            max={200}
            value={textSize}
            onChange={(e) => {
              setTextSize(Number(e.target.value) || 16);
              markDirty();
            }}
          />
        </Field>
        <div>
          <p className="ib-ws__section-label">{t('rails.text.alignment')}</p>
          <div className="ib-ws__segment">
            {IB_TEXT_ALIGN.map((a) => (
              <button
                key={a}
                type="button"
                className={`ib-ws__segment-btn${textAlign === a ? ' is-active' : ''}`}
                aria-pressed={textAlign === a}
                onClick={() => {
                  setTextAlign(a);
                  markDirty();
                }}
              >
                {t(`rails.text.align.${a}`)}
              </button>
            ))}
          </div>
        </div>
        <Field label={t('rails.text.effects')}>
          <select defaultValue="none" onChange={() => onToast(t('toasts.effectApplied'))}>
            <option value="none">{t('rails.text.effectOptions.none')}</option>
            <option value="shadow">{t('rails.text.effectOptions.shadow')}</option>
            <option value="outline">{t('rails.text.effectOptions.outline')}</option>
            <option value="glow">{t('rails.text.effectOptions.glow')}</option>
          </select>
        </Field>
      </div>
    </div>
  );
}

function ElementsDrawer({ onToast }: IbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.imageBuilder');
  const [category, setCategory] = useState<(typeof IB_ELEMENT_CATEGORIES)[number]>('shapes');

  return (
    <div className="ib-ws__rail-panel" data-testid="ib-rail-left-elements">
      <div className="ib-ws__rail-panel-head">
        <h2>{t('rails.elements.title')}</h2>
      </div>
      <div className="ib-ws__rail-panel-body ib-ws__left-stack">
        <div className="ib-ws__segment" data-testid="ib-element-cats">
          {IB_ELEMENT_CATEGORIES.map((c) => (
            <button
              key={c}
              type="button"
              className={`ib-ws__segment-btn${category === c ? ' is-active' : ''}`}
              aria-pressed={category === c}
              onClick={() => setCategory(c)}
            >
              {t(`rails.elements.categories.${c}`)}
            </button>
          ))}
        </div>
        <div className="ib-ws__element-grid">
          {[1, 2, 3, 4, 5, 6].map((n) => (
            <button
              key={n}
              type="button"
              className="ib-ws__element-card"
              onClick={() => onToast(t('toasts.elementAdded'))}
            >
              <IhIcon name="inventory" size={18} />
              <span>
                {t(`rails.elements.categories.${category}`)} {n}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

type LayersPanelProps = {
  layers: IbLayer[];
  setLayers: (updater: (prev: IbLayer[]) => IbLayer[]) => void;
  selectedLayerId: string;
  setSelectedLayerId: (id: string) => void;
  onToast: (msg: string) => void;
  side: 'left' | 'right';
  showReorder: boolean;
};

function LayersPanel({
  layers,
  setLayers,
  selectedLayerId,
  setSelectedLayerId,
  onToast,
  side,
  showReorder,
}: LayersPanelProps) {
  const t = useTranslations('creativeStudio.ds.imageBuilder');

  function toggleVisible(id: string) {
    setLayers((prev) =>
      prev.map((l) => (l.id === id ? { ...l, visible: !l.visible } : l)),
    );
  }

  function toggleLock(id: string) {
    setLayers((prev) =>
      prev.map((l) => (l.id === id ? { ...l, locked: !l.locked } : l)),
    );
  }

  function duplicateLayer(id: string) {
    setLayers((prev) => {
      const src = prev.find((l) => l.id === id);
      if (!src) return prev;
      const copy: IbLayer = {
        ...src,
        id: `l${Date.now()}`,
        name: `${src.name} copy`,
        locked: false,
      };
      const idx = prev.findIndex((l) => l.id === id);
      const next = [...prev];
      next.splice(idx + 1, 0, copy);
      return next;
    });
    onToast(t('toasts.layerDuplicated'));
  }

  function deleteLayer(id: string) {
    setLayers((prev) => {
      if (prev.length <= 1) return prev;
      return prev.filter((l) => l.id !== id);
    });
    onToast(t('toasts.layerDeleted'));
  }

  function moveLayer(id: string, dir: -1 | 1) {
    setLayers((prev) => {
      const idx = prev.findIndex((l) => l.id === id);
      const target = idx + dir;
      if (idx < 0 || target < 0 || target >= prev.length) return prev;
      const next = [...prev];
      const [item] = next.splice(idx, 1);
      if (!item) return prev;
      next.splice(target, 0, item);
      return next;
    });
  }

  return (
    <div className="ib-ws__rail-panel" data-testid={`ib-rail-${side}-layers`}>
      <div className="ib-ws__rail-panel-head">
        <h2>{t('rails.layers.title')}</h2>
        <StatusChip tone="info">{String(layers.length)}</StatusChip>
      </div>
      <div className="ib-ws__rail-panel-body">
        <ul className="ib-ws__layer-list" data-testid="ib-layer-list">
          {layers.map((layer) => (
            <li
              key={layer.id}
              className={`ib-ws__layer-row${selectedLayerId === layer.id ? ' is-selected' : ''}`}
            >
              <button
                type="button"
                className="ib-ws__layer-main"
                onClick={() => setSelectedLayerId(layer.id)}
              >
                <img src={layer.thumbUrl} alt="" className="ib-ws__layer-thumb" />
                <span className="ib-ws__layer-name">{layer.name}</span>
              </button>
              <div className="ib-ws__layer-actions">
                <button
                  type="button"
                  className="ib-ws__icon-btn"
                  aria-label={t('rails.layers.visibility')}
                  title={t('rails.layers.visibility')}
                  onClick={() => toggleVisible(layer.id)}
                >
                  <IhIcon name={layer.visible ? 'check' : 'empty'} size={11} />
                </button>
                <button
                  type="button"
                  className="ib-ws__icon-btn"
                  aria-label={t('rails.layers.lock')}
                  title={t('rails.layers.lock')}
                  onClick={() => toggleLock(layer.id)}
                >
                  <IhIcon name={layer.locked ? 'settings' : 'design'} size={11} />
                </button>
                {showReorder ? (
                  <>
                    <button
                      type="button"
                      className="ib-ws__icon-btn"
                      aria-label={t('rails.layers.up')}
                      onClick={() => moveLayer(layer.id, -1)}
                    >
                      <IhIcon name="trendingUp" size={11} />
                    </button>
                    <button
                      type="button"
                      className="ib-ws__icon-btn"
                      aria-label={t('rails.layers.down')}
                      onClick={() => moveLayer(layer.id, 1)}
                    >
                      <IhIcon name="chevronDown" size={11} />
                    </button>
                  </>
                ) : null}
                <button
                  type="button"
                  className="ib-ws__icon-btn"
                  aria-label={t('rails.layers.duplicate')}
                  onClick={() => duplicateLayer(layer.id)}
                >
                  <IhIcon name="documents" size={11} />
                </button>
                <button
                  type="button"
                  className="ib-ws__icon-btn"
                  aria-label={t('rails.layers.delete')}
                  onClick={() => deleteLayer(layer.id)}
                >
                  <IhIcon name="alert" size={11} />
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/* ─── Right drawers ────────────────────────────────────────────── */

export type IbRightRailDrawerProps = {
  id: IbRightRailId;
  layers: IbLayer[];
  setLayers: (updater: (prev: IbLayer[]) => IbLayer[]) => void;
  selectedLayerId: string;
  setSelectedLayerId: (id: string) => void;
  details: IbImageDetails;
  history: IbHistoryItem[];
  printExport: PrintExportState;
  patchPrint: (patch: Partial<PrintExportState>) => void;
  printValidation: PrintValidation;
  outputPixels: [number, number];
  digitalPreset: DigitalPresetKey;
  setDigitalPreset: (v: DigitalPresetKey) => void;
  collection: (typeof COLLECTIONS)[number];
  setCollection: (v: (typeof COLLECTIONS)[number]) => void;
  onAiTool: (key: IbAiToolKey) => void;
  onDownload: () => void;
  onToast: (msg: string) => void;
  markDirty: () => void;
};

export function IbRightRailDrawer(props: IbRightRailDrawerProps) {
  const { id } = props;
  if (id === 'aiTools') return <AiToolsDrawer {...props} />;
  if (id === 'layers') {
    return (
      <LayersPanel
        layers={props.layers}
        setLayers={props.setLayers}
        selectedLayerId={props.selectedLayerId}
        setSelectedLayerId={props.setSelectedLayerId}
        onToast={props.onToast}
        side="right"
        showReorder
      />
    );
  }
  if (id === 'details') return <DetailsDrawer {...props} />;
  if (id === 'history') return <HistoryDrawer {...props} />;
  return <ExportDrawer {...props} />;
}

function AiToolsDrawer({ onAiTool }: IbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.imageBuilder');

  return (
    <div className="ib-ws__rail-panel" data-testid="ib-rail-right-aiTools">
      <div className="ib-ws__rail-panel-head">
        <h2>{t('rails.aiTools.title')}</h2>
      </div>
      <div className="ib-ws__rail-panel-body">
        <div className="ib-ws__ai-tools-grid" data-testid="ib-ai-tools">
          {IB_AI_TOOLS.map((tool) => (
            <button
              key={tool.key}
              type="button"
              className="ib-ws__ai-tool-card"
              data-testid={`ib-ai-tool-${tool.key}`}
              onClick={() => onAiTool(tool.key)}
            >
              <IhIcon name={tool.icon} size={16} />
              <strong>{t(`rails.aiTools.tools.${tool.key}.title`)}</strong>
              <span>{t(`rails.aiTools.tools.${tool.key}.desc`)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function DetailsDrawer({ details }: IbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.imageBuilder');
  const rows: { key: keyof IbImageDetails; label: string }[] = [
    { key: 'resolution', label: t('rails.details.resolution') },
    { key: 'fileSize', label: t('rails.details.fileSize') },
    { key: 'createdDate', label: t('rails.details.createdDate') },
    { key: 'aiModel', label: t('rails.details.aiModel') },
    { key: 'aspectRatio', label: t('rails.details.aspectRatio') },
    { key: 'generationTime', label: t('rails.details.generationTime') },
  ];

  return (
    <div className="ib-ws__rail-panel" data-testid="ib-rail-right-details">
      <div className="ib-ws__rail-panel-head">
        <h2>{t('rails.details.title')}</h2>
      </div>
      <div className="ib-ws__rail-panel-body">
        <ul className="ib-ws__details-list" data-testid="ib-image-details">
          {rows.map((row) => (
            <li key={row.key}>
              <span>{row.label}</span>
              <strong>{details[row.key]}</strong>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function HistoryDrawer({ history, onToast }: IbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.imageBuilder');

  return (
    <div className="ib-ws__rail-panel" data-testid="ib-rail-right-history">
      <div className="ib-ws__rail-panel-head">
        <h2>{t('rails.history.title')}</h2>
      </div>
      <div className="ib-ws__rail-panel-body">
        <div className="ib-ws__history-list" data-testid="ib-history">
          {history.map((item) => (
            <button
              key={item.id}
              type="button"
              className="ib-ws__history-row"
              onClick={() => onToast(t('toasts.historyRestored'))}
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

function ExportDrawer({
  printExport,
  patchPrint,
  printValidation,
  outputPixels,
  digitalPreset,
  setDigitalPreset,
  collection,
  setCollection,
  onDownload,
  onToast,
}: IbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.imageBuilder');

  return (
    <div className="ib-ws__rail-panel" data-testid="ib-rail-right-export">
      <div className="ib-ws__rail-panel-head">
        <h2>{t('rails.export.title')}</h2>
      </div>
      <div className="ib-ws__rail-panel-body ib-ws__right-stack">
        <div className="ib-ws__export-path" role="tablist">
          <button
            type="button"
            role="tab"
            className={`ib-ws__export-path-btn${printExport.path === 'digital' ? ' is-active' : ''}`}
            aria-selected={printExport.path === 'digital'}
            data-testid="ib-export-path-digital"
            onClick={() => patchPrint({ path: 'digital' })}
          >
            {t('right.exportPaths.digital')}
          </button>
          <button
            type="button"
            role="tab"
            className={`ib-ws__export-path-btn${printExport.path === 'print' ? ' is-active' : ''}`}
            aria-selected={printExport.path === 'print'}
            data-testid="ib-export-path-print"
            onClick={() =>
              patchPrint({
                path: 'print',
                dpi: '300',
                colorProfile:
                  printExport.colorProfile === 'srgb' ? 'cmyk' : printExport.colorProfile,
              })
            }
          >
            {t('right.exportPaths.print')}
          </button>
        </div>

        {printExport.path === 'digital' ? (
          <div className="ib-ws__export-groups" data-testid="ib-digital-export">
            <div className="ib-ws__export-group">
              <span className="ib-ws__export-group-label">{t('right.digital.format')}</span>
              <div className="ib-ws__export-grid">
                {DIGITAL_FORMATS.map((key) => (
                  <button
                    key={key}
                    type="button"
                    className={`ib-ws__export-chip${printExport.digitalFormat === key ? ' is-selected' : ''}`}
                    aria-pressed={printExport.digitalFormat === key}
                    onClick={() => patchPrint({ digitalFormat: key })}
                  >
                    {t(`right.digital.formats.${key}`)}
                  </button>
                ))}
              </div>
            </div>
            <div className="ib-ws__export-group">
              <span className="ib-ws__export-group-label">{t('right.digital.presets')}</span>
              <div className="ib-ws__export-grid">
                {DIGITAL_PRESETS.map((key) => (
                  <button
                    key={key}
                    type="button"
                    className={`ib-ws__export-chip${digitalPreset === key ? ' is-selected' : ''}`}
                    aria-pressed={digitalPreset === key}
                    onClick={() => setDigitalPreset(key)}
                  >
                    {t(`right.digital.presetOptions.${key}`)}
                  </button>
                ))}
              </div>
            </div>
            <p className="ib-ws__export-estimate">
              {t('right.estimatedSize')}: {formatFileSize(printValidation.estimatedBytes)}
              {' · '}
              {outputPixels[0]}×{outputPixels[1]}px
            </p>
          </div>
        ) : (
          <div className="ib-ws__export-groups" data-testid="ib-print-export">
            <div className="ib-ws__export-group">
              <span className="ib-ws__export-group-label">{t('right.print.resolution')}</span>
              <div className="ib-ws__export-grid">
                {PRINT_RESOLUTIONS.map((key) => (
                  <button
                    key={key}
                    type="button"
                    className={`ib-ws__export-chip${printExport.resolution === key ? ' is-selected' : ''}`}
                    aria-pressed={printExport.resolution === key}
                    onClick={() => patchPrint({ resolution: key as PrintResolutionKey })}
                  >
                    {t(`right.print.resolutions.${key}`)}
                  </button>
                ))}
              </div>
            </div>
            <div className="ib-ws__export-group">
              <span className="ib-ws__export-group-label">{t('right.print.dpi')}</span>
              <div className="ib-ws__export-grid">
                {PRINT_DPI_OPTIONS.map((key) => (
                  <button
                    key={key}
                    type="button"
                    className={`ib-ws__export-chip${printExport.dpi === key ? ' is-selected' : ''}`}
                    onClick={() => patchPrint({ dpi: key as PrintDpiKey })}
                  >
                    {t(`right.print.dpiOptions.${key}`)}
                  </button>
                ))}
              </div>
            </div>
            <div className="ib-ws__export-group">
              <span className="ib-ws__export-group-label">{t('right.print.presets')}</span>
              <div className="ib-ws__export-grid">
                {PRINT_PRESETS.slice(0, 6).map((key) => (
                  <button
                    key={key}
                    type="button"
                    className={`ib-ws__export-chip${printExport.preset === key ? ' is-selected' : ''}`}
                    onClick={() => {
                      patchPrint(applyPrintPreset(key as PrintPresetKey, printExport));
                    }}
                  >
                    {t(`right.print.presetOptions.${key}`)}
                  </button>
                ))}
              </div>
            </div>
            <div className="ib-ws__export-group">
              <span className="ib-ws__export-group-label">{t('right.print.colorProfile')}</span>
              <div className="ib-ws__export-grid">
                {COLOR_PROFILES.map((key) => (
                  <button
                    key={key}
                    type="button"
                    className={`ib-ws__export-chip${printExport.colorProfile === key ? ' is-selected' : ''}`}
                    onClick={() => patchPrint({ colorProfile: key as ColorProfileKey })}
                  >
                    {t(`right.print.colorProfiles.${key}`)}
                  </button>
                ))}
              </div>
            </div>
            <div className="ib-ws__export-group">
              <span className="ib-ws__export-group-label">{t('right.print.fileFormat')}</span>
              <div className="ib-ws__export-grid">
                {PRINT_FORMATS.map((key) => (
                  <button
                    key={key}
                    type="button"
                    className={`ib-ws__export-chip${printExport.printFormat === key ? ' is-selected' : ''}`}
                    onClick={() => patchPrint({ printFormat: key as PrintFormatKey })}
                  >
                    {t(`right.print.formats.${key}`)}
                  </button>
                ))}
              </div>
            </div>
            <div className="ib-ws__export-group">
              <span className="ib-ws__export-group-label">{t('right.print.bleed')}</span>
              <div className="ib-ws__export-grid">
                {BLEED_OPTIONS.map((key) => (
                  <button
                    key={key}
                    type="button"
                    className={`ib-ws__export-chip${printExport.bleed === key ? ' is-selected' : ''}`}
                    onClick={() => patchPrint({ bleed: key as BleedKey })}
                  >
                    {t(`right.print.bleedOptions.${key}`)}
                  </button>
                ))}
              </div>
            </div>
            <div className="ib-ws__field-grid ib-ws__field-grid--3">
              <Field label={t('right.print.width')}>
                <input
                  type="number"
                  value={printExport.physicalWidth}
                  onChange={(e) =>
                    patchPrint({ physicalWidth: Number(e.target.value) || 0.1, preset: 'custom' })
                  }
                />
              </Field>
              <Field label={t('right.print.height')}>
                <input
                  type="number"
                  value={printExport.physicalHeight}
                  onChange={(e) =>
                    patchPrint({ physicalHeight: Number(e.target.value) || 0.1, preset: 'custom' })
                  }
                />
              </Field>
              <Field label={t('right.print.unit')}>
                <select
                  value={printExport.unit}
                  onChange={(e) => patchPrint({ unit: e.target.value as PrintUnitKey })}
                >
                  {PRINT_UNITS.map((u) => (
                    <option key={u} value={u}>
                      {t(`right.print.units.${u}`)}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
            <StatusChip
              tone={printValidation.finalState === 'printReady' ? 'success' : 'warning'}
            >
              {t(`right.print.final.${printValidation.finalState}`)}
            </StatusChip>
          </div>
        )}

        <Field label={t('right.collection')}>
          <select
            value={collection}
            onChange={(e) => setCollection(e.target.value as (typeof COLLECTIONS)[number])}
          >
            {COLLECTIONS.map((c) => (
              <option key={c} value={c}>
                {t(`collections.${c}`)}
              </option>
            ))}
          </select>
        </Field>

        <div className="ib-ws__export-actions">
          <Button variant="primary" size="sm" data-testid="ib-download" onClick={onDownload}>
            {t('right.download')}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            data-testid="ib-save-library"
            onClick={() => onToast(t('toasts.savedToLibrary'))}
          >
            {t('right.saveLibrary')}
          </Button>
        </div>
      </div>
    </div>
  );
}

/* ─── Zoom toolbar ─────────────────────────────────────────────── */

export type IbZoomToolbarProps = {
  engine: {
    mode: string;
    zoomPercent: number;
    autoFit: boolean;
    fitToView: () => void;
    actualSize: () => void;
    setPercent: (n: number) => void;
    setAutoFit: (v: boolean) => void;
  };
  aspectRatio: AspectRatio;
  onAspectChange: (v: AspectRatio) => void;
  canvasLocked: boolean;
  onToggleLock: () => void;
};

const ZOOM_STEP = 10;
const ZOOM_MIN = 10;
const ZOOM_MAX = 400;

export function IbZoomToolbar({
  engine,
  aspectRatio,
  onAspectChange,
  canvasLocked,
  onToggleLock,
}: IbZoomToolbarProps) {
  const t = useTranslations('creativeStudio.ds.imageBuilder');
  const percent = Math.round(engine.zoomPercent);

  function zoomBy(delta: number) {
    engine.setPercent(Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, percent + delta)));
  }

  return (
    <div
      className="ib-ws__zoom-bar"
      role="toolbar"
      aria-label={t('canvas.zoomBarAria')}
      data-testid="ib-zoom-bar"
    >
      <label className="ib-ws__aspect" data-testid="ib-canvas-aspect">
        <span className="ib-ws__sr-only">{t('canvas.aspectRatio')}</span>
        <select
          value={aspectRatio}
          onChange={(e) => onAspectChange(e.target.value as AspectRatio)}
          aria-label={t('canvas.aspectRatio')}
        >
          {ASPECT_RATIOS.map((ratio) => (
            <option key={ratio} value={ratio}>
              {ratio}
            </option>
          ))}
        </select>
      </label>

      <div className="ib-ws__zoom-bar-modes" role="group">
        <button
          type="button"
          className={`ib-ws__fit-btn${engine.mode === 'fit' ? ' is-active' : ''}`}
          aria-pressed={engine.mode === 'fit'}
          data-testid="ib-ftv-fit"
          onClick={() => engine.fitToView()}
        >
          {t('canvas.fitModes.fit')}
        </button>
        <button
          type="button"
          className={`ib-ws__fit-btn${engine.mode === 'actual' ? ' is-active' : ''}`}
          aria-pressed={engine.mode === 'actual'}
          data-testid="ib-ftv-actual"
          onClick={() => engine.actualSize()}
        >
          {t('canvas.fitModes.actual')}
        </button>
      </div>

      <IbZoomControls
        percent={percent}
        disabledOut={percent <= ZOOM_MIN || canvasLocked}
        disabledIn={percent >= ZOOM_MAX || canvasLocked}
        onZoomOut={() => zoomBy(-ZOOM_STEP)}
        onZoomIn={() => zoomBy(ZOOM_STEP)}
        onReset={() => engine.actualSize()}
      />

      <button
        type="button"
        className={`ib-ws__fit-btn${canvasLocked ? ' is-active' : ''}`}
        aria-pressed={canvasLocked}
        data-testid="ib-lock-canvas"
        onClick={onToggleLock}
      >
        {t('canvas.lockCanvas')}
      </button>
    </div>
  );
}
