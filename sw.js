const CACHE_VERSION = 'v13-i18n-monetization';
const CACHE_NAME = `literary-awards-${CACHE_VERSION}`;

const PRECACHE_URLS = [
  './',
  './index.html',
  './style.css',
  './config.js',
  './i18n.js',
  './strings.js',
  './affiliate.js',
  './app.js',
  './donate.js',
  './ads.js',
  './manifest.json',
  './about.html',
  './privacy.html',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './data/awards.json',
  './data/authors.json',
  './data/laureates/nobel.json',
  './data/laureates/booker.json',
  './data/laureates/intl-booker.json',
  './data/laureates/akutagawa.json'
  ,'./data/laureates/goncourt.json'
  ,'./data/laureates/pulitzer-fiction.json'
  ,'./data/laureates/national-book.json'
  ,'./data/laureates/cervantes.json'
  ,'./en/index.html'
  ,'./en/about.html'
  ,'./en/privacy.html'
  ,'./en/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      )
    ).then(() => self.clients.claim())
      // 新版が有効になった時点で、旧Workerに制御されていた画面も自動更新する。
      .then(() => self.clients.matchAll({ type: 'window' }))
      .then((clients) => Promise.all(clients.map((client) => client.navigate(client.url))))
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  if (new URL(event.request.url).origin !== self.location.origin) return;

  // 更新を確実に届けるためネットワーク優先。オフライン時だけキャッシュへ戻る。
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
