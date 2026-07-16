'use client';

import { useEffect } from 'react';

import { useCompanyBranding } from '@/lib/company/company-context';

/** Applies Company Foundation brand colors to CSS custom properties at runtime. */
export function BrandThemeInjector() {
  const { context, publicBrand, primaryColor, accentColor } = useCompanyBranding();

  useEffect(() => {
    const brand = context?.brand;
    const root = document.documentElement;

    if (brand?.primary_color) {
      root.style.setProperty('--brand-primary', brand.primary_color);
    } else if (primaryColor) {
      root.style.setProperty('--brand-primary', primaryColor);
    }

    if (brand?.accent_color) {
      root.style.setProperty('--accent', brand.accent_color);
      root.style.setProperty('--focus-ring', brand.accent_color);
    } else if (accentColor) {
      root.style.setProperty('--accent', accentColor);
      root.style.setProperty('--focus-ring', accentColor);
    }

    if (brand?.secondary_color) {
      root.style.setProperty('--brand-secondary', brand.secondary_color);
    }

    if (brand?.background_color) {
      root.style.setProperty('--bg', brand.background_color);
      root.style.setProperty('--background', brand.background_color);
    }

    if (brand?.surface_color) {
      root.style.setProperty('--surface', brand.surface_color);
      root.style.setProperty('--surface-elevated', brand.surface_color);
    }

    if (brand?.text_primary_color) {
      root.style.setProperty('--text', brand.text_primary_color);
      root.style.setProperty('--foreground', brand.text_primary_color);
    }

    if (brand?.text_secondary_color) {
      root.style.setProperty('--text-secondary', brand.text_secondary_color);
      root.style.setProperty('--muted', brand.text_secondary_color);
    }

    if (brand?.success_color) {
      root.style.setProperty('--success', brand.success_color);
    }

    if (brand?.warning_color) {
      root.style.setProperty('--warning', brand.warning_color);
    }

    if (brand?.error_color) {
      root.style.setProperty('--danger', brand.error_color);
      root.style.setProperty('--error', brand.error_color);
    }

    return () => {
      [
        '--brand-primary',
        '--brand-secondary',
        '--accent',
        '--focus-ring',
        '--bg',
        '--background',
        '--surface',
        '--surface-elevated',
        '--text',
        '--foreground',
        '--text-secondary',
        '--muted',
        '--success',
        '--warning',
        '--danger',
        '--error',
      ].forEach((prop) => root.style.removeProperty(prop));
    };
  }, [context, publicBrand, primaryColor, accentColor]);

  return null;
}
