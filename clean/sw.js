// Service Worker — self-destruct to clear old caches
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', () => {
  caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))));
  self.registration.unregister().then(() => self.clients.matchAll().then(clients => clients.forEach(c => c.navigate(c.url))));
});
