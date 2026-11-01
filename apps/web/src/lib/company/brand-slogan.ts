/** Company seed slogan. Custom slogans are shown as stored. */
export const DEFAULT_COMPANY_SLOGAN = "Building tomorrow's communities";

export function loginHeading(
  slogan: string | null | undefined,
  brandSlogan: string,
  title: string,
): string {
  const value = slogan?.trim();
  if (!value) return title;
  if (value === DEFAULT_COMPANY_SLOGAN) return brandSlogan;
  return value;
}
