const CACHE_NAME = 'hyd-transit-v1';
const STATIC_ASSETS = [
  './',
  './index.html',
  './styles.css',
  './stops.json',
  './all_bus_stops.json',
  './assets/telangana_logo.png',
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
      console.log('[ServiceWorker] Pre-caching static assets for offline transit planner');
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

  // Do not handle non-GET or chrome-extension schemes
  if (req.method !== 'GET' || !req.url.startsWith('http')) return;

  // Handle static assets & navigation with Cache-First & Network Fallback
  event.respondWith(
    caches.match(req).then((cachedResponse) => {
      const fetchPromise = fetch(req).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(req, responseToCache);
          });
        }
        return networkResponse;
      }).catch(() => {
        if (req.mode === 'navigate') {
          return caches.match('./index.html') || caches.match('./');
        }
      });

      return cachedResponse || fetchPromise;
    })
  );
});
