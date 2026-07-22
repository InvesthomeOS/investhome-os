/** Strip HTML and limit length for safe display of user-entered text. */
export function sanitizeDisplayText(input: string, maxLength = 500): string {
  const stripped = input
    .replace(/<[^>]*>/g, '')
    .replace(/[<>&"']/g, (char) => {
      const map: Record<string, string> = {
        '<': '&lt;',
        '>': '&gt;',
        '&': '&amp;',
        '"': '&quot;',
        "'": '&#39;',
      };
      return map[char] ?? char;
    })
    .trim();
  if (stripped.length <= maxLength) return stripped;
  return `${stripped.slice(0, maxLength)}…`;
}

/** Sanitize for plain-text rendering (React text nodes — no HTML entities needed). */
export function sanitizePlainText(input: string, maxLength = 500): string {
  const stripped = input.replace(/<[^>]*>/g, '').trim();
  if (stripped.length <= maxLength) return stripped;
  return `${stripped.slice(0, maxLength)}…`;
}
