/**
 * INVESTHOME OS Design System v1.0 — TypeScript mirror of semantic CSS tokens.
 * Source of truth for HEX/brand remains apps/web theme-tokens.css + brandTokens.
 */
import { brandTokens } from './brand-tokens.js';

/** UXR1 V2 product UI palette (logo Pantone does not dictate chrome). */
export const uxr1V2Tokens = {
  color: {
    navy900: '#0B1F3A',
    navy800: '#0F2744',
    navy700: '#1A3A5C',
    navy100: '#E8EEF5',
    navy50: '#F2F6FA',
    blue600: '#2563EB',
    blue500: '#3B82F6',
    blue100: '#DBEAFE',
    blue50: '#EFF6FF',
    gray50: '#F8FAFC',
    gray100: '#F1F5F9',
    gray200: '#E2E8F0',
    gray300: '#CBD5E1',
    gray500: '#64748B',
    gray700: '#334155',
    gray900: '#0F172A',
    canvas: '#FFFFFF',
  },
  radius: {
    card: '1rem',
    cardLg: '1.25rem',
  },
  shadow: {
    cardPremium: '0 1px 2px rgba(15, 39, 68, 0.04), 0 6px 20px rgba(15, 39, 68, 0.07)',
  },
  spacing: {
    shellContentPadX: '1.75rem',
    shellContentPadY: '1.25rem',
    sectionGap: '1.25rem',
    cardPaddingX: '1.5rem',
    cardPaddingY: '1.25rem',
  },
  pipelineTint: {
    lead: '#F0F7FF',
    qualify: '#EEF8F4',
    proposal: '#F5F3FF',
    negotiation: '#FFF7ED',
    won: '#ECFDF5',
    lost: '#F8FAFC',
  },
} as const;

export const designTokens = {
  color: {
    backgroundCanvas: '#F7F4EF',
    backgroundSubtle: brandTokens.surfaceMuted,
    backgroundElevated: brandTokens.surface,
    surfaceDefault: brandTokens.surface,
    surfaceSubtle: brandTokens.surfaceMuted,
    borderDefault: brandTokens.border,
    textPrimary: brandTokens.text,
    textSecondary: brandTokens.textMuted,
    brandPrimary: brandTokens.primary,
    brandSecondary: brandTokens.secondary,
    statusSuccess: '#16A34A',
    statusWarning: '#D97706',
    statusDanger: '#DC2626',
    statusInfo: '#5AA8A4',
    statusAi: '#6B5B95',
    /** V2 product UI (opt-in via data-ds-version=v2) */
    v2Canvas: uxr1V2Tokens.color.canvas,
    v2Navy: uxr1V2Tokens.color.navy800,
    v2Blue: uxr1V2Tokens.color.blue600,
    v2GrayBorder: uxr1V2Tokens.color.gray200,
  },
  spacing: {
    2: 2,
    4: 4,
    6: 6,
    8: 8,
    12: 12,
    16: 16,
    20: 20,
    24: 24,
    32: 32,
    40: 40,
    48: 48,
    64: 64,
  },
  radius: {
    small: '0.375rem',
    medium: '0.5rem',
    large: '0.75rem',
    extraLarge: '1rem',
    full: '999px',
    card: uxr1V2Tokens.radius.card,
    cardLg: uxr1V2Tokens.radius.cardLg,
  },
  shadow: {
    none: 'none',
    subtle: '0 1px 2px rgba(26, 20, 4, 0.04)',
    medium: '0 2px 8px rgba(26, 20, 4, 0.07)',
    card: '0 1px 3px rgba(26, 20, 4, 0.06), 0 1px 2px rgba(26, 20, 4, 0.04)',
    cardPremium: uxr1V2Tokens.shadow.cardPremium,
    elevated: '0 4px 16px rgba(26, 20, 4, 0.08)',
    overlay: '0 12px 32px rgba(26, 20, 4, 0.14)',
  },
  typography: {
    display: { size: '2rem', weight: 600, lineHeight: 1.2 },
    pageTitle: { size: '1.5rem', weight: 600, lineHeight: 1.25 },
    sectionTitle: { size: '1.125rem', weight: 600, lineHeight: 1.35 },
    cardTitle: { size: '1rem', weight: 600, lineHeight: 1.4 },
    body: { size: '0.9375rem', weight: 400, lineHeight: 1.5 },
    bodySmall: { size: '0.875rem', weight: 400, lineHeight: 1.45 },
    label: { size: '0.8125rem', weight: 500, lineHeight: 1.35 },
    caption: { size: '0.75rem', weight: 400, lineHeight: 1.4 },
    table: { size: '0.8125rem', weight: 400, lineHeight: 1.35 },
    metricLarge: { size: '1.75rem', weight: 600, lineHeight: 1.15 },
    metricMedium: { size: '1.25rem', weight: 600, lineHeight: 1.2 },
    code: { size: '0.8125rem', weight: 400, lineHeight: 1.4 },
  },
  grid: {
    columnsDesktop: 12,
    columnsTablet: 8,
    columnsMobile: 1,
    gapDesktop: 24,
    gapMobile: 16,
  },
} as const;

export type DesignSpacing = keyof typeof designTokens.spacing;
export type DesignRadius = keyof typeof designTokens.radius;
export type DesignShadow = keyof typeof designTokens.shadow;
