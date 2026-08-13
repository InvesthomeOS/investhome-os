'use client';

import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
} from 'react';

import {
  sortElementsByZ,
  type SocialElement,
} from './social-media-builder-elements';
import {
  constrainElement,
  fitMetricGroupPresentation,
  sanitizeGeometryPatch,
} from './social-media-builder-layout';

export type SmbArtboardElementsProps = {
  elements: SocialElement[];
  selectedElementId: string | null;
  editingElementId: string | null;
  imageUrlsByAssetId: Record<string, string>;
  canvasLocked: boolean;
  previewMode: boolean;
  canvasWidth?: number;
  canvasHeight?: number;
  onSelect: (elementId: string | null) => void;
  onPatchElement: (
    elementId: string,
    patch: Partial<SocialElement>,
    opts?: { live?: boolean; history?: boolean },
  ) => void;
  onBeginEdit: (elementId: string) => void;
  onEndEdit: () => void;
  onGestureStart: () => void;
  onGestureEnd: () => void;
};

type DragState = {
  id: string;
  mode: 'move' | 'resize';
  type: SocialElement['type'];
  startX: number;
  startY: number;
  origX: number;
  origY: number;
  origW: number;
  origH: number;
  canvasW: number;
  canvasH: number;
  scaleX: number;
  scaleY: number;
};

function finiteOr(n: unknown, fallback: number): number {
  const v = typeof n === 'number' ? n : Number(n);
  return Number.isFinite(v) ? v : fallback;
}

function isRenderableElement(el: SocialElement | null | undefined): el is SocialElement {
  if (!el || typeof el !== 'object') return false;
  if (typeof el.id !== 'string' || !el.id) return false;
  if (el.type !== 'TEXT' && el.type !== 'BUTTON' && el.type !== 'IMAGE' && el.type !== 'METRIC_GROUP') return false;
  return Number.isFinite(finiteOr(el.x, NaN)) && Number.isFinite(finiteOr(el.y, NaN));
}

function readCanvasScale(
  design: HTMLElement | null,
  artboard: HTMLElement | null,
  canvasW: number,
  canvasH: number,
): { scaleX: number; scaleY: number } {
  let scaleX = 1;
  let scaleY = 1;
  if (design && design.offsetWidth > 0 && design.offsetHeight > 0) {
    const rect = design.getBoundingClientRect();
    const sx = rect.width / design.offsetWidth;
    const sy = rect.height / design.offsetHeight;
    if (Number.isFinite(sx) && sx > 0.001) scaleX = sx;
    if (Number.isFinite(sy) && sy > 0.001) scaleY = sy;
  } else if (artboard && artboard.clientWidth > 0 && artboard.clientHeight > 0) {
    const sx = artboard.clientWidth / canvasW;
    const sy = artboard.clientHeight / canvasH;
    if (Number.isFinite(sx) && sx > 0.001) scaleX = sx;
    if (Number.isFinite(sy) && sy > 0.001) scaleY = sy;
  }
  return { scaleX, scaleY };
}

export function SmbArtboardElements({
  elements,
  selectedElementId,
  editingElementId,
  imageUrlsByAssetId,
  canvasLocked,
  previewMode,
  canvasWidth = 1080,
  canvasHeight = 1080,
  onSelect,
  onPatchElement,
  onBeginEdit,
  onEndEdit,
  onGestureStart,
  onGestureEnd,
}: SmbArtboardElementsProps) {
  const sorted = sortElementsByZ(elements.filter(isRenderableElement));
  const [draftText, setDraftText] = useState('');
  const editRef = useRef<HTMLTextAreaElement | HTMLInputElement | null>(null);
  const dragAliveRef = useRef(false);

  useEffect(() => {
    if (!editingElementId) return;
    const el = elements.find((e) => e.id === editingElementId);
    if (!el || (el.type !== 'TEXT' && el.type !== 'BUTTON')) {
      onEndEdit();
      return;
    }
    setDraftText(el.type === 'TEXT' ? el.content : el.label);
    const id = window.requestAnimationFrame(() => {
      editRef.current?.focus();
      editRef.current?.select?.();
    });
    return () => window.cancelAnimationFrame(id);
    // Only re-seed when entering edit for a new id
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editingElementId]);

  function commitEdit(elementId: string) {
    const el = elements.find((e) => e.id === elementId);
    if (!el) {
      onEndEdit();
      return;
    }
    const next = draftText;
    if (el.type === 'TEXT' && next !== el.content) {
      onPatchElement(elementId, { content: next });
    } else if (el.type === 'BUTTON' && next !== el.label) {
      onPatchElement(elementId, { label: next });
    }
    onEndEdit();
  }

  function beginDrag(
    event: ReactPointerEvent<HTMLElement>,
    el: SocialElement,
    mode: 'move' | 'resize',
  ) {
    if (canvasLocked || previewMode) return;
    if (editingElementId) return;
    if (!isRenderableElement(el)) return;
    // Only primary button
    if (typeof event.button === 'number' && event.button !== 0) return;
    event.stopPropagation();
    // Do not preventDefault — keeps click/selection stable inside CSS-transform + FS shells.
    // Do not use setPointerCapture — release throws InvalidStateError after FS remounts.
    onSelect(el.id);

    const currentTarget = event.currentTarget;
    if (!currentTarget || typeof currentTarget.closest !== 'function') return;

    const artboard = currentTarget.closest('[data-testid="smb-artboard"]') as HTMLElement | null;
    const design = currentTarget.closest(
      '[data-testid="smb-artboard-design"]',
    ) as HTMLElement | null;

    const cw = Math.max(1, finiteOr(canvasWidth, finiteOr(artboard?.dataset.width, 1080)));
    const ch = Math.max(1, finiteOr(canvasHeight, finiteOr(artboard?.dataset.height, 1080)));
    const { scaleX, scaleY } = readCanvasScale(design, artboard, cw, ch);

    const drag: DragState = {
      id: el.id,
      mode,
      type: el.type,
      startX: finiteOr(event.clientX, 0),
      startY: finiteOr(event.clientY, 0),
      origX: finiteOr(el.x, 0),
      origY: finiteOr(el.y, 0),
      origW: Math.max(24, finiteOr(el.width, 100)),
      origH: Math.max(24, finiteOr(el.height, 40)),
      canvasW: cw,
      canvasH: ch,
      scaleX,
      scaleY,
    };

    let dragging = false;
    dragAliveRef.current = true;
    let historyArmed = false;

    let lastW = drag.origW;
    let lastH = drag.origH;

    function onMove(ev: PointerEvent) {
      if (!dragAliveRef.current) return;
      const clientX = finiteOr(ev.clientX, drag.startX);
      const clientY = finiteOr(ev.clientY, drag.startY);
      const dx = clientX - drag.startX;
      const dy = clientY - drag.startY;
      if (!dragging && Math.abs(dx) < 3 && Math.abs(dy) < 3) return;
      if (!dragging) {
        dragging = true;
        if (!historyArmed) {
          historyArmed = true;
          onGestureStart();
        }
      }

      const sx = drag.scaleX > 0.001 ? drag.scaleX : 1;
      const sy = drag.scaleY > 0.001 ? drag.scaleY : 1;

      if (drag.mode === 'move') {
        const next = constrainElement(
          {
            type: drag.type,
            x: Math.round(drag.origX + dx / sx),
            y: Math.round(drag.origY + dy / sy),
            width: drag.origW,
            height: drag.origH,
          },
          drag.canvasW,
          drag.canvasH,
        );
        onPatchElement(drag.id, sanitizeGeometryPatch({ x: next.x, y: next.y }), { live: true });
      } else {
        const rawW = Math.max(24, Math.round(drag.origW + dx / sx));
        const rawH = Math.max(24, Math.round(drag.origH + dy / sy));
        const next = constrainElement(
          {
            type: drag.type,
            x: drag.origX,
            y: drag.origY,
            width: rawW,
            height: rawH,
          },
          drag.canvasW,
          drag.canvasH,
        );
        lastW = Math.max(8, next.width);
        lastH = Math.max(8, next.height);
        onPatchElement(
          drag.id,
          sanitizeGeometryPatch({
            width: lastW,
            height: lastH,
          }),
          { live: true },
        );
      }
    }

    function onUp() {
      dragAliveRef.current = false;
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onUp);
      if (dragging) {
        if (drag.mode === 'resize' && drag.type === 'TEXT') {
          // Commit width, then remeasure wrapping + height (not live — runs Layout Intelligence).
          onPatchElement(drag.id, sanitizeGeometryPatch({ width: lastW, height: lastH }), {
            history: false,
          });
        }
        onGestureEnd();
      }
    }

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onUp);
  }

  function handleDoubleClick(el: SocialElement) {
    if (canvasLocked || previewMode) return;
    if (el.type !== 'TEXT' && el.type !== 'BUTTON') return;
    onSelect(el.id);
    onBeginEdit(el.id);
  }

  function onEditKeyDown(
    event: ReactKeyboardEvent<HTMLTextAreaElement | HTMLInputElement>,
    id: string,
    kind: 'TEXT' | 'BUTTON',
  ) {
    // Isolate from canvas/window shortcuts (delete, nudge, undo, Enter-to-deselect).
    event.stopPropagation();
    if (typeof event.nativeEvent.stopImmediatePropagation === 'function') {
      event.nativeEvent.stopImmediatePropagation();
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      onEndEdit();
      return;
    }
    // TEXT: Enter and Shift+Enter insert a newline (textarea default). Do not preventDefault.
    // BUTTON: single-line — Enter commits.
    if (kind === 'BUTTON' && event.key === 'Enter') {
      event.preventDefault();
      commitEdit(id);
    }
  }

  return (
    <>
      {sorted.map((el) => {
        const selected = selectedElementId === el.id;
        const editing = editingElementId === el.id;
        const w = Math.max(8, finiteOr(el.width, 100));
        const h = Math.max(8, finiteOr(el.height, 40));
        const style: CSSProperties = {
          position: 'absolute',
          left: finiteOr(el.x, 0),
          top: finiteOr(el.y, 0),
          width: w,
          height: h,
          zIndex: Math.round(finiteOr(el.zIndex, 1)) + 10,
        };

        const resizeHandle =
          selected && !previewMode && !canvasLocked && !editing ? (
            <span
              className="smb-ws__el-resize"
              data-testid={`smb-el-resize-${el.id}`}
              onPointerDown={(e) => {
                e.stopPropagation();
                beginDrag(e, el, 'resize');
              }}
            />
          ) : null;

        if (el.type === 'TEXT') {
          const fontSize = Math.max(8, finiteOr(el.fontSize, 24));
          return (
            <div
              key={el.id}
              className={`smb-ws__el smb-ws__el--text${selected ? ' is-selected' : ''}${editing ? ' is-editing' : ''}`}
              style={{
                ...style,
                color: typeof el.color === 'string' && el.color.trim() ? el.color : '#ffffff',
                fontSize,
                fontWeight: el.fontWeight === 'bold' ? 700 : 400,
                textAlign: el.align === 'left' || el.align === 'right' ? el.align : 'center',
                lineHeight: 1.2,
              }}
              data-testid={`smb-el-${el.id}`}
              data-el-type="TEXT"
              data-el-role={el.role}
              data-text-edit={editing ? 'true' : 'false'}
              onClick={(e) => {
                e.stopPropagation();
                if (!editing) onSelect(el.id);
              }}
              onDoubleClick={(e) => {
                e.stopPropagation();
                e.preventDefault();
                handleDoubleClick(el);
              }}
              onPointerDown={(e) => {
                if (editing) {
                  e.stopPropagation();
                  return;
                }
                // Defer drag arming so double-click can enter inline edit without fighting move.
                if (e.detail >= 2) {
                  e.stopPropagation();
                  return;
                }
                beginDrag(e, el, 'move');
              }}
              role="button"
              tabIndex={0}
            >
              {editing ? (
                <textarea
                  ref={(node) => {
                    editRef.current = node;
                  }}
                  className="smb-ws__el-editor"
                  data-testid={`smb-el-editor-${el.id}`}
                  value={draftText}
                  onChange={(e) => {
                    const next = e.target.value;
                    setDraftText(next);
                    onPatchElement(el.id, { content: next }, { live: true, history: false });
                  }}
                  onBlur={() => commitEdit(el.id)}
                  onKeyDown={(e) => onEditKeyDown(e, el.id, 'TEXT')}
                  onKeyUp={(e) => e.stopPropagation()}
                  onClick={(e) => e.stopPropagation()}
                  onPointerDown={(e) => e.stopPropagation()}
                />
              ) : (
                typeof el.content === 'string' ? el.content : ''
              )}
              {resizeHandle}
            </div>
          );
        }

        if (el.type === 'BUTTON') {
          const btnH = Math.max(8, finiteOr(el.height, 40));
          const btnFont = Math.max(12, Math.round(btnH * 0.42));
          return (
            <div
              key={el.id}
              className={`smb-ws__el smb-ws__el--button${selected ? ' is-selected' : ''}${editing ? ' is-editing' : ''}`}
              data-cta-style={el.ctaStyle || 'PILL_BUTTON'}
              style={{
                ...style,
                background:
                  typeof el.backgroundColor === 'string' && el.backgroundColor.trim()
                    ? el.backgroundColor
                    : '#ffffff',
                color:
                  typeof el.textColor === 'string' && el.textColor.trim()
                    ? el.textColor
                    : '#111827',
                fontSize: btnFont,
              }}
              data-testid={`smb-el-${el.id}`}
              data-el-type="BUTTON"
              onClick={(e) => {
                e.stopPropagation();
                if (!editing) onSelect(el.id);
              }}
              onDoubleClick={(e) => {
                e.stopPropagation();
                e.preventDefault();
                handleDoubleClick(el);
              }}
              onPointerDown={(e) => {
                if (editing) {
                  e.stopPropagation();
                  return;
                }
                // Defer drag arming so double-click can enter inline edit without fighting move.
                if (e.detail >= 2) {
                  e.stopPropagation();
                  return;
                }
                beginDrag(e, el, 'move');
              }}
              role="button"
              tabIndex={0}
            >
              {editing ? (
                <input
                  ref={(node) => {
                    editRef.current = node;
                  }}
                  className="smb-ws__el-editor smb-ws__el-editor--button"
                  data-testid={`smb-el-editor-${el.id}`}
                  value={draftText}
                  onChange={(e) => setDraftText(e.target.value)}
                  onBlur={() => commitEdit(el.id)}
                  onKeyDown={(e) => onEditKeyDown(e, el.id, 'BUTTON')}
                  onKeyUp={(e) => e.stopPropagation()}
                  onClick={(e) => e.stopPropagation()}
                  onPointerDown={(e) => e.stopPropagation()}
                />
              ) : (
                <span>{typeof el.label === 'string' ? el.label : ''}</span>
              )}
              {resizeHandle}
            </div>
          );
        }

        if (el.type === 'METRIC_GROUP') {
          const metrics = Array.isArray(el.metrics) ? el.metrics : [];
          const requestedLayout =
            el.layout === 'stacked' || el.layout === 'cards' ? el.layout : 'horizontal';
          const presentation = fitMetricGroupPresentation(metrics, {
            groupWidth: Math.max(8, finiteOr(el.width, 400)),
            groupHeight: Math.max(8, finiteOr(el.height, 120)),
            requestedLayout,
            // Render honors persisted layout; LI already wrote fallback when needed.
            lockLayout: true,
          });
          const layout =
            requestedLayout === 'horizontal' && presentation.density === 'compact'
              ? 'horizontal'
              : requestedLayout;
          const color = typeof el.color === 'string' && el.color.trim() ? el.color : '#ffffff';
          const densityClass =
            layout === 'horizontal' && presentation.density === 'compact'
              ? ' smb-ws__el--metrics-compact'
              : '';
          const gridStyle: CSSProperties =
            layout === 'horizontal' || layout === 'cards'
              ? {
                  ...style,
                  color,
                  gap: presentation.gutter,
                  gridTemplateColumns: `repeat(${Math.max(1, presentation.columnCount)}, minmax(0, 1fr))`,
                  ['--smb-metric-value-row' as string]: `${presentation.valueRowHeight}px`,
                }
              : { ...style, color, gap: presentation.gutter };
          return (
            <div
              key={el.id}
              className={`smb-ws__el smb-ws__el--metrics smb-ws__el--metrics-${layout}${densityClass}${selected ? ' is-selected' : ''}`}
              style={gridStyle}
              data-testid={`smb-el-${el.id}`}
              data-el-type="METRIC_GROUP"
              data-metric-layout={layout}
              data-metric-density={presentation.density}
              data-metric-values-single-line={presentation.valuesSingleLine ? 'true' : 'false'}
              onClick={(e) => {
                e.stopPropagation();
                onSelect(el.id);
              }}
              onPointerDown={(e) => beginDrag(e, el, 'move')}
              role="button"
              tabIndex={0}
            >
              {metrics.map((metric) => (
                <div
                  key={metric.id}
                  className={`smb-ws__metric${metric.emphasis === 'primary' ? ' is-primary' : ''}`}
                  data-metric-id={metric.id}
                  data-metric-type={metric.type}
                >
                  <span
                    className="smb-ws__metric-value"
                    style={{
                      fontSize: presentation.valueFontSize,
                      minHeight: presentation.valueRowHeight,
                    }}
                  >
                    {metric.display_value}
                  </span>
                  <span
                    className="smb-ws__metric-label"
                    style={{ fontSize: presentation.labelFontSize }}
                  >
                    {metric.label}
                  </span>
                </div>
              ))}
              {resizeHandle}
            </div>
          );
        }

        if (el.type === 'IMAGE' && (el.role === 'background' || el.role === 'cover')) {
          return null;
        }
        const url = el.assetId ? imageUrlsByAssetId[el.assetId] : null;
        return (
          <div
            key={el.id}
            className={`smb-ws__el smb-ws__el--image${selected ? ' is-selected' : ''}${el.type === 'IMAGE' && el.role === 'logo' ? ' smb-ws__el--logo' : ''}`}
            style={style}
            data-testid={`smb-el-${el.id}`}
            data-el-type="IMAGE"
            data-el-role={el.type === 'IMAGE' ? el.role : undefined}
            data-asset-id={el.assetId ?? undefined}
            onClick={(e) => {
              e.stopPropagation();
              onSelect(el.id);
            }}
            onPointerDown={(e) => beginDrag(e, el, 'move')}
            role="button"
            tabIndex={0}
          >
            {url ? (
              <img src={url} alt="" draggable={false} />
            ) : (
              <span className="smb-ws__el-image-empty" />
            )}
            {resizeHandle}
          </div>
        );
      })}
    </>
  );
}
