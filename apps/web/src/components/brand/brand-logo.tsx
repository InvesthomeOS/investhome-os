'use client';

import { useSyncExternalStore } from 'react';

export type BrandLogoTone = 'auto' | 'color' | 'black' | 'white';
export type BrandLogoLayout = 'full' | 'mark';

const LOGO_SRC = {
  color: '/brand/logos/investhome-logo-color.png',
  black: '/brand/logos/investhome-logo-black.png',
  white: '/brand/logos/investhome-logo-white.png',
} as const;

const MARK_SRC = {
  color: '/brand/logos/investhome-mark-color.png',
  black: '/brand/logos/investhome-mark-black.png',
  white: '/brand/logos/investhome-mark-white.png',
} as const;

function subscribeTheme(onStoreChange: () => void) {
  if (typeof document === 'undefined') {
    return () => undefined;
  }
  const root = document.documentElement;
  const observer = new MutationObserver(onStoreChange);
  observer.observe(root, { attributes: true, attributeFilter: ['data-theme'] });
  return () => observer.disconnect();
}

function getResolvedTheme(): 'light' | 'dark' {
  if (typeof document === 'undefined') {
    return 'light';
  }
  return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
}

function resolveTone(tone: BrandLogoTone, theme: 'light' | 'dark'): keyof typeof LOGO_SRC {
  if (tone !== 'auto') {
    return tone;
  }
  return theme === 'dark' ? 'white' : 'color';
}

export interface BrandLogoProps {
  tone?: BrandLogoTone;
  layout?: BrandLogoLayout;
  className?: string;
  priority?: boolean;
  alt?: string;
}

export function BrandLogo({
  tone = 'auto',
  layout = 'full',
  className,
  priority = false,
  alt = 'Investhome',
}: BrandLogoProps) {
  const theme = useSyncExternalStore(subscribeTheme, getResolvedTheme, () => 'light' as const);
  const toneKey = resolveTone(tone, theme);
  const src = layout === 'mark' ? MARK_SRC[toneKey] : LOGO_SRC[toneKey];
  const classes = [
    'brand-logo',
    layout === 'mark' ? 'brand-logo--mark' : 'brand-logo--full',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    // eslint-disable-next-line @next/next/no-img-element -- brand masters are static public assets; avoid Next image optimizer for huge PNGs
    <img
      className={classes}
      src={src}
      alt={alt}
      decoding="async"
      fetchPriority={priority ? 'high' : 'auto'}
      draggable={false}
    />
  );
}
