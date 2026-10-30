export const PLATFORM_TIMEZONE = 'Europe/Istanbul';

export type GreetingPeriod = 'morning' | 'afternoon' | 'evening' | 'night';

export type GreetingIdentity = {
  full_name?: string | null;
  email?: string | null;
};

export function isValidTimeZone(value: string): boolean {
  const zone = value.trim();
  if (!zone) return false;
  try {
    Intl.DateTimeFormat('en-US', { timeZone: zone }).format(new Date());
    return true;
  } catch {
    return false;
  }
}

export function resolveGreetingTimezone(
  saved: string | null | undefined,
  browserZone?: string | null,
): string {
  const profileZone = saved?.trim() ?? '';
  if (profileZone && isValidTimeZone(profileZone)) return profileZone;
  const deviceZone = browserZone?.trim() ?? '';
  if (deviceZone && isValidTimeZone(deviceZone)) return deviceZone;
  return PLATFORM_TIMEZONE;
}

export function hourInTimeZone(date: Date, timeZone: string): number {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    hour: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(date);
  const raw = parts.find((part) => part.type === 'hour')?.value ?? '0';
  const hour = Number(raw);
  if (!Number.isFinite(hour)) return 0;
  return hour === 24 ? 0 : hour;
}

export function greetingPeriod(date: Date, timeZone: string): GreetingPeriod {
  const hour = hourInTimeZone(date, timeZone);
  if (hour >= 5 && hour <= 11) return 'morning';
  if (hour >= 12 && hour <= 17) return 'afternoon';
  if (hour >= 18 && hour <= 23) return 'evening';
  return 'night';
}

export function profileNameParts(fullName: string | null | undefined): { first: string; last: string } {
  const trimmed = (fullName ?? '').trim().replace(/\s+/g, ' ');
  if (!trimmed) return { first: '', last: '' };
  const [first, ...rest] = trimmed.split(' ');
  return { first: first ?? '', last: rest.join(' ') };
}

function nameFromEmail(email: string | null | undefined): string {
  const local = (email ?? '').split('@')[0] ?? '';
  const segment = local.split(/[._+-]/)[0] ?? '';
  const letters = segment.replace(/[^A-Za-zÀ-ÿĞğİıÖöŞşÜüÇç]/g, '');
  if (!letters) return '';
  return letters.charAt(0).toLocaleUpperCase('tr-TR') + letters.slice(1);
}

export function greetingName(user: GreetingIdentity | null | undefined): string {
  const fullName = user?.full_name?.trim() ?? '';
  const { first } = profileNameParts(fullName);
  if (first) return first;
  if (fullName) return fullName;
  return nameFromEmail(user?.email);
}

export function formatGreeting(
  period: GreetingPeriod,
  name: string,
  phrases: Record<GreetingPeriod, string>,
): string {
  const phrase = phrases[period];
  const cleanName = name.trim();
  return cleanName ? `${phrase} ${cleanName}` : phrase;
}
