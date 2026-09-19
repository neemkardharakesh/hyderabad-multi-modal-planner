const CACHE_NAME = 'hyd-transit-v3';
const STATIC_ASSETS = [
  './',
  './index.html',
  './styles.css',
  './manifest.json',
  './stops.json',
  './all_bus_stops.json',
  './assets/telangana_logo.png',
  './assets/icon-192.png',
  './assets/icon-512.png',
  './assets/charminar.png',
  './assets/metro_train.jpg',
  './assets/secretariat.jpg',
  './assets/tgsrtc_bus.jpg',
  './assets/chowmahalla.jpg',
  './assets/mmts_train1.jpg',
  './assets/buddha_statue.png',
  './assets/mmts_train2.jpg',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css',
  'https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css',
  'https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js',
  'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[ServiceWorker] Pre-caching static assets for Go Hyderabad');
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.warn('[ServiceWorker] Non-fatal asset caching note:', err);
      });
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[ServiceWorker] Clearing old cache:', key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Do not handle non-GET or chrome-extension schemes
  if (req.method !== 'GET' || !req.url.startsWith('http')) return;

  // 1. NETWORK-FIRST for API calls & Page Navigations (Live Data First)
  const isApiRequest = url.pathname.includes('/api/');
  const isNavigation = req.mode === 'navigate' || (req.headers.get('accept') && req.headers.get('accept').includes('text/html'));

  if (isApiRequest || isNavigation) {
    event.respondWith(
      fetch(req).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, responseToCache));
        }
        return networkResponse;
      }).catch(() => {
        console.warn('[ServiceWorker] Network request failed. Serving offline fallback for:', req.url);
        return caches.match(req).then((cachedResponse) => {
          if (cachedResponse) return cachedResponse;
          if (isNavigation) return caches.match('./index.html') || caches.match('./');
        });
      })
    );
    return;
  }

  // 2. CACHE-FIRST with Network Update for Static Assets (CSS, JS, Images, Fonts)
  event.respondWith(
    caches.match(req).then((cachedResponse) => {
      const fetchPromise = fetch(req).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, responseToCache));
        }
        return networkResponse;
      }).catch(() => {
        // Fallback silently if offline for static assets
      });

      return cachedResponse || fetchPromise;
    })
  );
});
