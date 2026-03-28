import { getSupabaseClient } from "@/lib/supabase";

// Use proxy path to avoid CORS issues; Next.js rewrites /api-proxy/* to the real API
const apiBaseUrl = "/api-proxy";

export type ApiWatchlistItem = {
  id: string;
  notes: string | null;
  created_at: string;
  asset: {
    id: string;
    name: string;
    symbol: string;
    exchange: string;
    currency: string;
    asset_class?: string;
    country_code?: string | null;
  };
  display: string;
};

export type ApiWatchlistResponse = {
  read_only: boolean;
  owner: {
    sub: string;
    role: string;
    email?: string;
  };
  watchlist: {
    id: string;
    name: string;
    is_default: boolean;
  };
  items: ApiWatchlistItem[];
};

export type WatchlistAssetInput = {
  symbol: string;
  exchange: string;
  notes?: string | null;
};

export type ApiRefreshResponse = {
  status: string;
  message: string;
  snapshot_id?: string;
  snapshot_asset_count?: number;
  data?: Record<string, unknown>;
};

export type ApiPriceHistoryPoint = {
  collected_at: string;
  price: number | null;
  valuation_brl: number | null;
  currency: string;
  fx_to_brl: number | null;
  data_quality: string | null;
};

export type ApiPriceHistoryResponse = {
  read_only: boolean;
  owner: {
    sub?: string;
    role?: string;
    email?: string;
  };
  asset: {
    id?: string;
    name?: string;
    symbol: string;
    exchange: string;
    currency?: string;
  };
  period: string;
  points: ApiPriceHistoryPoint[];
};

export type ApiWatchlistNewsItem = {
  symbol: string;
  asset_name: string;
  title: string;
  description: string | null;
  url: string;
  published_at: string;
  source: string | null;
  image: string | null;
};

export type ApiWatchlistNewsResponse = {
  read_only: boolean;
  owner: {
    sub?: string;
    role?: string;
    email?: string;
  };
  source: string;
  items: ApiWatchlistNewsItem[];
  message?: string;
};

export type ApiExchangeRate = {
  base_currency: string;
  quote_currency: string;
  rate: number;
  source?: string | null;
  collected_at: string;
};

export type ApiMarketOverviewResponse = {
  read_only: boolean;
  owner: {
    sub?: string;
    role?: string;
    email?: string;
  };
  summary: {
    asset_count: number;
    live_asset_count: number;
    fallback_asset_count: number;
    updated_at: string;
  };
  featured_assets: Array<{
    name: string;
    symbol: string;
    exchange: string;
    currency: string;
    asset_class?: string;
    country_code?: string | null;
    price: number | null;
    fx_to_brl?: number | null;
    valuation_brl: number | null;
    data_quality?: string | null;
  }>;
  currency_rates: ApiExchangeRate[];
  headline?: ApiWatchlistNewsItem | null;
};

async function getAccessToken(): Promise<string> {
  try {
    const supabase = getSupabaseClient();
    const { data, error } = await supabase.auth.getSession();
    if (error) throw error;
    const token = data?.session?.access_token;
    if (token && token.length > 10) {
      return token;
    }
    throw new Error("No active Supabase session");
  } catch (e) {
    // Dev mode fallback: return a fake token that API will accept in fallback mode
    console.warn("Using dev-token fallback", e);
    return "dev-token-" + Date.now();
  }
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await getAccessToken();
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API ${response.status}: ${body}`);
  }

  return (await response.json()) as T;
}

export async function fetchWatchlist(): Promise<ApiWatchlistResponse> {
  return apiRequest<ApiWatchlistResponse>("/watchlist", { method: "GET" });
}

export async function triggerRefresh(): Promise<ApiRefreshResponse> {
  return apiRequest<ApiRefreshResponse>("/refresh", { method: "POST", body: "{}" });
}

export async function addWatchlistItem(input: WatchlistAssetInput): Promise<ApiWatchlistResponse> {
  return apiRequest<ApiWatchlistResponse>("/watchlist/items", {
    method: "POST",
    body: JSON.stringify({
      symbol: input.symbol,
      exchange: input.exchange,
      notes: input.notes ?? null
    })
  });
}

export async function removeWatchlistItem(input: WatchlistAssetInput): Promise<ApiWatchlistResponse> {
  return apiRequest<ApiWatchlistResponse>("/watchlist/items", {
    method: "DELETE",
    body: JSON.stringify({
      symbol: input.symbol,
      exchange: input.exchange
    })
  });
}

export async function fetchPriceHistory(input: {
  symbol: string;
  exchange: string;
  period?: "30d" | "90d" | "1y" | "5y" | "custom";
  startDate?: string;
  endDate?: string;
  limit?: number;
}): Promise<ApiPriceHistoryResponse> {
  const params = new URLSearchParams();
  params.set("symbol", input.symbol);
  params.set("exchange", input.exchange);
  params.set("period", input.period ?? "1y");
  params.set("limit", String(input.limit ?? 1000));
  if (input.startDate) params.set("start_date", input.startDate);
  if (input.endDate) params.set("end_date", input.endDate);
  return apiRequest<ApiPriceHistoryResponse>(`/price-history?${params.toString()}`, { method: "GET" });
}

export async function fetchWatchlistNews(input?: {
  limit?: number;
  perAsset?: number;
  locale?: string;
}): Promise<ApiWatchlistNewsResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(input?.limit ?? 20));
  params.set("per_asset", String(input?.perAsset ?? 4));
  params.set("locale", input?.locale ?? "en");
  return apiRequest<ApiWatchlistNewsResponse>(`/watchlist/news?${params.toString()}`, { method: "GET" });
}

export async function fetchAssetNews(input: {
  symbol: string;
  exchange: string;
  locale?: string;
  limit?: number;
}): Promise<ApiWatchlistNewsResponse> {
  const params = new URLSearchParams();
  params.set("symbol", input.symbol);
  params.set("exchange", input.exchange);
  params.set("locale", input.locale ?? "en");
  params.set("limit", String(input.limit ?? 8));
  return apiRequest<ApiWatchlistNewsResponse>(`/asset/news?${params.toString()}`, { method: "GET" });
}

export async function fetchMarketOverview(input?: {
  locale?: string;
}): Promise<ApiMarketOverviewResponse> {
  const params = new URLSearchParams();
  params.set("locale", input?.locale ?? "en");
  return apiRequest<ApiMarketOverviewResponse>(`/market/overview?${params.toString()}`, { method: "GET" });
}
