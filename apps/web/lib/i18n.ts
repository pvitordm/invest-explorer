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
  allHistory: string;
  customRange: string;
  fromDate: string;
  toDate: string;
  applyRange: string;
  invalidDateRange: string;
  theme: string;
  themeSystem: string;
  themeLight: string;
  themeDark: string;
  relevantNews: string;
  refreshNews: string;
  noNews: string;
  loadingNews: string;
  selectAssetForNews: string;
  marketHighlights: string;
  daySummary: string;
  keyCurrencies: string;
  mainHeadline: string;
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
    allHistory: "Tudo",
    customRange: "Personalizado",
    fromDate: "De",
    toDate: "Até",
    applyRange: "Aplicar",
    invalidDateRange: "Selecione um intervalo válido de datas.",
    theme: "Tema",
    themeSystem: "Sistema",
    themeLight: "Claro",
    themeDark: "Escuro",
    relevantNews: "Notícias relevantes",
    refreshNews: "Atualizar notícias",
    noNews: "Sem notícias no momento.",
    loadingNews: "Carregando notícias...",
    selectAssetForNews: "Selecione um ativo para ver notícias relacionadas.",
    marketHighlights: "Destaques do mercado",
    daySummary: "Resumo do dia",
    keyCurrencies: "Principais moedas",
    mainHeadline: "Manchete principal"
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
    allHistory: "All",
    customRange: "Custom",
    fromDate: "From",
    toDate: "To",
    applyRange: "Apply",
    invalidDateRange: "Select a valid date range.",
    theme: "Theme",
    themeSystem: "System",
    themeLight: "Light",
    themeDark: "Dark",
    relevantNews: "Relevant news",
    refreshNews: "Refresh news",
    noNews: "No news right now.",
    loadingNews: "Loading news...",
    selectAssetForNews: "Select an asset to view related news.",
    marketHighlights: "Market highlights",
    daySummary: "Day summary",
    keyCurrencies: "Key currencies",
    mainHeadline: "Main headline"
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
