'use client';

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type RefObject,
} from 'react';
import { createPortal } from 'react-dom';

import {
  MediaLibraryTagEditor,
  type MediaLibraryTagEditorLabels,
} from './media-library-tag-editor';
import { pushRecentTags, uniqueTags } from './media-library-tag-utils';

export type MediaLibraryQuickTagPopoverProps = {
  open: boolean;
  anchorRef: RefObject<HTMLElement | null>;
  assetId: string;
  initialTags: string[];
  libraryTags: string[];
  recentTags: string[];
  labels: MediaLibraryTagEditorLabels & { title: string };
  busy?: boolean;
  error?: string | null;
  onClose: () => void;
  onApply: (assetId: string, tags: string[]) => Promise<boolean>;
  onRecentTagsChange?: (tags: string[]) => void;
};

const EDGE = 8;
const WIDTH = 280;

export function MediaLibraryQuickTagPopover({
  open,
  anchorRef,
  assetId,
  initialTags,
  libraryTags,
  recentTags,
  labels,
  busy = false,
  error = null,
  onClose,
  onApply,
  onRecentTagsChange,
}: MediaLibraryQuickTagPopoverProps) {
  const panelRef = useRef<HTMLDivElement | null>(null);
  const [pos, setPos] = useState({ top: 0, left: 0 });
  const [ready, setReady] = useState(false);
  const [draft, setDraft] = useState<string[]>(initialTags);
  const [localError, setLocalError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setDraft(uniqueTags(initialTags));
    setLocalError(null);
    setSaving(false);
  }, [open, assetId, initialTags]);

  const place = useCallback(() => {
    const anchor = anchorRef.current;
    const panel = panelRef.current;
    if (!anchor || !panel) return;
    const a = anchor.getBoundingClientRect();
    const p = panel.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const height = p.height || 320;

    let top = a.bottom + 6;
    let left = a.right - WIDTH;
    if (top + height > vh - EDGE) top = Math.max(EDGE, a.top - height - 6);
    if (left + WIDTH > vw - EDGE) left = vw - EDGE - WIDTH;
    if (left < EDGE) left = EDGE;
    setPos({ top, left });
    setReady(true);
  }, [anchorRef]);

  useLayoutEffect(() => {
    if (!open) {
      setReady(false);
      return;
    }
    place();
  }, [open, place, draft.length, error, localError]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    }
    function onPointer(e: MouseEvent) {
      const t = e.target as Node;
      if (panelRef.current?.contains(t)) return;
      if (anchorRef.current?.contains(t)) return;
      onClose();
    }
    function onReposition() {
      place();
    }
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onPointer);
    window.addEventListener('resize', onReposition);
    window.addEventListener('scroll', onReposition, true);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onPointer);
      window.removeEventListener('resize', onReposition);
      window.removeEventListener('scroll', onReposition, true);
    };
  }, [open, onClose, place, anchorRef]);

  async function handleApply() {
    setSaving(true);
    setLocalError(null);
    const ok = await onApply(assetId, uniqueTags(draft));
    setSaving(false);
    if (!ok) {
      setLocalError(error);
      return;
    }
    const recent = pushRecentTags(draft);
    onRecentTagsChange?.(recent);
    onClose();
  }

  if (!open || typeof document === 'undefined') return null;

  return createPortal(
    <div
      ref={panelRef}
      className="ml-quick-tag"
      role="dialog"
      aria-label={labels.title}
      data-testid="ml-quick-tag-popover"
      style={{
        top: pos.top,
        left: pos.left,
        width: WIDTH,
        visibility: ready ? 'visible' : 'hidden',
      }}
    >
      <div className="ml-quick-tag__head">{labels.title}</div>
      <MediaLibraryTagEditor
        value={draft}
        libraryTags={libraryTags}
        recentTags={recentTags}
        labels={labels}
        busy={busy || saving}
        error={localError || error}
        onChange={setDraft}
        onApply={() => void handleApply()}
        onCancel={onClose}
        testIdPrefix="ml-quick-tag"
      />
    </div>,
    document.body,
  );
}
