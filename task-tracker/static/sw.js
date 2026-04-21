// Service Worker: network-first + chat push notifications

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

self.addEventListener('fetch', (e) => {
  e.respondWith(fetch(e.request));
});

self.addEventListener('push', (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (_) {
    payload = {};
  }
  const title = payload.title || 'MiSpring: новое сообщение';
  const options = {
    body: payload.body || 'Откройте чат, чтобы прочитать',
    icon: '/static/apple-touch-icon.png',
    badge: '/static/apple-touch-icon.png',
    tag: payload.tag || 'mispring-chat',
    renotify: true,
    data: {
      url: payload.url || '/',
      dialog_id: payload.dialog_id || null,
    },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = (event.notification && event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      const opened = list.find((c) => c.url && c.url.includes(self.location.origin));
      if (opened) {
        opened.focus();
        opened.postMessage({ type: 'chat-open', url: targetUrl });
        return opened.navigate(targetUrl);
      }
      return clients.openWindow(targetUrl);
    })
  );
});
