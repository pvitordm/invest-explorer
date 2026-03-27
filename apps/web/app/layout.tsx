import "./globals.css";
import type { Metadata } from "next";
import type { Viewport } from "next";
import { ServiceWorkerRegister } from "@/components/ServiceWorkerRegister";

export const metadata: Metadata = {
  title: "Invest Explorer",
  description: "Bilingual investment tracker/explorer",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Invest Explorer"
  }
};

export const viewport: Viewport = {
  themeColor: "#154d84"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <ServiceWorkerRegister />
        {children}
      </body>
    </html>
  );
}
