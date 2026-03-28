"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { OfflineBanner } from "@/components/OfflineBanner";
import { InteractivePriceChart } from "@/components/InteractivePriceChart";
import {
  addWatchlistItem,
  fetchAssetNews,
  fetchMarketOverview,
  fetchPriceHistory,
  fetchWatchlist,
  removeWatchlistItem,
  triggerRefresh,
  type ApiExchangeRate,
  type ApiMarketOverviewResponse,
  type ApiPriceHistoryPoint,
  type ApiWatchlistNewsItem,
  type ApiWatchlistItem
} from "@/lib/api";
import {
  getLastSnapshot,
  getLastViewedAssets,
  getLastWatchlist,
  setLastSnapshot,
  setLastViewedAssets,
  setLastWatchlist
} from "@/lib/cache";
import { getInitialLocale, Locale, t } from "@/lib/i18n";
import { getSupabaseClient, hasSupabaseConfig, isSupabaseReal } from "@/lib/supabase";

type Asset = {
  name: string;
  symbol: string;
  exchange: string;
  currency: string;
};

type SnapshotAsset = Asset & {
  asset_class?: string;
  country_code?: string | null;
  price: number | null;
  fx_to_brl?: number | null;
  valuation_brl: number | null;
  data_quality?: "live" | "fallback";
};

type Snapshot = {
  base_currency: "BRL";
  updated_at: string;
  asset_count: number;
  live_asset_count?: number;
  fallback_asset_count?: number;
  assets: SnapshotAsset[];
};

type ViewedAsset = Asset & {
  viewedAt: string;
};

type WatchlistPerformance = {
  name: string;
  symbol: string;
  exchange: string;
  changePct: number;
};

type HistoryPeriod = "30d" | "90d" | "1y" | "5y" | "all" | "custom";
type ThemePreference = "system" | "light" | "dark";

type MarketOverview = ApiMarketOverviewResponse;
const BRAZIL_TIMEZONE = "America/Sao_Paulo";

function isoDateDaysAgo(days: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - days);
  return d.toISOString().slice(0, 10);
}

function isoDateToday(): string {
  return new Date().toISOString().slice(0, 10);
}

const fallbackSnapshot: Snapshot = {
  base_currency: "BRL",
  updated_at: "2026-03-26T20:48:23.000Z",
  asset_count: 8,
  live_asset_count: 0,
  fallback_asset_count: 8,
  assets: [
    { name: "Petrobras PN", symbol: "PETR4", exchange: "B3", currency: "BRL", price: 37, valuation_brl: 37, data_quality: "fallback" },
    { name: "Vale ON", symbol: "VALE3", exchange: "B3", currency: "BRL", price: 63, valuation_brl: 63, data_quality: "fallback" },
    { name: "Apple Inc.", symbol: "AAPL", exchange: "NASDAQ", currency: "USD", price: 210, fx_to_brl: 5, valuation_brl: 1050, data_quality: "fallback" },
    { name: "Microsoft Corp.", symbol: "MSFT", exchange: "NASDAQ", currency: "USD", price: 425, fx_to_brl: 5, valuation_brl: 2125, data_quality: "fallback" },
    { name: "Toyota Motor", symbol: "7203", exchange: "TSE", currency: "JPY", price: 2900, fx_to_brl: 0.033, valuation_brl: 95.7, data_quality: "fallback" },
    { name: "Sony Group", symbol: "6758", exchange: "TSE", currency: "JPY", price: 13200, fx_to_brl: 0.033, valuation_brl: 435.6, data_quality: "fallback" },
    { name: "Bitcoin", symbol: "BTC", exchange: "CRYPTO", currency: "USD", price: 69000, fx_to_brl: 5, valuation_brl: 345000, data_quality: "fallback" },
    { name: "Ethereum", symbol: "ETH", exchange: "CRYPTO", currency: "USD", price: 3600, fx_to_brl: 5, valuation_brl: 18000, data_quality: "fallback" }
  ]
};

function createRuntimeFallbackSnapshot(): Snapshot {
  return {
    ...fallbackSnapshot,
    updated_at: new Date().toISOString()
  };
}

function normalizeSnapshot(raw: unknown): Snapshot | null {
  if (!raw || typeof raw !== "object") return null;
  const candidate = raw as Record<string, unknown>;

  if (Array.isArray(candidate.assets)) {
    return {
      base_currency: "BRL",
      updated_at: String(candidate.updated_at ?? new Date().toISOString()),
      asset_count: Number(candidate.asset_count ?? candidate.assets.length ?? 0),
      live_asset_count: Number(candidate.live_asset_count ?? 0),
      fallback_asset_count: Number(candidate.fallback_asset_count ?? 0),
      assets: candidate.assets as SnapshotAsset[]
    };
  }

  if (candidate.sections && typeof candidate.sections === "object") {
    const sections = candidate.sections as Record<string, Asset[]>;
    const merged = [
      ...(sections.br ?? []),
      ...(sections.us ?? []),
      ...(sections.jp ?? []),
      ...(sections.crypto ?? [])
    ];
    return {
      base_currency: "BRL",
      updated_at: String(candidate.updatedAt ?? new Date().toISOString()),
      asset_count: merged.length,
      live_asset_count: 0,
      fallback_asset_count: merged.length,
      assets: merged.map((item) => ({ ...item, price: null, valuation_brl: null, data_quality: "fallback" }))
    };
  }

  return null;
}

function groupSnapshotAssets(snapshot: Snapshot): Record<"br" | "us" | "jp" | "crypto", SnapshotAsset[]> {
  const result: Record<"br" | "us" | "jp" | "crypto", SnapshotAsset[]> = {
    br: [],
    us: [],
    jp: [],
    crypto: []
  };

  for (const asset of snapshot.assets) {
    if (asset.exchange === "B3") result.br.push(asset);
    else if (asset.exchange === "NASDAQ") result.us.push(asset);
    else if (asset.exchange === "TSE") result.jp.push(asset);
    else result.crypto.push(asset);
  }

  return result;
}

function formatCurrency(value: number | null, currency: string, locale: Locale): string {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: currency === "JPY" ? 0 : 2
  }).format(value);
}

function pickPointValue(point: ApiPriceHistoryPoint): number | null {
  if (typeof point.valuation_brl === "number") return point.valuation_brl;
  if (typeof point.price === "number") return point.price;
  return null;
}

function calcChangePct(points: ApiPriceHistoryPoint[], days: number): number | null {
  if (!points.length) return null;
  const lastPoint = points[points.length - 1];
  const lastValue = pickPointValue(lastPoint);
  if (lastValue === null || lastValue === 0) return null;

  const lastTime = new Date(lastPoint.collected_at).getTime();
  const targetTime = lastTime - days * 24 * 60 * 60 * 1000;

  let baseValue: number | null = null;
  for (let i = points.length - 1; i >= 0; i -= 1) {
    const currentTime = new Date(points[i].collected_at).getTime();
    if (currentTime <= targetTime) {
      baseValue = pickPointValue(points[i]);
      break;
    }
  }

  if (baseValue === null || baseValue === 0) {
    baseValue = pickPointValue(points[0]);
  }

  if (baseValue === null || baseValue === 0) return null;
  return ((lastValue - baseValue) / baseValue) * 100;
}

function filterPointsByRange(
  points: ApiPriceHistoryPoint[],
  period: HistoryPeriod,
  customRange: { startDate: string; endDate: string } | null
): ApiPriceHistoryPoint[] {
  if (!points.length) return [];

  if (period === "all") {
    return points;
  }

  if (period === "custom") {
    if (!customRange) return [];
    const startMs = new Date(customRange.startDate).getTime();
    const endMs = new Date(customRange.endDate).getTime();
    if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || startMs > endMs) {
      return [];
    }
    return points.filter((point) => {
      const t = new Date(point.collected_at).getTime();
      return t >= startMs && t <= endMs + 24 * 60 * 60 * 1000 - 1;
    });
  }

  const daysByPeriod: Record<Exclude<HistoryPeriod, "custom" | "all">, number> = {
    "30d": 30,
    "90d": 90,
    "1y": 365,
    "5y": 365 * 5,
  };

  const lastPoint = points[points.length - 1];
  const endMs = new Date(lastPoint.collected_at).getTime();
  const days = daysByPeriod[period as Exclude<HistoryPeriod, "custom" | "all">] ?? 365;
  const startMs = endMs - days * 24 * 60 * 60 * 1000;
  return points.filter((point) => new Date(point.collected_at).getTime() >= startMs);
}

function buildInitialVisibleRange(
  points: ApiPriceHistoryPoint[],
  period: HistoryPeriod,
  customRange: { startDate: string; endDate: string } | null
): { fromIso: string; toIso: string } | null {
  const windowed = filterPointsByRange(points, period, customRange);
  if (!windowed.length) return null;
  return {
    fromIso: windowed[0].collected_at,
    toIso: windowed[windowed.length - 1].collected_at,
  };
}

function formatPercent(value: number | null, locale: Locale): string {
  if (value === null || Number.isNaN(value)) return "-";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toLocaleString(locale, { maximumFractionDigits: 2 })}%`;
}

function formatDateTimeInBrazil(value: string, locale: Locale): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "short",
    timeStyle: "medium",
    timeZone: BRAZIL_TIMEZONE,
  }).format(date);
}

function pickLatestTimestamp(values: Array<string | null | undefined>): string | null {
  let latestValue: string | null = null;
  let latestTs = Number.NEGATIVE_INFINITY;
  for (const raw of values) {
    if (!raw) continue;
    const ts = new Date(raw).getTime();
    if (!Number.isFinite(ts)) continue;
    if (ts > latestTs) {
      latestTs = ts;
      latestValue = raw;
    }
  }
  return latestValue;
}

function formatAssetValueSummary(asset: {
  price: number | null;
  currency: string;
  valuation_brl: number | null;
}, locale: Locale): string {
  if (asset.currency === "BRL") {
    return formatCurrency(asset.price ?? asset.valuation_brl, "BRL", locale);
  }
  return `${formatCurrency(asset.price, asset.currency, locale)} • ${formatCurrency(asset.valuation_brl, "BRL", locale)}`;
}

function resolveNewsEmptyStateMessage(message: string | undefined, locale: Locale): string {
  const normalized = (message ?? "").trim().toLowerCase();
  if (!normalized || normalized === "ok") {
    return locale === "pt-BR" ? "Sem notícias no momento." : "No news right now.";
  }
  return message as string;
}

export default function HomePage() {
  const selectedAssetCardRef = useRef<HTMLDivElement | null>(null);
  const [locale, setLocale] = useState<Locale>("pt-BR");
  const [themePreference, setThemePreference] = useState<ThemePreference>("system");
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">("light");
  const [isOffline, setIsOffline] = useState(false);
  const [snapshot, setSnapshot] = useState<Snapshot>(fallbackSnapshot);
  const [watchlistItems, setWatchlistItems] = useState<ApiWatchlistItem[]>([]);
  const [lastViewedAssets, setLastViewedAssetsState] = useState<ViewedAsset[]>([]);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [devMode, setDevMode] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [watchlistBusyKey, setWatchlistBusyKey] = useState<string | null>(null);
  const [historyPeriod, setHistoryPeriod] = useState<HistoryPeriod>("1y");
  const [customStartDate, setCustomStartDate] = useState<string>(isoDateDaysAgo(180));
  const [customEndDate, setCustomEndDate] = useState<string>(isoDateToday());
  const [appliedCustomRange, setAppliedCustomRange] = useState<{ startDate: string; endDate: string } | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<SnapshotAsset | null>(null);
  const [historyPoints, setHistoryPoints] = useState<ApiPriceHistoryPoint[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [watchlistPerformance, setWatchlistPerformance] = useState<WatchlistPerformance[]>([]);
  const [marketOverview, setMarketOverview] = useState<MarketOverview | null>(null);
  const [newsItems, setNewsItems] = useState<ApiWatchlistNewsItem[]>([]);
  const [isNewsLoading, setIsNewsLoading] = useState(false);
  const [newsStatusMessage, setNewsStatusMessage] = useState<string>("");
  const readOnlyMode = isOffline;
  const msg = useMemo(() => t(locale), [locale]);
  const groupedAssets = useMemo(() => groupSnapshotAssets(snapshot), [snapshot]);
  const watchlistSet = useMemo(
    () => new Set(watchlistItems.map((item) => `${item.asset.exchange}-${item.asset.symbol}`)),
    [watchlistItems]
  );
  const filteredHistoryPoints = useMemo(
    () => filterPointsByRange(historyPoints, historyPeriod, appliedCustomRange),
    [historyPoints, historyPeriod, appliedCustomRange]
  );
  const chartInitialVisibleRange = useMemo(
    () => buildInitialVisibleRange(historyPoints, historyPeriod, appliedCustomRange),
    [historyPoints, historyPeriod, appliedCustomRange]
  );
  const lastDataUpdatedAt = useMemo(
    () => pickLatestTimestamp([
      marketOverview?.summary?.data_updated_at,
      snapshot.updated_at,
    ]),
    [marketOverview?.summary?.data_updated_at, snapshot.updated_at]
  );

  async function loadLatestSnapshot() {
    // In dev mode, don't attempt Supabase DB queries
    if (devMode || isOffline) return;
    if (!hasSupabaseConfig() || !isAuthenticated) return;
    
    try {
      const supabase = getSupabaseClient();
      const { data, error } = await supabase
        .from("snapshots")
        .select("data")
        .order("created_at", { ascending: false })
        .limit(1);

      if (error) throw error;

      const latest = data?.[0]?.data;
      const normalized = normalizeSnapshot(latest);
      if (normalized) {
        setSnapshot(normalized);
        await setLastSnapshot(normalized);
      }
    } catch {
      setStatusMessage(locale === "pt-BR" ? "Falha ao carregar snapshot recente." : "Failed to load latest snapshot.");
    }
  }

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const savedTheme = window.localStorage.getItem("theme_preference");
    const initialTheme: ThemePreference = savedTheme === "light" || savedTheme === "dark" || savedTheme === "system" ? savedTheme : "system";
    setThemePreference(initialTheme);

    const applyTheme = (pref: ThemePreference) => {
      const next = pref === "system" ? (media.matches ? "dark" : "light") : pref;
      setResolvedTheme(next);
      document.documentElement.setAttribute("data-theme", next);
      document.documentElement.style.colorScheme = next;
    };

    applyTheme(initialTheme);
    const onMediaChange = () => applyTheme(themePreference === "system" ? "system" : themePreference);
    media.addEventListener("change", onMediaChange);

    return () => media.removeEventListener("change", onMediaChange);
  }, []);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const next = themePreference === "system" ? (media.matches ? "dark" : "light") : themePreference;
    setResolvedTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    document.documentElement.style.colorScheme = next;
    window.localStorage.setItem("theme_preference", themePreference);
  }, [themePreference]);

  useEffect(() => {
    const initial = getInitialLocale();
    setLocale(initial);

    const offline = typeof navigator !== "undefined" ? !navigator.onLine : false;
    setIsOffline(offline);

    // Detect if we're in dev mode (Supabase not real)
    const inDevMode = !isSupabaseReal();
    setDevMode(inDevMode);

    getLastSnapshot<unknown>().then((cached) => {
      const normalized = normalizeSnapshot(cached);
      if (normalized) setSnapshot(normalized);
      else {
        const runtimeFallback = createRuntimeFallbackSnapshot();
        setSnapshot(runtimeFallback);
        setLastSnapshot(runtimeFallback).catch(() => undefined);
      }
    });

    getLastWatchlist<ApiWatchlistItem[]>().then((cached) => {
      if (cached) setWatchlistItems(cached);
    });

    getLastViewedAssets<ViewedAsset[]>().then((cached) => {
      if (cached) setLastViewedAssetsState(cached);
    });

    let authUnsubscribe: (() => void) | null = null;

    // Only use Supabase auth if it's REAL (not dev mode)
    if (hasSupabaseConfig() && !inDevMode) {
      try {
        const supabase = getSupabaseClient();

        supabase.auth.getSession().then(({ data }) => {
          setIsAuthenticated(Boolean(data.session?.access_token));
        }).catch(() => {
          // Supabase unreachable, already in dev mode
        });

        const { data: authListener } = supabase.auth.onAuthStateChange((_event, session) => {
          setIsAuthenticated(Boolean(session?.access_token));
        });
        authUnsubscribe = () => authListener.subscription.unsubscribe();
      } catch (e) {
        console.warn("Supabase init failed, using dev mode", e);
      }
    } else if (inDevMode) {
      setIsAuthenticated(true);
      setStatusMessage(
        locale === "pt-BR"
          ? "Modo DEV ativo: sessão local iniciada automaticamente."
          : "DEV mode active: local session started automatically."
      );
    } else {
      setStatusMessage(
        locale === "pt-BR"
          ? "Configuração Supabase ausente no ambiente web (.env.local)."
          : "Supabase configuration missing in web environment (.env.local)."
      );
    }

    const toOffline = () => setIsOffline(true);
    const toOnline = () => setIsOffline(false);
    window.addEventListener("offline", toOffline);
    window.addEventListener("online", toOnline);
    return () => {
      window.removeEventListener("offline", toOffline);
      window.removeEventListener("online", toOnline);
      if (authUnsubscribe) authUnsubscribe();
    };
  }, [locale]);

  useEffect(() => {
    if (isOffline || !isAuthenticated) return;

    // Try to fetch watchlist, but don't break if it fails (dev mode)
    fetchWatchlist()
      .then(async (response) => {
        setWatchlistItems(response.items ?? []);
        await setLastWatchlist(response.items ?? []);
      })
      .catch(() => {
        // Silently fail in dev mode - watchlist is optional
      });

    fetchMarketOverview({ locale })
      .then((response) => setMarketOverview(response))
      .catch(() => setMarketOverview(null));

    loadLatestSnapshot().catch(() => undefined);
  }, [isOffline, isAuthenticated, locale]);

  useEffect(() => {
    if (!selectedAsset) {
      setNewsItems([]);
      setNewsStatusMessage(msg.selectAssetForNews);
      return;
    }

    if (isOffline || !isAuthenticated) {
      setNewsItems([]);
      setNewsStatusMessage(
        isOffline
          ? locale === "pt-BR"
            ? "Notícias indisponíveis offline."
            : "News is unavailable while offline."
          : locale === "pt-BR"
            ? "Ative uma sessão para carregar notícias."
            : "Start a session to load news."
      );
      return;
    }

    setIsNewsLoading(true);
    setNewsStatusMessage("");
    fetchAssetNews({
      symbol: selectedAsset.symbol,
      exchange: selectedAsset.exchange,
      locale,
      limit: 8
    })
      .then((response) => {
        setNewsItems(response.items ?? []);
        setNewsStatusMessage(
          response.items && response.items.length > 0
            ? ""
            : resolveNewsEmptyStateMessage(response.message, locale)
        );
      })
      .catch(() => {
        setNewsItems([]);
        setNewsStatusMessage(locale === "pt-BR" ? "Falha ao carregar notícias." : "Failed to load news.");
      })
      .finally(() => setIsNewsLoading(false));
  }, [selectedAsset, isOffline, isAuthenticated, locale, msg.selectAssetForNews]);

  useEffect(() => {
    if (!selectedAsset || isOffline || !isAuthenticated) return;

    setIsHistoryLoading(true);
    fetchPriceHistory({
      symbol: selectedAsset.symbol,
      exchange: selectedAsset.exchange,
      period: "max",
      limit: 20000
    })
      .then((response) => setHistoryPoints(response.points ?? []))
      .catch(() => setHistoryPoints([]))
      .finally(() => setIsHistoryLoading(false));
  }, [selectedAsset, isOffline, isAuthenticated]);

  useEffect(() => {
    if (isOffline || !isAuthenticated || watchlistItems.length === 0) {
      setWatchlistPerformance([]);
      return;
    }

    Promise.all(
      watchlistItems.map(async (item) => {
        const response = await fetchPriceHistory({
          symbol: item.asset.symbol,
          exchange: item.asset.exchange,
          period: "90d",
          limit: 300
        });
        return {
          name: item.asset.name,
          symbol: item.asset.symbol,
          exchange: item.asset.exchange,
          changePct: calcChangePct(response.points ?? [], 30) ?? 0
        };
      })
    )
      .then((data) => setWatchlistPerformance(data))
      .catch(() => setWatchlistPerformance([]));
  }, [isOffline, isAuthenticated, watchlistItems]);

  useEffect(() => {
    if (!selectedAsset || !selectedAssetCardRef.current) return;
    requestAnimationFrame(() => {
      selectedAssetCardRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  }, [selectedAsset]);

  function onLocaleChange(next: Locale) {
    if (readOnlyMode) return;
    setLocale(next);
    localStorage.setItem("locale", next);
  }

  function onThemeChange(next: ThemePreference) {
    if (readOnlyMode) return;
    setThemePreference(next);
  }

  async function refreshNow() {
    if (!navigator.onLine || !isAuthenticated || readOnlyMode) return;
    setIsRefreshing(true);
    try {
      const refresh = await triggerRefresh();
      // The API returns the full snapshot in refresh.data
      if (refresh.data) {
        const normalized = normalizeSnapshot(refresh.data);
        if (normalized) {
          setSnapshot(normalized);
          await setLastSnapshot(normalized);
        }
      }
      setStatusMessage(refresh.message);
    } catch (e) {
      console.error("Refresh error:", e);
      setStatusMessage(locale === "pt-BR" ? "Falha ao atualizar snapshot." : "Failed to refresh snapshot.");
    } finally {
      setIsRefreshing(false);
    }
  }

  async function loginAnonymously() {
    if (readOnlyMode) return;
    
    // In dev mode, skip Supabase auth entirely
    if (devMode) {
      setIsAuthenticated(true);
      setStatusMessage(
        locale === "pt-BR" 
          ? "Sessão DEV ativa (Supabase offline)." 
          : "DEV Session active (Supabase offline)."
      );
      return;
    }
    
    // Try real Supabase auth
    if (hasSupabaseConfig()) {
      try {
        const supabase = getSupabaseClient();
        const { error } = await supabase.auth.signInAnonymously();
        if (!error) {
          setStatusMessage(locale === "pt-BR" ? "Sessão ativa com sucesso." : "Session is active.");
          setIsAuthenticated(true);
          return;
        }
      } catch (e) {
        console.warn("Supabase auth failed", e);
      }
    }

    // Fallback: just enable dev mode
    setDevMode(true);
    setIsAuthenticated(true);
    setStatusMessage(
      locale === "pt-BR" 
        ? "Sessão DEV ativa (Supabase indisponível)." 
        : "DEV Session active (Supabase unavailable)."
    );
  }

  async function onViewAsset(asset: Asset) {
    if (readOnlyMode) return;
    const nextList: ViewedAsset[] = [
      { ...asset, viewedAt: new Date().toISOString() },
      ...lastViewedAssets.filter((item) => !(item.symbol === asset.symbol && item.exchange === asset.exchange))
    ].slice(0, 12);

    setLastViewedAssetsState(nextList);
    await setLastViewedAssets(nextList);

    const snapshotAsset = snapshot.assets.find((item) => item.symbol === asset.symbol && item.exchange === asset.exchange);
    if (snapshotAsset) {
      setSelectedAsset(snapshotAsset);
    }
  }

  async function onToggleWatchlist(asset: SnapshotAsset) {
    if (readOnlyMode || !isAuthenticated) return;
    const key = `${asset.exchange}-${asset.symbol}`;
    setWatchlistBusyKey(key);
    try {
      const response = watchlistSet.has(key)
        ? await removeWatchlistItem({ symbol: asset.symbol, exchange: asset.exchange })
        : await addWatchlistItem({ symbol: asset.symbol, exchange: asset.exchange });
      setWatchlistItems(response.items ?? []);
      await setLastWatchlist(response.items ?? []);
      setStatusMessage(
        locale === "pt-BR"
          ? watchlistSet.has(key)
            ? "Ativo removido da watchlist."
            : "Ativo adicionado na watchlist."
          : watchlistSet.has(key)
            ? "Asset removed from watchlist."
            : "Asset added to watchlist."
      );
    } catch {
      setStatusMessage(locale === "pt-BR" ? "Falha ao atualizar watchlist." : "Failed to update watchlist.");
    } finally {
      setWatchlistBusyKey(null);
    }
  }

  function applyCustomRange() {
    if (!customStartDate || !customEndDate || customStartDate > customEndDate) {
      setStatusMessage(msg.invalidDateRange);
      return;
    }

    setAppliedCustomRange({
      startDate: customStartDate,
      endDate: customEndDate
    });
    setHistoryPeriod("custom");
    setStatusMessage("");
  }

  async function refreshNews() {
    if (isOffline || !isAuthenticated || !selectedAsset) return;
    setIsNewsLoading(true);
    setNewsStatusMessage("");
    try {
      const response = await fetchAssetNews({
        symbol: selectedAsset.symbol,
        exchange: selectedAsset.exchange,
        locale,
        limit: 8
      });
      setNewsItems(response.items ?? []);
      setNewsStatusMessage(
        response.items && response.items.length > 0
          ? ""
          : resolveNewsEmptyStateMessage(response.message, locale)
      );
    } catch {
      setNewsItems([]);
      setNewsStatusMessage(locale === "pt-BR" ? "Falha ao carregar notícias." : "Failed to load news.");
    } finally {
      setIsNewsLoading(false);
    }
  }

  return (
    <main>
      <div className="toolbar">
        <h1>{msg.title}</h1>
        <button onClick={refreshNow} disabled={isOffline || !isAuthenticated || isRefreshing}>
          {isRefreshing
            ? locale === "pt-BR"
              ? "Atualizando..."
              : "Refreshing..."
            : msg.refreshNow}
        </button>
      </div>

      <p className="muted">{msg.subtitle}</p>
      <OfflineBanner message={msg.offlineBanner} isOffline={isOffline} />
      {readOnlyMode ? <p className="muted">{msg.readOnlyMode}</p> : null}
      {statusMessage ? <p className="muted">{statusMessage}</p> : null}
      <p className="muted snapshot-line" suppressHydrationWarning>
        {locale === "pt-BR" ? "Última atualização dos dados" : "Last data update"}: {formatDateTimeInBrazil(lastDataUpdatedAt ?? snapshot.updated_at, locale)} ({locale === "pt-BR" ? "UTC-3" : "UTC-3"}) • {locale === "pt-BR" ? "Base" : "Base"}: BRL
      </p>

      {marketOverview ? (
        <div className="card highlights-card">
          <div className="highlights-header">
            <div>
              <h3>{msg.marketHighlights}</h3>
              <p className="muted highlights-summary">
                {msg.daySummary}: {locale === "pt-BR" ? "ativos monitorados" : "tracked assets"} {marketOverview.summary.asset_count} • {locale === "pt-BR" ? "ao vivo" : "live"} {marketOverview.summary.live_asset_count} • {locale === "pt-BR" ? "fallback" : "fallback"} {marketOverview.summary.fallback_asset_count}
              </p>
            </div>
            <p className="muted highlights-updated" suppressHydrationWarning>
              {formatDateTimeInBrazil(marketOverview.summary.updated_at, locale)} ({locale === "pt-BR" ? "UTC-3" : "UTC-3"})
            </p>
          </div>

          <div className="highlights-grid">
            {marketOverview.featured_assets.map((asset) => (
              <article key={`${asset.exchange}-${asset.symbol}`} className="highlight-tile">
                <p className="muted highlight-kicker">{asset.exchange}</p>
                <strong>{asset.symbol}</strong>
                <p>{asset.name}</p>
                <p className="muted">
                  {formatAssetValueSummary(asset, locale)}
                </p>
              </article>
            ))}
          </div>

          <div className="highlights-bottom">
            <div className="headline-block">
              <h4>{msg.mainHeadline}</h4>
              {marketOverview.headline ? (
                <a href={marketOverview.headline.url} target="_blank" rel="noreferrer" className="news-title">
                  {marketOverview.headline.title}
                </a>
              ) : (
                <p className="muted">{msg.noNews}</p>
              )}
            </div>
            <div className="currencies-block">
              <h4>{msg.keyCurrencies}</h4>
              <div className="currency-list">
                {(marketOverview.currency_rates as ApiExchangeRate[]).filter((rate) => rate.base_currency !== "BRL").map((rate) => (
                  <div key={`${rate.base_currency}-${rate.quote_currency}`} className="currency-chip">
                    <strong>{rate.base_currency}/{rate.quote_currency}</strong>
                    <span>{formatCurrency(rate.rate, rate.quote_currency, locale)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      <div className="card">
        <h3>{msg.settings}</h3>
        <label>
          {msg.language}: {" "}
          <select
            value={locale}
            disabled={readOnlyMode}
            onChange={(e) => onLocaleChange(e.target.value as Locale)}
          >
            <option value="pt-BR">Português (Brasil)</option>
            <option value="en">English</option>
          </select>
        </label>
        <label style={{ marginLeft: "0.75rem" }}>
          {msg.theme}: {" "}
          <select
            value={themePreference}
            disabled={readOnlyMode}
            onChange={(e) => onThemeChange(e.target.value as ThemePreference)}
          >
            <option value="system">{msg.themeSystem}</option>
            <option value="light">{msg.themeLight}</option>
            <option value="dark">{msg.themeDark}</option>
          </select>
        </label>
        <p className="muted" style={{ marginTop: "0.75rem" }}>
          {isAuthenticated
            ? locale === "pt-BR"
              ? "Sessão Supabase ativa."
              : "Supabase session is active."
            : locale === "pt-BR"
              ? "Sem sessão ativa."
              : "No active session."}
        </p>
        {!isAuthenticated ? (
          <button onClick={loginAnonymously} disabled={isOffline || readOnlyMode}>
            {locale === "pt-BR" ? "Entrar anonimamente" : "Sign in anonymously"}
          </button>
        ) : null}
      </div>

      <div className="card">
        <h3>{msg.lastViewed}</h3>
        {lastViewedAssets.length === 0 ? (
          <p className="muted">{locale === "pt-BR" ? "Nenhum ativo visto ainda." : "No viewed assets yet."}</p>
        ) : (
          lastViewedAssets.map((asset) => (
            <p key={`${asset.exchange}-${asset.symbol}-viewed`}>
              {asset.name} <strong>{asset.symbol}</strong> • {asset.exchange} • {asset.currency}
            </p>
          ))
        )}
      </div>

      <div className="card">
        <h3>{locale === "pt-BR" ? "Watchlist" : "Watchlist"}</h3>
        {watchlistItems.length === 0 ? (
          <p className="muted">
            {locale === "pt-BR"
              ? "Sem itens por enquanto (ou usando cache offline)."
              : "No items yet (or offline cache in use)."}
          </p>
        ) : (
          watchlistItems.map((item) => <p key={item.id}>{item.display}</p>)
        )}

        <div className="watchlist-summary">
          <h4>{msg.watchlistSummary}</h4>
          {watchlistPerformance.length === 0 ? (
            <p className="muted">{msg.noPerformanceYet}</p>
          ) : (
            (() => {
              const sorted = [...watchlistPerformance].sort((a, b) => b.changePct - a.changePct);
              const topGainer = sorted[0];
              const topLoser = sorted[sorted.length - 1];
              return (
                <>
                  <p>
                    {msg.topGainer}: <strong>{topGainer.symbol}</strong> <span className={topGainer.changePct >= 0 ? "change-positive" : "change-negative"}>{formatPercent(topGainer.changePct, locale)}</span>
                  </p>
                  <p>
                    {msg.topLoser}: <strong>{topLoser.symbol}</strong> <span className={topLoser.changePct >= 0 ? "change-positive" : "change-negative"}>{formatPercent(topLoser.changePct, locale)}</span>
                  </p>
                </>
              );
            })()
          )}
        </div>
      </div>

      {selectedAsset ? (
        <div className="card" ref={selectedAssetCardRef}>
          <div className="history-header">
            <h3>{msg.assetHistory}: {selectedAsset.symbol}</h3>
            <div className="history-periods">
              {(["30d", "90d", "1y", "5y", "all"] as Exclude<HistoryPeriod, "custom">[]).map((p) => (
                <button
                  key={p}
                  onClick={() => {
                    setHistoryPeriod(p);
                    setAppliedCustomRange(null);
                  }}
                  disabled={isHistoryLoading || p === historyPeriod}
                >
                  {p === "all" ? msg.allHistory : p.toUpperCase()}
                </button>
              ))}
              <button onClick={() => setHistoryPeriod("custom")} disabled={isHistoryLoading || historyPeriod === "custom"}>
                {msg.customRange}
              </button>
            </div>
          </div>

          {historyPeriod === "custom" ? (
            <div className="history-custom-range">
              <label>
                {msg.fromDate}
                <input type="date" value={customStartDate} onChange={(e) => setCustomStartDate(e.target.value)} max={customEndDate || undefined} />
              </label>
              <label>
                {msg.toDate}
                <input type="date" value={customEndDate} onChange={(e) => setCustomEndDate(e.target.value)} min={customStartDate || undefined} />
              </label>
              <button onClick={applyCustomRange} disabled={isHistoryLoading}>{msg.applyRange}</button>
            </div>
          ) : null}

          {isHistoryLoading ? (
            <p className="muted">{locale === "pt-BR" ? "Carregando histórico..." : "Loading history..."}</p>
          ) : historyPoints.length < 2 ? (
            <p className="muted">{locale === "pt-BR" ? "Sem pontos suficientes para gráfico." : "Not enough points for chart."}</p>
          ) : (
            <>
              <InteractivePriceChart
                points={historyPoints}
                locale={locale}
                currency="BRL"
                theme={resolvedTheme}
                initialVisibleRange={chartInitialVisibleRange}
              />
              <div className="history-metrics muted">
                <span>{msg.dailyChange}: <strong className={(calcChangePct(filteredHistoryPoints, 1) ?? 0) >= 0 ? "change-positive" : "change-negative"}>{formatPercent(calcChangePct(filteredHistoryPoints, 1), locale)}</strong></span>
                <span>{msg.weeklyChange}: <strong className={(calcChangePct(filteredHistoryPoints, 7) ?? 0) >= 0 ? "change-positive" : "change-negative"}>{formatPercent(calcChangePct(filteredHistoryPoints, 7), locale)}</strong></span>
                <span>{msg.monthlyChange}: <strong className={(calcChangePct(filteredHistoryPoints, 30) ?? 0) >= 0 ? "change-positive" : "change-negative"}>{formatPercent(calcChangePct(filteredHistoryPoints, 30), locale)}</strong></span>
              </div>
            </>
          )}

          <div className="news-header" style={{ marginTop: "1.25rem" }}>
            <h3>{msg.relevantNews}</h3>
            <button onClick={refreshNews} disabled={isNewsLoading || isOffline || !isAuthenticated || !selectedAsset}>{msg.refreshNews}</button>
          </div>
          {isNewsLoading ? (
            <p className="muted">{msg.loadingNews}</p>
          ) : newsItems.length === 0 ? (
            <p className="muted">{newsStatusMessage || msg.noNews}</p>
          ) : (
            <div className="news-list">
              {newsItems.slice(0, 8).map((item) => (
                <article key={`${item.symbol}-${item.url}`} className="news-item">
                  <p className="news-meta muted">
                    <strong>{item.symbol}</strong>
                    {item.source ? ` • ${item.source}` : ""}
                    {item.published_at ? ` • ${formatDateTimeInBrazil(item.published_at, locale)}` : ""}
                  </p>
                  <a href={item.url} target="_blank" rel="noreferrer" className="news-title">{item.title}</a>
                  {item.description ? <p className="muted">{item.description}</p> : null}
                </article>
              ))}
            </div>
          )}
        </div>
      ) : null}

      <h2 className="section-title">{msg.explore}</h2>
      <Section title={msg.topBR} assets={groupedAssets.br} locale={locale} onViewAsset={onViewAsset} viewAssetLabel={msg.viewAsset} readOnlyMode={readOnlyMode} onToggleWatchlist={onToggleWatchlist} watchlistSet={watchlistSet} watchlistBusyKey={watchlistBusyKey} addToWatchlistLabel={msg.addToWatchlist} removeFromWatchlistLabel={msg.removeFromWatchlist} />
      <Section title={msg.topUS} assets={groupedAssets.us} locale={locale} onViewAsset={onViewAsset} viewAssetLabel={msg.viewAsset} readOnlyMode={readOnlyMode} onToggleWatchlist={onToggleWatchlist} watchlistSet={watchlistSet} watchlistBusyKey={watchlistBusyKey} addToWatchlistLabel={msg.addToWatchlist} removeFromWatchlistLabel={msg.removeFromWatchlist} />
      <Section title={msg.topJP} assets={groupedAssets.jp} locale={locale} onViewAsset={onViewAsset} viewAssetLabel={msg.viewAsset} readOnlyMode={readOnlyMode} onToggleWatchlist={onToggleWatchlist} watchlistSet={watchlistSet} watchlistBusyKey={watchlistBusyKey} addToWatchlistLabel={msg.addToWatchlist} removeFromWatchlistLabel={msg.removeFromWatchlist} />
      <Section title={msg.topCrypto} assets={groupedAssets.crypto} locale={locale} onViewAsset={onViewAsset} viewAssetLabel={msg.viewAsset} readOnlyMode={readOnlyMode} onToggleWatchlist={onToggleWatchlist} watchlistSet={watchlistSet} watchlistBusyKey={watchlistBusyKey} addToWatchlistLabel={msg.addToWatchlist} removeFromWatchlistLabel={msg.removeFromWatchlist} />
    </main>
  );
}

function Section({
  title,
  assets,
  locale,
  onViewAsset,
  viewAssetLabel,
  readOnlyMode,
  onToggleWatchlist,
  watchlistSet,
  watchlistBusyKey,
  addToWatchlistLabel,
  removeFromWatchlistLabel
}: {
  title: string;
  assets: SnapshotAsset[];
  locale: Locale;
  onViewAsset: (asset: Asset) => void;
  viewAssetLabel: string;
  readOnlyMode: boolean;
  onToggleWatchlist: (asset: SnapshotAsset) => void;
  watchlistSet: Set<string>;
  watchlistBusyKey: string | null;
  addToWatchlistLabel: string;
  removeFromWatchlistLabel: string;
}) {
  return (
    <div className="card">
      <h3>{title}</h3>
      {assets.map((asset) => (
        <div key={`${asset.exchange}-${asset.symbol}`} className="asset-row">
          <p className="asset-info">
            {asset.name} <strong>{asset.symbol}</strong> • {asset.exchange} • {asset.currency}
            <br />
            <span className="muted asset-meta">
              {asset.currency === "BRL"
                ? `${locale === "pt-BR" ? "Preço" : "Price"}: ${formatCurrency(asset.price ?? asset.valuation_brl, "BRL", locale)} • ${(asset.data_quality ?? "fallback").toUpperCase()}`
                : `${locale === "pt-BR" ? "Preço" : "Price"}: ${formatCurrency(asset.price, asset.currency, locale)} • ${locale === "pt-BR" ? "Valuation BRL" : "BRL valuation"}: ${formatCurrency(asset.valuation_brl, "BRL", locale)} • ${(asset.data_quality ?? "fallback").toUpperCase()}`}
            </span>
          </p>
          <div className="asset-actions">
            <button onClick={() => onViewAsset(asset)} disabled={readOnlyMode}>{viewAssetLabel}</button>
            <button onClick={() => onToggleWatchlist(asset)} disabled={readOnlyMode || watchlistBusyKey === `${asset.exchange}-${asset.symbol}`}>
              {watchlistSet.has(`${asset.exchange}-${asset.symbol}`) ? removeFromWatchlistLabel : addToWatchlistLabel}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
