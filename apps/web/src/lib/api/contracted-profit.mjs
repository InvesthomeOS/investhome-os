/** Blank stays unknown. A typed zero is kept. Never coerce an empty field to 0. */
export function contractedProfitInput(raw) {
  const trimmed = String(raw ?? '').trim();
  if (!trimmed) return null;
  if (!/^\d+(\.\d{1,2})?$/.test(trimmed)) {
    throw new Error('invalid_contracted_profit');
  }
  return trimmed;
}
