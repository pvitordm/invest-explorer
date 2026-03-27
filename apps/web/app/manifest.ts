import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Invest Explorer",
    short_name: "InvestX",
    description: "Investment tracker/explorer with BRL base",
    start_url: "/",
    display: "standalone",
    background_color: "#eef3f8",
    theme_color: "#154d84",
    lang: "pt-BR",
    icons: [
      {
        src: "/icon.svg",
        sizes: "any",
        type: "image/svg+xml"
      },
      {
        src: "/maskable-icon.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "maskable"
      }
    ]
  };
}
