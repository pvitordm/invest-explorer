"use client";

import { useEffect, useMemo, useState } from "react";
import { OfflineBanner } from "@/components/OfflineBanner";
import { fetchWatchlist, triggerRefresh, type ApiWatchlistItem } from "@/lib/api";
import {
  getLastSnapshot,
  getLastViewedAssets,
  getLastWatchlist,
  setLastSnapshot,
  setLastViewedAssets,
  setLastWatchlist
} from "@/lib/cache";
import { getInitialLocale, Locale, t } from "@/lib/i18n";
import { getSupabaseClient, hasSupabaseConfig } from "@/lib/supabase";

type Asset = {
  name: string;
  symbol: string;
  exchange: string;
  currency: string;
};

type Snapshot = {
  updatedAt: string;
  sections: Record<string, Asset[]>;
};

type ViewedAsset = Asset & {
  viewedAt: string;
};

const fallbackSnapshot: Snapshot = {
  updatedAt: new Date().toISOString(),
  sections: {
    br: [
      { name: "Petrobras PN", symbol: "PETR4", exchange: "B3", currency: "BRL" },
      { name: "Vale ON", symbol: "VALE3", exchange: "B3", currency: "BRL" }
    ],
    us: [
      { name: "Apple Inc.", symbol: "AAPL", exchange: "NASDAQ", currency: "USD" },
      { name: "Microsoft Corp.", symbol: "MSFT", exchange: "NASDAQ", currency: "USD" }
    ],
    jp: [
      { name: "Toyota Motor", symbol: "7203", exchange: "TSE", currency: "JPY" },
      { name: "Sony Group", symbol: "6758", exchange: "TSE", currency: "JPY" }
    ],
    crypto: [
      { name: "Bitcoin", symbol: "BTC", exchange: "CRYPTO", currency: "USD" },
      { name: "Ethereum", symbol: "ETH", exchange: "CRYPTO", currency: "USD" }
    ]
  }
};

export default function HomePage() {
  const [locale, setLocale] = useState<Locale>("pt-BR");
  const [isOffline, setIsOffline] = useState(false);
  const [snapshot, setSnapshot] = useState<Snapshot>(fallbackSnapshot);
  const [watchlistItems, setWatchlistItems] = useState<ApiWatchlistItem[]>([]);
  const [lastViewedAssets, setLastViewedAssetsState] = useState<ViewedAsset[]>([]);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const readOnlyMode = isOffline;
  const msg = useMemo(() => t(locale), [locale]);

  useEffect(() => {
    const initial = getInitialLocale();
    setLocale(initial);

    const offline = typeof navigator !== "undefined" ? !navigator.onLine : false;
    setIsOffline(offline);

    getLastSnapshot<Snapshot>().then((cached) => {
      if (cached) setSnapshot(cached);
      else setLastSnapshot(fallbackSnapshot).catch(() => undefined);
    });

    getLastWatchlist<ApiWatchlistItem[]>().then((cached) => {
      if (cached) setWatchlistItems(cached);
    });

    getLastViewedAssets<ViewedAsset[]>().then((cached) => {
      if (cached) setLastViewedAssetsState(cached);
    });

    let authUnsubscribe: (() => void) | null = null;

    if (hasSupabaseConfig()) {
      const supabase = getSupabaseClient();

      supabase.auth.getSession().then(({ data }) => {
        setIsAuthenticated(Boolean(data.session?.access_token));
      });

      const { data: authListener } = supabase.auth.onAuthStateChange((_event, session) => {
        setIsAuthenticated(Boolean(session?.access_token));
      });
      authUnsubscribe = () => authListener.subscription.unsubscribe();
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

    fetchWatchlist()
      .then(async (response) => {
        setWatchlistItems(response.items ?? []);
        await setLastWatchlist(response.items ?? []);
        setStatusMessage("");
      })
      .catch(() => {
        setStatusMessage(locale === "pt-BR" ? "Falha ao carregar watchlist da API." : "Failed to load watchlist from API.");
      });
  }, [isOffline, isAuthenticated, locale]);

  function onLocaleChange(next: Locale) {
    if (readOnlyMode) return;
    setLocale(next);
    localStorage.setItem("locale", next);
  }

  async function refreshNow() {
    if (!navigator.onLine || !isAuthenticated || readOnlyMode) return;
    try {
      const refresh = await triggerRefresh();
      await setLastSnapshot(snapshot);
      setStatusMessage(refresh.message);
    } catch {
      setStatusMessage(locale === "pt-BR" ? "Falha ao atualizar snapshot." : "Failed to refresh snapshot.");
    }
  }

  async function loginAnonymously() {
    if (readOnlyMode) return;
    if (!hasSupabaseConfig()) {
      setStatusMessage(
        locale === "pt-BR"
          ? "Configure NEXT_PUBLIC_SUPABASE_URL e NEXT_PUBLIC_SUPABASE_ANON_KEY para autenticar."
          : "Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY to authenticate."
      );
      return;
    }

    const supabase = getSupabaseClient();
    const { error } = await supabase.auth.signInAnonymously();
    if (error) {
      setStatusMessage(
        locale === "pt-BR"
          ? "Não foi possível autenticar anonimamente. Verifique se Anonymous Auth está habilitado no Supabase."
          : "Unable to sign in anonymously. Ensure Anonymous Auth is enabled in Supabase."
      );
      return;
    }
    setStatusMessage(locale === "pt-BR" ? "Sessão ativa com sucesso." : "Session is active.");
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

  return (
    <main>
      <div className="toolbar">
        <h1>{msg.title}</h1>
        <button onClick={refreshNow} disabled={isOffline || !isAuthenticated}>
          {msg.refreshNow}
        </button>
      </div>

      <p className="muted">{msg.subtitle}</p>
      <OfflineBanner message={msg.offlineBanner} isOffline={isOffline} />
      {readOnlyMode ? <p className="muted">{msg.readOnlyMode}</p> : null}
      {statusMessage ? <p className="muted">{statusMessage}</p> : null}

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
      <Section title={msg.topBR} assets={snapshot.sections.br} onViewAsset={onViewAsset} viewAssetLabel={msg.viewAsset} readOnlyMode={readOnlyMode} />
      <Section title={msg.topUS} assets={snapshot.sections.us} onViewAsset={onViewAsset} viewAssetLabel={msg.viewAsset} readOnlyMode={readOnlyMode} />
      <Section title={msg.topJP} assets={snapshot.sections.jp} onViewAsset={onViewAsset} viewAssetLabel={msg.viewAsset} readOnlyMode={readOnlyMode} />
      <Section title={msg.topCrypto} assets={snapshot.sections.crypto} onViewAsset={onViewAsset} viewAssetLabel={msg.viewAsset} readOnlyMode={readOnlyMode} />
    </main>
  );
}

function Section({
  title,
  assets,
  onViewAsset,
  viewAssetLabel,
  readOnlyMode
}: {
  title: string;
  assets: Asset[];
  onViewAsset: (asset: Asset) => void;
  viewAssetLabel: string;
  readOnlyMode: boolean;
}) {
  return (
    <div className="card">
      <h3>{title}</h3>
      {assets.map((asset) => (
        <div key={`${asset.exchange}-${asset.symbol}`} style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem", alignItems: "center" }}>
          <p>
            {asset.name} <strong>{asset.symbol}</strong> • {asset.exchange} • {asset.currency}
          </p>
          <button onClick={() => onViewAsset(asset)} disabled={readOnlyMode}>{viewAssetLabel}</button>
        </div>
      ))}
    </div>
  );
}
