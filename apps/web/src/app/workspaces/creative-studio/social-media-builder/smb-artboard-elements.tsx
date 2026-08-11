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
    // Do not preventDefault — keeps click/selection stable inside CSS-transform + FS shells.
    onSelect(el.id);
    const target = event.currentTarget;
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
    let dragging = false;

    function readScale(): { scaleX: number; scaleY: number } {
      // Prefer the design-pixel layer (transform scale) over the fitted frame size.
      const design = target.closest('[data-testid="smb-artboard-design"]') as HTMLElement | null;
      if (design) {
        const rect = design.getBoundingClientRect();
        const scaleX = rect.width / Math.max(1, design.offsetWidth);
        const scaleY = rect.height / Math.max(1, design.offsetHeight);
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
    }

    function onMove(ev: PointerEvent) {
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
