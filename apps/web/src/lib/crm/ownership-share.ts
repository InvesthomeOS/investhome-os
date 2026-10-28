/** Client check before an ownership save. The API validates again. */
export function ownershipShareError(values: string[]): string | null {
  let cents = 0;
  for (const value of values) {
    const text = value.trim();
    if (!/^\d+(\.\d{1,2})?$/.test(text)) return 'Sahiplik toplamı 100 olmalıdır.';
    const [whole, fraction = ''] = text.split('.');
    const frac = `${fraction}00`.slice(0, 2);
    cents += Number(whole) * 100 + Number(frac);
  }
  if (cents !== 10000) return 'Sahiplik toplamı 100 olmalıdır.';
  return null;
}
