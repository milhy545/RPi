// Service Worker for RPi TV PWA & Web Share Target
const CACHE_NAME = 'rpi-tv-v1';

self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
    // Intercept share target queries if needed or pass through
    if (event.request.method === 'GET') {
        event.respondWith(fetch(event.request));
    }
});
