/** Decide which notifications are new enough to toast.

The first successful fetch is the baseline. Later polls toast only unread ids
that were not in that baseline or any later response. The same id never toasts twice.
*/

export function notificationStatus(item) {
  return String(item?.status || '').trim().toLowerCase();
}

export function observeNotificationIds(seen, items) {
  const rows = Array.isArray(items) ? items : [];
  const ids = rows.map((item) => String(item.id));
  if (seen == null) {
    return { seen: new Set(ids), fresh: [] };
  }
  const fresh = rows.filter((item) => {
    const id = String(item.id);
    return notificationStatus(item) === 'unread' && !seen.has(id);
  });
  const next = new Set(seen);
  ids.forEach((id) => next.add(id));
  return { seen: next, fresh };
}
