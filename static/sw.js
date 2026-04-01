const CACHE_NAME = 'trumpkart-pwa-v1';
const STATIC_CACHE = 'trumpkart-static-v1';
const DYNAMIC_CACHE = 'trumpkart-dynamic-v1';

const APP_SHELL = [
    '/static/css/style.css',
    '/static/images/icon-192.png',
    '/static/images/icon-512.png',
];

self.addEventListener('install', function(event) {
    console.log('[TrumpKart SW] Installing...');
    event.waitUntil(
        caches.open(STATIC_CACHE).then(function(cache) {
            return cache.addAll(APP_SHELL);
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    console.log('[TrumpKart SW] Activating...');
    event.waitUntil(
        caches.keys().then(function(cacheNames) {
            return Promise.all(
                cacheNames.filter(function(name) {
                    return name !== STATIC_CACHE && name !== DYNAMIC_CACHE;
                }).map(function(name) {
                    return caches.delete(name);
                })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', function(event) {
    var request = event.request;
    var url = new URL(request.url);

    // ✅ Skip non-GET requests completely
    if (request.method !== 'GET') return;

    // ✅ Skip chrome extensions and non-http requests
    if (!url.protocol.startsWith('http')) return;

    // ✅ Skip external domains — let browser handle them normally
    if (url.origin !== self.location.origin) return;

    // ✅ Skip admin pages — always network only
    if (url.pathname.startsWith('/admin/')) return;

    // ✅ Skip auth pages — always network only
    if (url.pathname === '/login' || 
        url.pathname === '/logout' || 
        url.pathname === '/register') return;

    // ✅ Static assets — cache first
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(cacheFirst(request));
        return;
    }

    // ✅ HTML pages — network first, NO offline fallback for navigation
    if (request.headers.get('accept') && 
        request.headers.get('accept').includes('text/html')) {
        event.respondWith(networkOnly(request));
        return;
    }

    // ✅ Everything else — network first
    event.respondWith(networkFirst(request));
});

// Network Only — no cache fallback (for HTML pages)
function networkOnly(request) {
    return fetch(request).catch(function() {
        return caches.match('/offline/');
    });
}

// Cache First — for static assets
function cacheFirst(request) {
    return caches.match(request).then(function(cached) {
        if (cached) return cached;
        return fetch(request).then(function(response) {
            if (!response || response.status !== 200) return response;
            var clone = response.clone();
            caches.open(STATIC_CACHE).then(function(cache) {
                cache.put(request, clone);
            });
            return response;
        });
    });
}

// Network First — for dynamic content
function networkFirst(request) {
    return fetch(request).then(function(response) {
        if (response.ok) {
            var clone = response.clone();
            caches.open(DYNAMIC_CACHE).then(function(cache) {
                cache.put(request, clone);
            });
        }
        return response;
    }).catch(function() {
        return caches.match(request);
    });
}