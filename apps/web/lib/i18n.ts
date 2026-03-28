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
  assetHistory: string;
  watchlistSummary: string;
  topGainer: string;
  topLoser: string;
  noPerformanceYet: string;
  dailyChange: string;
  weeklyChange: string;
  monthlyChange: string;
  customRange: string;
  fromDate: string;
  toDate: string;
  applyRange: string;
  invalidDateRange: string;
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
    removeFromWatchlist: "Remover",
    assetHistory: "Histórico do ativo",
    watchlistSummary: "Resumo da watchlist",
    topGainer: "Maior alta",
    topLoser: "Maior baixa",
    noPerformanceYet: "Sem dados de performance ainda.",
    dailyChange: "Variação 1D",
    weeklyChange: "Variação 7D",
    monthlyChange: "Variação 30D",
    customRange: "Personalizado",
    fromDate: "De",
    toDate: "Até",
    applyRange: "Aplicar",
    invalidDateRange: "Selecione um intervalo válido de datas."
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
    removeFromWatchlist: "Remove",
    assetHistory: "Asset history",
    watchlistSummary: "Watchlist summary",
    topGainer: "Top gainer",
    topLoser: "Top loser",
    noPerformanceYet: "No performance data yet.",
    dailyChange: "1D change",
    weeklyChange: "7D change",
    monthlyChange: "30D change",
    customRange: "Custom",
    fromDate: "From",
    toDate: "To",
    applyRange: "Apply",
    invalidDateRange: "Select a valid date range."
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
