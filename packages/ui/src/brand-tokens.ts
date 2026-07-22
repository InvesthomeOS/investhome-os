/**
 * Official Investhome brand tokens from Kurumsal-font-renk color guide.
 * CSS variables are defined in apps/web theme-tokens.css; keep HEX in sync.
 */
export const brandTokens = {
  primary: '#9D7B55',
  primaryHover: '#866848',
  secondary: '#C3A47F',
  accent: '#77BFBB',
  black: '#000000',
  white: '#FFFFFF',
  surface: '#FFFFFF',
  surfaceMuted: '#F6F2EC',
  border: '#E4DCD2',
  text: '#000000',
  textMuted: '#7C7B7A',
} as const;

export type BrandTokenName = keyof typeof brandTokens;
