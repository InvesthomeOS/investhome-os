export const OS_TIME_ZONE: string;
export function formatOsDate(value: string | Date, locale?: string, timeZone?: string): string;
export function formatOsDateTime(value: string | Date, locale?: string, timeZone?: string): string;
export function formatOsRelative(value: string | Date, now?: string | Date, locale?: string): string;
