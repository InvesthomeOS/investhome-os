export function notificationTextPath(key: string): string;
export function isRawMessageKey(value: unknown): boolean;
export function notificationFallback(
  key: string,
  metadata?: Record<string, string>,
  locale?: string,
): string;
