/* Minimal PWA service worker for /app/ */

const CACHE_NAME = 'cla-app-v1';

// Keep this list intentionally small; Vite emits hashed assets.
const PRECACHE_URLS = [
  '/app/',
  '/app/manifest.webmanifest',
  '/app/icon.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)));
      await self.clients.claim();
    })(),
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Only handle same-origin GET requests.
  if (request.method !== 'GET') return;
  if (url.origin !== self.location.origin) return;

  // Only handle the app scope.
  if (!url.pathname.startsWith('/app/')) return;

  event.respondWith(
    (async () => {
      const cache = await caches.open(CACHE_NAME);

      // Network-first for navigation so the latest bundle loads.
      if (request.mode === 'navigate') {
        try {
          const fresh = await fetch(request);
          cache.put(request, fresh.clone());
          return fresh;
        } catch {
          const cached = await cache.match('/app/');
          if (cached) return cached;
          throw new Error('offline');
        }
      }

      // Cache-first for static assets.
      const cached = await cache.match(request);
      if (cached) return cached;

      try {
        const fresh = await fetch(request);
        cache.put(request, fresh.clone());
        return fresh;
      } catch {
        return new Response('', { status: 504, statusText: 'offline' });
      }
    })(),
  );
});
