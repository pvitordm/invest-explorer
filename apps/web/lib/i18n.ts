export type Locale = "pt-BR" | "en";

type Messages = {
  title: string;
  subtitle: string;
  settings: string;
  language: string;
  refreshNow: string;
  viewAsset: string;
  offlineBanner: string;
  readOnlyMode: string;
  lastViewed: string;
  explore: string;
  topBR: string;
  topUS: string;
  topJP: string;
  topCrypto: string;
  addToWatchlist: string;
  removeFromWatchlist: string;
};

const translations: Record<Locale, Messages> = {
  "pt-BR": {
    title: "Invest Explorer",
    subtitle: "Explorador de investimentos com base em BRL",
    settings: "Configurações",
    language: "Idioma",
    refreshNow: "Atualizar agora",
    viewAsset: "Ver ativo",
    offlineBanner: "Você está offline. Exibindo último snapshot em cache (somente leitura).",
    readOnlyMode: "Modo somente leitura ativo (offline). Edições desabilitadas.",
    lastViewed: "Últimos ativos vistos",
    explore: "Explorar",
    topBR: "Top BR",
    topUS: "Top US",
    topJP: "Top JP",
    topCrypto: "Top Crypto",
    addToWatchlist: "Adicionar",
    removeFromWatchlist: "Remover"
  },
  en: {
    title: "Invest Explorer",
    subtitle: "Investment explorer with BRL as base currency",
    settings: "Settings",
    language: "Language",
    refreshNow: "Refresh now",
    viewAsset: "View asset",
    offlineBanner: "You are offline. Showing last cached snapshot (read-only).",
    readOnlyMode: "Read-only mode is active (offline). Edits are disabled.",
    lastViewed: "Last viewed assets",
    explore: "Explore",
    topBR: "Top BR",
    topUS: "Top US",
    topJP: "Top JP",
    topCrypto: "Top Crypto",
    addToWatchlist: "Add",
    removeFromWatchlist: "Remove"
  }
};

export function getInitialLocale(): Locale {
  if (typeof window === "undefined") return "pt-BR";
  const saved = window.localStorage.getItem("locale");
  if (saved === "pt-BR" || saved === "en") return saved;
  return "pt-BR";
}

export function t(locale: Locale): Messages {
  return translations[locale];
}
