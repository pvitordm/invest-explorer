"use client";

import { useEffect } from "react";

export function ServiceWorkerRegister() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    // In development, ensure old production service workers are removed.
    if (process.env.NODE_ENV !== "production") {
      navigator.serviceWorker
        .getRegistrations()
        .then((registrations) => Promise.all(registrations.map((registration) => registration.unregister())))
        .then(async () => {
          if ("caches" in window) {
            const keys = await caches.keys();
            await Promise.all(keys.filter((key) => key.startsWith("invest-explorer-")).map((key) => caches.delete(key)));
          }
        })
        .catch(() => undefined);
      return;
    }

    let refreshing = false;

    navigator.serviceWorker
      .register("/sw.js?v=3")
      .then((registration) => {
        registration.update().catch(() => undefined);

        navigator.serviceWorker.addEventListener("controllerchange", () => {
          if (refreshing) return;
          refreshing = true;
          window.location.reload();
        });
      })
      .catch((error) => {
        console.warn("Service worker registration failed", error);
      });
  }, []);

  return null;
}
