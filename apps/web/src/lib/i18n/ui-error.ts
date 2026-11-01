/** User-facing API failures. The raw message stays in the console for diagnosis. */
export function uiError(error: unknown, fallback: string): string {
  const raw =
    error instanceof Error
      ? error.message
      : typeof error === 'string'
        ? error
        : '';
  if (raw && raw !== fallback && typeof console !== 'undefined') {
    console.error(raw);
  }
  return fallback;
}
