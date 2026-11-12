const PREFIX: Record<string, string> = {
  USD: '$',
  EUR: '€',
  GBP: '£',
  TRY: '₺',
  TL: '₺',
};

export function currencyCode(currency?: string | null): string {
  return (currency || '').trim().toUpperCase();
}

export function currencyPrefix(currency?: string | null): string {
  return PREFIX[currencyCode(currency)] || '';
}

export function numericAmount(value?: string | null): string {
  return String(value || '').replace(/[^0-9.]/g, '');
}

export function formatAgreementAmount(amount?: string | null, currency?: string | null): string | null {
  const raw = String(amount || '').trim();
  if (!raw) return null;
  const code = currencyCode(currency);
  const prefix = currencyPrefix(code);
  if (prefix && raw.startsWith(prefix)) return raw.replace(/\s*USD$/i, '').trim();
  const numeric = numericAmount(raw);
  if (!numeric || Number.isNaN(Number(numeric))) return raw;
  const formatted = new Intl.NumberFormat('en-US', {
    maximumFractionDigits: Number.isInteger(Number(numeric)) ? 0 : 2,
  }).format(Number(numeric));
  if (prefix) return `${prefix}${formatted}`;
  if (code) return `${formatted} ${code}`;
  return formatted;
}
