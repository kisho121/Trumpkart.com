const CACHE_NAME = 'trumpkart-v2';  // ← bump version
const STATIC_ASSETS = [
    '/',
    '/offline/',
    '/static/css/style.css',
];

self.addEventListener('install', event => {
    self.skipWaiting();  // ← activate immediately
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();  // ← take control immediately
});

self.addEventListener('fetch', event => {
    event.respondWith(
        fetch(event.request)
            .then(response => {
                const clone = response.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                return response;
            })
            .catch(() => caches.match(event.request).then(r => r || caches.match('/offline/')))
    );
});