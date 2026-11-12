/** Default reminder for a new task. Existing tasks are not rewritten. */

export const DEFAULT_TASK_REMINDER_MINUTES = 10;

export function reminderInstant(dueIso, minutes = DEFAULT_TASK_REMINDER_MINUTES) {
  const due = new Date(dueIso);
  if (Number.isNaN(due.getTime())) return null;
  return new Date(due.getTime() - Number(minutes) * 60_000).toISOString();
}

export function reminderPayload(dueIso, minutes, channel = 'in_app') {
  if (minutes === 'none' || minutes == null || !dueIso) return [];
  const remindAt = reminderInstant(dueIso, minutes);
  if (!remindAt) return [];
  const channels = channel === 'both' ? ['in_app', 'email'] : [channel || 'in_app'];
  return channels.map((item) => ({
    channel: item,
    remind_at: remindAt,
    offset_minutes: Number(minutes),
  }));
}
