type MessageValue = string | Messages;
export type Messages = { [key: string]: MessageValue };

function isPlainObject(value: unknown): value is Messages {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function mergeMessages(base: Messages, override: Messages): Messages {
  const merged: Messages = { ...base };

  for (const [key, value] of Object.entries(override)) {
    const baseValue = merged[key];

    if (isPlainObject(value) && isPlainObject(baseValue)) {
      merged[key] = mergeMessages(baseValue, value);
      continue;
    }

    merged[key] = value;
  }

  return merged;
}
