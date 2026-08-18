'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

import { Button, Dialog } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import { docIcon, type MediaAsset } from './media-library-model';

export const ML_LIGHTBOX_ZOOM_MIN = 0.25;
export const ML_LIGHTBOX_ZOOM_MAX = 2;
export const ML_LIGHTBOX_ZOOM_STEP = 0.25;
/** 100% = first-open contain/fit. Minus steps to 75/50/25 of that fit. */
export const ML_LIGHTBOX_ZOOM_FIT = 1;

export type MediaLibraryLightboxLabels = {
  title: string;
  prev: string;
  next: string;
  zoomIn: string;
  zoomOut: string;
  zoomLevel: (percent: number) => string;
  download: string;
  assetId: string;
  filename: string;
  resolution: string;
  source: string;
  resolutionUnavailable: string;
  googleDrive: string;
  uploaded: string;
};

export function clampLightboxZoom(zoom: number): number {
  const rounded = Math.round(zoom * 100) / 100;
  return Math.min(ML_LIGHTBOX_ZOOM_MAX, Math.max(ML_LIGHTBOX_ZOOM_MIN, rounded));
}

export function stepLightboxZoom(zoom: number, direction: 1 | -1): number {
  return clampLightboxZoom(zoom + direction * ML_LIGHTBOX_ZOOM_STEP);
}

export function lightboxNeighborId(
  ids: string[],
  currentId: string,
  direction: -1 | 1,
): string | null {
  const index = ids.indexOf(currentId);
  if (index < 0) return null;
  return ids[index + direction] ?? null;
}

export function lightboxSourceLabel(
  asset: Pick<MediaAsset, 'sourceType'>,
  labels: Pick<MediaLibraryLightboxLabels, 'googleDrive' | 'uploaded'>,
): string {
  if (asset.sourceType === 'google_drive') return labels.googleDrive;
  return labels.uploaded;
}

type MediaLibraryLightboxProps = {
  open: boolean;
  asset: MediaAsset | null;
  previewUrl: string | null;
  assetIds: string[];
  labels: MediaLibraryLightboxLabels;
  onClose: () => void;
  onNavigate: (id: string) => void;
  onDownload?: (asset: MediaAsset) => Promise<boolean> | boolean;
};

export function MediaLibraryLightbox({
  open,
  asset,
  previewUrl,
  assetIds,
  labels,
  onClose,
  onNavigate,
  onDownload,
}: MediaLibraryLightboxProps) {
  const [zoom, setZoom] = useState(ML_LIGHTBOX_ZOOM_FIT);
  const [downloadBusy, setDownloadBusy] = useState(false);
  const stageRef = useRef<HTMLDivElement>(null);
  const openedAtRef = useRef(0);

  const prevId = asset ? lightboxNeighborId(assetIds, asset.id, -1) : null;
  const nextId = asset ? lightboxNeighborId(assetIds, asset.id, 1) : null;
  const isOpen = open && Boolean(asset);

  if (isOpen && openedAtRef.current === 0) {
    openedAtRef.current = Date.now();
  }
  if (!isOpen) {
    openedAtRef.current = 0;
  }

  useEffect(() => {
    setZoom(ML_LIGHTBOX_ZOOM_FIT);
    setDownloadBusy(false);
  }, [asset?.id]);

  useEffect(() => {
    if (open && asset) openedAtRef.current = Date.now();
  }, [open, asset?.id]);

  useEffect(() => {
    if (!open) return;

    function onKey(event: KeyboardEvent) {
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        if (prevId) onNavigate(prevId);
        return;
      }
      if (event.key === 'ArrowRight') {
        event.preventDefault();
        if (nextId) onNavigate(nextId);
        return;
      }
      if (event.key === '+' || event.key === '=') {
        event.preventDefault();
        setZoom((current) => stepLightboxZoom(current, 1));
        return;
      }
      if (event.key === '-' || event.key === '_') {
        event.preventDefault();
        setZoom((current) => stepLightboxZoom(current, -1));
      }
    }

    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, prevId, nextId, onNavigate]);

  useEffect(() => {
    if (!open) return;
    const stage = stageRef.current;
    if (!stage) return;

    function onWheel(event: WheelEvent) {
      event.preventDefault();
      const direction: 1 | -1 = event.deltaY < 0 ? 1 : -1;
      setZoom((current) => stepLightboxZoom(current, direction));
    }

    stage.addEventListener('wheel', onWheel, { passive: false });
    return () => stage.removeEventListener('wheel', onWheel);
  }, [open, asset?.id]);

  const guardedClose = useCallback(() => {
    // Ignore the same click that opened the overlay (React 19 can deliver it to the new Dialog).
    if (Date.now() - openedAtRef.current < 250) return;
    onClose();
  }, [onClose]);

  const handleDownload = useCallback(async () => {
    if (!asset || !onDownload || downloadBusy) return;
    setDownloadBusy(true);
    try {
      await onDownload(asset);
    } finally {
      setDownloadBusy(false);
    }
  }, [asset, onDownload, downloadBusy]);

  if (typeof document === 'undefined') return null;

  return createPortal(
    <Dialog
      open={open && Boolean(asset)}
      onClose={guardedClose}
      title={asset?.name ?? labels.title}
    >
      {asset ? (
        <div className="ml-lightbox" data-testid="ml-lightbox">
          <div className="ml-lightbox__toolbar" role="toolbar" aria-label={labels.title}>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => prevId && onNavigate(prevId)}
              disabled={!prevId}
              aria-label={labels.prev}
              data-testid="ml-lightbox-prev"
            >
              <IhIcon name="chevronLeft" size={14} />
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setZoom((current) => stepLightboxZoom(current, -1))}
              disabled={zoom <= ML_LIGHTBOX_ZOOM_MIN}
              aria-label={labels.zoomOut}
              data-testid="ml-lightbox-zoom-out"
            >
              −
            </Button>
            <span className="ml-lightbox__zoom" data-testid="ml-lightbox-zoom-level">
              {labels.zoomLevel(Math.round(zoom * 100))}
            </span>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setZoom((current) => stepLightboxZoom(current, 1))}
              disabled={zoom >= ML_LIGHTBOX_ZOOM_MAX}
              aria-label={labels.zoomIn}
              data-testid="ml-lightbox-zoom-in"
            >
              <IhIcon name="plus" size={14} />
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => void handleDownload()}
              disabled={!onDownload || downloadBusy}
              aria-label={labels.download}
              data-testid="ml-lightbox-download"
            >
              {labels.download}
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => nextId && onNavigate(nextId)}
              disabled={!nextId}
              aria-label={labels.next}
              data-testid="ml-lightbox-next"
            >
              <IhIcon name="chevronRight" size={14} />
            </Button>
          </div>

          <div ref={stageRef} className="ml-lightbox__stage" data-testid="ml-lightbox-stage">
            <div className="ml-lightbox__frame" style={{ ['--ml-zoom' as string]: String(zoom) }}>
              {previewUrl && asset.kind === 'image' ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={previewUrl}
                  alt={asset.name}
                  className="ml-lightbox__image"
                  data-testid="ml-lightbox-image"
                />
              ) : (
                <div className="ml-lightbox__doc" data-testid="ml-lightbox-doc">
                  <IhIcon name={docIcon(asset.ext)} size={64} />
                </div>
              )}
            </div>
          </div>

          <dl className="ml-lightbox__meta">
            <div>
              <dt>{labels.assetId}</dt>
              <dd className="ml-ws__mono" data-testid="ml-lightbox-asset-id">
                {asset.id}
              </dd>
            </div>
            <div>
              <dt>{labels.filename}</dt>
              <dd data-testid="ml-lightbox-filename">{asset.name}</dd>
            </div>
            <div>
              <dt>{labels.resolution}</dt>
              <dd data-testid="ml-lightbox-resolution">
                {asset.resolution || labels.resolutionUnavailable}
              </dd>
            </div>
            <div>
              <dt>{labels.source}</dt>
              <dd data-testid="ml-lightbox-source">{lightboxSourceLabel(asset, labels)}</dd>
            </div>
          </dl>
        </div>
      ) : null}
    </Dialog>,
    document.body,
  );
}
