export const DEFAULT_TASK_REMINDER_MINUTES: number;
export function reminderInstant(dueIso: string, minutes?: number): string | null;
export function reminderPayload(
  dueIso: string,
  minutes: number | string,
  channel?: string,
): Array<{ channel: string; remind_at: string; offset_minutes: number }>;
