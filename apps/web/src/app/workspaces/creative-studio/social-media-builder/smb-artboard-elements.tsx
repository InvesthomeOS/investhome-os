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

export function SmbArtboardElements({
  elements,
  selectedElementId,
  imageUrlsByAssetId,
  canvasLocked,
  previewMode,
  onSelect,
  onPatchElement,
}: SmbArtboardElementsProps) {
  const sorted = sortElementsByZ(elements);

  function beginDrag(
    event: ReactPointerEvent<HTMLElement>,
    el: SocialElement,
    mode: 'move' | 'resize',
  ) {
    if (canvasLocked || previewMode) return;
    event.stopPropagation();
    event.preventDefault();
    onSelect(el.id);
    const target = event.currentTarget;
    const pointerId = event.pointerId;
    target.setPointerCapture(pointerId);
    const drag: DragState = {
      id: el.id,
      mode,
      startX: event.clientX,
      startY: event.clientY,
      origX: el.x,
      origY: el.y,
      origW: el.width,
      origH: el.height,
    };

    function onMove(ev: PointerEvent) {
      const dx = ev.clientX - drag.startX;
      const dy = ev.clientY - drag.startY;
      // Artboard uses CSS container; approximate 1 CSS px ≈ scale via offsetParent size.
      const artboard = target.closest('[data-testid="smb-artboard"]') as HTMLElement | null;
      const scaleX = artboard ? artboard.clientWidth / Math.max(1, Number(artboard.dataset.width) || artboard.clientWidth) : 1;
      const scaleY = artboard ? artboard.clientHeight / Math.max(1, Number(artboard.dataset.height) || artboard.clientHeight) : 1;
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
      target.releasePointerCapture(pointerId);
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    }

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  }

  return (
    <>
      {sorted.map((el) => {
        const selected = selectedElementId === el.id;
        const style: CSSProperties = {
          position: 'absolute',
          left: el.x,
          top: el.y,
          width: el.width,
          height: el.height,
          zIndex: el.zIndex + 10,
        };

        if (el.type === 'TEXT') {
          return (
            <div
              key={el.id}
              className={`smb-ws__el smb-ws__el--text${selected ? ' is-selected' : ''}`}
              style={{
                ...style,
                color: el.color,
                fontSize: el.fontSize,
                fontWeight: el.fontWeight === 'bold' ? 700 : 400,
                textAlign: el.align,
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
              {el.content}
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
          const btnFont = Math.max(12, Math.round(el.height * 0.42));
          return (
            <div
              key={el.id}
              className={`smb-ws__el smb-ws__el--button${selected ? ' is-selected' : ''}`}
              style={{
                ...style,
                background: el.backgroundColor,
                color: el.textColor,
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
              <span>{el.label}</span>
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
            {url ? <img src={url} alt="" draggable={false} /> : <span className="smb-ws__el-image-empty" />}
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
