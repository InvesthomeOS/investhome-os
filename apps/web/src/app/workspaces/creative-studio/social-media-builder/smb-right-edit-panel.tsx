'use client';

import { useTranslations } from 'next-intl';

import { Button } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  FORMAT_PRESETS,
  formatDimensions,
  type FormatPresetKey,
  type SocialPost,
} from './social-media-builder-model';
import { readStructuredDesignElements } from './social-media-builder-gpt-image';
import {
  clampFontSize,
  clampOpacity,
  nudgeFontSize,
  opacityToPercent,
  parseSocialFontWeight,
  parseSocialObjectFit,
  toColorInputValue,
  type SocialElement,
} from './social-media-builder-elements';

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="smb-ws__field">
      <span>{label}</span>
      {children}
    </label>
  );
}

export type SmbRightEditPanelProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedElement: SocialElement | null;
  post: SocialPost | null;
  formatPreset: FormatPresetKey;
  onFormatChange: (key: FormatPresetKey) => void;
  patchElement: (patch: Partial<SocialElement>) => void;
  onCopy: () => void;
  onDelete: () => void;
  onReplaceImage: () => void;
  onReplaceLogo: () => void;
  onChangeBackground: () => void;
  onSelectStructuredSlot?: (slotId: string) => void;
  canvasWidth: number;
  canvasHeight: number;
};

function contextKey(el: SocialElement | null): 'design' | 'text' | 'image' | 'logo' | 'cta' | 'badge' {
  if (!el) return 'design';
  if (el.type === 'TEXT') {
    if (el.role === 'eyebrow' || el.role === 'brand') return 'badge';
    return 'text';
  }
  if (el.type === 'BUTTON') return 'cta';
  if (el.type === 'IMAGE' && el.role === 'logo') return 'logo';
  if (el.type === 'IMAGE') return 'image';
  if (el.type === 'SHAPE') return 'badge';
  return 'design';
}

export function SmbRightEditPanel({
  open,
  onOpenChange,
  selectedElement,
  post,
  formatPreset,
  onFormatChange,
  patchElement,
  onCopy,
  onDelete,
  onReplaceImage,
  onReplaceLogo,
  onChangeBackground,
  onSelectStructuredSlot,
  canvasWidth,
  canvasHeight,
}: SmbRightEditPanelProps) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
  const ctx = contextKey(selectedElement);

  if (!open) {
    return (
      <div className="smb-ws__edit-panel smb-ws__edit-panel--collapsed" data-testid="smb-edit-panel">
        <button
          type="button"
          className="smb-ws__edit-panel-tab"
          data-testid="smb-edit-panel-open"
          aria-label={t('editPanel.open')}
          title={t('editPanel.title')}
          onClick={() => onOpenChange(true)}
        >
          <IhIcon name="design" size={16} />
          <span>{t('editPanel.title')}</span>
        </button>
      </div>
    );
  }

  return (
    <aside
      className="smb-ws__edit-panel"
      aria-label={t('editPanel.aria')}
      data-testid="smb-edit-panel"
      data-edit-context={ctx}
    >
      <div className="smb-ws__edit-panel-head smb-ws__panel-head">
        <h2 data-testid="smb-edit-panel-title">{t('editPanel.title')}</h2>
        <button
          type="button"
          className="smb-ws__icon-btn"
          data-testid="smb-edit-panel-close"
          aria-label={t('editPanel.close')}
          onClick={() => onOpenChange(false)}
        >
          <IhIcon name="chevronRight" size={14} />
        </button>
      </div>

      <div className="smb-ws__edit-panel-body smb-ws__panel-body smb-ws__left-stack" data-testid="smb-edit-panel-body">
        {ctx === 'design' ? (
          <DesignSection
            formatPreset={formatPreset}
            onFormatChange={onFormatChange}
            post={post}
            canvasWidth={canvasWidth}
            canvasHeight={canvasHeight}
            onChangeBackground={onChangeBackground}
            onSelectStructuredSlot={onSelectStructuredSlot}
          />
        ) : null}

        {ctx === 'text' && selectedElement?.type === 'TEXT' ? (
          <TextSection
            el={selectedElement}
            patch={patchElement}
            onCopy={onCopy}
            onDelete={onDelete}
          />
        ) : null}

        {ctx === 'image' && selectedElement?.type === 'IMAGE' ? (
          <ImageSection el={selectedElement} patch={patchElement} onReplace={onReplaceImage} />
        ) : null}

        {ctx === 'logo' && selectedElement?.type === 'IMAGE' ? (
          <LogoSection el={selectedElement} patch={patchElement} onReplace={onReplaceLogo} />
        ) : null}

        {ctx === 'cta' && selectedElement?.type === 'BUTTON' ? (
          <CtaSection el={selectedElement} patch={patchElement} onCopy={onCopy} onDelete={onDelete} />
        ) : null}

        {ctx === 'badge' && selectedElement ? (
          <BadgeSection el={selectedElement} patch={patchElement} onCopy={onCopy} onDelete={onDelete} />
        ) : null}
      </div>
    </aside>
  );
}

function DesignSection({
  formatPreset,
  onFormatChange,
  post,
  canvasWidth,
  canvasHeight,
  onChangeBackground,
  onSelectStructuredSlot,
}: {
  formatPreset: FormatPresetKey;
  onFormatChange: (key: FormatPresetKey) => void;
  post: SocialPost | null;
  canvasWidth: number;
  canvasHeight: number;
  onChangeBackground: () => void;
  onSelectStructuredSlot?: (slotId: string) => void;
}) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
  const structuredSlots = readStructuredDesignElements(post?.generationMeta).filter((el) => {
    const id = String(el.id || '').toLowerCase();
    return id !== 'background' && el.visible !== false;
  });
  return (
    <div data-testid="smb-edit-context-design">
      {structuredSlots.length > 0 ? (
        <>
          <p className="smb-ws__section-label">Structured elements</p>
          <div className="smb-ws__edit-format-grid" role="list" data-testid="smb-structured-slots">
            {structuredSlots.map((slot) => (
              <button
                key={slot.id}
                type="button"
                className="smb-ws__edit-format-btn"
                data-testid={`smb-structured-slot-${slot.id}`}
                onClick={() => onSelectStructuredSlot?.(slot.id)}
              >
                <strong>{slot.id}</strong>
                <span>{slot.content ? String(slot.content).slice(0, 42) : slot.role || slot.id}</span>
              </button>
            ))}
          </div>
        </>
      ) : null}
      <p className="smb-ws__section-label">{t('editPanel.contexts.design')}</p>
      <p className="smb-ws__section-label">{t('editPanel.format')}</p>
      <div className="smb-ws__edit-format-grid" role="group" aria-label={t('canvas.formatsAria')}>
        {FORMAT_PRESETS.map((f) => (
          <button
            key={f.key}
            type="button"
            className={`smb-ws__edit-format-btn${formatPreset === f.key ? ' is-active' : ''}`}
            aria-pressed={formatPreset === f.key}
            data-testid={`smb-edit-format-${f.key}`}
            onClick={() => onFormatChange(f.key)}
          >
            <strong>{t(`editPanel.formatLabels.${f.key}`)}</strong>
            <span>
              {f.width}:{f.height}
            </span>
          </button>
        ))}
      </div>

      <p className="smb-ws__section-label">{t('editPanel.canvas')}</p>
      <p className="smb-ws__muted" data-testid="smb-edit-canvas-info">
        {t('editPanel.canvasSize', {
          size: formatDimensions(canvasWidth, canvasHeight),
          name: post?.name ?? '—',
        })}
      </p>
      <Button
        variant="secondary"
        size="sm"
        data-testid="smb-edit-change-background"
        onClick={onChangeBackground}
      >
        {t('rails.content.changeImage')}
      </Button>
    </div>
  );
}

function TextSection({
  el,
  patch,
  onCopy,
  onDelete,
}: {
  el: Extract<SocialElement, { type: 'TEXT' }>;
  patch: (next: Partial<SocialElement>) => void;
  onCopy: () => void;
  onDelete: () => void;
}) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
  return (
    <div data-testid="smb-edit-context-text">
      <p className="smb-ws__section-label">{t('editPanel.contexts.text')}</p>
      <Field label={t('rails.content.headline')}>
        <textarea
          rows={4}
          value={el.content}
          data-testid="smb-edit-text-content"
          onChange={(e) => patch({ content: e.target.value })}
        />
      </Field>
      <Field label={t('rails.style.fontFamily')}>
        <select
          value={el.fontFamily ?? 'sans'}
          data-testid="smb-edit-font-family"
          onChange={(e) => {
            const v = e.target.value;
            if (v === 'sans' || v === 'serif' || v === 'system') patch({ fontFamily: v });
          }}
        >
          <option value="sans">{t('rails.style.fonts.sans')}</option>
          <option value="serif">{t('rails.style.fonts.serif')}</option>
          <option value="system">{t('rails.style.fonts.system')}</option>
        </select>
      </Field>
      <Field label={t('rails.style.fontSize')}>
        <div className="smb-ws__stepper" data-testid="smb-edit-font-size-stepper">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            data-testid="smb-edit-font-size-dec"
            onClick={() => patch({ fontSize: nudgeFontSize(el.fontSize, -2) })}
          >
            −
          </Button>
          <input
            type="number"
            min={8}
            max={200}
            value={Number.isFinite(el.fontSize) ? el.fontSize : 24}
            data-testid="smb-edit-font-size"
            onChange={(e) => patch({ fontSize: clampFontSize(e.target.value, 16) })}
          />
          <Button
            type="button"
            variant="secondary"
            size="sm"
            data-testid="smb-edit-font-size-inc"
            onClick={() => patch({ fontSize: nudgeFontSize(el.fontSize, 2) })}
          >
            +
          </Button>
        </div>
      </Field>
      <Field label={t('rails.style.fontWeight')}>
        <select
          value={el.fontWeight}
          data-testid="smb-edit-font-weight"
          onChange={(e) => patch({ fontWeight: parseSocialFontWeight(e.target.value) })}
        >
          <option value="normal">{t('rails.style.weights.normal')}</option>
          <option value="medium">{t('rails.style.weights.medium')}</option>
          <option value="semibold">{t('rails.style.weights.semibold')}</option>
          <option value="bold">{t('rails.style.weights.bold')}</option>
        </select>
      </Field>
      <Field label={t('rails.style.textColor')}>
        <input
          type="color"
          value={toColorInputValue(el.color, '#ffffff')}
          data-testid="smb-edit-text-color"
          onChange={(e) => patch({ color: e.target.value })}
        />
      </Field>
      <Field label={t('rails.style.align')}>
        <select
          value={el.align === 'left' || el.align === 'right' ? el.align : 'center'}
          data-testid="smb-edit-align"
          onChange={(e) => {
            const align = e.target.value;
            if (align === 'left' || align === 'center' || align === 'right') patch({ align });
          }}
        >
          <option value="left">{t('floating.alignModes.left')}</option>
          <option value="center">{t('floating.alignModes.center')}</option>
          <option value="right">{t('floating.alignModes.right')}</option>
        </select>
      </Field>
      <Field label={t('rails.style.lineHeight')}>
        <input
          type="number"
          min={0.8}
          max={3}
          step={0.05}
          value={el.lineHeight ?? 1.2}
          data-testid="smb-edit-line-height"
          onChange={(e) => {
            const n = Number(e.target.value);
            if (!Number.isFinite(n)) return;
            patch({ lineHeight: Math.max(0.8, Math.min(3, n)) });
          }}
        />
      </Field>
      <div className="smb-ws__chip-row">
        <Button variant="secondary" size="sm" data-testid="smb-edit-copy" onClick={onCopy}>
          {t('floating.copy')}
        </Button>
        <Button variant="secondary" size="sm" data-testid="smb-edit-delete" onClick={onDelete}>
          {t('floating.delete')}
        </Button>
      </div>
    </div>
  );
}

function ImageSection({
  el,
  patch,
  onReplace,
}: {
  el: Extract<SocialElement, { type: 'IMAGE' }>;
  patch: (next: Partial<SocialElement>) => void;
  onReplace: () => void;
}) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
  return (
    <div data-testid="smb-edit-context-image">
      <p className="smb-ws__section-label">{t('editPanel.contexts.image')}</p>
      <Button variant="secondary" size="sm" data-testid="smb-edit-replace-image" onClick={onReplace}>
        {t('editPanel.replaceImage')}
      </Button>
      <GeometryFields el={el} patch={patch} />
      <Field label={t('rails.style.cropFit')}>
        <select
          value={el.objectFit ?? 'cover'}
          data-testid="smb-edit-object-fit"
          onChange={(e) => {
            const fit = parseSocialObjectFit(e.target.value);
            if (fit) patch({ objectFit: fit });
          }}
        >
          <option value="cover">{t('rails.style.fitModes.cover')}</option>
          <option value="contain">{t('rails.style.fitModes.contain')}</option>
          <option value="fill">{t('rails.style.fitModes.fill')}</option>
        </select>
      </Field>
      <OpacityField value={el.opacity} onChange={(opacity) => patch({ opacity })} />
      <label className="smb-ws__toggle-row">
        <span>{t('rails.style.lockAspect')}</span>
        <input
          type="checkbox"
          checked={el.lockAspectRatio !== false}
          data-testid="smb-edit-lock-aspect"
          onChange={(e) => patch({ lockAspectRatio: e.target.checked })}
        />
      </label>
    </div>
  );
}

function LogoSection({
  el,
  patch,
  onReplace,
}: {
  el: Extract<SocialElement, { type: 'IMAGE' }>;
  patch: (next: Partial<SocialElement>) => void;
  onReplace: () => void;
}) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
  return (
    <div data-testid="smb-edit-context-logo">
      <p className="smb-ws__section-label">{t('editPanel.contexts.logo')}</p>
      <Button variant="secondary" size="sm" data-testid="smb-edit-replace-logo" onClick={onReplace}>
        {t('editPanel.replaceLogo')}
      </Button>
      <GeometryFields el={el} patch={patch} />
      <OpacityField value={el.opacity} onChange={(opacity) => patch({ opacity })} />
      <label className="smb-ws__toggle-row">
        <span>{t('rails.style.lockAspect')}</span>
        <input
          type="checkbox"
          checked={el.lockAspectRatio !== false}
          data-testid="smb-edit-lock-aspect"
          onChange={(e) => patch({ lockAspectRatio: e.target.checked })}
        />
      </label>
    </div>
  );
}

function CtaSection({
  el,
  patch,
  onCopy,
  onDelete,
}: {
  el: Extract<SocialElement, { type: 'BUTTON' }>;
  patch: (next: Partial<SocialElement>) => void;
  onCopy: () => void;
  onDelete: () => void;
}) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
  const fontSize = el.fontSize ?? Math.max(12, Math.round(el.height * 0.42));
  return (
    <div data-testid="smb-edit-context-cta">
      <p className="smb-ws__section-label">{t('editPanel.contexts.cta')}</p>
      <Field label={t('rails.style.ctaLabel')}>
        <input
          value={el.label}
          data-testid="smb-edit-cta-label"
          onChange={(e) => patch({ label: e.target.value })}
        />
      </Field>
      <Field label={t('rails.style.fontSize')}>
        <input
          type="number"
          min={8}
          max={200}
          value={fontSize}
          data-testid="smb-edit-cta-font-size"
          onChange={(e) => patch({ fontSize: clampFontSize(e.target.value, 16) })}
        />
      </Field>
      <Field label={t('rails.content.buttonTextColor')}>
        <input
          type="color"
          value={toColorInputValue(el.textColor, '#111827')}
          data-testid="smb-edit-cta-text-color"
          onChange={(e) => patch({ textColor: e.target.value })}
        />
      </Field>
      <Field label={t('rails.content.buttonBg')}>
        <input
          type="color"
          value={toColorInputValue(el.backgroundColor, '#ffffff')}
          data-testid="smb-edit-cta-bg"
          onChange={(e) => patch({ backgroundColor: e.target.value })}
        />
      </Field>
      <Field label={t('rails.style.borderRadius')}>
        <input
          type="number"
          min={0}
          max={200}
          value={el.borderRadius ?? Math.round(el.height / 2)}
          data-testid="smb-edit-cta-radius"
          onChange={(e) => {
            const n = Number(e.target.value);
            if (!Number.isFinite(n)) return;
            patch({ borderRadius: Math.max(0, Math.round(n)) });
          }}
        />
      </Field>
      <GeometryFields el={el} patch={patch} />
      <div className="smb-ws__chip-row">
        <Button variant="secondary" size="sm" data-testid="smb-edit-copy" onClick={onCopy}>
          {t('floating.copy')}
        </Button>
        <Button variant="secondary" size="sm" data-testid="smb-edit-delete" onClick={onDelete}>
          {t('floating.delete')}
        </Button>
      </div>
    </div>
  );
}

function BadgeSection({
  el,
  patch,
  onCopy,
  onDelete,
}: {
  el: SocialElement;
  patch: (next: Partial<SocialElement>) => void;
  onCopy: () => void;
  onDelete: () => void;
}) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
  return (
    <div data-testid="smb-edit-context-badge">
      <p className="smb-ws__section-label">{t('editPanel.contexts.badge')}</p>
      {el.type === 'TEXT' ? (
        <>
          <Field label={t('rails.content.headline')}>
            <textarea
              rows={3}
              value={el.content}
              data-testid="smb-edit-badge-text"
              onChange={(e) => patch({ content: e.target.value })}
            />
          </Field>
          <Field label={t('rails.style.textColor')}>
            <input
              type="color"
              value={toColorInputValue(el.color, '#ffffff')}
              data-testid="smb-edit-badge-color"
              onChange={(e) => patch({ color: e.target.value })}
            />
          </Field>
        </>
      ) : null}
      {el.type === 'SHAPE' ? (
        <Field label={t('editPanel.fill')}>
          <input
            type="color"
            value={toColorInputValue(el.fill, '#075b75')}
            data-testid="smb-edit-badge-fill"
            onChange={(e) => patch({ fill: e.target.value })}
          />
        </Field>
      ) : null}
      <GeometryFields el={el} patch={patch} />
      {'opacity' in el ? (
        <OpacityField value={el.opacity} onChange={(opacity) => patch({ opacity })} />
      ) : null}
      <div className="smb-ws__chip-row">
        <Button variant="secondary" size="sm" data-testid="smb-edit-copy" onClick={onCopy}>
          {t('floating.copy')}
        </Button>
        <Button variant="secondary" size="sm" data-testid="smb-edit-delete" onClick={onDelete}>
          {t('floating.delete')}
        </Button>
      </div>
    </div>
  );
}

function GeometryFields({
  el,
  patch,
}: {
  el: SocialElement;
  patch: (next: Partial<SocialElement>) => void;
}) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
  const lockAspect = el.type === 'IMAGE' ? el.lockAspectRatio !== false : false;
  return (
    <>
      <Field label={t('rails.style.size')}>
        <div className="smb-ws__stepper" data-testid="smb-edit-size">
          <input
            type="number"
            min={8}
            max={4000}
            value={Math.round(el.width)}
            data-testid="smb-edit-width"
            aria-label={t('rails.style.width')}
            onChange={(e) => {
              const nextW = Math.max(8, Math.round(Number(e.target.value) || el.width));
              if (lockAspect) {
                const ratio = el.width / Math.max(1, el.height);
                patch({ width: nextW, height: Math.max(8, Math.round(nextW / ratio)) });
              } else {
                patch({ width: nextW });
              }
            }}
          />
          <span className="smb-ws__stepper-unit">×</span>
          <input
            type="number"
            min={8}
            max={4000}
            value={Math.round(el.height)}
            data-testid="smb-edit-height"
            aria-label={t('rails.style.height')}
            onChange={(e) => {
              const nextH = Math.max(8, Math.round(Number(e.target.value) || el.height));
              if (lockAspect) {
                const ratio = el.width / Math.max(1, el.height);
                patch({ height: nextH, width: Math.max(8, Math.round(nextH * ratio)) });
              } else {
                patch({ height: nextH });
              }
            }}
          />
        </div>
      </Field>
      <Field label={t('rails.style.position')}>
        <div className="smb-ws__stepper" data-testid="smb-edit-position">
          <input
            type="number"
            value={Math.round(el.x)}
            data-testid="smb-edit-x"
            aria-label="X"
            onChange={(e) => {
              const n = Number(e.target.value);
              if (!Number.isFinite(n)) return;
              patch({ x: Math.round(n) });
            }}
          />
          <input
            type="number"
            value={Math.round(el.y)}
            data-testid="smb-edit-y"
            aria-label="Y"
            onChange={(e) => {
              const n = Number(e.target.value);
              if (!Number.isFinite(n)) return;
              patch({ y: Math.round(n) });
            }}
          />
        </div>
      </Field>
    </>
  );
}

function OpacityField({
  value,
  onChange,
}: {
  value: number | undefined;
  onChange: (opacity: number) => void;
}) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
  return (
    <Field label={t('rails.style.opacity')}>
      <input
        type="number"
        min={0}
        max={100}
        value={opacityToPercent(value)}
        data-testid="smb-edit-opacity"
        onChange={(e) => onChange(clampOpacity(Number(e.target.value) / 100, 1))}
      />
    </Field>
  );
}
