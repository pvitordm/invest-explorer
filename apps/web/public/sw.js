const CACHE_NAME = "invest-explorer-v3";
const APP_SHELL = ["/", "/manifest.webmanifest"];

function shouldCache(request, url) {
  if (request.method !== "GET") return false;
  if (url.origin !== self.location.origin) return false;

  // Never cache API calls; stale API/auth responses break interactions.
  if (url.pathname.startsWith("/api-proxy/")) return false;

  // Avoid caching Next.js data payloads that are tightly coupled to app version.
  if (url.pathname.startsWith("/_next/data/")) return false;

  // Avoid caching script/style chunks to prevent stale UI after deployments.
  if (url.pathname.startsWith("/_next/static/")) return false;
  if (["script", "style", "worker"].includes(request.destination)) return false;

  return true;
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (!shouldCache(request, url)) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => caches.match("/"))
    );
    return;
  }

  // Default network-first for other same-origin resources.
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response && response.ok) {
          const cloned = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, cloned));
        }
        return response;
      })
      .catch(() => caches.match(request))
  );
});
