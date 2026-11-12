export const OS_TIME_ZONE = 'Europe/Istanbul';

const TURKISH_MONTHS = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara'];

function asDate(value) {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function parts(date, timeZone) {
  const listed = new Intl.DateTimeFormat('en-GB', {
    timeZone,
    day: 'numeric',
    month: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(date);
  const read = (type) => listed.find((part) => part.type === type)?.value || '';
  return {
    day: Number(read('day')),
    month: Number(read('month')),
    year: read('year'),
    hour: read('hour'),
    minute: read('minute'),
  };
}

export function formatOsDate(value, locale = 'tr', timeZone = OS_TIME_ZONE) {
  const date = asDate(value);
  if (!date) return '—';
  const item = parts(date, timeZone);
  if (locale === 'tr') return `${item.day} ${TURKISH_MONTHS[item.month - 1]} ${item.year}`;
  return new Intl.DateTimeFormat('en-GB', {
    timeZone,
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(date);
}

export function formatOsDateTime(value, locale = 'tr', timeZone = OS_TIME_ZONE) {
  const date = asDate(value);
  if (!date) return '—';
  const item = parts(date, timeZone);
  return `${formatOsDate(date, locale, timeZone)} · ${item.hour}:${item.minute}`;
}

export function formatOsRelative(value, now = new Date(), locale = 'tr') {
  const date = asDate(value);
  const current = asDate(now);
  if (!date || !current) return '—';
  const minutes = Math.round((current.getTime() - date.getTime()) / 60000);
  const elapsed = Math.abs(minutes);
  if (elapsed < 1) return locale === 'tr' ? 'az önce' : 'just now';
  if (elapsed < 60) return locale === 'tr' ? `${elapsed} dk önce` : `${elapsed} min ago`;
  const hours = Math.round(elapsed / 60);
  if (hours < 24) return locale === 'tr' ? `${hours} sa önce` : `${hours} hr ago`;
  const days = Math.round(hours / 24);
  return locale === 'tr' ? `${days} gün önce` : `${days} days ago`;
}
