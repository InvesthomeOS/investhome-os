/**
 * Shared Media Library selectability rules for Creative Studio builders.
 * ACTIVE → selectable; MISSING → visible but disabled; archived/error → not selectable.
 */

import type { CreativeStudioMediaAsset } from '@/lib/api/creative-studio';

import { isDemoAssetId, isMediaAssetUuid } from './cs-image-ref';

export type CsAssetDisabledReason =
  | 'missing'
  | 'archived'
  | 'error'
  | 'demo'
  | 'invalid';

export type CsAssetSelectability = {
  selectable: boolean;
  /** When false, reason explains why (for badges / tooltips). */
  reason: CsAssetDisabledReason | null;
};

export function normalizeSyncStatus(
  syncStatus: string | null | undefined,
): string {
  return String(syncStatus || '')
    .trim()
    .toLowerCase();
}

export function getAssetSelectability(
  asset: Pick<
    CreativeStudioMediaAsset,
    'id' | 'archived_at' | 'sync_status'
  >,
): CsAssetSelectability {
  if (!asset?.id || isDemoAssetId(asset.id) || !isMediaAssetUuid(asset.id)) {
    return { selectable: false, reason: 'demo' };
  }
  if (asset.archived_at) {
    return { selectable: false, reason: 'archived' };
  }
  const sync = normalizeSyncStatus(asset.sync_status);
  if (sync === 'missing') {
    return { selectable: false, reason: 'missing' };
  }
  if (sync === 'error' || sync === 'corrupted') {
    return { selectable: false, reason: 'error' };
  }
  return { selectable: true, reason: null };
}

/** Include in picker lists: non-archived (MISSING/error stay visible but disabled). */
export function shouldShowInBuilderPicker(
  asset: Pick<CreativeStudioMediaAsset, 'archived_at'>,
): boolean {
  return !asset.archived_at;
}

/**
 * Filter for builder apply lists that only want ACTIVE selectable assets
 * (legacy Website Builder rail that cannot show disabled state).
 */
export function isActiveSelectableAsset(
  asset: Pick<CreativeStudioMediaAsset, 'id' | 'archived_at' | 'sync_status'>,
): boolean {
  return getAssetSelectability(asset).selectable;
}
