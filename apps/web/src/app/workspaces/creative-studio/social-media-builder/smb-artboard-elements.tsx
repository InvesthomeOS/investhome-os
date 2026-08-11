'use client';

import type { CSSProperties, PointerEvent as ReactPointerEvent } from 'react';

import {
  sortElementsByZ,
  type SocialElement,
} from './social-media-builder-elements';

export type SmbArtboardElementsProps = {
  elements: SocialElement[];
  selectedElementId: string | null;
  imageUrlsByAssetId: Record<string, string>;
  canvasLocked: boolean;
  previewMode: boolean;
  onSelect: (elementId: string | null) => void;
  onPatchElement: (elementId: string, patch: Partial<SocialElement>) => void;
};

type DragState = {
  id: string;
  mode: 'move' | 'resize';
  startX: number;
  startY: number;
  origX: number;
  origY: number;
  origW: number;
  origH: number;
};

function finiteOr(n: unknown, fallback: number): number {
  const v = typeof n === 'number' ? n : Number(n);
  return Number.isFinite(v) ? v : fallback;
}

function isRenderableElement(el: SocialElement | null | undefined): el is SocialElement {
  if (!el || typeof el !== 'object') return false;
  if (typeof el.id !== 'string' || !el.id) return false;
  if (el.type !== 'TEXT' && el.type !== 'BUTTON' && el.type !== 'IMAGE') return false;
  return Number.isFinite(finiteOr(el.x, NaN)) && Number.isFinite(finiteOr(el.y, NaN));
}

export function SmbArtboardElements({
  elements,
  selectedElementId,
  imageUrlsByAssetId,
  canvasLocked,
  previewMode,
  onSelect,
  onPatchElement,
}: SmbArtboardElementsProps) {
  const sorted = sortElementsByZ(elements.filter(isRenderableElement));

  function beginDrag(
    event: ReactPointerEvent<HTMLElement>,
    el: SocialElement,
    mode: 'move' | 'resize',
  ) {
    if (canvasLocked || previewMode) return;
    if (!isRenderableElement(el)) return;
    event.stopPropagation();
    // Do not preventDefault — keeps click/selection stable inside CSS-transform + FS shells.
    // Do not use setPointerCapture — release throws InvalidStateError after FS remounts.
    onSelect(el.id);
    const target = event.currentTarget;
    if (!target || typeof target.closest !== 'function') return;

    const drag: DragState = {
      id: el.id,
      mode,
      startX: event.clientX,
      startY: event.clientY,
      origX: finiteOr(el.x, 0),
      origY: finiteOr(el.y, 0),
      origW: Math.max(24, finiteOr(el.width, 100)),
      origH: Math.max(24, finiteOr(el.height, 40)),
    };
    let dragging = false;
    let alive = true;

    function readScale(): { scaleX: number; scaleY: number } {
      try {
        const design = target.closest('[data-testid="smb-artboard-design"]') as HTMLElement | null;
        if (design && design.offsetWidth > 0 && design.offsetHeight > 0) {
          const rect = design.getBoundingClientRect();
          const scaleX = rect.width / design.offsetWidth;
          const scaleY = rect.height / design.offsetHeight;
          if (scaleX > 0.001 && scaleY > 0.001) return { scaleX, scaleY };
        }
        const artboard = target.closest('[data-testid="smb-artboard"]') as HTMLElement | null;
        const scaleX = artboard
          ? artboard.clientWidth / Math.max(1, Number(artboard.dataset.width) || artboard.clientWidth)
          : 1;
        const scaleY = artboard
          ? artboard.clientHeight / Math.max(1, Number(artboard.dataset.height) || artboard.clientHeight)
          : 1;
        return {
          scaleX: scaleX > 0.001 ? scaleX : 1,
          scaleY: scaleY > 0.001 ? scaleY : 1,
        };
      } catch {
        return { scaleX: 1, scaleY: 1 };
      }
    }

    function onMove(ev: PointerEvent) {
      if (!alive) return;
      const dx = ev.clientX - drag.startX;
      const dy = ev.clientY - drag.startY;
      if (!dragging && Math.abs(dx) < 3 && Math.abs(dy) < 3) return;
      dragging = true;
      const { scaleX, scaleY } = readScale();
      if (drag.mode === 'move') {
        onPatchElement(drag.id, {
          x: Math.round(drag.origX + dx / scaleX),
          y: Math.round(drag.origY + dy / scaleY),
        } as Partial<SocialElement>);
      } else {
        onPatchElement(drag.id, {
          width: Math.max(24, Math.round(drag.origW + dx / scaleX)),
          height: Math.max(24, Math.round(drag.origH + dy / scaleY)),
        } as Partial<SocialElement>);
      }
    }

    function onUp() {
      alive = false;
      // Window-level listeners only — avoid pointer capture APIs.
      // Capture release throws InvalidStateError after FS/transform re-renders remount nodes.
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onUp);
    }

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onUp);
  }

  return (
    <>
      {sorted.map((el) => {
        const selected = selectedElementId === el.id;
        const style: CSSProperties = {
          position: 'absolute',
          left: finiteOr(el.x, 0),
          top: finiteOr(el.y, 0),
          width: Math.max(8, finiteOr(el.width, 100)),
          height: Math.max(8, finiteOr(el.height, 40)),
          zIndex: Math.round(finiteOr(el.zIndex, 1)) + 10,
        };

        if (el.type === 'TEXT') {
          const fontSize = Math.max(8, finiteOr(el.fontSize, 24));
          return (
            <div
              key={el.id}
              className={`smb-ws__el smb-ws__el--text${selected ? ' is-selected' : ''}`}
              style={{
                ...style,
                color: typeof el.color === 'string' && el.color.trim() ? el.color : '#ffffff',
                fontSize,
                fontWeight: el.fontWeight === 'bold' ? 700 : 400,
                textAlign: el.align === 'left' || el.align === 'right' ? el.align : 'center',
              }}
              data-testid={`smb-el-${el.id}`}
              data-el-type="TEXT"
              data-el-role={el.role}
              onClick={(e) => {
                e.stopPropagation();
                onSelect(el.id);
              }}
              onPointerDown={(e) => beginDrag(e, el, 'move')}
              role="button"
              tabIndex={0}
            >
              {typeof el.content === 'string' ? el.content : ''}
              {selected && !previewMode && !canvasLocked ? (
                <span
                  className="smb-ws__el-resize"
                  data-testid={`smb-el-resize-${el.id}`}
                  onPointerDown={(e) => beginDrag(e, el, 'resize')}
                />
              ) : null}
            </div>
          );
        }

        if (el.type === 'BUTTON') {
          const btnH = Math.max(8, finiteOr(el.height, 40));
          const btnFont = Math.max(12, Math.round(btnH * 0.42));
          return (
            <div
              key={el.id}
              className={`smb-ws__el smb-ws__el--button${selected ? ' is-selected' : ''}`}
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
                onSelect(el.id);
              }}
              onPointerDown={(e) => beginDrag(e, el, 'move')}
              role="button"
              tabIndex={0}
            >
              <span>{typeof el.label === 'string' ? el.label : ''}</span>
              {selected && !previewMode && !canvasLocked ? (
                <span
                  className="smb-ws__el-resize"
                  data-testid={`smb-el-resize-${el.id}`}
                  onPointerDown={(e) => beginDrag(e, el, 'resize')}
                />
              ) : null}
            </div>
          );
        }

        const url = el.assetId ? imageUrlsByAssetId[el.assetId] : null;
        return (
          <div
            key={el.id}
            className={`smb-ws__el smb-ws__el--image${selected ? ' is-selected' : ''}`}
            style={style}
            data-testid={`smb-el-${el.id}`}
            data-el-type="IMAGE"
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
            {selected && !previewMode && !canvasLocked ? (
              <span
                className="smb-ws__el-resize"
                data-testid={`smb-el-resize-${el.id}`}
                onPointerDown={(e) => beginDrag(e, el, 'resize')}
              />
            ) : null}
          </div>
        );
      })}
    </>
  );
}
