self.addEventListener('push', (event) => {
  let payload = { title: 'Investhome', body: '', notification_id: '' };
  try {
    payload = { ...payload, ...(event.data ? event.data.json() : {}) };
  } catch {
    payload.body = event.data ? event.data.text() : '';
  }
  event.waitUntil(
    self.registration.showNotification(payload.title || 'Investhome', {
      body: payload.body || '',
      tag: payload.notification_id || undefined,
      requireInteraction: true,
      data: payload,
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      const target = clients.find((client) => 'focus' in client);
      if (target) {
        target.postMessage({ type: 'notification-refresh' });
        return target.focus();
      }
      return self.clients.openWindow('/');
    }),
  );
});
