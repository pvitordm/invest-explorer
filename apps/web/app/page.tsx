"use client";

import { useEffect, useMemo, useState } from "react";
import { OfflineBanner } from "@/components/OfflineBanner";
import { addWatchlistItem, fetchWatchlist, removeWatchlistItem, triggerRefresh, type ApiWatchlistItem } from "@/lib/api";
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

export default function HomePage() {
  const [locale, setLocale] = useState<Locale>("pt-BR");
  const [isOffline, setIsOffline] = useState(false);
  const [snapshot, setSnapshot] = useState<Snapshot>(fallbackSnapshot);
  const [watchlistItems, setWatchlistItems] = useState<ApiWatchlistItem[]>([]);
  const [lastViewedAssets, setLastViewedAssetsState] = useState<ViewedAsset[]>([]);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [devMode, setDevMode] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [watchlistBusyKey, setWatchlistBusyKey] = useState<string | null>(null);
  const readOnlyMode = isOffline;
  const msg = useMemo(() => t(locale), [locale]);
  const groupedAssets = useMemo(() => groupSnapshotAssets(snapshot), [snapshot]);
  const watchlistSet = useMemo(
    () => new Set(watchlistItems.map((item) => `${item.asset.exchange}-${item.asset.symbol}`)),
    [watchlistItems]
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
      setStatusMessage(
        locale === "pt-BR"
          ? "Modo DEV: Supabase não configurado. Use 'Entrar anonimamente' para começar."
          : "DEV Mode: Supabase not configured. Click 'Sign in anonymously' to start."
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

    loadLatestSnapshot().catch(() => undefined);
  }, [isOffline, isAuthenticated, locale]);

  function onLocaleChange(next: Locale) {
    if (readOnlyMode) return;
    setLocale(next);
    localStorage.setItem("locale", next);
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
        {locale === "pt-BR" ? "Snapshot em" : "Snapshot at"}: {new Date(snapshot.updated_at).toLocaleString(locale)} • {locale === "pt-BR" ? "Base" : "Base"}: BRL
      </p>

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
      </div>

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
              {locale === "pt-BR" ? "Preço" : "Price"}: {formatCurrency(asset.price, asset.currency, locale)} • {locale === "pt-BR" ? "Valuation BRL" : "BRL valuation"}: {formatCurrency(asset.valuation_brl, "BRL", locale)} • {(asset.data_quality ?? "fallback").toUpperCase()}
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
