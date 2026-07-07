/* シンプルなオフラインキャッシュ。app_feed.json はネットワーク優先。 */
const CACHE = "kensho-v1";
const SHELL = ["index.html", "app.js", "styles.css", "manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) =>
    Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // 懸賞データとAPIは常に最新を取りに行く
  if (url.pathname.endsWith("app_feed.json") || url.hostname.includes("googleapis") || url.hostname.includes("api.github")) {
    return; // デフォルト(ネットワーク)に任せる
  }
  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
});
