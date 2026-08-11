'use client';

import type { CSSProperties, PointerEvent as ReactPointerEvent } from 'react';

import {
  sortElementsByZ,
  type SocialElement,
} from './social-media-builder-elements';
import { constrainElement, sanitizeGeometryPatch } from './social-media-builder-layout';

export type SmbArtboardElementsProps = {
  elements: SocialElement[];
  selectedElementId: string | null;
  imageUrlsByAssetId: Record<string, string>;
  canvasLocked: boolean;
  previewMode: boolean;
  canvasWidth?: number;
  canvasHeight?: number;
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
  canvasW: number;
  canvasH: number;
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
  canvasWidth = 1080,
  canvasHeight = 1080,
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

    const artboard =
      typeof event.currentTarget?.closest === 'function'
        ? (event.currentTarget.closest('[data-testid="smb-artboard"]') as HTMLElement | null)
        : null;
    const design =
      typeof event.currentTarget?.closest === 'function'
        ? (event.currentTarget.closest('[data-testid="smb-artboard-design"]') as HTMLElement | null)
        : null;

    const cw = Math.max(
      1,
      finiteOr(canvasWidth, finiteOr(artboard?.dataset.width, 1080)),
    );
    const ch = Math.max(
      1,
      finiteOr(canvasHeight, finiteOr(artboard?.dataset.height, 1080)),
    );

    // Snapshot scale at pointer-down — avoid reading detached nodes mid-drag after FS remount.
    let scaleX = 1;
    let scaleY = 1;
    try {
      if (design && design.offsetWidth > 0 && design.offsetHeight > 0) {
        const rect = design.getBoundingClientRect();
        const sx = rect.width / design.offsetWidth;
        const sy = rect.height / design.offsetHeight;
        if (Number.isFinite(sx) && sx > 0.001) scaleX = sx;
        if (Number.isFinite(sy) && sy > 0.001) scaleY = sy;
      } else if (artboard && artboard.clientWidth > 0 && artboard.clientHeight > 0) {
        const sx = artboard.clientWidth / cw;
        const sy = artboard.clientHeight / ch;
        if (Number.isFinite(sx) && sx > 0.001) scaleX = sx;
        if (Number.isFinite(sy) && sy > 0.001) scaleY = sy;
      }
    } catch {
      scaleX = 1;
      scaleY = 1;
    }

    const drag: DragState = {
      id: el.id,
      mode,
      startX: finiteOr(event.clientX, 0),
      startY: finiteOr(event.clientY, 0),
      origX: finiteOr(el.x, 0),
      origY: finiteOr(el.y, 0),
      origW: Math.max(24, finiteOr(el.width, 100)),
      origH: Math.max(24, finiteOr(el.height, 40)),
      canvasW: cw,
      canvasH: ch,
    };
    let dragging = false;
    let alive = true;

    function onMove(ev: PointerEvent) {
      if (!alive) return;
      const clientX = finiteOr(ev.clientX, drag.startX);
      const clientY = finiteOr(ev.clientY, drag.startY);
      const dx = clientX - drag.startX;
      const dy = clientY - drag.startY;
      if (!dragging && Math.abs(dx) < 3 && Math.abs(dy) < 3) return;
      dragging = true;

      if (drag.mode === 'move') {
        const next = constrainElement(
          {
            type: el.type,
            x: Math.round(drag.origX + dx / scaleX),
            y: Math.round(drag.origY + dy / scaleY),
            width: drag.origW,
            height: drag.origH,
          },
          drag.canvasW,
          drag.canvasH,
        );
        onPatchElement(drag.id, sanitizeGeometryPatch({ x: next.x, y: next.y }));
      } else {
        const rawW = Math.max(24, Math.round(drag.origW + dx / scaleX));
        const rawH = Math.max(24, Math.round(drag.origH + dy / scaleY));
        const next = constrainElement(
          {
            type: el.type,
            x: drag.origX,
            y: drag.origY,
            width: rawW,
            height: rawH,
          },
          drag.canvasW,
          drag.canvasH,
        );
        onPatchElement(
          drag.id,
          sanitizeGeometryPatch({ width: next.width, height: next.height }),
        );
      }
    }

    function onUp() {
      alive = false;
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
                lineHeight: 1.2,
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
                  onPointerDown={(e) => {
                    e.stopPropagation();
                    beginDrag(e, el, 'resize');
                  }}
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
                  onPointerDown={(e) => {
                    e.stopPropagation();
                    beginDrag(e, el, 'resize');
                  }}
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
                onPointerDown={(e) => {
                  e.stopPropagation();
                  beginDrag(e, el, 'resize');
                }}
              />
            ) : null}
          </div>
        );
      })}
    </>
  );
}
