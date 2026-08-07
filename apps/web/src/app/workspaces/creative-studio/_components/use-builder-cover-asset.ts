'use client';

/**
 * Shared cover/hero image slot for Creative Studio builders.
 * Persists CsImageRef (Asset ID primary); resolves live content on load.
 */

import { useCallback, useEffect, useMemo, useState, type Dispatch, type SetStateAction } from 'react';

import {
  imageRefFromLegacyUrl,
  imageRefFromMediaAsset,
  resolveDisplayUrl,
  type CsImageRef,
} from './cs-image-ref';
import type { CsMediaPickerItem } from './use-cs-media-library';
import { useCsMediaLibrary } from './use-cs-media-library';

export type UseBuilderCoverAssetResult = {
  media: ReturnType<typeof useCsMediaLibrary>;
  coverImage: CsImageRef | null;
  setCoverImage: (ref: CsImageRef | null) => void;
  galleryImages: CsImageRef[];
  setGalleryImages: Dispatch<SetStateAction<CsImageRef[]>>;
  coverDisplayUrl: string;
  galleryDisplayUrls: string[];
  pickerOpen: boolean;
  openPicker: (mode?: 'cover' | 'gallery') => void;
  closePicker: () => void;
  pickerMode: 'cover' | 'gallery';
  applyPickerSelection: (ref: CsImageRef, item: CsMediaPickerItem) => void;
  clearCover: () => void;
};

export function useBuilderCoverAsset(options: {
  templateCoverUrl: string;
  templateGalleryUrls?: string[];
  enabled?: boolean;
}): UseBuilderCoverAssetResult {
  const { templateCoverUrl, templateGalleryUrls = [], enabled = true } = options;
  const media = useCsMediaLibrary({ enabled, imagesOnly: true });

  const [coverImage, setCoverImage] = useState<CsImageRef | null>(null);
  const [galleryImages, setGalleryImages] = useState<CsImageRef[]>([]);
  const [resolvedCover, setResolvedCover] = useState<string | null>(null);
  const [resolvedGallery, setResolvedGallery] = useState<Record<string, string>>({});
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerMode, setPickerMode] = useState<'cover' | 'gallery'>('cover');

  // Project/template switch: keep Asset ID refs; seed URL-only legacy from template when empty.
  useEffect(() => {
    setCoverImage((prev) => {
      if (prev?.asset_id) return prev;
      return imageRefFromLegacyUrl(templateCoverUrl, 'cover');
    });
  }, [templateCoverUrl]);

  useEffect(() => {
    setGalleryImages((prev) => {
      if (prev.some((r) => r.asset_id)) return prev;
      if (!templateGalleryUrls.length) return prev;
      return templateGalleryUrls
        .map((u) => imageRefFromLegacyUrl(u, 'gallery'))
        .filter((r): r is CsImageRef => r != null);
    });
  }, [templateGalleryUrls]);

  useEffect(() => {
    const assetId = coverImage?.asset_id;
    if (!assetId) {
      setResolvedCover(null);
      return;
    }
    let cancelled = false;
    void media.ensureDisplayUrl(assetId).then((url) => {
      if (!cancelled) setResolvedCover(url);
    });
    return () => {
      cancelled = true;
    };
  }, [coverImage?.asset_id, media.ensureDisplayUrl]);

  useEffect(() => {
    const ids = galleryImages
      .map((r) => r.asset_id)
      .filter((id): id is string => Boolean(id));
    for (const id of ids) {
      void media.ensureDisplayUrl(id).then((url) => {
        if (url) setResolvedGallery((prev) => ({ ...prev, [id]: url }));
      });
    }
  }, [galleryImages, media.ensureDisplayUrl]);

  const coverDisplayUrl = useMemo(
    () =>
      resolveDisplayUrl({
        ref: coverImage,
        resolvedAssetUrl: resolvedCover,
        templateUrl: templateCoverUrl,
      }) ?? templateCoverUrl,
    [coverImage, resolvedCover, templateCoverUrl],
  );

  const galleryDisplayUrls = useMemo(() => {
    if (galleryImages.length) {
      return galleryImages
        .map((ref) =>
          resolveDisplayUrl({
            ref,
            resolvedAssetUrl: ref.asset_id ? resolvedGallery[ref.asset_id] : null,
            templateUrl: templateGalleryUrls[0] ?? templateCoverUrl,
          }),
        )
        .filter((u): u is string => Boolean(u));
    }
    return templateGalleryUrls.length ? [...templateGalleryUrls] : [];
  }, [galleryImages, resolvedGallery, templateCoverUrl, templateGalleryUrls]);

  const openPicker = useCallback((mode: 'cover' | 'gallery' = 'cover') => {
    setPickerMode(mode);
    setPickerOpen(true);
  }, []);

  const closePicker = useCallback(() => setPickerOpen(false), []);

  const applyPickerSelection = useCallback(
    (ref: CsImageRef, _item: CsMediaPickerItem) => {
      if (pickerMode === 'gallery') {
        setGalleryImages((prev) =>
          [ref, ...prev.filter((r) => !(ref.asset_id && r.asset_id === ref.asset_id))].slice(
            0,
            12,
          ),
        );
      } else {
        setCoverImage(ref);
      }
      setPickerOpen(false);
    },
    [pickerMode],
  );

  const clearCover = useCallback(() => {
    setCoverImage(null);
    setResolvedCover(null);
  }, []);

  return {
    media,
    coverImage,
    setCoverImage,
    galleryImages,
    setGalleryImages,
    coverDisplayUrl,
    galleryDisplayUrls,
    pickerOpen,
    openPicker,
    closePicker,
    pickerMode,
    applyPickerSelection,
    clearCover,
  };
}

/** Convenience: build ref from uploaded/selected Media Library asset. */
export function coverRefFromAsset(
  asset: Parameters<typeof imageRefFromMediaAsset>[0],
  role: string = 'cover',
): CsImageRef {
  return imageRefFromMediaAsset(asset, role);
}
